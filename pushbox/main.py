import json
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QProgressBar, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys
from core.const import stylesheet
from core.config import ConfigManager


# ---------- Onboarding ----------
class OnboardingPage(QWidget):
    def __init__(self, switch_to_auth):
        super().__init__()

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
            label_title.setFont(QFont("Montserrat", 35, QFont.Weight.Bold))
            label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label_sub = QLabel(subtitle)
            label_sub.setFont(QFont("Arial", 12))
            label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_sub.setWordWrap(True)

            btn = QPushButton("Next" if i < len(data) - 1 else "Get Started")
            btn.setFixedWidth(150)
            btn.clicked.connect(
                (lambda _, idx=i: self.next_page(idx, switch_to_auth))
            )

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
            switch_to_auth()


# ---------- Auth ----------
class AuthPage(QWidget):
    def __init__(self, switch_to_dashboard, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("PushBox")
        title.setFont(QFont("Montserrat", 60, QFont.Weight.Bold))
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
            "token": self.token.text()
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()


# ---------- Backup ----------
class BackupPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label = QLabel("Select a folder to backup")
        self.select_btn = QPushButton("Choose Folder")
        self.backup_btn = QPushButton("Backup Now")

        layout.addWidget(self.label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.backup_btn)
        self.setLayout(layout)


# ---------- Restore ----------
class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)


# ---------- Settings ----------
class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)


# ---------- Dashboard ----------
class DashboardPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        layout = QVBoxLayout(self)
        self.repo_list = QListWidget()
        layout.addWidget(QLabel("Your Backup Folders"))
        layout.addWidget(self.repo_list)

        btn_layout = QHBoxLayout()
        self.new_folder_btn = QPushButton("+ New Backup Folder")
        btn_layout.addWidget(self.new_folder_btn)
        layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.file_view = QListWidget()
        layout.addWidget(QLabel("Files in Selected Backup"))
        layout.addWidget(self.file_view)

        # Hook
        self.new_folder_btn.clicked.connect(self.create_backup_repo)

    def create_backup_repo(self):
        folder_name, ok = QInputDialog.getText(self, "New Backup", "Folder/Repo name:")
        if not ok or not folder_name:
            return

        # Local folder
        os.makedirs(folder_name, exist_ok=True)

        # TODO: GitHub API → create repo
        # For now, just simulate
        self.repo_list.addItem(folder_name)

    def upload_folder(self, folder_path, repo_name):
        total_size = sum(os.path.getsize(os.path.join(dp, f))
                         for dp, dn, filenames in os.walk(folder_path)
                         for f in filenames)

        if total_size > 1_000_000_000:  # 1GB
            QMessageBox.warning(self, "Error", "Folder exceeds 1GB limit.")
            return

        uploaded = 0
        for dp, dn, filenames in os.walk(folder_path):
            for f in filenames:
                path = os.path.join(dp, f)
                size = os.path.getsize(path)

                # TODO: push via GitHub API
                uploaded += size
                progress_val = int((uploaded / total_size) * 100)
                self.progress.setValue(progress_val)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        # ConfigManager first
        self.config_manager = ConfigManager()

        if self.config_manager.data.get("onboarding_done"):
            if self.config_manager.data.get("token"):
                self.show_dashboard()
            else:
                self.show_auth()
        else:
            self.mainStack.setCurrentIndex(0)

        self.config_manager.data["onboarding_done"] = True
        self.config_manager.save_config()

        self.onboarding_page = OnboardingPage(self.show_auth)
        self.auth_page = AuthPage(self.show_dashboard, self.config_manager)
        self.dashboard_page = DashboardPage()

        # Add to stack
        self.mainStack.addWidget(self.onboarding_page)   # index 0
        self.mainStack.addWidget(self.auth_page)         # index 1
        self.mainStack.addWidget(self.dashboard_page)    # index 2

        self.mainStack.setCurrentIndex(0)

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
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())
