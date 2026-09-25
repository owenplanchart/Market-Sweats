from dataclasses import replace
import json
import numpy as np
import cv2
import pytest
from arucomarket.config import Config
from arucomarket.detection import Detector, Geometry, Observation
from arucomarket.state import Engine
from arucomarket.recording import Recorder, replay
from arucomarket.capture import Frame, Movie, Synthetic


def obs(mid=0, t=0., frame=0, x=.3, y=.4, oid=None):
    return Observation(oid or f'{frame}:{mid}:{x}', t, mid, [[x*100,y*100]]*4,
                       [x*100,y*100], [[x*100,y*100]]*4, [x*100,y*100], [x,y], .02, frame, 'test')


def test_filter_every_id_before_drawing_and_logs():
    image = np.full((500, 1000, 3), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for i, mid in enumerate([0, 1, 2, 3, 4, 5, 49]):
        x, y = 30+(i%4)*240, 30+(i//4)*240
        marker = cv2.aruco.generateImageMarker(dictionary, mid, 160)
        image[y:y+160, x:x+160] = marker[:, :, None]
    _, raw = Detector(Config()).detect(image, 0., 0, 'fixture')
    assert sorted(o.marker_id for o in raw) == [0, 1, 2, 3, 4]
    e = Engine(Config())
    e.process(0, 0, 'test', [obs(i) for i in range(8)])
    assert {o.marker_id for o in e.raw} == set(range(5))


def test_simultaneous_copies_are_preserved_but_one_market_sample():
    e = Engine(Config())
    raw = [obs(x=.3), obs(x=.32), obs(x=.34)]
    fresh = e.process(0, 0, 'test', raw)
    assert len(e.raw) == 3
    assert len(fresh) == 1
    assert fresh[0].normalised[0] == pytest.approx(.32)
    assert len(fresh[0].contributors) == 3
    assert e.candles[0][0].count == 1


def test_real_detector_retains_same_id_copies():
    image = np.full((600, 1000, 3), 255, np.uint8)
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), 2, 120)
    for x in [100, 500]:
        image[100:220, x:x+120] = marker[:, :, None]
    _, raw = Detector(Config()).detect(image, 1., 10, 'fixture')
    assert [o.marker_id for o in raw] == [2, 2]
    e = Engine(Config())
    assert e.process(1., 10, 'fixture', raw) == []
    assert e.states[2] == 'ambiguous'


def test_ambiguity_keeps_last_seen_without_new_sample():
    e = Engine(Config())
    e.process(0, 0, 'test', [obs()])
    assert e.process(.2, 1, 'test', [obs(t=.2, frame=1, x=.2), obs(t=.2, frame=1, x=.8)]) == []
    assert e.states[0] == 'ambiguous'
    assert e.histories[0][-1].timestamp == 0


def test_missing_is_not_zero_empty_intervals_freshness_and_duplicate_frames():
    e = Engine(Config())
    raw = [obs(t=.1)]
    e.process(.1, 0, 'test', raw)
    assert e.process(.1, 0, 'test', raw) == []
    e.process(.2, 1, 'test', [])
    assert e.states[0] == 'stale'
    e.process(4., 2, 'test', [])
    assert e.states[0] == 'lost'
    assert not e.histories[1]
    e.process(5.1, 3, 'test', [obs(t=5.1, frame=3, x=.6)])
    assert [c.start for c in e.candles[0]] == [0., 5.]
    assert [c.close for c in e.candles[0]] == [130., 160.]


def test_ohlc_irregular_timestamps():
    e = Engine(Config())
    for frame, (t,x) in enumerate([(0.,.4),(.04,.2),(.78,.8),(.99,.3),(1.,.6)]):
        e.process(t, frame, 'test', [obs(t=t, frame=frame, x=x)])
    c = e.candles[0][0]
    assert (c.open,c.high,c.low,c.close,c.count) == (140,180,120,130,4)
    assert e.candles[0][1].open == 160


def test_seek_source_changes_and_histories_bounded():
    e = Engine(Config(history_limit=3))
    for i in range(8):
        e.process(float(i), i, 'test', [obs(t=float(i), frame=i)])
    assert len(e.histories[0]) == len(e.candles[0]) == 3
    e.process(1., 0, 'test', [obs(t=1.)])
    assert len(e.histories[0]) == len(e.candles[0]) == 1
    e.process(2., 1, 'new source', [])
    assert not e.histories[0]


@pytest.mark.parametrize('rotation', [0,1,2,3])
@pytest.mark.parametrize('mirror', [False, True])
def test_transform_alignment(rotation, mirror):
    image = np.zeros((5,7,3), np.uint8)
    image[1,2] = 255
    g = Geometry(7, 5, Config(rotation_quarters=rotation, mirror=mirror))
    point = g.points([[2,1]])[0].astype(int)
    transformed = g.image(image)
    assert (transformed[point[1], point[0]] == 255).all()
    assert transformed.shape[:2] == g.size[::-1]


def test_roi_has_no_silent_clamp():
    g = Geometry(101,101,Config(roi=[.25,.25,.5,.5]))
    assert g.normalise([50,50]) == [.5,.5]
    assert g.normalise([0,0]) == [-.5,-.5]


def test_jsonl_roundtrip_including_empty_frames_and_resets(tmp_path):
    path = tmp_path/'session.jsonl'
    e = Engine(Config())
    r = Recorder(path, e.config)
    for i, t in enumerate([0., .1, 2.]):
        raw = [obs(t=t, frame=i)] if i == 0 else []
        r.frame(Frame(np.zeros((2,2,3), np.uint8), t, i, 'test'), raw)
        e.process(t, i, 'test', raw)
    r.close()
    assert replay(path).snapshot() == e.snapshot()
    with pytest.raises(FileExistsError):
        Recorder(path, e.config)
    with path.open('a') as f:
        f.write(json.dumps({'type':'reset','reason':'seek','epoch':1})+'\n')
    assert not replay(path).histories[0]


def test_invalid_config_and_timestamp():
    with pytest.raises(ValueError): Config(active_ids=[0,1,2,3,4,5])
    with pytest.raises(ValueError): Config(candle_seconds=0)
    with pytest.raises(ValueError): Engine(Config()).process(float('nan'), 0, 'x', [])


def test_movie_pts_and_seek(tmp_path):
    import av
    path = tmp_path/'timing.mp4'
    with av.open(str(path), 'w') as out:
        stream = out.add_stream('mpeg4', rate=10)
        stream.width, stream.height = 64,64
        stream.pix_fmt = 'yuv420p'
        for i in range(15):
            frame = av.VideoFrame.from_ndarray(np.full((64,64,3),i*10,np.uint8), format='bgr24')
            for packet in stream.encode(frame): out.mux(packet)
        for packet in stream.encode(): out.mux(packet)
    m = Movie(path)
    times = [m.read().timestamp for _ in range(3)]
    assert times == pytest.approx([0,.1,.2])
    m.seek(.8)
    f = m.read()
    assert f.timestamp == pytest.approx(.8)
    assert f.frame_id == 0
    m.close()


def test_camera_latest_frame_queue_and_drop_counter(monkeypatch):
    from threading import Event
    from arucomarket.capture import Camera
    release = Event()
    class FakeCapture:
        def __init__(self, index, backend): self.i = 0
        def isOpened(self): return True
        def read(self):
            if self.i == 3:
                release.wait(2)
                return False, None
            self.i += 1
            return True, np.full((3,3,3),self.i,np.uint8)
        def release(self): pass
    monkeypatch.setattr(cv2,'VideoCapture',FakeCapture)
    camera = Camera(0)
    try:
        with camera.condition:
            assert camera.condition.wait_for(lambda: camera.frame_id == 2, timeout=2)
        latest = camera.read()
        assert latest.frame_id == 2
        assert camera.dropped == 2
        assert latest.timestamp >= 0
    finally:
        release.set()
        camera.close()
    assert not camera.reader.is_alive()


def test_worker_preserves_last_snapshot_at_eof(monkeypatch):
    import time
    import arucomarket.worker as worker_module
    class ShortSource(Synthetic):
        def read(self):
            return super().read() if self.frame_id < 2 else None
    monkeypatch.setattr(worker_module,'open_source',lambda *args: ShortSource())
    worker = worker_module.Worker(Config(),'synthetic',None)
    worker.start()
    try:
        deadline = time.monotonic()+3
        while time.monotonic()<deadline:
            item = worker.output.get(timeout=2)
            assert 'error' not in item
            if item.get('eof'):
                assert item['state']['frame_id'] == 2
                assert item['state']['timestamp'] == pytest.approx(2/30)
                break
        else:
            pytest.fail('EOF not delivered')
    finally:
        worker.stopping.set()
        worker.join(2)


def test_slow_movie_decode_cannot_starve_playback(monkeypatch):
    """Decode slower than PTS cadence must still produce fresh display frames."""
    from types import SimpleNamespace
    import arucomarket.worker as worker_module
    now = [0.]
    class Stop:
        stopped = False
        def is_set(self): return self.stopped
        def set(self): self.stopped = True
        def wait(self, seconds): now[0] += seconds
    class SlowMovie:
        duration = 1.
        i = -1
        def read(self):
            self.i += 1
            now[0] += .08  # 80ms decode for a 33ms source interval
            if self.i == 30: return None
            return Frame(np.zeros((8,8,3),np.uint8), self.i/30, self.i, 'slow fixture')
        def close(self): pass
    class PassThroughDetector:
        def __init__(self, config): pass
        def detect(self, image, *args): return image, []
    monkeypatch.setattr(worker_module,'open_source',lambda *args: SlowMovie())
    monkeypatch.setattr(worker_module,'Detector',PassThroughDetector)
    monkeypatch.setattr(worker_module,'time',SimpleNamespace(monotonic=lambda:now[0],perf_counter=lambda:now[0]))
    worker = worker_module.Worker(Config(),'movie','fixture')
    worker.stopping = Stop()
    frames = []
    def collect(payload):
        assert 'error' not in payload, payload
        if payload.get('eof'):
            worker.stopping.set()
        elif 'state' in payload:
            frames.append(payload)
    worker.publish = collect
    worker.run()
    ids = [p['state']['frame_id'] for p in frames]
    assert len(ids) >= 10, 'Slow playback must not skip every subsequent frame'
    assert ids[-1] >= 27
    assert max(b-a for a,b in zip(ids,ids[1:])) <= 3
    assert worker.dropped > 0
    assert frames[-1]['playback_resyncs'] > 0
    for p in frames:
        assert p['state']['timestamp'] == p['state']['frame_id']/30
