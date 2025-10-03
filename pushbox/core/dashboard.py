import base64
from pathlib import Path
from urllib.parse import quote
import requests

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QRunnable, QThreadPool, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QPushButton, QMessageBox, QFileDialog, QProgressBar, QApplication,
    QScrollArea, QGridLayout, QInputDialog, QMenu
)
from .signals.file_item import FileItemWidget
import keyring
import time
import threading

# Variables
username = None
token = None

def get_auth_info(event=None):
    global username, token

    token_enc = keyring.get_password("pushbox", "token")
    token_bytes = base64.b64decode(token_enc + "===")  # pad if missing
    token = token_bytes.decode("utf-8")
    username = keyring.get_password("pushbox", "username")

def wait_for_keyring(event=None):
    while not keyring.get_password("pushbox", "token"):
        print("Waiting for authentication info to be set in keyring...")
        time.sleep(1)
    get_auth_info()

thread = None

def wfk_thread(event=None):
    global thread

    if keyring.get_password("pushbox", "token"):
        get_auth_info()
    else:
        if thread is None or not thread.is_alive():
            thread = threading.Thread(target=wait_for_keyring)
            thread.daemon = True
            thread.start()

# ==============================================================================
# == HELPER WIDGETS
# ==============================================================================


class BackupItemWidget(QPushButton):
    """A custom button to visually represent a backup repository."""

    def __init__(self, repo_name, parent=None):
        display_name = repo_name.replace("backup-", "", 1).replace("-", " ").title()
        super().__init__(display_name, parent)
        self.repo_name = repo_name
        self.setMinimumSize(180, 120)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1c1c2b;
                border: 1px solid #44445a;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
                font-size: 16px;
                padding: 10px;
                white-space: normal;
            }
            QPushButton:hover {
                background-color: #2a2a3b;
            }
        """)


# ==============================================================================
# == WORKER & SIGNAL CLASSES FOR THREADING
# ==============================================================================

class WorkerSignals(QObject):
    """A generic signal holder to avoid repetition."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class ThumbnailSignals(QObject):
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str, str)


class CreateRepoWorker(QRunnable):
    def __init__(self, signals, username, token, repo_name):
        super().__init__()
        self.signals, self.username, self.token, self.repo_name = signals, username, token, repo_name

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            url = "https://api.github.com/user/repos"
            payload = {"name": self.repo_name, "private": True}
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.signals.finished.emit(self.repo_name)
        except Exception as e:
            self.signals.error.emit(str(e))


class RepoListWorker(QRunnable):
    def __init__(self, signals, username, token):
        super().__init__()
        self.signals, self.username, self.token = signals, username, token

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            url = "https://api.github.com/user/repos?per_page=100"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            repos = response.json()
            backup_repos = sorted([r['name'] for r in repos if r['name'].startswith("backup-")])
            self.signals.finished.emit(backup_repos)
        except Exception as e:
            self.signals.error.emit(str(e))


class FileListWorker(QRunnable):
    def __init__(self, signals, username, token, repo_name):
        super().__init__()
        self.signals, self.username, self.token, self.repo_name = signals, username, token, repo_name

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            files = response.json()
            self.signals.finished.emit(files)
        except Exception as e:
            self.signals.error.emit(str(e))


class ThumbnailWorker(QRunnable):
    def __init__(self, signals, username, token, repo_name, file_name):
        super().__init__()
        self.signals, self.username, self.token, self.repo_name, self.file_name = signals, username, token, repo_name, file_name

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            encoded_file = quote(self.file_name)
            # !!! BUG FIX: Was using self.token instead of self.repo_name !!!
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/{encoded_file}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            content = base64.b64decode(response.json()['content'])
            pixmap = QPixmap()
            pixmap.loadFromData(content)
            self.signals.finished.emit(self.file_name, pixmap)
        except Exception as e:
            self.signals.error.emit(self.file_name, str(e))


class FileDownloaderWorker(QRunnable):
    def __init__(self, signals, username, token, repo_name, file_name, save_path):
        super().__init__()
        self.signals, self.username, self.token = signals, username, token
        self.repo_name, self.file_name, self.save_path = repo_name, file_name, save_path

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            encoded_file = quote(self.file_name)
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/{encoded_file}"
            meta = requests.get(url, headers=headers)
            meta.raise_for_status()
            download_url = meta.json().get("download_url")
            if not download_url: raise ValueError("Download URL not found.")
            content = requests.get(download_url, headers=headers, stream=True)
            content.raise_for_status()
            with open(self.save_path, 'wb') as f:
                for chunk in content.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.signals.finished.emit(str(self.save_path))
        except Exception as e:
            self.signals.error.emit(str(e))


# ==============================================================================
# == MAIN DASHBOARD PAGE
# ==============================================================================

class DashboardPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.thread_pool = QThreadPool()
        self.cache_dir = Path.home() / ".pushbox_cache"
        self.temp_dir = self.cache_dir / "temp_files"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.file_widgets = {}
        self.virtual_folders = self.config_manager.data.get("virtual_folders", {})
        self.current_backup_repo = None
        self.stack = QStackedWidget()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stack)

        self.icon_map = {
            ".py": QPixmap("assets/icons/python.png"),
            ".md": QPixmap("assets/icons/markdown.png"),
            ".txt": QPixmap("assets/icons/text.png"),
        }
        self.generic_file_icon = QPixmap("pushbox/assets/icons/file.png")
        self.image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

        self.backups_view = self._create_backups_view()
        self.stack.addWidget(self.backups_view)
        self.files_view = self._create_files_view()
        self.stack.addWidget(self.files_view)
        self.load_backups_from_github()

    def _create_backups_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        header = QHBoxLayout()
        header.addWidget(QLabel("Your Backups"))
        header.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_backups_from_github)
        header.addWidget(refresh_btn)
        self.new_backup_btn = QPushButton("+ New Backup")
        self.new_backup_btn.clicked.connect(self.create_new_backup)
        header.addWidget(self.new_backup_btn)
        reset_auth_btn = QPushButton("🔄️ Reset Authentication")
        reset_auth_btn.clicked.connect(self.reset_auth)
        header.addWidget(reset_auth_btn)
        layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.backups_grid_widget = QWidget()
        self.backups_grid_layout = QGridLayout(self.backups_grid_widget)
        self.backups_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.backups_grid_widget)
        layout.addWidget(scroll)
        return container
    
    def reset_auth(self):
        confirm = QMessageBox.question(self, "Confirm Reset", "Are you sure you want to reset authentication? This will quit the program; you will need to reopen the application to re-authenticate.")
        if confirm == QMessageBox.StandardButton.Yes:
            keyring.delete_password("pushbox", "token")
            keyring.delete_password("pushbox", "username")
            self.config_manager.data["onboarding_done"] = False
            self.config_manager.save_config()
            QApplication.quit()

    def _create_files_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        header = QHBoxLayout()
        back_btn = QPushButton("← Back to All Backups")
        back_btn.clicked.connect(self.show_backups_view)
        header.addWidget(back_btn)
        header.addStretch()
        self.add_file_btn = QPushButton("+ Add File(s)")
        self.upload_btn = QPushButton("Push Changes to GitHub")
        self.add_file_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder)
        header.addWidget(self.add_file_btn)
        header.addWidget(self.upload_btn)
        layout.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.files_grid_widget = QWidget()
        self.files_grid_layout = QGridLayout(self.files_grid_widget)
        self.files_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.files_grid_widget)
        layout.addWidget(scroll)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        return container

    def show_backups_view(self):
        self.stack.setCurrentWidget(self.backups_view)
        self.load_backups_from_github()

    def show_files_view(self, repo_name):
        self.current_backup_repo = repo_name
        self.file_widgets.clear()
        for i in reversed(range(self.files_grid_layout.count())):
            self.files_grid_layout.itemAt(i).widget().setParent(None)
        self.stack.setCurrentWidget(self.files_view)
        self.load_files_from_github(repo_name)

    def load_backups_from_github(self):
        cfg = self.config_manager.load_config()
        wfk_thread()
        signals = WorkerSignals()
        signals.finished.connect(self.on_backups_loaded)
        signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Could not fetch backups:\n{e}"))
        worker = RepoListWorker(signals, username, token)
        self.thread_pool.start(worker)

    def on_backups_loaded(self, repo_names):
        for i in reversed(range(self.backups_grid_layout.count())):
            self.backups_grid_layout.itemAt(i).widget().setParent(None)
        cols = 3
        for i, name in enumerate(repo_names):
            widget = BackupItemWidget(name)
            widget.clicked.connect(lambda checked, r=name: self.show_files_view(r))
            self.backups_grid_layout.addWidget(widget, i // cols, i % cols)

    def load_files_from_github(self, repo_name):
        cfg = self.config_manager.load_config()
        wfk_thread()
        signals = WorkerSignals()
        signals.finished.connect(self.on_files_loaded)
        signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Could not fetch files:\n{e}"))
        worker = FileListWorker(signals, username, token, repo_name)
        self.thread_pool.start(worker)

    def on_files_loaded(self, files_info):
        for file_info in files_info:
            if file_info['type'] == 'file':
                self._add_file_item(Path(file_info['name']), is_local=False)
        local_files = self.virtual_folders.get(self.current_backup_repo, [])
        remote_files = {f['name'] for f in files_info}
        for local_path_str in local_files:
            local_path = Path(local_path_str)
            if local_path.name not in remote_files:
                self._add_file_item(local_path, is_local=True)

    def _add_file_item(self, path: Path, is_local: bool):

        file_suffix = path.suffix.lower()
        default_pixmap = None
        should_fetch_thumb = False

        self.generic_file_icon = QPixmap("assets/icons/file.png")
        self.image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        self.doc_ext = {".pdf"}

        file_widget = FileItemWidget(path, is_local)
        file_widget.open_requested.connect(self.handle_open_request)
        file_widget.download_requested.connect(self.handle_download_request)
        self.file_widgets[path.name] = file_widget
        cols = 4
        pos = self.files_grid_layout.count()

        if file_suffix in self.image_extensions or self.doc_ext:
            # It's an image, so we should fetch its unique thumbnail
            should_fetch_thumb = True
            default_pixmap = None  # No default, show "Loading..."
        elif file_suffix in self.icon_map:
            # It's a known file type with a default icon
            default_pixmap = self.icon_map[file_suffix]
        else:
            # It's an unknown file type, use the generic icon
            default_pixmap = self.generic_file_icon

        self.files_grid_layout.addWidget(file_widget, pos // cols, pos % cols)

        if should_fetch_thumb and not is_local:
            cached_thumb_path = self.cache_dir / f"{self.current_backup_repo}_{path.name}"
            if cached_thumb_path.exists():
                file_widget.set_thumbnail(QPixmap(str(cached_thumb_path)))
                return
            cfg = self.config_manager.load_config()
            wfk_thread()
            signals = ThumbnailSignals()
            signals.finished.connect(self.on_thumbnail_loaded)
            signals.error.connect(lambda fname, err: print(f"Thumb error {fname}: {err}"))
            global username, token
            worker = ThumbnailWorker(signals, username, token, self.current_backup_repo,
                                     path.name)
            self.thread_pool.start(worker)

    def on_thumbnail_loaded(self, filename: str, pixmap: QPixmap):
        if filename in self.file_widgets:
            self.file_widgets[filename].set_thumbnail(pixmap)
        if not pixmap.isNull():
            cached_path = self.cache_dir / f"{self.current_backup_repo}_{filename}"
            pixmap.save(str(cached_path))

    def create_new_backup(self):
        name, ok = QInputDialog.getText(self, "New Backup", "Enter a name for the new backup:")
        if ok and name:
            repo_name = "backup-" + name.lower().replace(" ", "-")
            cfg = self.config_manager.load_config()
            wfk_thread()
            signals = WorkerSignals()
            signals.finished.connect(self.on_repo_created)
            signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Could not create repo:\n{e}"))
            worker = CreateRepoWorker(signals, username, token, repo_name)
            self.thread_pool.start(worker)

    def on_repo_created(self, repo_name):
        QMessageBox.information(self, "Success", f"Repository '{repo_name}' created on GitHub.")
        self.load_backups_from_github()

    def add_files_to_folder(self):
        if not self.current_backup_repo: return
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Add")
        if not files: return
        if self.current_backup_repo not in self.virtual_folders:
            self.virtual_folders[self.current_backup_repo] = []
        new_files_added = False
        for f in files:
            if f not in self.virtual_folders[self.current_backup_repo]:
                self.virtual_folders[self.current_backup_repo].append(f)
                self._add_file_item(Path(f), is_local=True)
                new_files_added = True
        if new_files_added:
            self.save_virtual_folders()
            QMessageBox.information(self, "Files Added", "Files added locally. Click 'Push Changes' to upload them.")

    def save_virtual_folders(self):
        self.config_manager.data["virtual_folders"] = self.virtual_folders
        self.config_manager.save_config()

    def handle_open_request(self, file_path: Path):
        if file_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
            return
        save_path = self.temp_dir / file_path.name
        cfg = self.config_manager.load_config()
        wfk_thread()
        signals = WorkerSignals()
        signals.finished.connect(lambda path: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}"))
        worker = FileDownloaderWorker(signals, username, token, "token", self.current_backup_repo,
                                      file_path.name, save_path)
        self.thread_pool.start(worker)

    def handle_download_request(self, file_path: Path):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File As...", file_path.name)
        if not save_path: return
        cfg = self.config_manager.load_config()
        wfk_thread()
        signals = WorkerSignals()
        signals.finished.connect(lambda path: QMessageBox.information(self, "Success", f"File saved to {path}"))
        signals.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Failed to download file:\n{e}"))
        worker = FileDownloaderWorker(signals, username, token, "token", self.current_backup_repo,
                                      file_path.name, Path(save_path))
        self.thread_pool.start(worker)

    def upload_folder(self):
        if not self.current_backup_repo: return
        local_files_str = self.virtual_folders.get(self.current_backup_repo, [])
        if not local_files_str:
            QMessageBox.information(self, "No Changes", "No new local files to upload.")
            return
        # This can be refactored into its own UploaderWorker class for better UI responsiveness
        cfg = self.config_manager.load_config()
        wfk_thread()
        global username, token
        repo_name = self.current_backup_repo
        headers = {"Authorization": f"token {token}"}
        files_to_upload = [Path(p) for p in local_files_str]
        total_size = sum(p.stat().st_size for p in files_to_upload if p.exists())
        uploaded_size = 0
        self.progress.setValue(0)
        for file_path in files_to_upload:
            if not file_path.exists(): continue
            try:
                content = file_path.read_bytes()
                encoded_content = base64.b64encode(content).decode()
                encoded_name = quote(file_path.name)
                url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{encoded_name}"
                sha = None
                r_check = requests.get(url, headers=headers)
                if r_check.status_code == 200: sha = r_check.json()['sha']
                payload = {"message": f"Update {file_path.name}", "content": encoded_content}
                if sha: payload['sha'] = sha
                r_put = requests.put(url, headers=headers, json=payload)
                r_put.raise_for_status()
                uploaded_size += file_path.stat().st_size
                self.progress.setValue(int((uploaded_size / total_size) * 100))
                QApplication.processEvents()
            except Exception as e:
                QMessageBox.warning(self, "Upload Failed", f"Failed to upload {file_path.name}:\n{e}")
                self.progress.setValue(0)
                return
        self.progress.setValue(100)
        QMessageBox.information(self, "Upload Complete", "All new files have been pushed to GitHub.")
        self.virtual_folders[self.current_backup_repo] = []
        self.save_virtual_folders()
        self.show_files_view(self.current_backup_repo)
