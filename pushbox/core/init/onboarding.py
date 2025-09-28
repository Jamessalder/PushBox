from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QStackedWidget
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton
)


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