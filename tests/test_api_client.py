import pytest
import os
from bot.mixamo_api_client import MixamoAPIClient
from unittest.mock import patch, MagicMock
import requests
from tenacity import wait_exponential
import json

def test_init_no_token_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        MixamoAPIClient()

def test_init_with_token_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    token_content = "mock_bearer_token"
    token_file = tmp_path / "mixamo_token.txt"
    token_file.write_text(token_content)
    client = MixamoAPIClient()
    assert client.token == token_content
    assert client.headers["Authorization"] == f"Bearer {token_content}"
    assert client.headers["X-Api-Key"] == "mixamo2"

def test_request_with_retry_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_req.return_value = mock_response
        result = client.request("GET", "http://example.com")
        assert result == {"success": True}
        mock_req.assert_called_once()

def test_request_with_retry_fail_then_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    client.request.retry.wait = wait_exponential(multiplier=0.01, min=0.01, max=0.1)
    with patch("requests.request") as mock_req:
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.RequestException()
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"success": True}
        mock_req.side_effect = [mock_fail, mock_success]
        result = client.request("GET", "http://example.com")
        assert result == {"success": True}
        assert mock_req.call_count == 2

def test_upload_character(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"character_id": "char_123"}
        mock_req.return_value = mock_response
        fbx_path = tmp_path / "model.fbx"
        fbx_path.write_text("dummy fbx content")
        char_id = client.upload_character(str(fbx_path))
        assert char_id == "char_123"
        assert mock_req.called
        method, url = mock_req.call_args[0]
        assert method == "POST"
        assert "characters" in url

def test_upload_character_uuid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_proc = MagicMock()
        mock_proc.status_code = 200
        mock_proc.json.return_value = {"status": "processing", "uuid": "uuid_123"}
        mock_comp = MagicMock()
        mock_comp.status_code = 200
        mock_comp.json.return_value = {"status": "completed", "job_result": "done"}
        mock_req.side_effect = [mock_proc, mock_comp]
        fbx_path = tmp_path / "model.fbx"
        fbx_path.write_text("dummy")
        with patch("time.sleep", return_value=None):
            char_id = client.upload_character(str(fbx_path))
            assert char_id == "uuid_123"
            assert mock_req.call_count == 2

def test_fetch_animation_catalog_caching(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    catalog_file = tmp_path / "animations_catalog.json"
    mock_data = {
        "results": [
            {"id": "anim_1", "name": "Walk"},
            {"id": "anim_2", "name": "Run"}
        ]
    }
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_req.return_value = mock_response
        
        # 1. Fetch from API
        catalog = client.fetch_animation_catalog(limit=2)
        assert len(catalog) == 2
        assert catalog[0]["name"] == "Walk"
        assert mock_req.call_count == 1
        
        # Verify file created
        assert catalog_file.exists()
        with open(catalog_file, "r") as f:
            cached_data = json.load(f)
            assert len(cached_data) == 2
            
        # 2. Fetch again, should use cache (mock_req should NOT be called again)
        catalog2 = client.fetch_animation_catalog(limit=2, force_refresh=False)
        assert len(catalog2) == 2
        assert mock_req.call_count == 1 # Still 1

def test_export_animation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job_123"}
        mock_req.return_value = mock_response
        gms_hash = {"params": "1,2,3"}
        job_id = client.export_animation("char_123", [gms_hash], "Walk")
        assert job_id == "job_123"
        assert mock_req.called
        method, url = mock_req.call_args[0]
        assert method == "POST"
        assert "animations/export" in url

def test_monitor_export_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_processing = MagicMock()
        mock_processing.status_code = 200
        mock_processing.json.return_value = {"status": "processing"}
        mock_completed = MagicMock()
        mock_completed.status_code = 200
        mock_completed.json.return_value = {"status": "completed", "job_result": "http://download.url"}
        mock_req.side_effect = [mock_processing, mock_completed]
        with patch("time.sleep", return_value=None):
            download_url = client.monitor_export_progress("char_123")
            assert download_url == "http://download.url"
            assert mock_req.call_count == 2

def test_download_animations_threaded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    anims = [{"id": "anim_1", "name": "Walk"}]
    output_dir = str(tmp_path / "output")
    with patch("requests.request") as mock_req, \
         patch("requests.get") as mock_get, \
         patch("time.sleep", return_value=None):
        mock_product = MagicMock()
        mock_product.status_code = 200
        mock_product.json.return_value = {"details": {"gms_hash": {"params": [[0, "val"]]}}}
        mock_export = MagicMock()
        mock_export.status_code = 200
        mock_export.json.return_value = {"job_id": "job_1"}
        mock_monitor = MagicMock()
        mock_monitor.status_code = 200
        mock_monitor.json.return_value = {"status": "completed", "job_result": "http://dl.url"}
        mock_req.side_effect = [mock_product, mock_export, mock_monitor]
        mock_dl = MagicMock()
        mock_dl.status_code = 200
        mock_dl.iter_content.return_value = [b"fbx_data"]
        mock_dl.headers = {"content-length": "8"}
        mock_get.return_value = mock_dl
        mock_callback = MagicMock()
        results = client.download_animations("char_123", anims, output_dir, progress_callback=mock_callback)
        assert results["anim_1"] is True
        assert os.path.exists(os.path.join(output_dir, "Walk_anim_1_char_123_with_skin.fbx"))
        mock_callback.assert_called_with(1, 1, "Walk", 0)

def test_export_animation_no_skin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job_123"}
        mock_req.return_value = mock_response
        gms_hash = {"params": "1,2,3"}
        client.export_animation("char_123", [gms_hash], "Walk", include_skin=False)
        args, kwargs = mock_req.call_args
        payload = kwargs["json"]
        assert payload["preferences"]["skin"] == "false"

def test_export_animation_inplace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job_123"}
        mock_req.return_value = mock_response
        
        gms_hash = {"params": "1,2,3"}
        client.export_animation("char_123", [gms_hash], "Walk", inplace=True)
        
        args, kwargs = mock_req.call_args
        payload = kwargs["json"]
        assert payload["gms_hash"][0]["inplace"] is True

def test_process_single_animation_inplace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    client = MixamoAPIClient()
    anims = [{"id": "anim_1", "name": "Walk"}]
    output_dir = str(tmp_path / "output")
    os.makedirs(output_dir, exist_ok=True)
    
    with patch("requests.request") as mock_req, \
         patch("requests.get") as mock_get, \
         patch("time.sleep", return_value=None):
        
        mock_product = MagicMock()
        mock_product.status_code = 200
        mock_product.json.return_value = {"details": {"gms_hash": {"params": [[0, "val"]]}}}
        mock_export = MagicMock()
        mock_export.status_code = 200
        mock_export.json.return_value = {"job_id": "job_1"}
        mock_monitor = MagicMock()
        mock_monitor.status_code = 200
        mock_monitor.json.return_value = {"status": "completed", "job_result": "http://dl.url"}
        mock_req.side_effect = [mock_product, mock_export, mock_monitor]
        
        mock_dl = MagicMock()
        mock_dl.status_code = 200
        mock_dl.iter_content.return_value = [b"fbx_data"]
        mock_get.return_value = mock_dl
        
        # Test with inplace=True
        client._process_single_animation("char_123", anims[0], output_dir, inplace=True)
        
        # Verify filename contains _inplace
        expected_filename = "Walk_inplace_anim_1_char_123_with_skin.fbx"
        assert os.path.exists(os.path.join(output_dir, expected_filename))
        
        # Verify export_animation was called with inplace=True
        # export_animation is the second call in the side_effect sequence for mock_req
        # but wait, mock_req is called inside export_animation which is called by _process_single_animation
        # Let's verify the payload of the export call
        args, kwargs = mock_req.call_args_list[1]
        payload = kwargs["json"]
        assert payload["gms_hash"][0]["inplace"] is True
