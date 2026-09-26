"""Exercise prediction with actual detector input and render native trial views."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
import math
from PySide6 import QtWidgets
from arucomarket.config import Config
from arucomarket.capture import Movie, Synthetic
from arucomarket.detection import Detector
from arucomarket.state import Engine
from arucomarket.ui import Window

parser = argparse.ArgumentParser()
parser.add_argument('--movie', action='store_true')
parser.add_argument('--layout-only', action='store_true')
args = parser.parse_args()
config = Config.load('config.json')
kind = 'movie' if args.movie else 'synthetic'
app = QtWidgets.QApplication([])
window = Window(config, kind, config.movie if args.movie else None, start_worker=False)
window.resize(1440, 1000)
window.show()
if args.layout_only:
    for _ in range(8): app.processEvents()
    for name in ('market_scroll', 'panels', 'tabs', 'trial'):
        widget = getattr(window, name)
        print(name, 'size', widget.size(), 'min', widget.minimumSizeHint(), 'hint', widget.sizeHint())
    for chart in (window.trial.height_plot, window.trial.quote_plot):
        print('chart', chart.size(), chart.minimumSizeHint(), chart.minimumSize())
    window.grab().save('artifacts/trial-layout.png')
    window.close()
    sys.exit(0)
source = Movie(config.movie, 12) if args.movie else Synthetic()
engine, detector = Engine(config), Detector(config)
end = 28 if args.movie else 12
saved = False
quote_frames = {mid: dict(sighting=0, estimated=0) for mid in config.active_ids}
try:
    while True:
        frame = source.read()
        if frame is None or frame.timestamp >= end:
            break
        image, raw = detector.detect(frame.image, frame.timestamp, frame.frame_id, frame.source)
        engine.process(frame.timestamp, frame.frame_id, frame.source, raw)
        state = engine.snapshot()
        for mid, ball in state['market']['balls'].items():
            round_ = ball['round']
            if round_ and round_['status'] == 'OPEN' and frame.timestamp < round_['terms']['expiry']:
                quote = round_['quotes'][-1]
                assert quote[0] == frame.timestamp, 'An active quote must advance on every source frame'
                assert math.isfinite(quote[1]), 'Missing sightings must not break the quote'
                quote_frames[mid][quote[2]] += 1
        if frame.frame_id % 5 == 0:
            window.worker.publish(dict(image=image, state=state, kind=kind, duration=source.duration,
                                       analysis_ms=0, dropped=0, display_dropped=0))
            window.poll()
            app.processEvents()
        if not saved:
            for mid, ball in state['market']['balls'].items():
                round_ = ball['round']
                if (round_ and round_['status'] == 'OPEN' and frame.timestamp - round_['terms']['opened'] >= 1.5
                        and (not args.movie or ball['quote_mode'] == 'estimated')):
                    window.trial.ball.setCurrentIndex(mid)
                    window.worker.publish(dict(image=image, state=state, kind=kind, duration=source.duration,
                                               analysis_ms=0, dropped=0, display_dropped=0))
                    window.poll()
                    for _ in range(8): app.processEvents()
                    assert not window.trial.band.path().isEmpty(), 'Forecast range must render'
                    assert window.market_scroll.verticalScrollBar().maximum() == 0, 'Desktop trial should fit'
                    assert window.trial.visible_ids == set(config.active_ids)
                    assert all(toggle.isChecked() for toggle in window.trial.visibility.values())
                    plotted_histories = 0
                    plotted_contracts = 0
                    for ball_id in config.active_ids:
                        observed_x, _ = window.trial.series[ball_id]['observed'].getData()
                        if observed_x is not None and len(observed_x) >= 2:
                            plotted_histories += 1
                        quote_x, _ = window.trial.series[ball_id]['quote'].getData()
                        estimate_x, _ = window.trial.series[ball_id]['estimated_quote'].getData()
                        if ((quote_x is not None and len(quote_x) >= 2)
                                or (estimate_x is not None and len(estimate_x) >= 2)):
                            plotted_contracts += 1
                    minimum_balls = 2 if args.movie else 3
                    assert plotted_histories >= minimum_balls, 'Multiple ball histories must render together'
                    assert plotted_contracts >= minimum_balls, 'Multiple contract quotes must render together'
                    window.trial.visibility[mid].setChecked(False)
                    app.processEvents()
                    assert mid not in window.trial.visible_ids
                    assert not window.trial.series[mid]['observed'].isVisible()
                    window.trial.choose_row(config.active_ids.index(mid), 0)
                    app.processEvents()
                    assert window.trial.visibility[mid].isChecked(), 'Ticker focus must reveal a hidden ball'
                    assert window.trial.series[mid]['observed'].isVisible()
                    if args.movie:
                        projected_x, projected_y = window.trial.estimated_quote.getData()
                        assert projected_x is not None and len(projected_x) >= 2, 'Dashed quote must render'
                        assert 'Estimated' in window.trial.round_label.text()
                    window.grab().save(f'artifacts/trial-{kind}-active.png')
                    saved = True
                    break
    report = {}
    for mid, ball in engine.snapshot()['market']['balls'].items():
        report[mid] = {key: ball[key] for key in ('counts', 'balance', 'scored', 'forecast_mae', 'hold_mae')}
        report[mid]['quote_frames'] = quote_frames[mid]
    Path(f'artifacts/trial-{kind}-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    assert sum(row['estimated'] for row in quote_frames.values()) > 0
    if not args.movie:
        assert saved, 'Synthetic detector never opened a usable bet'
        assert sum(sum(ball['counts'].values()) for ball in report.values()) >= 5
        for width, height, label in [(1440, 1000, 'desktop'), (900, 1600, 'portrait'), (1080, 720, 'small')]:
            window.resize(width, height)
            for _ in range(8): app.processEvents()
            assert window.trial.height_plot.height() >= 190
            assert window.trial.quote_plot.height() >= 190
            window.grab().save(f'artifacts/trial-{label}.png')
        window.trial.ball.setCurrentIndex(4)
        assert window.view.prediction_ball == 4
        window.clear()
        assert window.trial.state is None
        assert window.trial.round_label.text() == 'Waiting for fresh motion history'
finally:
    source.close()
    window.close()
print(f'{kind}: paper-market pipeline and rendering PASS')
