from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QLineEdit
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton
)
import base64

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
            "token": (base64.b64encode(self.token.text())),

            "onboarding_done": self.config_manager.data.get("onboarding_done", False)
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()
