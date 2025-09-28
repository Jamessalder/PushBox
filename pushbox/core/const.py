stylesheet = """
QWidget {
    background-color: #0f0f1a;
    color: #f0f0f0;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif;
    font-size: 15px;
    font-weight: 400;
}

/* --- Input Fields (QLineEdit, QTextEdit, etc.) --- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1c1c2b;
    color: #f0f0f0;
    padding: 10px;
    border: 1px solid #44445a;
    border-radius: 8px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #8a3ffc;
    background-color: #222233; /* Slightly lighter on focus */
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #2a2a3b;
    color: #78788c;
    border: 1px solid #44445a;
}

/* --- Buttons --- */
QPushButton {
    background-color: #8a3ffc;
    color: #ffffff;
    padding: 10px 15px;
    border-radius: 8px;
    border: none;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #a061fd;
}

QPushButton:pressed {
    background-color: #7b2ff8;
}

QPushButton:disabled {
    background-color: #44445a;
    color: #78788c;
}

/* --- List & Tree Widgets --- */
QListWidget, QTreeView {
    background-color: #1c1c2b;
    border: 1px solid #44445a;
    border-radius: 8px;
    padding: 5px;
}

QListWidget::item, QTreeView::item {
    padding: 12px;
    margin: 3px;
    border-radius: 6px;
}

QListWidget::item:hover, QTreeView::item:hover {
    background-color: #2a2a3b;
}

QListWidget::item:selected, QTreeView::item:selected {
    background-color: #8a3ffc;
    color: #ffffff;
}

/* --- ScrollBars --- */
QScrollBar:vertical {
    border: none;
    background: #1c1c2b;
    width: 12px;
    margin: 15px 0 15px 0;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #44445a;
    min-height: 25px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #8a3ffc;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* --- Progress Bar --- */
QProgressBar {
    border: 1px solid #44445a;
    border-radius: 8px;
    text-align: center;
    color: #f0f0f0;
    background-color: #1c1c2b;
}

QProgressBar::chunk {
    border-radius: 6px;
    background-color: qlineargradient(spread:pad, x1:0, y1:0.5, x2:1, y2:0.5, stop:0 #8a3ffc, stop:1 #a061fd);
}

/* --- Labels --- */
QLabel:disabled {
    color: #78788c;
}

"""
