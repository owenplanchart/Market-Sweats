"""Application-wide quit handling, independent of chart/window focus."""
from PySide6 import QtCore, QtWidgets


class Application(QtWidgets.QApplication):
    def __init__(self, args):
        super().__init__(args)
        self._quit_requested = False
        self.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type() in (QtCore.QEvent.Type.ShortcutOverride, QtCore.QEvent.Type.KeyPress)
                and event.key() == QtCore.Qt.Key.Key_Q
                and event.modifiers() in (QtCore.Qt.KeyboardModifier.NoModifier,
                                          QtCore.Qt.KeyboardModifier.ShiftModifier)
                and self.activeModalWidget() is None):
            # Reserve q/Q before a focused chart or control consumes the key.
            # Modal file pickers retain normal filename typing.
            event.accept()
            if event.type() == QtCore.QEvent.Type.KeyPress and not self._quit_requested:
                self._quit_requested = True
                QtCore.QTimer.singleShot(0, self.quit)
            return True
        return super().eventFilter(watched, event)
