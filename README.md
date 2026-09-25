# ArUcoMarket — Stage 1

A local screen-based installation prototype: camera/movie observations of five ArUco-marked balls, a position-derived artistic index, and observation-only OHLC. Missing evidence remains visible. No simulated trading, forecasts, audio or speaker control is implemented.

## To-do:
Lets create a precitive graph and a derivative graph how do we go about that?

## Run

The project virtual environment is already installed on this Mac. From this directory:

```sh
.venv/bin/python -m arucomarket
```

The default movie path is set in `config.json`. For other sources:

```sh
.venv/bin/python -m arucomarket --synthetic
.venv/bin/python -m arucomarket --movie /path/to/movie.MOV
.venv/bin/python -m arucomarket --camera 0
```

Movie starts playing immediately. Space pauses/resumes; Reset starts a new timeline; the slider seeks and clears history; Escape exits fullscreen. Drag the splitter to change camera/market proportions. Choose the ball for the OHLC panel. Layer toggles and trail persistence affect presentation only. The five ticker rows show current or explicitly held values, age and state. Dashed connections join sightings across long gaps; they do not assert an unseen trajectory.

The default **Fit screen** layout keeps the portrait dome feed beside the markets on wide screens and stacks the views on tall screens. On wide screens, the two charts sit beside each other below the ticker. The provisional 900×1600 window is fitted to the available desktop at startup. Choose **Portrait views / Side by side** to override the arrangement without changing observations, coordinates or index values. Drag either divider to allocate space; the camera image fits without cropping or stretching. Charts have a minimum readable height; a forced tall layout on a short screen scrolls instead of flattening the plots.

The **Observed index** chart connects every consecutive sighting within each ball’s retained history. Short gaps use solid lines; gaps longer than `gap_seconds` use dashed lines between the actual endpoints. Dots remain genuine sightings, and lines never connect different balls or extend beyond the last sighting.

The second chart, **OHLC / Observed range**, summarises each source-time interval for the selected ball. Open and close are its first and last observed index values; high and low are the extrema. The body spans open to close and the wick spans low to high. A single value becomes a dash; an interval without sightings is blank. These summarise the artistic position index, not trades. Hover over the chart for a reminder.

## Vertical iPhone / Continuity Camera

Confirmed setup: mount the phone vertically to capture the full dome and connect through **Continuity Camera**. Camera capture explicitly uses macOS AVFoundation. The actual device index and delivered image orientation still require a live check; no camera was activated during development.

1. Enable Continuity Camera under iPhone Settings → General → AirPlay & Continuity (or AirPlay & Handoff). Use the same Apple Account with two-factor authentication on both devices, with Wi-Fi and Bluetooth enabled.
2. Mount the iPhone securely, locked, with its rear cameras facing the dome. Apple supports portrait mounting. Continuity can connect wirelessly or over USB; for USB, trust the Mac on the phone.
3. In ArUcoMarket, choose the **Device** index corresponding to the iPhone and click **Connect iPhone / camera**. Index 0 is only a placeholder and may select the Mac's built-in camera. Grant macOS camera permission and reconnect if the first attempt requests access.
4. Check that the entire dome is upright and visible. We suggest disabling Center Stage and background-blur effects to keep the scene stable and markers unaltered. If the delivered image is sideways, set `rotation_quarters` in a live-session config before restarting; do not force a rotation on an already upright feed. This transform also applies to movie playback when using that config.

Apple's [Continuity Camera setup guide](https://support.apple.com/en-in/102546) covers connection and permissions. Portrait display layout and physical phone orientation are independent; switching views does not rotate the input image. Live discovery, orientation and latency remain unverified on this iPhone.

## Fresh installation

Tested on this Mac with Python 3.11.14, arm64, macOS 15.7.3. Use Python 3.11 (the system Python 3.9 is too old for this project):

```sh
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements-lock.txt
.venv/bin/python -m arucomarket
```

The pins were installed and tested together. The PyAV wheel requires macOS 14 or newer. Do not install a second OpenCV wheel alongside `opencv-contrib-python`. Qt's CPU feature probe failed inside the Codex sandbox but passed outside it; run the app normally from Terminal.

## Record and replay

```sh
mkdir -p logs
.venv/bin/python -m arucomarket --log logs/session-001.jsonl
.venv/bin/python -m arucomarket --headless --start 15 --seconds 1 --log logs/clip-15.jsonl
.venv/bin/python -m arucomarket --replay logs/clip-15.jsonl
```

Choose a new log filename each time. Replay prints final observation/market state; it does not replay video. Headless movie processing is unpaced and analyses every decoded frame in the requested segment. Source time, not wall time, controls OHLC.

## Configuration and validation

`config.json` fixes IDs 0–4 and holds analysis scale, ROI, presentation transform, grouping distance, index formula, history bounds and window size. Default ROI is explicitly the whole frame; set a dome ROI before starting an exhibition session if desired. Mapping and ROI remain fixed during a session. The index is an artistic abstraction, not a traded price.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_footage.py
.venv/bin/python scripts/verify_ui.py
.venv/bin/python scripts/verify_playback.py
```

The UI check runs offscreen and writes preview PNGs to `artifacts/`. The playback check runs the real movie worker and Qt interface together for eight seconds to detect stalls. The footage check analyses four selected one-second clips. It is not a whole-movie accuracy benchmark. Under sustained processing load the movie can slow down, but consecutive frame skips are bounded so playback cannot freeze in an endless catch-up loop; source timestamps remain unchanged.

Read [verification results](docs/verification.md), [TD behavioural inventory](docs/reference-inventory.md), and [architecture/data definitions](docs/architecture.md). Local previews: [interface](artifacts/ui-preview.png), [footage overlays](artifacts/footage-contact-sheet.jpg).

References used for API checks: [OpenCV ArucoDetector](https://docs.opencv.org/4.7.0/d2/d1a/classcv_1_1aruco_1_1ArucoDetector.html), [PyAV timestamps](https://pyav.org/docs/stable/api/time.html), [Qt for Python setup](https://doc.qt.io/qtforpython-6.8/gettingstarted.html).
