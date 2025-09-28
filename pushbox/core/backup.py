import os
import base64
from pathlib import Path
import requests
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, \
    QProgressBar, QMessageBox, QApplication
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

        # Buttons
        self.new_folder_btn = QPushButton("+ New Folder")
        self.add_files_btn = QPushButton("Add Files")
        self.upload_btn = QPushButton("Upload Folder")
        self.add_files_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        layout.addWidget(self.new_folder_btn)
        layout.addWidget(self.add_files_btn)
        layout.addWidget(self.upload_btn)

        # Folder & file views
        layout.addWidget(QLabel("Folders (Staging)"))
        self.folder_list = QListWidget()
        layout.addWidget(self.folder_list)
        layout.addWidget(QLabel("Files in Selected Folder"))
        self.file_view = QListWidget()
        layout.addWidget(self.file_view)

        # Progress bar
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.setLayout(layout)

        self.current_folder_name = None
        self.current_folder_path = None

        # Hooks
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        self.add_files_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder_to_github)
        self.folder_list.currentTextChanged.connect(self.on_folder_selected)

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
        for f in files:
            dest = self.current_folder_path / Path(f).name
            if not dest.exists():
                dest.write_bytes(Path(f).read_bytes())
        self.load_folder_files(self.current_folder_path)
        self.upload_btn.setEnabled(True)

    def upload_folder_to_github(self):
        if not self.current_folder_name or not self.current_folder_path:
            QMessageBox.warning(self, "No folder", "Select a folder first.")
            return

        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")
        if not username or not token:
            QMessageBox.warning(self, "Credentials Missing", "Set GitHub username/token first.")
            return

        repo_name = self.current_folder_name

        # Create GitHub repo
        url = "https://api.github.com/user/repos"
        headers = {"Authorization": f"token {token}"}
        resp = requests.post(url, headers=headers, json={"name": repo_name, "private": True})
        if resp.status_code not in (200, 201):
            QMessageBox.critical(self, "GitHub Error", f"Could not create repo:\n{resp.text}")
            return

        # Upload files individually
        files = list(self.current_folder_path.iterdir())
        total = len(files)
        for i, f in enumerate(files, 1):
            with open(f, "rb") as fp:
                content = base64.b64encode(fp.read()).decode()
            path = f.name
            api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
            r = requests.put(api_url, headers=headers, json={"message": "PushBox backup", "content": content})
            if r.status_code not in (200, 201):
                QMessageBox.warning(self, "Upload Failed", f"Failed to upload {f.name}")
            self.progress.setValue(int(i/total*100))
            QApplication.processEvents()
        self.progress.setValue(100)
        QMessageBox.information(self, "Backup Complete", f"Folder uploaded as repo: {repo_name}")

        # Update local config
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
