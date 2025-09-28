import os
import json


class ConfigManager:
    def __init__(self, app_name="PushBox"):
        self.config_dir = os.path.join(os.getenv("LOCALAPPDATA"), app_name)
        self.config_file = os.path.join(self.config_dir, "config.json")

        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        if not os.path.exists(self.config_file):
            self.save_config({"username": "", "token": ""})

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except Exception:
            return {"username": "", "token": ""}

    def save_config(self, data):
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=4)
