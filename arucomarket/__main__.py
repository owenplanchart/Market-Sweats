import argparse
import json
from pathlib import Path
from .config import Config


def main():
    parser = argparse.ArgumentParser(description="ArUcoMarket Stage 1 — artistic observed index")
    parser.add_argument("--config", default="config.json")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--movie")
    source.add_argument("--camera", type=int)
    source.add_argument("--synthetic", action="store_true")
    source.add_argument("--replay", help="Headless JSONL replay and state summary")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--seconds", type=float, default=5, help="Headless source-time segment length")
    parser.add_argument("--log", help="New JSONL path; refuses overwrite")
    args = parser.parse_args()
    if args.replay:
        from .recording import replay
        print(json.dumps(replay(args.replay).snapshot(), indent=2))
        return
    config = Config.load(args.config)
    kind, value = "movie", args.movie or config.movie
    if args.synthetic:
        kind, value = "synthetic", None
    elif args.camera is not None:
        kind, value = "camera", args.camera
    if args.headless:
        from .capture import open_source
        from .detection import Detector
        from .state import Engine
        from .recording import Recorder
        source = open_source(kind, value, args.start)
        recorder = None
        engine, detector = Engine(config), Detector(config)
        frames = raw_count = samples = 0
        try:
            if args.log:
                recorder = Recorder(args.log, config)
            while True:
                frame = source.read()
                if frame is None or frame.timestamp >= args.start+args.seconds:
                    break
                _, observations = detector.detect(frame.image, frame.timestamp, frame.frame_id, frame.source)
                samples += len(engine.process(frame.timestamp, frame.frame_id, frame.source, observations))
                raw_count += len(observations)
                frames += 1
                if recorder:
                    recorder.frame(frame, observations)
            print(json.dumps({"source": source.source, "frames": frames, "raw_observations": raw_count,
                              "ball_samples": samples, "last_timestamp": engine.timestamp, "states": engine.states}, indent=2))
        finally:
            source.close()
            if recorder:
                recorder.close()
        return
    from PySide6.QtWidgets import QApplication
    from .ui import Window
    app = QApplication([])
    window = Window(config, kind, value, args.log)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
