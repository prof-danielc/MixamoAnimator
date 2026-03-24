import os
import json
from pathlib import Path
import pytest
from config.settings import SettingsManager

def test_settings_manager_init_creates_default_config(tmp_path):
    config_path = tmp_path / "config.json"
    sm = SettingsManager(str(config_path))
    
    assert config_path.exists()
    assert sm.email == ""
    assert sm.password == ""
    
    with open(config_path, "r") as f:
        data = json.load(f)
        assert data["email"] == ""
        assert data["password"] == ""

def test_settings_manager_load_existing_config(tmp_path):
    config_path = tmp_path / "config.json"
    initial_data = {"email": "test@example.com", "password": "password123"}
    with open(config_path, "w") as f:
        json.dump(initial_data, f)
        
    sm = SettingsManager(str(config_path))
    assert sm.email == "test@example.com"
    assert sm.password == "password123"

def test_settings_manager_save(tmp_path):
    config_path = tmp_path / "config.json"
    sm = SettingsManager(str(config_path))
    
    sm.email = "new@example.com"
    sm.password = "newpassword"
    sm.save()
    
    with open(config_path, "r") as f:
        data = json.load(f)
        assert data["email"] == "new@example.com"
        assert data["password"] == "newpassword"

def test_settings_manager_corrupted_json(tmp_path):
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        f.write("invalid json")
        
    sm = SettingsManager(str(config_path))
    # Should fallback to defaults if corrupted
    assert sm.email == ""
    assert sm.password == ""
