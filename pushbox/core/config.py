import json
import os
from pathlib import Path


class ConfigManager:
    def __init__(self, config_file="config.json"):
        # Path under LocalAppData
        base_dir = Path(os.getenv("LOCALAPPDATA", ".")) / "PushBox"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = base_dir / config_file

        # in-memory data
        self.data = {}

        # Load existing or create defaults
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                # corrupted/empty file → reset
                self.data = self.default_config()
                self.save_config()
        else:
            self.data = self.default_config()
            self.save_config()

    def default_config(self):
        return {
            "onboarding_done": False,
            "username": "",
            "token": "",
            "repos": []
        }

    def load_config(self):
        return self.data

    def save_config(self, data=None):
        if data:
            self.data = data
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
