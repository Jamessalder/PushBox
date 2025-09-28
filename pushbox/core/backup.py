import os
import shutil
import subprocess
from pathlib import Path

import requests
from PyQt6.QtWidgets import QMessageBox


def start_backup(self):
    if not self.current_folder or not self.current_repo_name:
        QMessageBox.warning(self, "No folder", "Choose a folder first.")
        return

    cfg = self.config_manager.load_config()
    username = cfg.get("username")
    token = cfg.get("token")
    repo_name = self.current_repo_name

    # --- 1. staging dir ---
    base_dir = Path(os.getenv("LOCALAPPDATA")) / "PushBox" / "staging"
    staging_dir = base_dir / repo_name
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    shutil.copytree(self.current_folder, staging_dir)  # copy only contents

    # --- 2. create repo via GitHub API ---
    url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {token}"}
    resp = requests.post(url, headers=headers, json={"name": repo_name, "private": True})
    if resp.status_code not in (200, 201):
        QMessageBox.critical(self, "GitHub Error", f"Could not create repo:\n{resp.text}")
        return

    # --- 3. init git + push ---
    try:
        subprocess.run(["git", "init"], cwd=staging_dir, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin",
             f"https://{username}:{token}@github.com/{username}/{repo_name}.git"],
            cwd=staging_dir, check=True
        )
        subprocess.run(["git", "add", "."], cwd=staging_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial backup"], cwd=staging_dir, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=staging_dir, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=staging_dir, check=True)
    except subprocess.CalledProcessError as e:
        QMessageBox.critical(self, "Git Error", str(e))
        return

    # --- 4. update config ---
    repos = self.config_manager.data.get("repos", [])
    if repo_name not in repos:
        repos.append(repo_name)
        self.config_manager.data["repos"] = repos
        self.config_manager.save_config()

    QMessageBox.information(self, "Backup Complete", f"Folder backed up as repo {repo_name}")
