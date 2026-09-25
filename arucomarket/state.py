"""Headless observations and a separate source-time experimental paper market."""
from collections import deque
from dataclasses import dataclass, asdict
import math
import numpy as np
from .config import Config
from .prediction import PaperMarket


@dataclass(frozen=True)
class Sample:
    marker_id: int
    timestamp: float
    frame_id: int
    centre: list[float]
    normalised: list[float]
    marker_scale: float
    contributors: list[str]
    index: float


@dataclass
class Candle:
    start: float
    open: float
    high: float
    low: float
    close: float
    count: int = 1

    def add(self, value):
        self.high = max(self.high, value)
        self.low = min(self.low, value)
        self.close = value
        self.count += 1


class Engine:
    def __init__(self, config: Config):
        self.config = config
        self.reset()

    def reset(self):
        self.market = PaperMarket(self.config)
        self.timestamp = None
        self.frame_id = None
        self.source = None
        self.histories = {i: deque(maxlen=self.config.history_limit) for i in self.config.active_ids}
        self.candles = {i: deque(maxlen=self.config.history_limit) for i in self.config.active_ids}
        self.states = {i: "lost" for i in self.config.active_ids}
        self.raw = []

    def process(self, timestamp, frame_id, source, observations):
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("Invalid source timestamp")
        if self.timestamp is not None:
            if source == self.source and frame_id == self.frame_id and timestamp == self.timestamp:
                return []  # repeated UI refresh / repeated replay frame is not evidence
            if source != self.source or timestamp <= self.timestamp or frame_id <= self.frame_id:
                self.reset()
        self.timestamp, self.frame_id, self.source = timestamp, frame_id, source
        self.raw = [o for o in observations if o.marker_id in self.config.active_ids]
        for o in self.raw:
            if o.timestamp != timestamp or o.frame_id != frame_id or o.source != source:
                raise ValueError("Observation metadata does not match its source frame")
            if not np.isfinite([*o.normalised, *o.display_centre, o.marker_scale]).all():
                raise ValueError("Non-finite observation")
        fresh = []
        for mid in self.config.active_ids:
            group = [o for o in self.raw if o.marker_id == mid]
            history = self.histories[mid]
            self.states[mid] = "stale" if history and timestamp-history[-1].timestamp <= self.config.lost_after else "lost"
            if not group:
                continue
            xy = np.array([o.normalised for o in group])
            # Conservative complete-link test: do not choose a reflection cluster silently.
            diameter = np.linalg.norm(xy[:, None]-xy[None, :], axis=2).max()
            if diameter > self.config.group_distance:
                self.states[mid] = "ambiguous"
                continue
            centre = np.median([o.display_centre for o in group], axis=0).tolist()
            norm = np.median(xy, axis=0).tolist()
            sample = Sample(mid, timestamp, frame_id, centre, norm,
                            float(np.median([o.marker_scale for o in group])),
                            [o.observation_id for o in group],
                            self.config.index_base + self.config.index_gain*norm[0])
            history.append(sample)
            fresh.append(sample)
            self.states[mid] = "observed"
            start = math.floor(timestamp/self.config.candle_seconds)*self.config.candle_seconds
            candles = self.candles[mid]
            if candles and candles[-1].start == start:
                candles[-1].add(sample.index)
            else:
                candles.append(Candle(start, sample.index, sample.index, sample.index, sample.index))
        self.market.process(timestamp, self.histories, self.states)
        return fresh

    def snapshot(self):
        return {
            "timestamp": self.timestamp, "frame_id": self.frame_id, "source": self.source,
            "states": self.states.copy(), "raw": [o.to_dict() for o in self.raw],
            "histories": {i: [asdict(s) for s in h] for i, h in self.histories.items()},
            "candles": {i: [asdict(c) for c in cs] for i, cs in self.candles.items()},
            "market": self.market.snapshot(),
        }
