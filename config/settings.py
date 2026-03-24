import json
import os
from pathlib import Path
from typing import Optional


class SettingsManager:
    """
    Manages the configuration settings for the MixamoAnimator bot.
    Handles loading and saving to a config.json file in the project root.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.email: str = ""
        self.password: str = ""
        self.load()

    def load(self) -> None:
        """
        Loads settings from the config.json file.
        If the file does not exist, it initializes with empty values and saves it.
        """
        if not self.config_path.exists():
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.email = data.get("email", "")
                self.password = data.get("password", "")
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or unreadable, we keep defaults and potentially overwrite on next save
            pass

    def save(self) -> None:
        """
        Saves the current settings to the config.json file.
        """
        data = {
            "email": self.email,
            "password": self.password
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError:
            # Handle potential permission issues or other IO errors
            pass
