"""Versioned, frame-based JSONL with empty frames and explicit temporal resets."""
import json
from .config import Config
from .detection import Observation
from .state import Engine


class Recorder:
    def __init__(self, path, config):
        self.file = open(path, "x", encoding="utf8")  # never overwrite an existing session
        self.write({"type": "session", "schema": 1, "config": config.to_dict()})

    def write(self, record):
        self.file.write(json.dumps(record, allow_nan=False)+"\n")
        self.file.flush()

    def reset(self, reason, epoch):
        self.write({"type": "reset", "reason": reason, "epoch": epoch})

    def frame(self, frame, observations):
        self.write({"type": "frame", "timestamp": frame.timestamp, "frame_id": frame.frame_id,
                    "source": frame.source, "source_size": list(frame.image.shape[1::-1]),
                    "observations": [o.to_dict() for o in observations]})

    def close(self):
        self.file.close()


def replay(path):
    engine = None
    with open(path, encoding="utf8") as file:
        for line in file:
            row = json.loads(line)
            if row["type"] == "session":
                if row["schema"] != 1:
                    raise ValueError("Unsupported log schema")
                engine = Engine(Config(**row["config"]))
            elif engine is None:
                raise ValueError("Log is missing session header")
            elif row["type"] == "reset":
                engine.reset()
            elif row["type"] == "frame":
                engine.process(row["timestamp"], row["frame_id"], row["source"],
                               [Observation(**o) for o in row["observations"]])
    if engine is None:
        raise ValueError("Empty log")
    return engine
