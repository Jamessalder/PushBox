import os
import shutil
from pathlib import Path
import requests
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from config import ConfigManager


APP_DIR = Path(os.getenv("LOCALAPPDATA")) / "PushBox"
STAGING_DIR = APP_DIR / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)


class BackupPage(QWidget):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager

        layout = QVBoxLayout(self)

        # Top buttons
        btn_layout = QHBoxLayout()
        self.new_folder_btn = QPushButton("+ New Folder")
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.setEnabled(False)
        self.upload_btn = QPushButton("Upload to GitHub")
        self.upload_btn.setEnabled(False)
        btn_layout.addWidget(self.new_folder_btn)
        btn_layout.addWidget(self.add_files_btn)
        btn_layout.addWidget(self.upload_btn)
        layout.addLayout(btn_layout)

        # Folder list
        layout.addWidget(QLabel("Folders (Staging / Repo)"))
        self.folder_list = QListWidget()
        layout.addWidget(self.folder_list)

        # File view
        layout.addWidget(QLabel("Files in Selected Folder"))
        self.file_view = QListWidget()
        layout.addWidget(self.file_view)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.setLayout(layout)

        # Internal state
        self.current_folder_name = None
        self.current_folder_path = None

        # Hooks
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        self.add_files_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder_to_github)
        self.folder_list.currentTextChanged.connect(self.on_folder_selected)

        # Load existing staging folders
        self.load_staging_folders()

    def create_new_folder(self):
        folder_name, ok = QFileDialog.getSaveFileName(self, "New Folder Name (virtual)")
        if not ok or not folder_name.strip():
            return
        folder_name = Path(folder_name).stem
        folder_path = STAGING_DIR / folder_name
        folder_path.mkdir(exist_ok=True)
        self.folder_list.addItem(folder_name)

    def add_files_to_folder(self):
        if not self.current_folder_path:
            QMessageBox.warning(self, "Select Folder", "Select a folder first.")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to add")
        if not files:
            return

        total_size = sum(os.path.getsize(f) for f in files)
        if total_size > 1_000_000_000:
            QMessageBox.warning(self, "Too large", "Files exceed 1GB limit.")
            return

        for f in files:
            shutil.copy(f, self.current_folder_path)
        self.load_folder_files(self.current_folder_path)
        self.upload_btn.setEnabled(True)

    def upload_folder_to_github(self):
        if not self.current_folder_name or not self.current_folder_path:
            QMessageBox.warning(self, "No folder", "Select a folder first.")
            return

        repo_name = self.current_folder_name

        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")
        if not username or not token:
            QMessageBox.warning(self, "Credentials Missing", "Set your GitHub username/token first.")
            return

        # Create GitHub repo
        url = "https://api.github.com/user/repos"
        headers = {"Authorization": f"token {token}"}
        resp = requests.post(url, headers=headers, json={"name": repo_name, "private": True})
        if resp.status_code not in (200, 201):
            QMessageBox.critical(self, "GitHub Error", f"Could not create repo:\n{resp.text}")
            return

        # Init git, commit, push
        try:
            subprocess.run(["git", "init"], cwd=self.current_folder_path, check=True)
            subprocess.run(["git", "remote", "add", "origin",
                            f"https://{username}:{token}@github.com/{username}/{repo_name}.git"],
                           cwd=self.current_folder_path, check=True)
            subprocess.run(["git", "add", "."], cwd=self.current_folder_path, check=True)
            subprocess.run(["git", "commit", "-m", "Backup from PushBox"], cwd=self.current_folder_path, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=self.current_folder_path, check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=self.current_folder_path, check=True)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Git Error", str(e))
            return

        QMessageBox.information(self, "Backup Complete", f"Folder uploaded as repo: {repo_name}")

        # Add to config local list
        repos = cfg.get("repos", [])
        if repo_name not in repos:
            repos.append(repo_name)
            cfg["repos"] = repos
            self.config_manager.save_config(cfg)

    def on_folder_selected(self, folder_name):
        if not folder_name:
            return
        self.current_folder_name = folder_name
        self.current_folder_path = STAGING_DIR / folder_name
        self.add_files_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.load_folder_files(self.current_folder_path)

    def load_folder_files(self, folder_path: Path):
        self.file_view.clear()
        for f in folder_path.iterdir():
            item = QListWidgetItem(f.name)
            if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                pixmap = QPixmap(str(f))
                item.setIcon(QIcon(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)))
            self.file_view.addItem(item)

    def load_staging_folders(self):
        for folder in STAGING_DIR.iterdir():
            if folder.is_dir():
                self.folder_list.addItem(folder.name)
