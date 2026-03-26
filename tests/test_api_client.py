import pytest
import os
from bot.mixamo_api_client import MixamoAPIClient

def test_init_no_token_file(tmp_path, monkeypatch):
    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)
    
    with pytest.raises(FileNotFoundError):
        MixamoAPIClient()

def test_init_with_token_file(tmp_path, monkeypatch):
    # Setup mock token file
    monkeypatch.chdir(tmp_path)
    token_content = "mock_bearer_token"
    token_file = tmp_path / "mixamo_token.txt"
    token_file.write_text(token_content)
    
    client = MixamoAPIClient()
    assert client.token == token_content
    assert client.headers["Authorization"] == f"Bearer {token_content}"
    assert client.headers["X-Api-Key"] == "mixamo2"

from unittest.mock import patch, MagicMock
import requests
from tenacity import wait_exponential

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
    
    # Speed up retries for tests
    client.request.retry.wait = wait_exponential(multiplier=0.01, min=0.01, max=0.1)
    
    with patch("requests.request") as mock_req:
        # First call fails, second succeeds
        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = requests.exceptions.RequestException()
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"success": True}
        
        mock_req.side_effect = [mock_fail, mock_success]
        
        result = client.request("GET", "http://example.com")
        assert result == {"success": True}
        assert mock_req.call_count == 2
