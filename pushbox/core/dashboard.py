from pathlib import Path

import requests
from PyQt6.QtCore import QThreadPool, QUrl
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtWidgets import (
    QInputDialog, QScrollArea, QGridLayout
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QMessageBox, QFileDialog, QProgressBar, QApplication
)

from .signals.file_item import FileItemWidget
from .signals.thumb import ThumbnailWorker


class DashboardPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        self.thread_pool = QThreadPool()

        self.cache_dir = Path.home() / ".pushbox_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir = Path.home() / ".pushbox_cache" / "temp_files"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.file_widgets = {}

        layout = QHBoxLayout(self)

        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Your Backups"))

        self.folder_list = QListWidget()
        left_v.addWidget(self.folder_list)

        self.new_folder_btn = QPushButton("+ New Backup")
        self.add_file_btn = QPushButton("+ Add File(s)")
        self.upload_btn = QPushButton("Push Selected Folder to GitHub")

        self.add_file_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)

        left_v.addWidget(self.new_folder_btn)
        left_v.addWidget(self.add_file_btn)
        left_v.addWidget(self.upload_btn)

        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("Files"))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.grid_container)

        right_v.addWidget(self.scroll_area)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right_v.addWidget(self.progress)

        layout.addLayout(left_v, stretch=1)
        layout.addLayout(right_v, stretch=2)
        self.setLayout(layout)

        self.virtual_folders = {}
        self.current_folder = None

        self.folder_list.currentTextChanged.connect(self.on_folder_selected)
        self.new_folder_btn.clicked.connect(self.create_virtual_folder)
        self.add_file_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder)

        self.load_folders_from_config()

    def handle_open_request(self, file_path: Path):
        """
        Handles the open request by downloading the file to a temporary
        location and then opening it with the default application.
        """
        if not self.current_folder:
            return

        QMessageBox.information(self, "Opening File",
                                f"Now preparing to open '{file_path.name}' from GitHub...\nThe file will be downloaded to a temporary location first.")

        # Define the temporary path for the file
        temp_file_path = self.temp_dir / file_path.name

        # --- Re-use download logic ---
        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")
        repo_name = self.current_folder
        headers = {"Authorization": f"token {token}"}
        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path.name}"

        try:
            meta_response = requests.get(url, headers=headers)
            meta_response.raise_for_status()
            download_url = meta_response.json().get("download_url")

            if not download_url:
                QMessageBox.critical(self, "Error", "Could not find a download URL for this file.")
                return

            content_response = requests.get(download_url, headers=headers, stream=True)
            content_response.raise_for_status()

            with open(temp_file_path, 'wb') as f:
                for chunk in content_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # --- File is downloaded, now open it ---
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(temp_file_path)))

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Failed to Open", f"An error occurred while downloading the file:\n{e}")

        print(f"Download requested for {file_path.name} from repo {self.current_folder}")

        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")

        if not username or not token:
            QMessageBox.warning(self, "Auth Missing", "GitHub username & token are required.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save File As...", file_path.name)
        if not save_path:
            return

        repo_name = self.current_folder
        file_name = file_path.name
        headers = {"Authorization": f"token {token}"}
        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_name}"

        try:

            meta_response = requests.get(url, headers=headers)
            meta_response.raise_for_status()
            file_data = meta_response.json()
            download_url = file_data.get("download_url")

            if not download_url:
                QMessageBox.critical(self, "Download Error", "Could not find a download URL for this file.")
                return

            content_response = requests.get(download_url, headers=headers, stream=True)
            content_response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in content_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            QMessageBox.information(self, "Success", f"Successfully downloaded '{file_name}' to:\n{save_path}")

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Download Failed", f"An error occurred:\n{e}")

    def load_folders_from_config(self):
        raw_folders = self.config_manager.data.get("virtual_folders", {})
        self.virtual_folders = {}
        for folder, file_list in raw_folders.items():
            self.virtual_folders[folder] = [Path(f) for f in file_list]
            self.folder_list.addItem(folder)

    def save_folders_to_config(self):
        json_safe_folders = {}
        for folder, file_list in self.virtual_folders.items():
            json_safe_folders[folder] = [str(f) for f in file_list]
        self.config_manager.data["virtual_folders"] = json_safe_folders
        self.config_manager.save_config()

    def on_folder_selected(self, folder_name):
        self.current_folder = folder_name
        self.file_widgets.clear()

        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        if folder_name:
            self.add_file_btn.setEnabled(True)
            self.upload_btn.setEnabled(len(self.virtual_folders[folder_name]) > 0)
            for file_path in self.virtual_folders[folder_name]:
                self.add_file_item(file_path)
        else:
            self.add_file_btn.setEnabled(False)
            self.upload_btn.setEnabled(False)

    def add_files_to_folder(self):
        if not self.current_folder: return
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if not files: return
        for f in files:
            path = Path(f)
            if path not in self.virtual_folders[self.current_folder]:
                self.virtual_folders[self.current_folder].append(path)
                self.add_file_item(path)
        self.upload_btn.setEnabled(True)
        self.save_folders_to_config()

        try:
            self.upload_folder()
        except Exception as e:
            pass

    def add_file_item(self, path: Path):
        """Creates a placeholder widget and starts a background download for the thumbnail."""
        file_widget = FileItemWidget(path)

        file_widget.open_requested.connect(self.handle_open_request)
        file_widget.download_requested.connect(self.handle_download_request)

        self.file_widgets[path.name] = file_widget

        cols = 4
        pos = self.grid_layout.count()
        self.grid_layout.addWidget(file_widget, pos // cols, pos % cols)

        cached_thumb_path = self.cache_dir / f"{self.current_folder}_{path.name}"
        if cached_thumb_path.exists():
            pixmap = QPixmap(str(cached_thumb_path))
            file_widget.set_thumbnail(pixmap)
            return

        cfg = self.config_manager.load_config()
        worker = ThumbnailWorker(
            username=cfg.get("username"),
            token=cfg.get("token"),
            repo_name=self.current_folder,
            file_name=path.name
        )
        worker.signals.finished.connect(self.on_thumbnail_loaded)
        worker.signals.error.connect(lambda fname, err: print(f"Error loading {fname}: {err}"))
        self.thread_pool.start(worker)

    def on_thumbnail_loaded(self, filename: str, pixmap: QPixmap):
        """Slot to receive the downloaded thumbnail and update the UI."""

        if filename in self.file_widgets:
            self.file_widgets[filename].set_thumbnail(pixmap)

        if not pixmap.isNull():
            cached_thumb_path = self.cache_dir / f"{self.current_folder}_{filename}"
            pixmap.save(str(cached_thumb_path))

    def create_virtual_folder(self):
        folder_name, ok = QInputDialog.getText(self, "New Virtual Folder", "Enter folder name:")
        if not ok or not folder_name.strip(): return
        folder_name = folder_name.strip()
        if folder_name in self.virtual_folders:
            QMessageBox.warning(self, "Exists", "A folder with that name already exists.")
            return
        self.virtual_folders[folder_name] = []
        self.folder_list.addItem(folder_name)
        self.save_folders_to_config()

    def upload_folder(self):

        if not self.current_folder: return
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
        import base64
        from urllib.parse import quote
        repo_name = self.current_folder
        headers = {"Authorization": f"token {token}"}
        repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
        try:
            r = requests.get(repo_url, headers=headers)
            if r.status_code == 404:
                payload = {"name": repo_name, "private": False}
                r_create = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
                if r_create.status_code not in (200, 201):
                    QMessageBox.critical(self, "Error",
                                         f"Cannot create repo:\n{r_create.status_code}\n{r_create.json()}")
                    return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Exception checking/creating repo:\n{e}")
            return
        total_size = sum(f.stat().st_size for f in files)
        uploaded = 0
        self.progress.setValue(0)
        for f in files:
            try:
                content = f.read_bytes()
            except Exception as e:
                QMessageBox.warning(self, "Read Error", f"Cannot read {f.name}:\n{e}")
                continue
            encoded = base64.b64encode(content).decode()
            file_path_url = quote(f.name)
            url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path_url}"
            try:
                r_check = requests.get(url, headers=headers)
                payload = {"message": f"Add {f.name}", "content": encoded}
                if r_check.status_code == 200:
                    payload["sha"] = r_check.json()["sha"]
                r_file = requests.put(url, headers=headers, json=payload)
                if r_file.status_code not in (200, 201):
                    QMessageBox.warning(self, "Upload Failed", f"Failed to upload {f.name}:\n{r_file.json()}")
                    continue
            except Exception as e:
                QMessageBox.warning(self, "Network Error", f"Error uploading {f.name}:\n{e}")
                continue
            uploaded += f.stat().st_size
            perc = int(uploaded / total_size * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()
        self.progress.setValue(100)
        QMessageBox.information(self, "Backup Complete", f"Backed Up!")
