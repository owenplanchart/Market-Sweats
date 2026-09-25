# Verification — initial Stage 1 build

Tested locally on 23–24 September 2026, arm64 macOS 15.7.3, Homebrew Python 3.11.14. Pinned primary packages: OpenCV contrib 4.11.0.86, NumPy 2.2.6, PySide6 6.8.3, PyQtGraph 0.13.7, PyAV 16.0.1 and pytest 8.3.5. `requirements-lock.txt` includes transitive versions actually installed.

## Automated synthetic / logic checks

`python -m pytest -q`: **22 passed** after the playback freeze fix. These are software fixtures, not physical detection-rate evidence.

- Actual synthetic ArUco image detection accepts every ID 0–4 and excludes 5 and 49.
- Multiple same-ID marker images survive as separate observations; compatible copies consolidate into one median sample and one activity count.
- Widely separated same-ID detections become ambiguous and do not update held evidence.
- Missing data stays absent; stale/lost transitions use source time; refreshing a frame cannot add a sample.
- Irregular source times populate correct OHLC bins and values; missing bins are absent.
- Seeking, source identity changes and history bounds clear/limit temporal state.
- All four presentation rotations, with and without mirroring, keep points on their pixels; ROI coordinates do not silently clamp.
- JSONL roundtrip preserves empty frames, evidence, ages and candles; reset events clear state; overwrite is refused.
- Generated video verifies PTS playback and seek-to-target behaviour.
- Mocked camera verifies a one-frame pending buffer, newest-frame delivery and replacement counts.
- Worker EOF preserves the last processed snapshot.

`python scripts/verify_ui.py`: **PASS**, Qt offscreen outside the sandbox. Renders a real movie segment, saves 1440×900 and 1080×720 previews, checks camera-only/layer/trail/ball controls, and exercises the actual synthetic worker's pause/resume/reset clock. Qt emits harmless offscreen size-hint/font warnings. The native desktop window has not been operated manually as an installation session.

24 September layout update: the current smoke check renders the new **900×1600 portrait arrangement** and a 1080×720 side-by-side arrangement. It checks splitter orientation, camera-only visibility, and that changing layouts preserves the exact observation state. The portrait preview was visually inspected: full upright dome, readable five-ball ticker and charts, no stretched image. All 21 core tests still pass. `artifacts/ui-portrait-preview.png` shows the new default.

## Real movie checks

### Market visibility fix — 24 September

The reported 1866×881 screenshot showed the portrait stack compressed until both plot areas were almost flat. Fit screen now adapts to window shape, compacts the ticker, and places the charts alongside each other on wide screens. Axes have stronger contrast, sighting markers are larger, and both charts have a minimum height. OHLC graphics notify the plot when their data bounds change so its vertical scale includes the observed values.

Updated Qt checks pass at 1866×881 (chart heights 392/355), 1440×900 (411/374), 1080×720 (257/220), and 900×1600. At the two wide desktop sizes, both charts and axes fit without market scrolling. Explicit portrait on a short window scrolls instead of collapsing charts. Checks also verify OHLC bounds, camera-only mode, and unchanged observation state across layout switches. Wide and tall previews were visually inspected. All 22 core tests pass.

### Playback freeze fix — 24 September

Reproduced the reported still frame using the real movie worker: six frames were published, then all subsequent frames were skipped (192 skips in about eight seconds). Decoder/conversion work could exceed the movie cadence, so skipping frames against the original wall clock could never recover.

The fix caps consecutive late-frame skips at two, then rebases only wall-time scheduling while preserving source PTS. OpenCV rotation replaces an equivalent but slower NumPy rotation/copy, and identity presentation transforms no longer warp/copy the entire 4K image. A deterministic slow-decoder regression test failed before the fix and passes after it; all 22 tests pass.

`python scripts/verify_playback.py`: **PASS** with the real movie worker and offscreen Qt presentation together. In an eight-second check, 140 distinct frames reached the interface, source time advanced from 0 to 7.703 seconds, and the largest interval between presented frames was 0.124 seconds. There were 93 late-frame skips and no wall-clock resyncs in that run. This verifies recovery from the reported freeze, not full 30fps performance. The running desktop app needs to be restarted to load the fix. Report: `artifacts/playback-report.json`.

### Selected-clip detection checks from the initial build

Source: `/Users/owenplanchart/TouchDesignerProjects/ArucoMarkerSketch/ArucoBalls.MOV`, 190,935,900 bytes. Decode metadata: 3840×2160 stored pixels, −90° display rotation (upright 2160×3840), approximately 29.989 fps, duration 61.022 seconds.

Selected clips only, half-resolution default detector, no enhancement or thinning:

| Source interval | Frames analysed | Accepted marker sightings | Accepted ball samples |
|---|---:|---|---:|
| 0–1 s | 30 | none | 0 |
| 15–16 s | 30 | ID 0: 3 | 3 |
| 30–31 s | 30 | ID 3: 1 | 1 |
| 45–46 s | 30 | ID 0: 1; ID 4: 1 | 2 |

Inspected the contact sheet and Qt previews visually: portrait image upright, un-stretched, observed marker polygons on their markings, camera/market panels readable. The 15–16s clip was additionally recorded and replayed through JSONL; all three ball samples and their OHLC activity survived with no invented observations for other balls.

Median detection-plus-presentation-transform time in the final sampled run was approximately 12.0–12.5ms per decoded frame (maximum 17.9ms). This excludes video decoding, logging, snapshot construction and Qt drawing. It is **not an end-to-end frame-rate promise** or a detection-accuracy measurement. Detailed local measurements and previews are under `artifacts/` and can be regenerated with `scripts/verify_footage.py`.

The six accepted sightings across 120 frames are sparse. IDs 1 and 2 were not accepted in these selected clips. There is no labelled ground truth or live TD comparison, so no recall/precision or detection-rate parity claim is made. Preserve the baseline until that comparison demonstrates a need to change it.

## Remaining installation work

- Portrait arrangement and a vertical iPhone through Continuity Camera are confirmed. Confirm final display resolution and the actual iPhone device index, then test macOS permission, delivered orientation, live capture latency, pause/reconnect and prolonged operation on the actual setup.
- Compare detection with the running TD project on the same source timestamps before considering any detector changes. Exact TD GPU resize equivalence and TD's OpenCV version remain unverified.
- Set a deliberate dome ROI and verify the conservative grouping threshold on more real observations, including multiple visible copies/reflections. The initial ROI is the full frame; no calibrated dome or sphere geometry is claimed.
- Benchmark complete display performance and drops with the real installation. Hardware loop/reconnect soak tests are still outstanding.

At the end of Stage 1, prediction and paper-market checks were deferred. The following trial updates supersede that status; audio remains unimplemented.
# UP / DOWN trial verification — 25 September 2026

- 39 pytest cases pass after the continuous-quote update. Coverage includes the existing observation engine, frozen bet terms, UP/DOWN outcomes, virtual payouts, neutral refunds, missing/ambiguous expiry voids, first-sighting settlement tolerance, no bets on stationary or overly sparse input, reset, duplicate frames and deterministic recorded replay with missing frames. Interpolation checks verify two-sighting fitting, unchanged real sample/candle counts, and time weighting independent of detection bursts. New checks verify continuing quotes through lost states, increasing target uncertainty, correction on reacquisition without rewriting history, and no future-sighting leakage into the terminal expiry estimate.
- `scripts/verify_trial.py` exercises the actual synthetic image generator, ArUco detector, engine and Qt panels. The 12-second fixture completed 10 rounds: five wins and five losses. Native screenshots checked at 1440×1000, 900×1600 and 1080×720; both graphs fit the desktop and portrait layouts, with scrolling on the small window. Forecast shading and selected-ball camera overlay were visually inspected.
- `scripts/verify_trial.py --movie` processed the original movie from 12–28 seconds. With interpolation, five rounds voided for missing expiry evidence and two bets remained open at the cutoff. Before interpolation this segment had only one voided round. There are still no scored real-footage forecasts in this segment, so this does not establish useful prediction accuracy.
- With continuous quotes enabled, that movie segment produced 654 estimated quote updates and 23 updates from fresh sightings. The verification asserts a finite quote at the current source timestamp on every active pre-expiry frame. Synthetic input produced 230 estimated updates and 1,028 sighting updates, filling its previously broken quote traces too. Settlement results remain unchanged.
- After interpolation, the synthetic fixture's aggregate mean absolute forecast error was approximately 36.8 height points, versus 36.5 for staying at the opening height (10 matched outcomes). This small synthetic sample does not calibrate the model's quote or uncertainty range or show an advantage over the baseline.
- Existing observation-layout and worker pause/resume/reset checks pass. After the continuous-quote update, the integrated real-movie playback check delivered 140 UI frames over eight wall seconds, reached source time 7.70 seconds, and had a maximum display gap of 0.10 seconds.
- Qt rendering checks run outside the sandbox because its processor-feature probe reports missing NEON inside the sandbox. No camera was activated. Captures and reports are under ignored `artifacts/trial-*` paths.
