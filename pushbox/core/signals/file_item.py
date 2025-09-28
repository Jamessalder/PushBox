from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMenu
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMessageBox
)


class FileItemWidget(QWidget):
    """A custom widget to represent a single file in the grid."""
    open_requested = pyqtSignal(Path)
    download_requested = pyqtSignal(Path)

    def __init__(self, path: Path, is_local=False, parent=None):
        super().__init__(parent)
        self.file_path = path
        self.setToolTip(f"File: {self.file_path.name}")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        vbox = QVBoxLayout(self)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label = QLabel("Loading...")
        if is_local: self.image_label.setText("New File")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self.image_label)
        name_label = QLabel(self.file_path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        vbox.addWidget(name_label)
        self.setMinimumHeight(140)

    def set_thumbnail(self, pixmap: QPixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("Preview\nUnavailable")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.file_path)
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        menu = QMenu(self)
        download_action = menu.addAction("Download to...")
        download_action.triggered.connect(lambda: self.download_requested.emit(self.file_path))
        menu.exec(self.mapToGlobal(position))
