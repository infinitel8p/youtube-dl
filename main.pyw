import sys
import proxy
import logging
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from lib.py_toggle import PyToggle

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
        self.setWindowTitle('Proxy Settings')
        my_icon = QIcon()
        my_icon.addFile('icon.png')
        self.setWindowIcon(my_icon)
        # resize window
        self.resize(350, 250)
        # create container and layout
        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet("#container {background-color: #222}")

        # create widgets
        self.edit = QLineEdit(proxy.fill_in())
        self.button_save = QPushButton('Apply new Proxy Address')
        self.button_save.setFixedWidth(150)
        self.label = QLabel("Turn Proxy ON/OFF:")
        self.label.setStyleSheet("color: white;")
        self.label.setFixedWidth(150)
        self.toggle = PyToggle()
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
        self.nested_layout_1.addWidget(self.button_save)
        self.nested_layout_2.addWidget(
            self.label, Qt.AlignCenter, Qt.AlignLeft)
        self.nested_layout_2.addWidget(
            self.toggle, Qt.AlignCenter, Qt.AlignCenter)
        self.main_layout.addLayout(self.nested_layout_1)
        self.main_layout.addLayout(self.nested_layout_2)
        self.main_layout.addWidget(self.logTextBox.widget)
        # set layout and central widget
        self.setLayout(self.main_layout)
        self.container.setLayout(self.main_layout)
        self.setCentralWidget(self.container)

        # add button signal to proxy_changer slot
        self.button_save.clicked.connect(self.proxy_changer)

        # show window
        self.show()

    def proxy_changer(self):
        proxy.change_address(self.edit.text())


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    # create QtApplication
    app = QApplication(sys.argv)
    # create and show the window
    settings = MainWindow()
    settings.show()
    # check current settings
    proxy.status_check()
    proxy.server_check()
    # run the main Qt loop
    sys.exit(app.exec())
