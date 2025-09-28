import base64

import requests
from PyQt6.QtCore import QRunnable
from PyQt6.QtGui import QPixmap

from worker import WorkerSignals


class ThumbnailWorker(QRunnable):
    """Worker thread for downloading a thumbnail from GitHub."""

    def __init__(self, username, token, repo_name, file_name):
        super().__init__()
        self.signals = WorkerSignals()
        self.username = username
        self.token = token
        self.repo_name = repo_name
        self.file_name = file_name

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/{self.file_name}"

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            content_b64 = response.json()['content']
            decoded_bytes = base64.b64decode(content_b64)

            pixmap = QPixmap()
            pixmap.loadFromData(decoded_bytes)

            self.signals.finished.emit(self.file_name, pixmap)

        except Exception as e:
            self.signals.error.emit(self.file_name, str(e))