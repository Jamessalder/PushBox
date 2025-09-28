from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QInputDialog, QScrollArea, QGridLayout, QApplication
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from pathlib import Path
import requests
import base64

class BackupPage(QWidget):
    """Manages virtual folders and files inside them, ready for GitHub upload"""
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QHBoxLayout(self)

        # Left: Virtual Folders
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Virtual Folders"))

        from PyQt6.QtWidgets import QListWidget
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

        # Right: Files in a scrollable grid
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("Files in Virtual Folder"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid_widget)

        right_v.addWidget(self.scroll)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right_v.addWidget(self.progress)

        layout.addLayout(left_v, stretch=1)
        layout.addLayout(right_v, stretch=2)
        self.setLayout(layout)

        # Internal state
        self.virtual_folders = {}  # folder_name -> list of Path objects
        self.current_folder = None

        # Hooks
        self.new_folder_btn.clicked.connect(self.create_virtual_folder)
        self.add_file_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder)
        self.folder_list.currentTextChanged.connect(self.on_folder_selected)

        self.load_folders_from_config()

    def load_folders_from_config(self):
        self.virtual_folders = {}
        saved = self.config_manager.data.get("virtual_folders", {})
        for folder, files in saved.items():
            self.virtual_folders[folder] = [Path(f) for f in files]
            self.folder_list.addItem(folder)

    def save_folders_to_config(self):
        serialized = {f: [str(p) for p in paths] for f, paths in self.virtual_folders.items()}
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
        # Clear previous grid items
        for i in reversed(range(self.grid_layout.count())):
            w = self.grid_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

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
        # Widget with thumbnail + filename
        file_widget = QWidget()
        vbox = QVBoxLayout(file_widget)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Thumbnail for images
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
            try:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)
                    lbl_img = QLabel()
                    lbl_img.setPixmap(pixmap)
                    lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    vbox.addWidget(lbl_img)
            except Exception as e:
                print(f"Error loading image {path}: {e}")

        lbl_name = QLabel(path.name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setWordWrap(True)
        vbox.addWidget(lbl_name)

        # Add to grid
        cols = 4
        pos = self.grid_layout.count()
        r, c = divmod(pos, cols)
        self.grid_layout.addWidget(file_widget, r, c)

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

        repo_name = self.current_folder
        headers = {"Authorization": f"token {token}"}

        # Create repo if missing
        repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
        r = requests.get(repo_url, headers=headers)
        if r.status_code == 404:
            payload = {"name": repo_name, "private": False}
            r_create = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
            if r_create.status_code not in (201, 200):
                QMessageBox.critical(self, "Error", f"Cannot create repo: {r_create.json()}")
                return

        total_size = sum(f.stat().st_size for f in files)
        uploaded = 0
        self.progress.setValue(0)

        for f in files:
            content = f.read_bytes()
            encoded = base64.b64encode(content).decode()
            url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{f.name}"
            payload = {"message": f"Add {f.name}", "content": encoded}
            r_file = requests.put(url, headers=headers, json=payload)
            if r_file.status_code not in (201, 200):
                QMessageBox.warning(self, "Upload failed", f"Failed to upload {f.name}: {r_file.json()}")
            uploaded += f.stat().st_size
            self.progress.setValue(int(uploaded / total_size * 100))
            QApplication.processEvents()

        self.progress.setValue(100)
        QMessageBox.information(self, "Backup complete", f"Virtual folder '{self.current_folder}' uploaded to GitHub.")
