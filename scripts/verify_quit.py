"""Q must exit the application event loop, not merely hide a chart/window."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if len(sys.argv) == 1:
    for case in ('chart', 'control', 'fullscreen', 'uppercase'):
        subprocess.run([sys.executable, __file__, case], check=True, timeout=15, cwd=ROOT)
    print('Application-wide Q quit: PASS')
    sys.exit(0)

from PySide6 import QtCore, QtTest, QtWidgets
from arucomarket.application import Application
from arucomarket.config import Config
from arucomarket.ui import Window

case = sys.argv[1]
app = Application([])
# Merely closing the main window must not make this regression test pass.
app.setQuitOnLastWindowClosed(False)
extra = QtWidgets.QWidget()
extra.show()
window = Window(Config(), 'synthetic', None)
app.aboutToQuit.connect(window.shutdown)
window.showFullScreen() if case == 'fullscreen' else window.show()
window.activateWindow()
target = window.camera_index.lineEdit() if case == 'control' else window.trial.height_plot
target.setFocus()
failures = []
sent = []

def press_q():
    try:
        assert window.worker.is_alive()
        assert window.isVisible() and extra.isVisible()
        sent.append(True)
        modifier = QtCore.Qt.KeyboardModifier.ShiftModifier if case == 'uppercase' else QtCore.Qt.KeyboardModifier.NoModifier
        QtTest.QTest.keyClick(target, QtCore.Qt.Key.Key_Q, modifier)
    except Exception as exc:
        failures.append(str(exc))
        app.exit(2)

QtCore.QTimer.singleShot(300, press_q)
QtCore.QTimer.singleShot(5000, lambda: app.exit(3))
result = app.exec()
assert result == 0 and sent and not failures, (case, result, failures)
assert window.worker.stopping.is_set()
assert not window.worker.is_alive(), 'Application quit left the worker running'
assert not window.timer.isActive()
print(f'{case}: Q exited the entire event loop and stopped the worker')
