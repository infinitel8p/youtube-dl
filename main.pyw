import sys
import handler
import logging
import downloader
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

# Uncomment below for terminal log messages
# logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(name)s - %(levelname)s - %(message)s')


class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setStyleSheet("background-color: #777")
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle('Youtube Downloader')
        my_icon = QIcon()
        my_icon.addFile('icon.png')
        self.setWindowIcon(my_icon)
        # resize window
        self.resize(650, 550)
        # create container and layout
        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet("#container {background-color: #222}")

        # create widgets
        self.edit = QLineEdit()
        self.edit.paste()
        self.button_paste = QPushButton("Paste")
        self.button_paste.setFixedWidth(100)
        self.button_clear = QPushButton("Clear")
        self.button_paste.setFixedWidth(100)
        self.button_save = QPushButton("Download")
        self.button_save.setFixedWidth(100)
        self.label = QLabel("File Format:")
        self.label.setStyleSheet("color: white;")
        self.label.setFixedWidth(150)
        self.label2 = QLabel("Empty")
        self.label2.setStyleSheet("color: white;")
        self.label2.setFixedWidth(150)
        self.logTextBox = QTextEditLogger(self)

        # You can format what is printed to text box
        self.logTextBox.setFormatter(logging.Formatter(
            '%(levelname)s: %(message)s'))
        logging.getLogger().addHandler(self.logTextBox)
        # control the logging level
        logging.getLogger().setLevel(logging.NOTSET)

        # create layout
        self.main_layout = QVBoxLayout()
        self.nested_layout_1 = QHBoxLayout()
        self.nested_layout_2 = QHBoxLayout()
        self.nested_layout_1.addWidget(self.edit)
        self.nested_layout_1.addWidget(self.button_paste)
        self.nested_layout_1.addWidget(self.button_clear)
        self.nested_layout_1.addWidget(self.button_save)
        self.nested_layout_2.addWidget(
            self.label, Qt.AlignCenter, Qt.AlignLeft)
        self.nested_layout_2.addWidget(
            self.label2, Qt.AlignCenter, Qt.AlignRight)
        self.main_layout.addLayout(self.nested_layout_1)
        self.main_layout.addLayout(self.nested_layout_2)
        self.main_layout.addWidget(self.logTextBox.widget)
        # set layout and central widget
        self.setLayout(self.main_layout)
        self.container.setLayout(self.main_layout)
        self.setCentralWidget(self.container)

        # add button callbacks
        self.button_paste.clicked.connect(self.paste_clipboard)
        self.button_clear.clicked.connect(self.clear_line)
        self.button_save.clicked.connect(self.run_download)

        # show window
        self.show()

    def paste_clipboard(self):
        self.edit.paste()

    def clear_line(self):
        self.edit.clear()

    def run_download(self):
        downloader.run(self.edit.text())


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    # create QtApplication
    app = QApplication(sys.argv)
    # create and show the window
    downloader_app = MainWindow()
    downloader_app.show()
    # run the main Qt loop
    sys.exit(app.exec())
