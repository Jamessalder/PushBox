stylesheet = """
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
"""
