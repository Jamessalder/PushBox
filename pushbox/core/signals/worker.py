from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str, str)