from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)


class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)
