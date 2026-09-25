"""File PTS, live monotonic acquisition time, and labelled deterministic fixtures."""
from dataclasses import dataclass
from pathlib import Path
import time
import math
import sys
from threading import Thread, Condition
import av
import cv2
import numpy as np


@dataclass
class Frame:
    image: np.ndarray
    timestamp: float
    frame_id: int
    source: str


class Movie:
    def __init__(self, path, start=0.):
        if not Path(path).is_file():
            raise FileNotFoundError(f"Movie does not exist: {path}")
        self.container = av.open(str(path))
        self.stream = self.container.streams.video[0]
        self.origin = float((self.stream.start_time or 0)*self.stream.time_base)
        self.duration = float(self.stream.duration*self.stream.time_base) if self.stream.duration else 0.
        self.source = str(Path(path).resolve())
        self.frame_id = -1
        self.seek(start)

    def seek(self, target):
        self.target = max(0., target)
        self.container.seek(int((self.target+self.origin)/self.stream.time_base), stream=self.stream, backward=True)
        self.frames = self.container.decode(self.stream)
        self.frame_id = -1

    def read(self):
        for frame in self.frames:
            if frame.pts is None:
                raise ValueError("Movie frame has no presentation timestamp; refusing a guessed clock")
            timestamp = float(frame.pts*frame.time_base)-self.origin
            if timestamp+1e-7 < self.target:
                continue
            self.frame_id += 1
            image = frame.to_ndarray(format="bgr24")
            # FFmpeg display matrix uses counter-clockwise degrees.
            angle = getattr(frame, "rotation", 0)
            turns = round(angle/90) % 4
            if turns:
                rotation = {1: cv2.ROTATE_90_COUNTERCLOCKWISE, 2: cv2.ROTATE_180,
                            3: cv2.ROTATE_90_CLOCKWISE}[turns]
                image = cv2.rotate(image, rotation)
            return Frame(image, timestamp, self.frame_id, self.source)
        return None

    def close(self):
        self.container.close()


class Camera:
    duration = 0.

    def __init__(self, index, start=0.):
        self.capture = cv2.VideoCapture(int(index), cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"Camera {index} unavailable. For Continuity Camera, lock and mount the iPhone, enable Continuity Camera, and check the device index and macOS camera permission. After granting permission, reconnect.")
        self.source = f"camera:{index}"
        self.origin = time.monotonic()
        self.frame_id = -1
        self.condition = Condition()
        self.latest = None
        self.error = None
        self.stopped = False
        self.dropped = 0
        self.reader = Thread(target=self._acquire, daemon=True)
        self.reader.start()

    def _acquire(self):
        try:
            while not self.stopped:
                ok, image = self.capture.read()
                acquired = time.monotonic()
                with self.condition:
                    if not ok:
                        self.error = "Camera stopped delivering frames"
                        self.condition.notify_all()
                        return
                    self.frame_id += 1
                    if self.latest is not None:
                        self.dropped += 1
                    self.latest = Frame(image, acquired-self.origin, self.frame_id, self.source)
                    self.condition.notify_all()
        finally:
            self.capture.release()

    def read(self):
        with self.condition:
            ready = self.condition.wait_for(lambda: self.latest is not None or self.error or self.stopped, timeout=2)
            if not ready or self.error:
                raise RuntimeError(self.error or "Camera timed out")
            frame, self.latest = self.latest, None
            return frame

    def close(self):
        with self.condition:
            self.stopped = True
            self.condition.notify_all()
        self.reader.join(timeout=2)


class Synthetic:
    duration = 0.
    source = "SYNTHETIC TEST — not physical evidence"

    def __init__(self, path=None, start=0.):
        self.frame_id = int(start*30)-1
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.markers = [cv2.aruco.generateImageMarker(dictionary, i, 64) for i in range(6)]

    def read(self):
        self.frame_id += 1
        t = self.frame_id/30
        image = np.full((1080, 720, 3), 22, dtype=np.uint8)
        cv2.ellipse(image, (360, 520), (300, 470), 0, 0, 360, (75, 78, 80), 2)
        cv2.putText(image, "SYNTHETIC TEST", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, .8, (190, 190, 190), 1)
        for mid in range(6):
            if mid < 5 and (int(t)+mid)%7 == 0:
                continue  # explicit fixture gap; never applied to real video
            x = int(150+mid*75+50*math.sin(t*.8+mid))
            y = int(450+270*math.sin(t*.7+mid*1.3))
            cv2.circle(image, (x, y), 55, (35, 112, 220), -1)
            image[y-40:y+40, x-40:x+40] = 245
            image[y-32:y+32, x-32:x+32] = self.markers[mid][:, :, None]
        return Frame(image, t, self.frame_id, self.source)

    def close(self):
        pass


def open_source(kind, value=None, start=0.):
    return {"movie": Movie, "camera": Camera, "synthetic": Synthetic}[kind](value, start)
