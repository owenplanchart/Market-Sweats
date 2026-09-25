"""Session configuration. Index mapping and geometry are fixed until restart."""
from dataclasses import dataclass, asdict, field
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Config:
    movie: str = ""
    active_ids: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    analysis_scale: float = 0.5
    roi: list[float] = field(default_factory=lambda: [0., 0., 1., 1.])
    rotation_quarters: int = 0
    mirror: bool = False
    group_distance: float = 0.12
    lost_after: float = 3.
    gap_seconds: float = 0.5
    trail_seconds: float = 8.
    history_limit: int = 1800
    candle_seconds: float = 1.
    index_base: float = 100.
    index_gain: float = 100.
    window_width: int = 900
    window_height: int = 1600
    layout: str = "auto"
    camera_index: int = 0
    loop: bool = False

    def __post_init__(self):
        if self.active_ids != [0, 1, 2, 3, 4]:
            raise ValueError("The confirmed active IDs must be exactly [0, 1, 2, 3, 4]")
        if not 0 < self.analysis_scale <= 1:
            raise ValueError("analysis_scale must be in (0, 1]")
        if len(self.roi) != 4 or not all(math.isfinite(v) for v in self.roi):
            raise ValueError("roi must contain four finite fractions")
        x, y, w, h = self.roi
        if min(x, y) < 0 or min(w, h) <= 0 or x+w > 1 or y+h > 1:
            raise ValueError("roi must lie inside the image")
        for name in ("group_distance", "lost_after", "gap_seconds", "trail_seconds", "candle_seconds"):
            v = getattr(self, name)
            if not math.isfinite(v) or v <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.history_limit < 2 or self.rotation_quarters not in (0, 1, 2, 3):
            raise ValueError("Invalid history limit or rotation")
        if not all(math.isfinite(v) for v in (self.index_base, self.index_gain)):
            raise ValueError("Index mapping must be finite")
        if min(self.window_width, self.window_height) < 320:
            raise ValueError("Window dimensions must be at least 320")
        if self.layout not in ("auto", "portrait", "side_by_side"):
            raise ValueError("layout must be auto, portrait or side_by_side")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text()))

    def to_dict(self):
        return asdict(self)
