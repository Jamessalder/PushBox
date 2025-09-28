from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys


# ---------- Pages ----------
class AuthPage(QWidget):
    def __init__(self, switch_to_dashboard):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("PushBox")
        title.setFont(QFont("Montserrat", 32, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Secure GitHub Backup")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("GitHub Username")

        self.token = QLineEdit()
        self.token.setPlaceholderText("Personal Access Token")
        self.token.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_btn = QPushButton("Save & Continue")
        self.login_btn.clicked.connect(switch_to_dashboard)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.username)
        layout.addWidget(self.token)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)


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


class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.addItem(QListWidgetItem("Backup"))
        self.sidebar.addItem(QListWidgetItem("Restore"))
        self.sidebar.addItem(QListWidgetItem("Settings"))

        # Substack
        self.substack = QStackedWidget()
        self.backup_page = BackupPage()
        self.restore_page = RestorePage()
        self.settings_page = SettingsPage()

        self.substack.addWidget(self.backup_page)   # index 0
        self.substack.addWidget(self.restore_page)  # index 1
        self.substack.addWidget(self.settings_page) # index 2

        # Switch on sidebar click
        self.sidebar.currentRowChanged.connect(self.substack.setCurrentIndex)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.substack, stretch=1)
        self.setLayout(layout)


# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        # Pages
        self.auth_page = AuthPage(self.show_dashboard)
        self.dashboard_page = DashboardPage()

        self.mainStack.addWidget(self.auth_page)     # index 0
        self.mainStack.addWidget(self.dashboard_page) # index 1

        self.mainStack.setCurrentIndex(0)

        # Apply Styles
        self.apply_styles()

    def show_dashboard(self):
        self.mainStack.setCurrentIndex(1)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #eeeeee;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #333;
                border-radius: 6px;
                background-color: #1e1e1e;
                color: #fff;
            }
            QLineEdit:focus {
                border: 2px solid #00c6ff;
                background-color: #222;
            }
            QPushButton {
                padding: 8px;
                border-radius: 6px;
                background-color: #00c6ff;
                color: #121212;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0072ff;
                color: white;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                padding: 10px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0072ff;
                color: white;
            }
        """)


# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())
