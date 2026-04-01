import pytest
from unittest.mock import MagicMock, patch
from bot.mixamo_bot import MixamoBot
import os

@pytest.fixture
def mock_playwright():
    with patch("bot.mixamo_bot.sync_playwright") as mock_sync:
        mock_pw = MagicMock()
        mock_sync.return_value.start.return_value = mock_pw
        
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        
        # Mock locator chain: locator().filter().first.count()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_locator.filter.return_value = mock_locator
        mock_locator.first = mock_locator
        mock_locator.count.return_value = 1
        
        # Mock evaluate to return a string (token)
        mock_page.evaluate.return_value = "mock_token"
        
        # Mock get_by_text chain
        mock_page.get_by_text.return_value = mock_locator
        
        # Mock storage_state to return a dict
        mock_context.storage_state.return_value = {}
        
        yield {
            "playwright": mock_pw,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page
        }

def test_bot_start(mock_playwright):
    bot = MixamoBot(headless=True)
    bot.start()
    
    mock_playwright["playwright"].chromium.launch.assert_called_once_with(headless=True)
    mock_playwright["browser"].new_context.assert_called_once()
    mock_playwright["context"].new_page.assert_called_once()

def test_bot_login_success(mock_playwright):
    bot = MixamoBot()
    bot.start()
    
    mock_playwright["page"].wait_for_url.side_effect = [Exception("Timeout"), None]
    
    success = bot.login("test@example.com", "password123")
    assert success is True

def test_bot_login_already_logged_in(mock_playwright):
    bot = MixamoBot()
    bot.start()
    
    mock_playwright["page"].wait_for_url.return_value = None
    
    success = bot.login("test@example.com", "password123")
    assert success is True

def test_bot_upload_character(tmp_path, monkeypatch, mock_playwright):
    monkeypatch.chdir(tmp_path)
    dummy_fbx = tmp_path / "dummy.fbx"
    dummy_fbx.write_text("dummy content")
    (tmp_path / "mixamo_token.txt").write_text("token")
    
    with patch("requests.request") as mock_req:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"character_id": "char_123"}
        mock_req.return_value = mock_response
        
        bot = MixamoBot()
        success = bot.upload_character(str(dummy_fbx))
        assert success is True
        assert bot.character_id == "char_123"

def test_bot_download_animations(tmp_path, monkeypatch, mock_playwright):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    
    bot = MixamoBot()
    bot.start()
    
    mock_download_info = MagicMock()
    mock_download = MagicMock()
    mock_download.suggested_filename = "anim.fbx"
    mock_download_info.value = mock_download
    
    mock_playwright["page"].expect_download.return_value.__enter__.return_value = mock_download_info        

    results = bot.download_animations([{"id": "a1", "name": "Walk"}], "output")
    assert "a1" in results
