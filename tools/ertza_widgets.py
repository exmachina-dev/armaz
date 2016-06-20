from PySide import QtGui, QtCore


class SwitchWidget(QtGui.QPushButton):
    valueChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setCheckable(True)
        self.state = None
        self.step = 1

        self.setMinimumSize(1, 30)
        self.checked = 0
        self.choices = ['Off', 'On']
        self.colors = [QtGui.QColor(96, 156, 96), QtGui.QColor(156, 96, 96)]
        self.bg_color = QtGui.QColor(56, 56, 56)

        self.setState(0)

    def setChecked(self, value):
        self.checked = value

    def isChecked(self):
        return self.checked

    def mousePressEvent(self, ev):
        self.setChecked(True)
        self.pressPos = ev.pos()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        self.setChecked(False)

    def mouseMoveEvent(self, ev):
        diff = ev.pos() - self.pressPos
        self.setState(diff.x())

    def focusInEvent(self, ev):
        self.setChecked(True)
        self.update()
        ev.accept()

    def focusOutEvent(self, ev):
        self.setChecked(False)
        self.update()
        ev.accept()

    def getState(self):
        return self.state

    def setState(self, x):
        new_state = min(max(0, int(round(x / self.step, 0))), len(self.choices) - 1)

        self.update()
        if self.state == new_state:
            return

        self.state = new_state
        self.valueChanged.emit(self.state)

    def paintEvent(self, ev):
        qp = QtGui.QPainter(self)
        self.drawWidget(qp)

    def drawWidget(self, qp):
        font = QtGui.QFont('Monospace', 10, QtGui.QFont.Bold)
        qp.setFont(font)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)

        size = self.size()
        w = size.width()
        h = size.height()

        self.step = w / len(self.choices)
        begin_but = self.step * self.state

        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.bg_color)
        qp.drawRoundedRect(1, 1, w - 2, h - 2, 4, 4)

        qp.setPen(self.colors[self.state])
        qp.setBrush(self.colors[self.state])
        qp.drawRoundedRect(begin_but + 1, 2, self.step - 2, h - 4, 5, 5)

        if self.isChecked():
            qp.setPen(QtGui.QPen(self.colors[self.state].lighter(150), 1))
            qp.setBrush(QtCore.Qt.NoBrush)
            qp.drawRoundedRect(begin_but + 2, 2, self.step - 4, h - 5, 3, 3)

        pen = QtGui.QPen(self.bg_color.lighter(200), 2, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRoundedRect(1, 1, w-2, h-2, 4, 4)

        for i, t in enumerate(self.choices):
            if i == self.state:
                qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 200)))
            else:
                qp.setPen(QtGui.QPen(self.colors[i].darker(100)))
            metrics = qp.fontMetrics()
            fw = metrics.width(t)
            fh = metrics.height()
            qp.drawText((i + 1) * self.step - self.step/2 - (fw / 2), h/2 + fh/2 - 1, str(t))

    def resizeEvent(self, ev):
        self.setState(self.state)
        QtGui.QPushButton.resizeEvent(self, ev)


class PushButton(QtGui.QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(parent=parent)

        self.step = 1

        self.state = None
        self.setMinimumSize(1, 30)
        self.text = text
        self.color = QtGui.QColor(96, 156, 96)
        self.bg_color = QtGui.QColor(56, 56, 56)

        self.setState(0)

    def getState(self):
        return self.state

    def setState(self, x):
        new_state = x

        self.update()
        if self.state == new_state:
            return

        self.state = new_state
        self.clicked.emit()

    def mousePressEvent(self, ev):
        self.setState(True)
        ev.accept()

    def mouseReleaseEvent(self, ev):
        self.setState(False)

    def paintEvent(self, ev):
        qp = QtGui.QPainter(self)
        self.drawWidget(qp)

    def drawWidget(self, qp):
        font = QtGui.QFont('Monospace', 10, QtGui.QFont.Bold)
        qp.setFont(font)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)

        size = self.size()
        w = size.width()
        h = size.height()

        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.bg_color)
        qp.drawRoundedRect(1, 1, w - 2, h - 2, 4, 4)

        qp.setPen(self.color)
        qp.setBrush(self.color)
        qp.drawRoundedRect(1, 2, w - 2, h - 4, 5, 5)

        if self.getState():
            qp.setPen(QtGui.QPen(self.color.lighter(150), 1))
            qp.setBrush(QtCore.Qt.NoBrush)
            qp.drawRoundedRect(2, 2, w - 4, h - 5, 3, 3)

        pen = QtGui.QPen(self.bg_color.lighter(200), 2, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRoundedRect(1, 1, w-2, h-2, 4, 4)

        if not self.getState():
            qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 200)))
        else:
            qp.setPen(QtGui.QPen(self.color.darker(300)))
        metrics = qp.fontMetrics()
        fw = metrics.width(self.text)
        fh = metrics.height()
        qp.drawText(w / 2 - fw / 2, h/2 + fh/2 - 1, self.text)

    def resizeEvent(self, ev):
        self.setState(self.state)
        QtGui.QPushButton.resizeEvent(self, ev)
