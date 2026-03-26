import pytest
import os
from unittest.mock import patch, MagicMock
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
        yield mock_pw

def test_mixamo_bot_api_integration(tmp_path, monkeypatch, mock_playwright):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mixamo_token.txt").write_text("token")
    
    # Mock MixamoAPIClient
    with patch("bot.mixamo_bot.MixamoAPIClient") as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.upload_character.return_value = "char_123"
        mock_api.fetch_animation_catalog.return_value = [{"id": "a1", "name": "Walk"}]
        mock_api.download_animations.return_value = {"a1": True}
        
        bot = MixamoBot()
        
        # Test character upload delegation
        assert bot.upload_character("model.fbx") is True
        assert bot.character_id == "char_123"
        mock_api.upload_character.assert_called_with("model.fbx")
        
        # Test catalog delegation
        catalog = bot.fetch_animation_catalog(limit=1)
        assert catalog == [{"id": "a1", "name": "Walk"}]
        mock_api.fetch_animation_catalog.assert_called_with(limit=1)
        
        # Test download delegation
        results = bot.download_animations([{"id": "a1", "name": "Walk"}], "out")
        assert results == {"a1": True}
        mock_api.download_animations.assert_called_with("char_123", [{"id": "a1", "name": "Walk"}], "out", progress_callback=None)

def test_mixamo_bot_token_extraction(tmp_path, monkeypatch, mock_playwright):
    monkeypatch.chdir(tmp_path)
    # No token file initially
    
    bot = MixamoBot()
    assert bot.api_client is None
    
    # Mock successful login and token in local storage
    # We need to mock the page.evaluate to return a token
    mock_page = mock_playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value
    mock_page.url = "https://www.mixamo.com/#/"
    mock_page.evaluate.return_value = "extracted_token"
    
    with patch("bot.mixamo_bot.MixamoAPIClient") as mock_api_class:
        # Simulate login success
        # In this test we just call a method that would be triggered after login
        bot.page = mock_page
        bot._context = MagicMock()
        
        # We need to manually call the part of login that saves the token for testing
        bot._extract_and_save_token()
        
        assert os.path.exists("mixamo_token.txt")
        assert open("mixamo_token.txt").read() == "extracted_token"
        assert bot.api_client is not None
        mock_api_class.assert_called_once_with(token_file="mixamo_token.txt")
