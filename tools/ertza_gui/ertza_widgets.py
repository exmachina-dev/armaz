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
        self.colors = [QtGui.QColor(81, 122, 81), QtGui.QColor(122, 81, 81)]
        self.bg_color = QtGui.QColor(34, 41, 50)

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
        self.color = QtGui.QColor(81, 122, 81)
        self.bg_color = QtGui.QColor(30, 36, 44)

        self.setState(0)

    def getState(self):
        return self.state

    def setState(self, x):
        new_state = x

        self.update()
        if self.state == new_state:
            return

        self.state = new_state
        if self.state:
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


class UpdatableTableWidget(QtGui.QTableWidget):
    valueChanged = QtCore.Signal(str, object)

    def __init__(self, *args, **kwargs):
        self._keys = list()
        self._vtypes = {}

        super().__init__(*args, **kwargs)

    @QtCore.Slot()
    def clear_values(self):
        for r in range(len(self._keys)):
            self.setItem(r, 1, QtGui.QTableWidgetItem(''))

    @QtCore.Slot(object)
    def update_content(self, obj):
        key, args = obj[0], obj[1:]
        value = vtype = unit = None
        if isinstance(args, (tuple, list)):
            if len(args) == 1:
                value = args[0]
            elif len(args) == 2:
                vtype, unit = args
            elif len(args) == 3:
                value, vtype, unit = args
        else:
            value = args

        if isinstance(value, bool):
            value = 'on' if value else 'off'
        elif isinstance(value, float):
            value = '{:.2f}'.format(value)

        if key not in self._keys:
            self._keys.append(key)
            self.setRowCount(len(self._keys))
            self.setItem(len(self._keys)-1, 0, QtGui.QTableWidgetItem(str(key)))

        i = self._keys.index(key)
        if value is not None:
            self.setItem(i, 1, QtGui.QTableWidgetItem(str(value)))

        if unit is not None:
            self.setItem(i, 2, QtGui.QTableWidgetItem(str(unit)))

        if vtype is not None:
            if hasattr(__builtins__, vtype):
                self._vtypes[key] = getattr(__builtins__, vtype)

        self.horizontalHeader().stretchLastSection()
        self.resizeColumnsToContents()

    @QtCore.Slot(QtGui.QTableWidgetItem)
    def update_value(self, item):
        x, y = item.column(), item.row()
        if x is not 1 or not item.isSelected():
            return

        key = self._keys[y]
        value = item.text()

        if key in self._vtypes.keys():
            value = self._vtypes[key](value)

        self.valueChanged.emit(key, value)
