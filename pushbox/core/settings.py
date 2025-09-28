from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)


class SettingsPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)
