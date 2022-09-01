
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
import proxy
import subprocess


class PyToggle(QCheckBox):
    def __init__(
        self,
        width=60,
        bg_color="#777",
        circle_color="#DDD",
        active_color="#00ff03"
    ):
        QCheckBox.__init__(self)

        # set default parameters
        self.setFixedSize(width, 28)
        self.setCursor(Qt.PointingHandCursor)

        # create color objects
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color

        # check current regkey value for proxy and set toggle status
        regkey_check = subprocess.Popen(
            proxy.proxy_status_query, shell=True, stdout=subprocess.PIPE)
        regkey_check_return = regkey_check.stdout.read().split()
        if regkey_check_return[-1] == b'0x0':
            self.setChecked(False)
        if regkey_check_return[-1] == b'0x1':
            self.setChecked(True)

        # connect state changed
        self.stateChanged.connect(self.change_proxy_status)

    def change_proxy_status(self):
        regkey_check = subprocess.Popen(
            proxy.proxy_status_query, shell=True, stdout=subprocess.PIPE)
        regkey_check_return = regkey_check.stdout.read().split()

        if regkey_check_return[-1] == b'0x0':
            proxy.activate()
        if regkey_check_return[-1] == b'0x1':
            proxy.deactivate()

    # set new hit area
    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    # draw new items
    def paintEvent(self, e):
        # set painter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # set no pen
        p.setPen(Qt.NoPen)

        # draw rectangle
        rect = QRect(0, 0, self.width(), self.height())

        if not self.isChecked():
            # draw background
            p.setBrush(QColor(self._bg_color))
            p.drawRoundedRect(0, 0, rect.width(), self.height(),
                              self.height()/2, self.height()/2)

            # draw circle
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(3, 3, 22, 22)

        else:
            # draw background
            p.setBrush(QColor(self._active_color))
            p.drawRoundedRect(0, 0, rect.width(), self.height(),
                              self.height()/2, self.height()/2)

            # draw circle
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self.width() - 26, 3, 22, 22)

        # end painter
        p.end()
