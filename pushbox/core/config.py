import os
import json


# ConfigManager
class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                return json.load(f)
        return {"onboarding_done": False, "token": ""}

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=2)
