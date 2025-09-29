import sys

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget
)
from PyQt6.QtWidgets import (
    QApplication
)

from .core.config import ConfigManager
from .core.const import stylesheet
from .core.dashboard import DashboardPage
from pushbox.core.init.auth import AuthPage
from pushbox.core.files.backup import BackupPage
from pushbox.core.files.restore import RestorePage
from .core.settings import SettingsPage
from pushbox.core.init.onboarding import OnboardingPage

import base64


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

        cfg = self.config_manager.load_config()
        token_enc = cfg.get("token", "")

        token = ""
        if token_enc:
            try:
                token_bytes = base64.b64decode(token_enc + "===")  # pad if missing
                token = token_bytes.decode("utf-8")
            except Exception as e:
                print("Token decode failed:", e)

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
