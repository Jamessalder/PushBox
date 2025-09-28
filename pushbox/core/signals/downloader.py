# In a file like signals/downloader.py
from urllib.parse import quote

import requests
from PyQt6.QtCore import QRunnable


class FileDownloaderWorker(QRunnable):
    """Worker thread for downloading a full file to a temp location."""

    def __init__(self, username, token, repo_name, file_name, temp_path):
        super().__init__()
        # We can reuse WorkerSignals if we adapt it, or create new ones.
        # For now, let's make a specific signal.
        from PyQt6.QtCore import QObject, pyqtSignal

        class DownloaderSignals(QObject):
            finished = pyqtSignal(str)  # Emits the temp file path on success
            error = pyqtSignal(str)  # Emits an error message on failure

        self.signals = DownloaderSignals()
        self.username = username
        self.token = token
        self.repo_name = repo_name
        self.file_name = file_name
        self.temp_path = temp_path

    def run(self):
        try:
            headers = {"Authorization": f"token {self.token}"}
            # **IMPORTANT BUG FIX:** Filenames with spaces or special chars need to be URL-encoded.
            encoded_file_name = quote(self.file_name)
            url = f"https://api.github.com/repos/{self.username}/{self.repo_name}/contents/{encoded_file_name}"

            meta_response = requests.get(url, headers=headers)
            meta_response.raise_for_status()
            download_url = meta_response.json().get("download_url")

            if not download_url:
                raise ValueError("Could not find a download URL for this file.")

            content_response = requests.get(download_url, headers=headers, stream=True)
            content_response.raise_for_status()

            with open(self.temp_path, 'wb') as f:
                for chunk in content_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.signals.finished.emit(str(self.temp_path))

        except Exception as e:
            self.signals.error.emit(str(e))
