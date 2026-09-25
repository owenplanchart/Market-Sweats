"""Inspect selected short segments, never claim a full-footage detection benchmark."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import time
import statistics
from collections import Counter
import cv2
import numpy as np
from arucomarket.config import Config
from arucomarket.capture import Movie
from arucomarket.detection import Detector
from arucomarket.state import Engine

config = Config.load('config.json')
detector = Detector(config)
results, previews = [], []
for start in [0,15,30,45]:
    movie = Movie(config.movie, start)
    engine = Engine(config)
    counts, timings = Counter(), []
    frames = samples = ambiguous = 0
    best = None
    while True:
        frame = movie.read()
        if frame is None or frame.timestamp >= start+1:
            break
        before = time.perf_counter()
        image, raw = detector.detect(frame.image, frame.timestamp, frame.frame_id, frame.source)
        timings.append((time.perf_counter()-before)*1000)
        fresh = engine.process(frame.timestamp, frame.frame_id, frame.source, raw)
        samples += len(fresh)
        ambiguous += sum(v == 'ambiguous' for v in engine.states.values())
        frames += 1
        counts.update(o.marker_id for o in raw)
        if best is None or len(raw) > best[0]:
            best = len(raw), image, raw, frame.timestamp
    movie.close()
    _, image, raw, timestamp = best
    for o in raw:
        pts = np.array(o.display_corners,dtype=np.int32)
        cv2.polylines(image,[pts],True,(60,255,90),5)
        xy = tuple(np.array(o.display_centre,dtype=int))
        cv2.putText(image,str(o.marker_id),xy,cv2.FONT_HERSHEY_SIMPLEX,2,(60,255,90),4)
    image = cv2.resize(image,(360,640))
    cv2.putText(image,f'{timestamp:.3f}s / {len(raw)} markers',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    previews.append(image)
    results.append({'start':start,'seconds':1,'frames':frames,'raw_by_id':dict(counts),'ball_samples':samples,
                    'ambiguous_ball_frames':ambiguous,'median_detection_and_transform_ms':statistics.median(timings),
                    'max_detection_and_transform_ms':max(timings)})
cv2.imwrite('artifacts/footage-contact-sheet.jpg',np.concatenate(previews,axis=1))
Path('artifacts/footage-report.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
