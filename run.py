import sys
from PyQt6.QtWidgets import QApplication

from pushbox.window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 640)
    window.show()
    sys.exit(app.exec())