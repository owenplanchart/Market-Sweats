# Architecture and data contract

ArUcoMarket is a local Python application with no server. PyAV obtains actual movie presentation timestamps and display rotation rather than estimating timestamps from frame rate.

- `capture.py`: movie PTS and seeks; live monotonic acquisition timestamps; deterministic, clearly labelled synthetic markers. Live acquisition continuously replaces a single pending frame, so slow analysis prefers recent evidence. Camera backend behaviour still needs installation testing.
- `detection.py`: one default ArUco detector; immutable raw observations; ID allowlist; image/overlay transforms.
- `state.py`: one robust surface-position proxy per compatible ID group; bounded histories; explicit freshness; observation-only index and OHLC.
- `prediction.py`: independent four-second paper market consuming accepted samples. Frozen forecast and contract dataclasses, bounded quote/result histories, model quotes, source-time expiry, virtual cash accounting, and matched forecast/stay-put error totals.
- `trial_ui.py`: selected-ball height forecast and contract quote, automatic-bet ticker, result history and error comparison. All curves are presentation of engine snapshots; UI refreshes never place bets.
- `recording.py`: versioned JSONL with full configuration, processed frames (including empty frames), and reset events; deterministic headless replay.
- `worker.py`: capture/analysis/logging thread; controls queue bounded to 16; latest-only UI mailbox. Qt polls at 30Hz. Movie frames more than 150ms late can be skipped before analysis and counted, at most two consecutively. If still late, wall-time scheduling rebases and the next frame is processed, preventing an endless skip loop when decoding itself is slow. Original source PTS and OHLC timing never change. Sustained overload can slow playback; the status bar reports playback resyncs. This is latency management, not an artistic sampling control.
- `ui.py`: aspect-preserving Qt camera painting, configurable trails, original vertical forecast ghost, and tabs for the trial and unchanged observation index/OHLC.

Installation choice (24 September): vertical iPhone through Continuity Camera. The default `layout: "auto"` (Fit screen) stacks views in tall windows at least 1150 pixels high and uses a side-by-side split otherwise. In the latter arrangement, market widths of at least 700 pixels put the charts next to one another below the ticker. Explicit `"portrait"` and `"side_by_side"` overrides remain available. Charts have 220-pixel minimum heights and the market panel can scroll on constrained screens. Layout changes affect widget arrangement only. The provisional window is 900×1600, fitted to the available desktop on startup; final installation pixels and camera device index remain unmeasured. OpenCV capture requests AVFoundation explicitly on macOS. No automatic rotation or crop is inferred from screen layout.

The engine has no GUI imports and can be replayed headlessly. Prediction consumes fresh samples and stores independent immutable opening forecasts; it never writes back into observations. Its velocity fit uses a uniform approximately 10Hz grid linearly interpolated between real sightings over the trailing 1.2 seconds, including one older anchor when necessary. At least two real sightings spanning 0.3 seconds are required, and adjacent input gaps cannot exceed `lost_after`. Only completed intervals ending at the current fresh sighting can be used. Original-sighting residuals and a gap penalty set the heuristic spread; increasing grid density cannot masquerade as more evidence. Forecast metadata records actual sighting count, fitting-grid count and largest gap. All plotted sighting traces connect retained real points directly, including long gaps; these visual lines do not populate observation histories or candles. Paper-market processing occurs after every accepted source frame, including frames with no observations, and is independent of the latest-only UI mailbox. Resets rebuild all market state. Current-code replay reconstructs forecasts and contracts deterministically from observation logs; schema 1 does not persist independent forecast events, so it is not an audit archive across model/code revisions.

Trial constants: four-second horizon, 10-credit stake, 1,000 initial credits per ball, ±0.015 normalised-height neutral zone, 0.35-second forward-only settlement tolerance and 1.5-second result hold. A fresh sighting at/after expiry inside that window settles; otherwise the contract voids. Stale/ambiguous frames cannot settle. Quotes use Gaussian tails with a heuristic spread and price neutral outcomes as a refund of the entry quote. The opening quote conditions on a non-neutral outcome (bounded to 1–99); each later quote represents estimated per-unit payout for those fixed terms. The model is explicitly uncalibrated.

An open contract retains its latest sighting-based model independently of the current observation state. Every processed pre-expiry frame appends `[source_time, quote, kind]`, where kind is `sighting` or `estimated`. Missing, ambiguous and lost frames extrapolate the retained model. The predicted fixed-expiry mean remains anchored to the last real evidence; target-time spread is `model.spread(expiry − issued) + 0.06 × evidence_age`, so the model cannot grow certain merely because the deadline is approaching. Clear reacquisition replaces the fit or, if too sparse for a fit, reanchors to the measured position with decayed velocity and propagated uncertainty. This fallback is still labelled estimated and cannot open a new bet. All quote records and original terms are immutable once issued; the active model is replaced separately. At expiry, a final estimated quote uses only the model available before expiry, and subsequent settlement adds a separately labelled terminal `settlement` point. No later sighting can leak into that expiry estimate. UI paths group runs of each quote kind, with dashed estimates, solid updates from sightings, and a payout/refund marker. Source-time pause and EOF freeze quotes along with the rest of the engine.

Only the current/latest round and the most recent 30 settled records per ball are retained in memory, plus cumulative counts and error totals. Original forecasts are retained with each archived contract. Quote history is bounded to 600 points per active round. Error comparison includes every non-void settled outcome, uses the original four-second endpoint against the qualifying sighting, and therefore includes up to 0.35 seconds of settlement-time tolerance. These samples are selected by bet eligibility and marker visibility.

## Coordinates and grouping

Raw pixels mean the upright source frame **after container rotation**, before configurable presentation rotation/mirroring. Origin is top left; x increases right, y down. `corners` retains OpenCV's marker-relative corner ordering; this is not a guarantee of screen-space top-left after marker rotation. `display_*` applies the configured clockwise quarter-turns and optional horizontal mirror. The same affine matrix renders the image and points.

`roi = [left, top, width, height]` is expressed in fractions of the displayed image. It normalises positions without cropping the raw evidence. Default is the full frame until the dome ROI is deliberately configured. Normalised x = `(display_x/(display_width−1)−left)/roi_width`; analogous y. Values outside the ROI are not clamped. Changing ROI, rotation, mirror, or index mapping requires a new session; each recording stores its config.

Copies of one ID pass a conservative complete-link compatibility test: the largest pairwise normalised-centre distance must be ≤ `group_distance` (default .12 ROI units). Their component-wise median centre, normalised coordinate and scale produce one visible-surface proxy, retaining every contributor ID. Any incompatible pair flags the whole ID as ambiguous for that frame; no cluster is chosen silently. This is a documented geometric heuristic, not a probability or reconstructed sphere centre. Reflections and changes in visible surface markings remain unresolved sources of error.

## Fields

| Object / field | Meaning |
|---|---|
| Observation `observation_id` | Epoch, frame sequence and detector-instance index, unique in one recording |
| `timestamp` | File PTS in seconds relative to stream start, or monotonic seconds since live source opened |
| `frame_id`, `source` | Source sequence within the current epoch and source identity |
| `marker_id` | Ball ID, exactly one of 0–4 |
| `corners`, `centre` | Four marker corners and their mean in upright source pixels |
| `display_corners`, `display_centre` | Those points after user presentation transforms |
| `normalised` | Position in configured ROI, x right and y down |
| `marker_scale` | Mean raw marker side length divided by max raw image dimension; **not depth** |
| Sample `centre`, `normalised`, `marker_scale` | Medians from compatible marker instances |
| Sample `contributors` | All contributing raw observation IDs |
| Sample `index` | `index_base + index_gain*x_normalised` (default 100 + 100x) |
| State `observed` | A compatible fresh sample in this source frame |
| State `stale` | No fresh sample, but last accepted sample is at most `lost_after` seconds old |
| State `lost` | Never seen, or last accepted sample older than that threshold |
| State `ambiguous` | Same-ID instances spatially inconsistent in this frame; last accepted sample is held separately |
| Ticker age | Current source timestamp minus last accepted sample timestamp; absent values are em dashes |
| Candle `start/open/high/low/close/count` | Source-time interval start, observed index aggregates, and number of accepted ball samples |

Each candle covers `[start, start+candle_seconds)`. Only intervals with genuine samples exist; there is no zero or carry-forward candle. The current candle is provisional while source time is inside its interval. Activity is sample count, never trading volume. Financial volatility is not calculated in Stage 1; speed is not presented as volatility. History limits apply independently to samples and candles per ball. Raw frames live only in the one-frame state and optional append-only disk log.

## Clock and playback semantics

Movie pause stops frame consumption and thus the source clock. Resume rebases wall-time scheduling without inventing observations. Reset, seek, source change and loop clear engine state; seeking resumes playback. The engine also clears on non-monotonic timestamps or restarted frame sequence. Equal repeated frame identity/time is ignored, not sampled twice. Forward gaps remain gaps rather than erasing intentional missing evidence. Live capture keeps acquiring while paused and resumes with the newest frame and its real acquisition time.

JSONL has a `session` header (`schema: 1`, complete configuration), `reset` events, and `frame` records containing `timestamp`, `frame_id`, `source`, `source_size` (upright width/height), and `observations`. Empty processed frames are retained so freshness replays correctly. Frame sequence jumps reveal skipped acquisition frames. Logs contain observations, not video; headless replay reproduces state and candles but cannot recreate the camera image. Existing log paths are never overwritten.

Counters distinguish skipped late movie frames, live acquisition frames replaced before analysis, and UI updates replaced after analysis. UI replacement does not discard engine samples or recorded observations. Camera replacement count belongs to the current camera source; movie/display counters last for the worker session.
