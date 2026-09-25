"""Capture/analysis outside Qt. Latest-only display mailbox; fixed-size controls."""
from queue import Queue, Empty, Full
from threading import Thread, Event
import time
from .capture import open_source
from .detection import Detector
from .state import Engine
from .recording import Recorder


class Worker(Thread):
    def __init__(self, config, kind, value, log=None):
        super().__init__(daemon=True)
        self.config, self.kind, self.value = config, kind, value
        self.log_path = log
        self.output = Queue(maxsize=1)
        self.commands = Queue(maxsize=16)
        self.stopping = Event()
        self.paused = False
        self.dropped = 0
        self.display_dropped = 0
        self.playback_resyncs = 0
        self.epoch = 0

    def command(self, name, value=None):
        try:
            self.commands.put_nowait((name, value))
            return True
        except Full:
            return False

    def publish(self, payload):
        try:
            self.output.put_nowait(payload)
        except Full:
            try:
                self.output.get_nowait()
            except Empty:
                pass
            self.display_dropped += 1
            self.output.put_nowait(payload)

    def run(self):
        source = recorder = None
        engine, detector = Engine(self.config), Detector(self.config)
        anchor = None
        pending = None
        eof = False
        last_payload = None
        consecutive_skips = 0
        try:
            if self.log_path:
                recorder = Recorder(self.log_path, self.config)
            source = open_source(self.kind, self.value)
            while not self.stopping.is_set():
                changed = False
                while True:
                    try:
                        name, value = self.commands.get_nowait()
                    except Empty:
                        break
                    if name == "pause":
                        self.paused = bool(value)
                        anchor = None
                        consecutive_skips = 0
                    elif name in ("source", "seek", "reset"):
                        if name == "source":
                            self.kind, self.value = value
                        target = float(value) if name == "seek" else 0.
                        source.close()
                        source = open_source(self.kind, self.value, target)
                        engine.reset()
                        pending, anchor, eof = None, None, False
                        last_payload = None
                        consecutive_skips = 0
                        self.epoch += 1
                        changed = True
                        if recorder:
                            recorder.reset(name, self.epoch)
                if changed:
                    self.publish({"clear": True, "paused": self.paused})
                if self.paused or eof:
                    self.stopping.wait(.015)
                    continue
                if pending is None:
                    pending = source.read()
                if pending is None:
                    if self.kind == "movie" and self.config.loop:
                        self.command("reset")
                    else:
                        eof = True
                        self.publish({**(last_payload or {}), "eof": True})
                    continue
                frame = pending
                if self.kind != "camera":
                    if anchor is None:
                        anchor = time.monotonic()-frame.timestamp
                    remaining = anchor+frame.timestamp-time.monotonic()
                    if remaining > 0:
                        self.stopping.wait(min(remaining, .01))
                        continue
                    if remaining < -.15:
                        if consecutive_skips < 2:
                            self.dropped += 1
                            consecutive_skips += 1
                            pending = None
                            continue
                        # Decode itself may be slower than source cadence. Skipping
                        # cannot catch up in that case: rebase wall-time scheduling,
                        # show this frame, and retain its original source PTS.
                        anchor = time.monotonic()-frame.timestamp
                        self.playback_resyncs += 1
                consecutive_skips = 0
                pending = None
                started = time.perf_counter()
                image, observations = detector.detect(frame.image, frame.timestamp, frame.frame_id, frame.source, self.epoch)
                engine.process(frame.timestamp, frame.frame_id, frame.source, observations)
                if recorder:
                    recorder.frame(frame, observations)
                last_payload = {"image": image, "state": engine.snapshot(),
                              "duration": source.duration, "kind": self.kind,
                              "analysis_ms": (time.perf_counter()-started)*1000,
                              "dropped": self.dropped, "camera_dropped": getattr(source, "dropped", 0),
                              "playback_resyncs": self.playback_resyncs,
                              "display_dropped": self.display_dropped}
                self.publish(last_payload)
        except Exception as exc:
            self.publish({"error": f"{type(exc).__name__}: {exc}"})
        finally:
            if source:
                source.close()
            if recorder:
                recorder.close()
