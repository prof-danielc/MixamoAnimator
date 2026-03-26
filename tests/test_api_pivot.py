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
