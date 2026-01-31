import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "aussprachetrainer"
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default settings
        self.defaults = {
            "font_size": 14,
            "font_family": "Inter",
            "is_fullscreen": False,
            "window_state": "normal",
            "mode": "Offline",
            "dialect": "Germany (Standard)",
            "voice": "Default",
            "sidebar_width": 220,
            "history_panel_width": 350,
            "auto_switch_mode": True,
            "connection_mode": "Online",
            "online_voice": "de",
            "offline_voice": "de+m3",
            "window_width": 1100,
            "window_height": 700,
            "window_x": 100,
            "window_y": 100
        }
        self.settings = self.defaults.copy()
        self.load()

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"DEBUG: Failed to load config: {e}")

    def save(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"DEBUG: Failed to save config: {e}")

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()
