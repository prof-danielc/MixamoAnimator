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
