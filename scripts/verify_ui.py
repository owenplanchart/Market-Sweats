"""Offscreen native Qt smoke test; uses a real movie frame and worker clock checks."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import time
from queue import Empty
from PySide6 import QtWidgets, QtCore
from arucomarket.config import Config
from arucomarket.capture import Movie
from arucomarket.detection import Detector
from arucomarket.state import Engine
from arucomarket.ui import Window
from arucomarket.worker import Worker

config = Config.load('config.json')
app = QtWidgets.QApplication([])
window = Window(config, 'movie', config.movie, start_worker=False)
window.tabs.setCurrentIndex(1)
window.resize(900,1600)
window.show()
source = Movie(config.movie, 15)
engine, detector = Engine(config), Detector(config)
for _ in range(30):
    frame = source.read()
    image, raw = detector.detect(frame.image,frame.timestamp,frame.frame_id,frame.source)
    engine.process(frame.timestamp,frame.frame_id,frame.source,raw)
window.worker.publish({'image':image,'state':engine.snapshot(),'kind':'movie','duration':source.duration,
                       'analysis_ms':0,'dropped':0,'display_dropped':0})
window.poll()
for _ in range(8): app.processEvents()
window.grab().save('artifacts/ui-preview.png')
window.grab().save('artifacts/ui-portrait-preview.png')
assert window.split.orientation() == QtCore.Qt.Orientation.Vertical
assert window.market_scroll.y() > window.view.y()
assert window.width() < window.height()
assert window.ticker.rowCount() == 5
window.camera_only.setChecked(True)
assert window.market_scroll.isHidden()
window.camera_only.setChecked(False)
window.set_layer('labels',False)
window.trail.setValue(12)
assert window.view.trail_seconds == 12
window.candle_ball.setCurrentIndex(4)
# The user's wide screen must keep both charts visible, not flatten them.
window.candle_ball.setCurrentIndex(0)
window.layout_mode.setCurrentIndex(window.layout_mode.findData('auto'))
for width, height, name in [(1866,881,'wide'), (1440,900,'desktop'), (1080,720,'small')]:
    window.resize(width,height)
    for _ in range(8): app.processEvents()
    assert window.split.orientation() == QtCore.Qt.Orientation.Horizontal
    for chart in (window.history,window.ohlc):
        assert chart.height() >= 220
        assert chart.getViewBox().sceneBoundingRect().height() >= 130
    if width >= 1440:
        assert window.charts.orientation() == QtCore.Qt.Orientation.Horizontal
        window.grab().save(f'artifacts/ui-{name}-preview.png')
        assert window.market_scroll.verticalScrollBar().maximum() == 0
    window.grab().save(f'artifacts/ui-{name}-preview.png')
    print(f'{width}x{height}: chart heights {window.history.height()}, {window.ohlc.height()}')
# Auto must restore stacking on a tall screen; explicit portrait may scroll on a short screen.
window.resize(900,1600)
for _ in range(8): app.processEvents()
assert window.split.orientation() == QtCore.Qt.Orientation.Vertical
window.layout_mode.setCurrentIndex(window.layout_mode.findData('portrait'))
window.resize(1080,720)
for _ in range(8): app.processEvents()
assert window.history.height() >= 220 and window.ohlc.height() >= 220
assert window.market_scroll.verticalScrollBar().maximum() > 0
assert window.last_payload['state'] == engine.snapshot(), 'Layout changes must not alter observations'
# A changing OHLC item's bounds must notify the plot, keeping observed values in view.
window.ohlc.getViewBox().updateAutoRange()
lo,hi = window.ohlc.getViewBox().viewRange()[1]
for candle in engine.candles[0]:
    assert lo <= candle.low <= candle.high <= hi
source.close()
window.close()

# Exercise actual threaded pipeline, pause/resume, reset and bounded mailbox.
w = Worker(config,'synthetic',None)
w.start()
def get_frame(timeout=5):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            item = w.output.get(timeout=.1)
        except Empty:
            continue
        assert 'error' not in item, item
        if 'state' in item:
            return item
    raise AssertionError('Worker timeout')
a = get_frame()
w.command('pause',True)
time.sleep(.15)
while not w.output.empty(): w.output.get_nowait()
time.sleep(.2)
assert w.output.empty(), 'Paused source generated new evidence'
w.command('pause',False)
b = get_frame()
assert 0 < b['state']['timestamp']-a['state']['timestamp'] < .3
w.command('reset')
c = get_frame()
# An already in-flight snapshot may precede the reset command.
if c['state']['timestamp'] > .05: c = get_frame()
assert c['state']['timestamp'] < .1
w.stopping.set()
w.join(3)
assert not w.is_alive()
print('Qt rendering, panel controls, worker pause/resume/reset: PASS')
