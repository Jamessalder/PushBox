import os
from pathlib import Path
import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar, QMessageBox, QInputDialog, QApplication
)

class BackupPage(QWidget):
    """Manages virtual folders and files inside them, ready for GitHub upload"""
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QHBoxLayout(self)

        # Left: Virtual Folders
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Virtual Folders"))

        self.folder_list = QListWidget()
        left_v.addWidget(self.folder_list)

        self.new_folder_btn = QPushButton("+ New Virtual Folder")
        self.add_file_btn = QPushButton("+ Add File(s)")
        self.upload_btn = QPushButton("Push to GitHub")
        self.upload_btn.setEnabled(False)
        self.add_file_btn.setEnabled(False)

        left_v.addWidget(self.new_folder_btn)
        left_v.addWidget(self.add_file_btn)
        left_v.addWidget(self.upload_btn)

        # Right: Files inside selected virtual folder
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("Files in Virtual Folder"))

        self.file_list = QListWidget()
        right_v.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right_v.addWidget(self.progress)

        layout.addLayout(left_v, stretch=1)
        layout.addLayout(right_v, stretch=2)

        self.setLayout(layout)

        # Internal state
        self.virtual_folders = {}  # folder_name -> list of file paths
        self.current_folder = None

        # Hooks
        self.new_folder_btn.clicked.connect(self.create_virtual_folder)
        self.add_file_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder)
        self.folder_list.currentTextChanged.connect(self.on_folder_selected)

        # Load saved virtual folders (local cache)
        self.load_folders_from_config()

    def load_folders_from_config(self):
        self.virtual_folders = self.config_manager.data.get("virtual_folders", {})
        for folder in self.virtual_folders.keys():
            self.folder_list.addItem(folder)

    def save_folders_to_config(self):
        # Convert Path objects to strings before saving
        serialized = {}
        for folder, files in self.virtual_folders.items():
            serialized[folder] = [str(f) for f in files]
        self.config_manager.data["virtual_folders"] = serialized
        self.config_manager.save_config()

    def create_virtual_folder(self):
        folder_name, ok = QInputDialog.getText(self, "New Virtual Folder", "Folder name:")
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()
        if folder_name in self.virtual_folders:
            QMessageBox.information(self, "Exists", "Folder already exists.")
            return
        self.virtual_folders[folder_name] = []
        self.folder_list.addItem(folder_name)
        self.save_folders_to_config()

    def on_folder_selected(self, folder_name):
        self.current_folder = folder_name
        self.file_list.clear()
        if folder_name:
            self.add_file_btn.setEnabled(True)
            self.upload_btn.setEnabled(len(self.virtual_folders[folder_name]) > 0)
            for file_path in self.virtual_folders[folder_name]:
                self.add_file_item(file_path)
        else:
            self.add_file_btn.setEnabled(False)
            self.upload_btn.setEnabled(False)

    def add_files_to_folder(self):
        if not self.current_folder:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if not files:
            return
        for f in files:
            path = Path(f)
            if path not in self.virtual_folders[self.current_folder]:
                self.virtual_folders[self.current_folder].append(path)
                self.add_file_item(path)
        self.upload_btn.setEnabled(True)
        self.save_folders_to_config()

    def add_file_item(self, path):
        lw_item = QListWidgetItem(path.name)
        try:
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    lw_item.setIcon(QIcon(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)))
            else:
                lw_item.setIcon(self.style().standardIcon(QPushButton().style().SP_FileIcon))
        except Exception:
            lw_item.setIcon(self.style().standardIcon(QPushButton().style().SP_FileIcon))
        self.file_list.addItem(lw_item)

    def upload_folder(self):
        if not self.current_folder:
            return
        files = self.virtual_folders.get(self.current_folder, [])
        if not files:
            QMessageBox.information(self, "Empty", "No files to upload.")
            return

        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")
        if not username or not token:
            QMessageBox.warning(self, "Auth missing", "Enter GitHub username & token first.")
            return

        repo_name = self.current_folder  # using virtual folder name as repo
        headers = {"Authorization": f"token {token}"}

        # 1️⃣ Create repo if it doesn't exist
        repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
        r = requests.get(repo_url, headers=headers)
        if r.status_code == 404:
            # Create repo
            payload = {"name": repo_name, "private": False}
            r_create = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
            if r_create.status_code not in (201, 200):
                QMessageBox.critical(self, "Error", f"Cannot create repo: {r_create.json()}")
                return

        # 2️⃣ Upload files individually
        total_size = sum(f.stat().st_size for f in files)
        uploaded = 0
        self.progress.setValue(0)

        for f in files:
            content = f.read_bytes()
            import base64
            encoded = base64.b64encode(content).decode()
            file_path = f.name  # root of repo
            url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"
            payload = {"message": f"Add {file_path}", "content": encoded}
            r_file = requests.put(url, headers=headers, json=payload)
            if r_file.status_code not in (201, 200):
                QMessageBox.warning(self, "Upload failed", f"Failed to upload {file_path}: {r_file.json()}")
            uploaded += f.stat().st_size
            perc = int(uploaded / total_size * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()

        self.progress.setValue(100)
        QMessageBox.information(self, "Backup complete", f"Virtual folder '{self.current_folder}' uploaded to GitHub.")
