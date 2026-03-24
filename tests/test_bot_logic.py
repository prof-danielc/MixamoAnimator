import pytest
from unittest.mock import MagicMock, patch
from bot.mixamo_bot import MixamoBot

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
    
    # Mock page.goto and wait_for_url
    # First call to wait_for_url (check if already logged in) should fail (timeout)
    # Second call (after login steps) should succeed
    mock_playwright["page"].wait_for_url.side_effect = [Exception("Timeout"), None]
    
    success = bot.login("test@example.com", "password123")
    
    assert success is True
    mock_playwright["page"].goto.assert_called_with(bot.LOGIN_URL)
    mock_playwright["page"].fill.assert_any_call('input[name="username"]', "test@example.com")
    mock_playwright["page"].fill.assert_any_call('input[name="password"]', "password123")
    mock_playwright["context"].storage_state.assert_called_once_with(path=bot.SESSION_FILE)

def test_bot_login_already_logged_in(mock_playwright):
    bot = MixamoBot()
    bot.start()
    
    # First call to wait_for_url succeeds
    mock_playwright["page"].wait_for_url.return_value = None
    
    success = bot.login("test@example.com", "password123")
    
    assert success is True
    # Should not have filled username/password
    mock_playwright["page"].fill.assert_not_called()

def test_bot_upload_character(mock_playwright):
    bot = MixamoBot()
    bot.start()
    
    success = bot.upload_character("dummy.fbx")
    
    assert success is True
    mock_playwright["page"].goto.assert_called_with("https://www.mixamo.com/#/?page=1&query=&type=Character")
    mock_playwright["page"].set_input_files.assert_called_with('input[type="file"]', "dummy.fbx")
    # Check if "Next" buttons were clicked
    assert mock_playwright["page"].click.call_count >= 2

def test_bot_download_animations(mock_playwright):
    bot = MixamoBot()
    bot.start()
    
    # Mock download context manager
    mock_download_info = MagicMock()
    mock_download = MagicMock()
    mock_download.suggested_filename = "anim.fbx"
    mock_download_info.value = mock_download
    
    mock_playwright["page"].expect_download.return_value.__enter__.return_value = mock_download_info
    
    results = bot.download_animations(["anim1"], "output")
    
    assert results["anim1"] is True
    mock_playwright["page"].goto.assert_any_call("https://www.mixamo.com/#/?page=1&query=&type=Motion%2CCharacter&product_id=anim1")
    mock_download.save_as.assert_called_once()
