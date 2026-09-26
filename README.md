# ArUcoMarket — UP / DOWN trial

A local screen-based installation prototype: camera/movie observations of five ArUco-marked balls, a position-derived artistic index, observation-only OHLC, and an experimental automatic UP/DOWN paper market. Missing evidence remains visible. All stakes and payouts are virtual. Audio and speaker control are not implemented.

## TODOs

- [x] **Show multiple balls together in both trial charts:** all five balls are enabled by default in the **Height** and **Credits per unit** charts. The coloured **Show** checkboxes control each ball independently, while **Focus** selects the detailed forecast band, contract text, result ledger and camera ghost. Clicking a ticker row focuses and reveals that ball.
- [x] **Add Q to quit the application:** pressing **Q** or **Shift+Q** while the application is active exits the whole Qt application, stops its worker, and releases the source/recording. Space pauses/resumes, and Escape exits fullscreen.
- [ ] **Make the charts read more clearly as financial graphs:** review the visual language of the market panels and explore recognisable financial treatments such as green/red candlesticks, while keeping observations, forecasts, quotes and settlements truthful and distinguishable.
- [ ] **Translate graph activity into regulatory and free-market speech:** develop a concept for turning market movements, forecasts, uncertainty and outcomes into spoken language resembling speeches or senate-hearing exchanges about regulation and the free market. Define the mapping and tone before choosing or implementing speech-generation and audio tools.

## Handoff for a new chat

**Current checkpoint — 26 September 2026:** the continuous-quote trial works with the movie, both trial charts can show all five balls together with independent visibility controls, and Q exits the entire application regardless of whether a chart, control, or fullscreen view has focus. The next work is to strengthen the charts' recognisable financial visual language, then design how graph activity could drive regulatory and free-market speech or senate-hearing dialogue.

The GitHub project is [Market-Sweats](https://github.com/owenplanchart/Market-Sweats), on branch `main`. This Mac's working folder is `/Users/owenplanchart/Developer/Python/marketSweats1`; the Python package and application are named `arucomarket`. Continue from the working implementation, including the original observation charts and the newer paper-market tab.

For a new chat, use this starting message:

> Continue the Market-Sweats project in this workspace. Read README.md, especially TODOs and the handoff, then docs/architecture.md and docs/verification.md. Check the Git working tree before editing. The four-second automatic UP/DOWN market, continuous estimated quotes, five-ball Height and Credits-per-unit views, and application-wide Q quit command are working. Help me define and tackle the next scoped task while preserving the current source-time, observation and settlement behaviour.

### Development workflow

1. Read this README and the linked architecture/verification notes, then inspect `git status`. Preserve existing work and identify which TODO is being addressed.
2. Launch `.venv/bin/python -m arucomarket` from the project root to use the configured movie. Use `.venv/bin/python -m arucomarket --synthetic` for a repeatable demonstration. The local virtual environment is ready on this Mac; see **Fresh installation** for another machine.
3. Check both input types when changing forecasting or market presentation. Synthetic sightings are frequent; real movie sightings are intermittent. A smooth synthetic demonstration alone does not verify the movie workflow.
4. Change the relevant files below. Keep real observations, interpolated fitting points, extrapolated estimates and settled outcomes distinct. Preserve the shared Show controls and focused-ball detail when changing either trial chart.
5. Run `.venv/bin/python -m pytest -q` for engine changes. Use `scripts/verify_trial.py` and `scripts/verify_trial.py --movie` for trial UI/quote changes, `scripts/verify_ui.py` for the original charts and controls, `scripts/verify_playback.py` for threaded playback changes, and `scripts/verify_quit.py` for application-wide Q shutdown. Inspect relevant screenshots under `artifacts/`. These standalone scripts are not all part of pytest. Qt checks need a normal native environment; its CPU-feature probe can fail inside the sandbox with a NEON error.
6. Relaunch the application after code changes; an already running window does not reload Python modules. Movie reset/seek clears the session, bets and virtual balances. Keep README behaviour, TODO completion and verification notes current with the implementation.
7. When committing a requested checkpoint, review `git diff --check` and the staged files, then commit and push to `origin/main`. Generated previews, logs and the virtual environment are ignored; the movie itself is an external local asset.

| File | Responsibility |
| --- | --- |
| `arucomarket/application.py` | Application-wide keyboard handling and Q shutdown |
| `arucomarket/prediction.py` | Interpolated motion fits, retained models, continuous quotes, fixed bet terms, settlement and virtual balances |
| `arucomarket/trial_ui.py` | Multi-ball Height and credits-per-unit charts, shared visibility controls, focused-ball detail, trial ticker, estimate styling and results |
| `arucomarket/ui.py` | Main window, camera overlays, layout, original index/OHLC tab and worker cleanup |
| `arucomarket/state.py` | Genuine observations, freshness, per-ball histories/OHLC and market snapshots |
| `arucomarket/worker.py`, `capture.py`, `recording.py` | Source-time processing, playback/camera acquisition, recording and deterministic replay |
| `tests/test_core.py`, `tests/test_prediction.py`, `scripts/verify_*.py` | Logic tests and native rendering/playback/shutdown checks |

### Behaviour to carry forward

- The system automatically bets **UP or DOWN over four source seconds**, with one open bet per ball, a 10-credit stake and 1,000 starting virtual credits per ball. Opening direction, height, quote and expiry stay fixed.
- Straight lines join sightings. Interpolation between already known sightings supplies evenly spaced motion-fit points. **Extrapolation** from the last model keeps an existing bet's quote updating while the marker is hidden; these are two different operations.
- On the quote chart, solid segments use fresh sightings and dashed segments are estimated. The ticker prefixes estimated quotes with `~`. Missing evidence widens uncertainty. Reacquisition corrects the model without rewriting old quotes. New bets need a fresh fitted forecast.
- Both trial charts show every enabled ball in the same colour used by the ticker and camera overlay. Show toggles apply to both charts. Focus changes the detailed band, contract text, ledger and camera ghost; it does not hide other enabled balls.
- Only a real, unambiguous sighting within the expiry window can settle a directional outcome. Estimates never create observations, OHLC samples or settlement evidence. Missing expiry evidence voids the bet and refunds its stake.
- Movie pause stops the source clock; reset, seek, loop and source changes clear the session. EOF freezes any unfinished round. All of this remains independent of UI refresh rate.
- Q is handled by the application before focused charts or controls can consume it. It exits the application event loop and triggers the same worker cleanup used when the main window closes. Modal file dialogs retain normal Q typing.

**Validation at this checkpoint:** 39 tests pass. Movie and synthetic rendering checks pass, including simultaneous ball histories/contracts, shared Show toggles, ticker-to-focus selection and restoration of a hidden focused ball. Real-movie playback remains responsive. The application-wide quit check passes with a chart focused, a control focused, fullscreen, and uppercase Q, and confirms that the worker stops. In the checked 12–28 second movie segment, 654 estimated quote updates filled previously missing portions of the quote chart; five rounds still voided for missing expiry sightings, and two were open at the cutoff. This verifies continuous pricing, not predictive accuracy. The uncertainty/quote model is uncalibrated, and the small synthetic accuracy check did not beat a stay-put baseline. See [verification results](docs/verification.md) for details.

**Local assets and configuration:** `config.json` points to a movie outside this repository; set `movie` or pass `--movie /path/to/file.MOV` on another machine. `artifacts/` and `logs/` are generated locally and are not available just by cloning. Trial constants currently live in `PaperMarket` in `prediction.py`; capture/geometry/layout settings live in `Config` and `config.json`. The actual iPhone camera index, orientation and live latency still need installation testing.

## Four-second paper-market trial

The default **UP / DOWN trial** tab shows automatic four-second bets on each ball's vertical movement. Both charts show all five balls by default, with one consistent colour per ball. Use the coloured **Show** checkboxes to hide or reveal a ball in both charts. Click a ticker row or use **Focus** to choose which ball supplies the detailed uncertainty band, contract text, result ledger and original camera ghost; focusing does not hide the other enabled balls. Height is `100 × (1 − normalised_y)`, increasing upward; it is a screen-position proxy, not measured physical altitude. The existing horizontal artistic index and OHLC remain in **Observed index / OHLC**.

Each ball starts with 1,000 virtual credits and stakes 10 per round. The opening height, direction, entry quote, four-second expiry, and original forecast are fixed. Dots are sightings and solid straight lines join them, including gaps. For each enabled ball, the coloured dashed curve is the original forecast and the coloured dotted curve is the latest forecast for the same expiry; endpoint labels and coloured expiry lines identify the contract. The focused ball is drawn more strongly. While its bet is active, the shaded range follows the latest model and widens during missing sightings; after settlement it shows the original forecast range. It is a heuristic, **not a calibrated confidence interval**. The camera ghost retains the focused ball's original height prediction at expiry; its oval width does not predict horizontal motion. Off-image predictions are clipped by the camera view and remain visible on the graph.

### Camera overlay legend

- A **coloured square/polygon around an ArUco marker** is a genuine detection in the current source frame. Its label gives the ball ID and normalised x/y position. A `?` indicates incompatible same-ID detections, so that frame is ambiguous.
- **Coloured connected lines** are the ball's recent genuine sightings. They join the measured positions within the Trail persistence window; the line between sightings is a visual connection rather than evidence that the ball followed that exact path.
- A **small dashed circle** is the last known position of a ball that is not detected in the current frame. It is stronger while the ball is stale and fainter after it is considered lost. This held location is display-only and cannot create observations, open a bet or settle one.
- A **solid circle connected to a dotted vertical line**, with a label such as `0 DOWN · original +4s`, is the focused ball's original four-second forecast endpoint. The translucent vertical oval shows its heuristic uncertainty; its width is only a readable glyph and does not forecast horizontal movement. This circle is a prediction, not a detected marker or held location.

The forecast is an unconstrained screen-position extrapolation. It does not model the dome boundary, floor, collisions, gravity or where a physical ball is allowed to travel. The current `roi` is the whole source frame, and the camera renderer clips the forecast to that frame rather than to the visible dome. A forecast circle can therefore appear below or outside the physical marker area, as in a strong DOWN projection. It remains an estimate and cannot settle the contract; settlement still requires a genuine marker detection near expiry.

The chosen contract is quoted in credits per unit (0–100). Ten credits buy `10 / entry_quote` units. A win pays 100 per unit, a loss pays zero, and a neutral or void round refunds the stake. The ticker shows available **cash**, excluding the stake while it is in an open bet; the header shows settled profit/loss. There is one active bet per ball, followed by a 1.5-second result hold. After that hold the last result remains visible until a new eligible bet opens.

Quotes update on **every processed source frame until expiry**, even when a marker is hidden, ambiguous or lost. Solid quote segments update from fresh sightings; dashed segments extrapolate from the last motion model. A `~` prefix in the ticker and a sighting-age message identify estimates. With no new evidence, the model keeps its fixed-expiry projected mean and adds an uncertainty penalty of 0.06 normalised-height units per second without a clear sighting, so time alone does not make it more certain. A returning marker refreshes the fit; if there is not yet enough history to fit velocity, its real position corrects the model while the retained velocity decays. Historical quotes and the original bet are never rewritten. New bets still require a fresh fitted forecast. The terminal dot is the actual payout or refund, separate from estimated quotes.

Settlement uses the **first unambiguous fresh sighting at or after expiry, within 0.35 source seconds**. Movement within ±1.5 percentage points of ROI height is neutral. Without a qualifying sighting, the round voids at the end of that window. No held location or forecast can settle a bet. Movie pause freezes source time; reset, seek, loop and source changes clear forecasts, balances and bets. EOF freezes any unfinished round until reset.

The starter model linearly interpolates between known sightings onto an evenly spaced grid of roughly 0.1-second steps, then fits vertical velocity over the last 1.2 seconds and damps it over the forecast horizon. It requires at least two real sightings spanning 0.3 seconds; an older anchor can supply the beginning of that window. Gaps longer than `lost_after` (default three seconds) are excluded from the fit. Interpolation only uses completed intervals ending at a fresh sighting: no later video frames are read and no past forecast is rewritten. Beyond the latest sighting, the separate extrapolation model described above supplies labelled estimates for existing bets. The uncertainty estimate uses real-sighting residuals and widens with the largest input gap; grid points are not independent evidence. Sightings, activity, OHLC and settlement retain real samples only. Motion inside the neutral zone produces no new bet. Quotes are generated from an uncalibrated Gaussian error model; they are experimental estimates, not exchange prices. The footer compares the frozen four-second forecast's average absolute height error with a stay-put baseline, using the same settled observations. This is a small, selected sample, not a whole-footage accuracy score.

For a readily visible trial, run `.venv/bin/python -m arucomarket --synthetic` or click **Synthetic test**. The existing movie has intermittent sightings: with interpolated fitting, the checked 12–28 second segment completed five void rounds and had two open bets at the cutoff. There were no valid expiry observations to score. Use the movie or camera to assess real tracking; synthetic motion demonstrates the interaction and does not establish physical prediction accuracy.

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

Movie starts playing immediately. **Q quits the whole application**; Space pauses/resumes; Reset starts a new timeline; the slider seeks and clears history; Escape exits fullscreen. Drag the splitter to change camera/market proportions. Use the trial's Show controls and Focus picker for its multi-ball charts; choose the separate ball control in **Observed index / OHLC** for the OHLC panel. Layer toggles and trail persistence affect presentation only. The five ticker rows show current or explicitly held values, age and state. Straight connections join sightings across gaps; they interpolate rather than measure the unseen trajectory.

The default **Fit screen** layout keeps the portrait dome feed beside the markets on wide screens and stacks the views on tall screens. The trial’s height and quote charts are stacked below its ticker. In the original observation tab, the index and OHLC charts sit beside each other when there is enough width. The provisional 900×1600 window is fitted to the available desktop at startup. Choose **Portrait views / Side by side** to override the arrangement without changing observations, coordinates or index values. Drag either divider to allocate space; the camera image fits without cropping or stretching. Charts have a minimum readable height; a forced tall layout on a short screen scrolls instead of flattening the plots.

The **Observed index** and **Height** charts connect every consecutive sighting within each ball’s retained history with solid straight lines, including long gaps. Camera trails use the same straight connections within the trail-persistence window. Dots remain genuine sightings, and lines never connect different balls or extend beyond the last sighting. Only the forecast curves extend into the future. The legacy `gap_seconds` configuration field remains loadable for older recordings; the trial's input-gap limit is now `lost_after`.

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
.venv/bin/python scripts/verify_trial.py
.venv/bin/python scripts/verify_trial.py --movie
.venv/bin/python scripts/verify_quit.py
```

The UI check runs offscreen and writes preview PNGs to `artifacts/`. The playback check runs the real movie worker and Qt interface together for eight seconds to detect stalls. The footage check analyses four selected one-second clips. It is not a whole-movie accuracy benchmark. Under sustained processing load the movie can slow down, but consecutive frame skips are bounded so playback cannot freeze in an endless catch-up loop; source timestamps remain unchanged.

Read [verification results](docs/verification.md), [TD behavioural inventory](docs/reference-inventory.md), and [architecture/data definitions](docs/architecture.md). Preview images and reports under `artifacts/` are generated on demand by the verification scripts and can be deleted between checks.

References used for API checks: [OpenCV ArucoDetector](https://docs.opencv.org/4.7.0/d2/d1a/classcv_1_1aruco_1_1ArucoDetector.html), [PyAV timestamps](https://pyav.org/docs/stable/api/time.html), [Qt for Python setup](https://doc.qt.io/qtforpython-6.8/gettingstarted.html).
