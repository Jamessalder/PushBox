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
    """A clickable widget that now loads its thumbnail asynchronously."""
    download_requested = pyqtSignal(Path)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.file_path = path
        self.setToolTip(f"File: {self.file_path.name}\nLocation: {self.file_path}")

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Connect that signal to our method that shows the menu
        self.customContextMenuRequested.connect(self.show_context_menu)

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


        super().mousePressEvent(event)

    def show_context_menu(self, position):
        menu = QMenu(self)
        download_action = menu.addAction("Download again...")
        download_action.triggered.connect(lambda: self.download_requested.emit(self.file_path))
        menu.exec(self.mapToGlobal(position))
