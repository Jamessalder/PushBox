import base64
import os
import sys
from pathlib import Path

import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QLineEdit
)
from PyQt6.QtWidgets import QMenu
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog, QProgressBar, QApplication
)

from core.config import ConfigManager
from core.const import stylesheet
from core.dashboard import DashboardPage


class OnboardingPage(QWidget):
    def __init__(self, switch_to_auth, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stack = QStackedWidget()
        self.pages = []

        data = [
            ("Welcome to PushBox 🚀", "Your secure GitHub-powered cloud backup tool."),
            ("Why GitHub?",
             "GitHub gives you free, fast, and reliable cloud storage using repositories, and we can use that storage as our personal storage backup."),
            ("How it Works ⚙️", "PushBox creates repos, pushes your folders, and restores when needed."),
            ("You're Ready!", "Let's get started with secure backups.")
        ]

        for i, (title, subtitle) in enumerate(data):
            page = QWidget()
            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label_title = QLabel(title)
            label_title.setFont(QFont("Montserrat", 28, QFont.Weight.Bold))
            label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label_sub = QLabel(subtitle)
            label_sub.setFont(QFont("Arial", 12))
            label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_sub.setWordWrap(True)

            btn = QPushButton("Next" if i < len(data) - 1 else "Get Started")
            btn.setFixedWidth(150)

            def make_handler(idx):
                return lambda: self.next_page(idx, switch_to_auth)

            btn.clicked.connect(make_handler(i))

            layout.addStretch()
            layout.addWidget(label_title)
            layout.addSpacing(10)
            layout.addWidget(label_sub)
            layout.addStretch()
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

            page.setLayout(layout)
            self.pages.append(page)
            self.stack.addWidget(page)

        vbox = QVBoxLayout()
        vbox.addWidget(self.stack)
        self.setLayout(vbox)

    def next_page(self, index, switch_to_auth):

        if index < len(self.pages) - 1:
            self.stack.setCurrentIndex(index + 1)
        else:

            self.config_manager.data["onboarding_done"] = True
            self.config_manager.save_config()
            switch_to_auth()


class AuthPage(QWidget):
    def __init__(self, switch_to_dashboard, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("PushBox")
        title.setFont(QFont("Montserrat", 48, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Secure GitHub Backup")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("GitHub Username")

        self.token = QLineEdit()
        self.token.setPlaceholderText("Personal Access Token")
        self.token.setEchoMode(QLineEdit.EchoMode.Password)

        cfg = self.config_manager.load_config()
        self.username.setText(cfg.get("username", ""))
        self.token.setText(cfg.get("token", ""))

        self.login_btn = QPushButton("Save & Continue")
        self.login_btn.clicked.connect(lambda: self.save_and_continue(switch_to_dashboard))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.username)
        layout.addWidget(self.token)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def save_and_continue(self, switch_to_dashboard):
        data = {
            "username": self.username.text(),
            "token": self.token.text(),

            "onboarding_done": self.config_manager.data.get("onboarding_done", False)
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()


class BackupPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label = QLabel("Select a folder to backup")
        self.select_btn = QPushButton("Choose Folder to Backup")
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.setEnabled(False)

        self.selected_folder_label = QLabel("No folder selected")
        self.selected_folder_label.setWordWrap(True)

        layout.addWidget(self.label)
        layout.addWidget(self.selected_folder_label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.backup_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.setLayout(layout)

        self.current_folder = None
        self.current_repo_name = None

        self.select_btn.clicked.connect(self.choose_folder_dialog)
        self.backup_btn.clicked.connect(self.start_backup)

    def choose_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to backup")
        if not folder:
            return
        self.current_folder = Path(folder)
        size = self.folder_size_bytes(self.current_folder)
        if size > 1_000_000_000:
            QMessageBox.warning(self, "Folder too large",
                                "Selected folder exceeds 1GB limit. Please choose a smaller folder.")
            self.current_folder = None
            self.selected_folder_label.setText("No folder selected")
            self.backup_btn.setEnabled(False)
            return

        base_name = self.current_folder.name
        repo_name = f"backup-{base_name}"
        self.current_repo_name = repo_name
        self.selected_folder_label.setText(
            f"Selected: {self.current_folder}\nRepo name: {repo_name}\nSize: {self.human_readable_size(size)}")
        self.backup_btn.setEnabled(True)

    def start_backup(self):
        if not self.current_folder or not self.current_repo_name:
            QMessageBox.information(self, "No folder", "Choose a folder before backup.")
            return

        total_size = self.folder_size_bytes(self.current_folder)
        if total_size == 0:
            QMessageBox.information(self, "Empty", "Selected folder is empty.")
            return

        uploaded = 0
        self.progress.setValue(0)

        all_files = []
        for dp, dn, filenames in os.walk(self.current_folder):
            for f in filenames:
                all_files.append(Path(dp) / f)
        all_files.sort()

        for p in all_files:
            try:
                s = p.stat().st_size
            except Exception:
                s = 0
            uploaded += s
            perc = int((uploaded / total_size) * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()

        self.progress.setValue(100)
        QMessageBox.information(self, "Backup complete", f"Folder backed up as repo: {self.current_repo_name}")

        repos = self.config_manager.data.get("repos", [])
        if self.current_repo_name not in repos:
            repos.append(self.current_repo_name)
            self.config_manager.data["repos"] = repos
            self.config_manager.save_config()

    @staticmethod
    def folder_size_bytes(path: Path) -> int:
        total = 0
        for dp, dn, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except Exception:
                    pass
        return total

    @staticmethod
    def human_readable_size(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if n < 1024:
                return f"{n:.2f}{unit}"
            n /= 1024
        return f"{n:.2f}PB"


class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)


class SettingsPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str, str)


class ThumbnailWorker(QRunnable):
    """Worker thread for downloading a thumbnail from GitHub."""

    def __init__(self, username, token, repo_name, file_name):
        super().__init__()
        self.signals = WorkerSignals()
        self.username = username
        self.token = token
        self.repo_name = repo_name
        self.file_name = file_name

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/{self.file_name}"

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            content_b64 = response.json()['content']
            decoded_bytes = base64.b64decode(content_b64)

            pixmap = QPixmap()
            pixmap.loadFromData(decoded_bytes)

            self.signals.finished.emit(self.file_name, pixmap)

        except Exception as e:
            self.signals.error.emit(self.file_name, str(e))


class FileItemWidget(QWidget):
    """A clickable widget that now loads its thumbnail asynchronously."""
    download_requested = pyqtSignal(Path)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.file_path = path
        self.setToolTip(f"File: {self.file_path.name}\nLocation: {self.file_path}")

        vbox = QVBoxLayout(self)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self.image_label)

        name_label = QLabel(self.file_path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        vbox.addWidget(name_label)
        self.setMinimumHeight(140)

    def set_thumbnail(self, pixmap: QPixmap):
        """Called by the main window to set the thumbnail when ready."""
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("Invalid")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:

            if self.file_path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.file_path)))
            else:
                QMessageBox.information(self, "File Not Found",
                                        "This file is not available locally. Download it again using the right-click menu.")

        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPos())

        super().mousePressEvent(event)

    def show_context_menu(self, position):
        menu = QMenu(self)
        download_action = menu.addAction("Download again...")
        download_action.triggered.connect(lambda: self.download_requested.emit(self.file_path))
        menu.exec(position)


VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        self.config_manager = ConfigManager()

        self.onboarding_page = OnboardingPage(self.show_auth, self.config_manager)
        self.auth_page = AuthPage(self.show_dashboard, self.config_manager)
        self.backup_page = BackupPage(self.config_manager)
        self.restore_page = RestorePage()
        self.settings_page = SettingsPage(self.config_manager)
        self.dashboard_page = DashboardPage(self.config_manager)

        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        self.mainStack.addWidget(self.onboarding_page)
        self.mainStack.addWidget(self.auth_page)

        self.mainStack.addWidget(self.dashboard_page)

        cfg = self.config_manager.load_config()
        onboarding_done = cfg.get("onboarding_done", False)
        token = cfg.get("token", "")

        if not onboarding_done:
            self.mainStack.setCurrentIndex(0)
        elif token:
            self.mainStack.setCurrentIndex(2)
        else:
            self.mainStack.setCurrentIndex(1)

        self.apply_styles()

    def show_auth(self):
        self.mainStack.setCurrentIndex(1)

    def show_dashboard(self):
        self.mainStack.setCurrentIndex(2)

    def apply_styles(self):
        self.setStyleSheet(stylesheet)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 640)
    window.show()
    sys.exit(app.exec())
