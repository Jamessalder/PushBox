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
    open_requested = pyqtSignal(Path)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.file_path = path
        self.setToolTip(f"File: {self.file_path.name}\nLocation: {self.file_path}")

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
        """Handle mouse clicks by emitting signals."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Emit a signal to request opening the file from the cloud
            self.open_requested.emit(self.file_path)

        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPos())

        super().mousePressEvent(event)

    def show_context_menu(self, position):
        """Create and show a right-click context menu."""
        menu = QMenu(self)
        # Add a new option to view the file directly on GitHub.com
        view_on_github_action = menu.addAction("View on GitHub")
        download_action = menu.addAction("Download to...")

        # Connect the actions to their respective signals
        view_on_github_action.triggered.connect(self.open_on_github)
        download_action.triggered.connect(lambda: self.download_requested.emit(self.file_path))

        menu.exec(position)

    def open_on_github(self):
        """A helper to emit the open_requested signal with a flag or open the browser directly."""
        # This is a good place to add the logic to open the browser
        # For simplicity, we'll just re-use the open_requested logic for now.
        # A more advanced implementation could have a separate signal.
        QMessageBox.information(self, "Coming Soon", "This will open the file in your web browser.")