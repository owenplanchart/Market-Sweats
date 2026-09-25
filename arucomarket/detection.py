"""TD baseline: half-resolution, default 4x4_50 detector, no enhancement."""
from dataclasses import dataclass, asdict
import cv2
import numpy as np
from .config import Config


@dataclass(frozen=True)
class Observation:
    observation_id: str
    timestamp: float
    marker_id: int
    corners: list[list[float]]  # upright source pixels, before user transforms
    centre: list[float]
    display_corners: list[list[float]]
    display_centre: list[float]
    normalised: list[float]  # x right, y down within configured ROI
    marker_scale: float
    frame_id: int
    source: str

    def to_dict(self):
        return asdict(self)


class Geometry:
    """User rotations/mirror are affine; ROI normalises without cropping evidence."""
    def __init__(self, width, height, config):
        self.raw_size = (width, height)
        self.matrix = np.eye(3)
        for _ in range(config.rotation_quarters):
            self.matrix = np.array([[0, -1, height-1], [1, 0, 0], [0, 0, 1]]) @ self.matrix
            width, height = height, width
        if config.mirror:
            self.matrix = np.array([[-1, 0, width-1], [0, 1, 0], [0, 0, 1]]) @ self.matrix
        self.size = width, height
        self.roi = config.roi

    def points(self, points):
        p = np.asarray(points)
        return (np.c_[p, np.ones(len(p))] @ self.matrix.T)[:, :2]

    def image(self, image):
        if np.array_equal(self.matrix, np.eye(3)):
            return image  # no 4K copy/warp needed for the default presentation
        return cv2.warpAffine(image, self.matrix[:2], self.size, flags=cv2.INTER_NEAREST)

    def normalise(self, point):
        x, y, w, h = self.roi
        width, height = self.size
        return [(point[0] / max(1, width-1) - x) / w,
                (point[1] / max(1, height-1) - y) / h]


class Detector:
    def __init__(self, config: Config):
        self.config = config
        self.detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
            cv2.aruco.DetectorParameters())

    def detect(self, bgr, timestamp, frame_id, source, epoch=0):
        h, w = bgr.shape[:2]
        geometry = Geometry(w, h, self.config)
        aw, ah = max(1, round(w*self.config.analysis_scale)), max(1, round(h*self.config.analysis_scale))
        reduced = cv2.resize(bgr, (aw, ah), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(reduced, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        observations = []
        for i, (pts, mid) in enumerate(zip(corners, [] if ids is None else ids.flatten())):
            if int(mid) not in self.config.active_ids:
                continue  # before every downstream output, including debug overlays
            # Pixel-centre mapping through OpenCV resize, including odd dimensions.
            raw = (pts[0].astype(float) + .5) * [w/aw, h/ah] - .5
            centre = raw.mean(axis=0)
            shown = geometry.points(raw)
            display_centre = shown.mean(axis=0)
            side = np.linalg.norm(np.roll(raw, -1, axis=0)-raw, axis=1).mean()
            observations.append(Observation(
                f"{epoch}:{frame_id}:{i}", float(timestamp), int(mid), raw.tolist(), centre.tolist(),
                shown.tolist(), display_centre.tolist(), geometry.normalise(display_centre),
                float(side / max(w, h)), frame_id, source))
        return geometry.image(bgr), observations
