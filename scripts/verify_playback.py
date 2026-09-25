"""Exercise the actual movie worker, Qt event loop and presentation together."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import time
from PySide6 import QtWidgets
from arucomarket.config import Config
from arucomarket.ui import Window

config = Config.load('config.json')
app = QtWidgets.QApplication([])
window = Window(config, 'movie', config.movie)
window.show()
frames = {}
started = time.monotonic()
try:
    while time.monotonic()-started < 8:
        app.processEvents()
        payload = window.last_payload
        if payload:
            state = payload['state']
            frames[state['frame_id']] = (time.monotonic()-started, state['timestamp'])
        assert window.worker.is_alive(), window.status.text()
        time.sleep(.005)
    window.grab().save('artifacts/playback-verified.png')
    rows = list(frames.values())
    assert len(rows) >= 10, f'Only {len(rows)} frames reached the UI'
    assert rows[-1][1] > 2, f'Source clock did not advance: {rows}'
    assert rows[-1][0] > 7, 'No fresh image reached Qt near the end of the check'
    assert max(b[0]-a[0] for a,b in zip(rows,rows[1:])) < 1, 'Presentation stalled for a full second'
    report = {'ui_frames': len(rows), 'first_pts': rows[0][1], 'last_pts': rows[-1][1],
              'wall_seconds': rows[-1][0], 'dropped': window.worker.dropped,
              'playback_resyncs': window.worker.playback_resyncs,
              'max_display_gap_seconds': max(b[0]-a[0] for a,b in zip(rows,rows[1:]))}
    Path('artifacts/playback-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    window.close()
print('Real movie + worker + Qt presentation: PASS')
