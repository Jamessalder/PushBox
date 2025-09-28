import os
import sys
from pathlib import Path

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QListWidget, QInputDialog, QProgressBar, QMessageBox,
    QFileDialog
)
from PyQt6.QtWidgets import QListWidgetItem

from core.config import ConfigManager
from core.const import stylesheet


class OnboardingPage(QWidget):
    def __init__(self, switch_to_auth, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stack = QStackedWidget()
        self.pages = []

        # Define onboarding content (title, subtitle)
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

            # capture i in lambda properly
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
        # if not last page, show next
        if index < len(self.pages) - 1:
            self.stack.setCurrentIndex(index + 1)
        else:
            # mark onboarding done in config and save
            self.config_manager.data["onboarding_done"] = True
            self.config_manager.save_config()
            switch_to_auth()


# ---------- Auth ----------
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

        # Load saved creds if available
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
            # preserve onboarding flag if previously set
            "onboarding_done": self.config_manager.data.get("onboarding_done", False)
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()


# ---------- Backup ----------
class BackupPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label = QLabel("Select a folder to backup")
        self.select_btn = QPushButton("Choose Folder to Backup")
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.setEnabled(False)  # enabled after folder chosen

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

        # internal state
        self.current_folder = None
        self.current_repo_name = None

        # hooks
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

        # propose repo name derived from folder name and timestamp
        base_name = self.current_folder.name
        repo_name = f"backup-{base_name}"
        self.current_repo_name = repo_name
        self.selected_folder_label.setText(f"Selected: {self.current_folder}\nRepo name: {repo_name}\nSize: {self.human_readable_size(size)}")
        self.backup_btn.setEnabled(True)

    def start_backup(self):
        if not self.current_folder or not self.current_repo_name:
            QMessageBox.information(self, "No folder", "Choose a folder before backup.")
            return

        # TODO: create repo on GitHub using token and username from config_manager
        # TODO: initialize local temporary repo or use git to add/commit files, then push to created repo
        # For now simulate upload progress by iterating files and updating progress bar

        total_size = self.folder_size_bytes(self.current_folder)
        if total_size == 0:
            QMessageBox.information(self, "Empty", "Selected folder is empty.")
            return

        uploaded = 0
        self.progress.setValue(0)
        # Walk files in sorted order to make deterministic progress
        all_files = []
        for dp, dn, filenames in os.walk(self.current_folder):
            for f in filenames:
                all_files.append(Path(dp) / f)
        all_files.sort()

        # simulate uploading each file (replace with actual push logic)
        for p in all_files:
            try:
                s = p.stat().st_size
            except Exception:
                s = 0
            uploaded += s
            perc = int((uploaded / total_size) * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()  # keep UI responsive

        self.progress.setValue(100)
        QMessageBox.information(self, "Backup complete", f"Folder backed up as repo: {self.current_repo_name}")

        # Add to repo list stored in config (local cache). Real app should verify with GitHub
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


# ---------- Restore ----------
class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)


# ---------- Settings ----------
class SettingsPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)


# ---------- Dashboard ----------
class DashboardPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        layout = QHBoxLayout(self)

        # Left: repos list
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Your Backup Folders (Repos)"))
        self.repo_list = QListWidget()
        left_v.addWidget(self.repo_list)

        self.new_folder_btn = QPushButton("+ New Backup Folder")
        left_v.addWidget(self.new_folder_btn)

        layout.addLayout(left_v, stretch=1)

        # Right: detail / files
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("Files in Selected Backup"))
        self.file_view = QListWidget()
        right_v.addWidget(self.file_view)

        layout.addLayout(right_v, stretch=2)

        self.setLayout(layout)

        # Hookups
        self.new_folder_btn.clicked.connect(self.create_backup_repo)
        self.repo_list.currentTextChanged.connect(self.on_repo_selected)

        # load repos from config (local cache) - in real app fetch from GitHub API
        repos = self.config_manager.data.get("repos", [])
        for r in repos:
            self.repo_list.addItem(QListWidgetItem(r))

    def create_backup_repo(self):
        # We ask user to select a folder to backup (must be <= 1GB)
        folder = QFileDialog.getExistingDirectory(self, "Select folder to backup")
        if not folder:
            return
        folder_path = Path(folder)
        size = BackupPage.folder_size_bytes(folder_path)
        if size > 1_000_000_000:
            QMessageBox.warning(self, "Folder too large",
                                "Selected folder exceeds 1GB limit. Please choose a smaller folder.")
            return

        # Ask for a repo name (default derived from folder)
        default_repo = f"backup-{folder_path.name}"
        repo_name, ok = QInputDialog.getText(self, "Repo name", "Name for GitHub repo:", text=default_repo)
        if not ok or not repo_name.strip():
            return
        repo_name = repo_name.strip()

        # TODO: Create repo on GitHub using token and username; initialize and push.
        # For now: add to UI list and save in config
        if repo_name not in self.config_manager.data.get("repos", []):
            self.repo_list.addItem(repo_name)
            repos = self.config_manager.data.get("repos", [])
            repos.append(repo_name)
            self.config_manager.data["repos"] = repos
            self.config_manager.save_config()

            QMessageBox.information(self, "Queued", f"Folder will be backed up as repo: {repo_name}\n\n(Implement actual push logic in TODO.)")
        else:
            QMessageBox.information(self, "Exists", "A repo with that name already exists in your local list.")

    def on_repo_selected(self, repo_name):
        if not repo_name:
            return
        self.load_repo_files(repo_name)

    def load_repo_files(self, repo_name):
        self.file_view.clear()
        cfg = self.config_manager.load_config()
        username = cfg["username"];
        token = cfg["token"]

        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/"
        headers = {"Authorization": f"token {token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return

        for item in resp.json():
            if item["type"] == "file":
                name = item["name"]
                download_url = item["download_url"]

                lw_item = QListWidgetItem(name)
                # if image → show thumbnail
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    img_bytes = requests.get(download_url).content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_bytes)
                    lw_item.setIcon(QIcon(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)))
                self.file_view.addItem(lw_item)


# ---------- Main ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        # Config manager first
        self.config_manager = ConfigManager()

        # Create pages
        self.onboarding_page = OnboardingPage(self.show_auth, self.config_manager)
        self.auth_page = AuthPage(self.show_dashboard, self.config_manager)
        self.backup_page = BackupPage(self.config_manager)
        self.restore_page = RestorePage()
        self.settings_page = SettingsPage(self.config_manager)
        self.dashboard_page = DashboardPage(self.config_manager)

        # Main stack
        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        # Add pages
        self.mainStack.addWidget(self.onboarding_page)   # index 0
        self.mainStack.addWidget(self.auth_page)         # index 1
        # you could add a consolidated dashboard stack, for simplicity add a Dashboard as index 2:
        self.mainStack.addWidget(self.dashboard_page)    # index 2

        # Decide which page to show
        cfg = self.config_manager.load_config()
        onboarding_done = cfg.get("onboarding_done", False)
        token = cfg.get("token", "")

        if not onboarding_done:
            self.mainStack.setCurrentIndex(0)  # show onboarding
        elif token:
            self.mainStack.setCurrentIndex(2)  # skip auth, go to dashboard
        else:
            self.mainStack.setCurrentIndex(1)  # show auth

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
