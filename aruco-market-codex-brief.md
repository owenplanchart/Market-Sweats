# ArUco dome market — draft Codex build prompt

This is a proposed build brief, not an instruction to implement every stage at once. The ball IDs, target hardware and screen-based presentation are confirmed below. Implement Stage 1 first; later stages describe the intended extension.

## Purpose

Build a small standalone application to replace the core functions of my TouchDesigner installation. A camera observes ping-pong balls bouncing inside a glass dome. There are five balls. Each ball carries the same marker six times around its surface; each ball has its own marker ID. The five ball IDs are exactly 0–4. Ignore every other ID, including 5. Intermittent observations are intentional: the artwork explores systems constructing authoritative predictions and financial abstractions from incomplete access to the physical world. It is inspired by N. Katherine Hayles's Unthought, chapter 6.

The visible layers should be: physical events, sparse observations, predictions, and eventually speculative contracts based on those predictions. Do not optimise away the conceptual role of missing data. Do not deliberately degrade detection unless I explicitly enable an artistic sampling control.

## Inspect the reference before implementing

Read TD-export.zip as a behavioural reference, not a node-for-node migration target. Its exported Python DATs have a binary header before their Python text. Inventory the existing functions and document which are preserved, simplified, deferred, or unresolved.

The reference uses OpenCV DICT_4X4_50, movie/synthetic-marker/camera inputs, half-resolution analysis, marker centres and corners, last-known values, simple constant-velocity forecasts, filtered trails, text/rings/spheres, red/green geometry, purple forecast paths, feedback persistence, and experimental camera/lighting/POP branches.

Known issues to avoid:
- The fixed tables and hold logic correctly include IDs 0–4 for the confirmed five-ball arrangement. Preserve this set.
- Some raw geometry/debug outputs accept all detected IDs. Filter to 0–4 immediately after detection, before any downstream tracking, drawing, logging, or market calculation.
- A dictionary keyed solely by marker ID overwrites simultaneous instances of the same ID. Preserve every allowed observation.
- The predictor divides position changes by a TD frame duration despite irregular sightings. Use each observation's actual source timestamp.
- Held positions lack freshness metadata. Never treat them as new measurements.
- The value named tz is normalised apparent marker size, not calibrated depth. Call it marker_scale.
- The reference's vol is speed magnitude, not financial volatility. Keep these separate.
- Replace channel-number selections and changing row offsets with named data fields and explicit identities.
- Rectangular clamping is not a physical model of dome collisions.

The ZIP references ArucoBalls.MOV, marker JPGs, and an HDR image, but does not include these assets. For Codex running locally on the artist's Mac, the source movie is /Users/owenplanchart/TouchDesignerProjects/ArucoMarkerSketch/ArucoBalls.MOV. Check that this path exists in your execution environment before opening it; this chat workspace cannot access that Mac path. Three supplied stills show orange marked balls at different heights inside a tall transparent dome above a speaker, with varying marker orientations and overlapping balls. These establish visual context, not detection-rate measurements. The artist reports good detection in TD. Inspect selected movie timestamps and short motion segments initially, rather than every frame. Do not claim real-footage validation without running it. Synthetic fixtures may validate logic but must be labelled as synthetic.

## Proposed implementation

Prefer a local Python application using OpenCV and NumPy for vision/data, PySide6 for the window and controls, and PyQtGraph for live plots. Confirm compatible versions in the target environment and pin a tested set. Target an Apple M4 Mac running macOS. The live camera will probably be an iPhone; keep the capture-device selection configurable and confirm the actual connection method during camera testing.

Use a handful of readable modules for capture, detection, observation/track state, prediction, market rules, rendering, and configuration. No web service, cloud dependency, database server, neural-network training, or elaborate framework is needed for the first build. Keep processing independent from rendering so observations can be replayed headlessly.

The artist reports that the existing TD script tracks the balls well. Preserve its dictionary, detector parameters and effective preprocessing as the initial baseline; do not introduce segmentation, machine learning or detector retuning without demonstrated need. TD-specific RGB, vertical-flip and texture-coordinate handling must be translated to the actual camera/video pixel convention rather than blindly copied. Validate equivalent detection and correct overlay orientation on the source movie. Create the detector once. Make analysis resolution configurable independently of display resolution. Keep the UI responsive with bounded queues and histories; prefer recent frames over accumulating latency. Record dropped-frame statistics. Reset temporal state on seek, loop, source change, or timestamp discontinuity.

Use video presentation timestamps for file playback and monotonic acquisition timestamps for live capture. Pausing video pauses its simulation clock. Aim for responsive 1080p display, but benchmark actual hardware and footage before promising a frame rate.

## Identity and coordinates

Use marker ID as the ball identity under the confirmed arrangement: five balls, with six copies of one ID per ball. Use an explicit active-ball ID list [0, 1, 2, 3, 4], also used as the detector-output allowlist. Never interpret the six copies on one ball as independent balls.

Keep observations as a list with observation ID, source timestamp, marker ID, four corners, centre, apparent scale, and source/frame metadata. Separate observed values, held values, estimated state, and future forecasts. Store last-seen time and state such as observed, stale, lost, or ambiguous. If using a quality score, define its heuristic meaning; do not invent a calibrated probability from the detector.

Use a documented 2D image coordinate system and consistent transforms for crop, resize, rotation, mirroring, and display. Keep raw pixel coordinates and normalised dome-ROI coordinates. Marker centres are surface points, not exact ball centres. Do not claim 3D reconstruction from marker scale or a planar homography of airborne balls.

Retain all raw marker observations. Within each frame, group spatially compatible detections of the same ID into one ball observation. Initially use a documented robust average of their marker centres as a visible-surface position proxy, retaining the individual corners and contributing observation IDs. This is not a reconstructed sphere centre: rotation and changes in which markings are visible can shift it. Create at most one market sample per ball per source frame, regardless of how many copies are visible. Widely separated same-ID detections may be reflections or false positives; flag them as ambiguous rather than averaging across the dome. Begin without ball segmentation; add it only if real-footage testing demonstrates a need.

## Stage 1 — observations and a position-derived market display

Support movie playback first, followed by selectable camera input and a clearly labelled synthetic test source. Provide play/pause, reset, fullscreen, source selection, layer toggles, and adjustable trail length.

Keep the camera image prominent. Draw marker quadrilaterals, IDs, brief coordinate labels, and trails. Use distinct styling for actual observations, stale last-known locations, and inferred movement. Never draw a held location as a current detection. Connect successive sightings of the same ball with straight line segments. These segments connect observations; they do not assert the unseen trajectory. Add a vertex only on a fresh sighting. Allow adjustable trail length and persistence, and use dashed or faded segments across long gaps. Never connect different balls or invent intervening measured points.

Present the work on a screen showing the camera view of the dome, with market data in separate rectangular panels. This is camera-feed compositing, not projection mapping onto the physical dome or balls. Start with a resizable split screen: portrait dome feed on the left, approximately 40% of the width, and stacked market panels on the right. Preserve the camera aspect ratio without stretching. Use one shared colour per ball across its trace, ticker and charts. Stage 1 panels show the observed index and five-ball ticker; add prediction and derivative panels only when those stages exist, without dummy financial data. Allow a camera-only view and adjustable panel proportions. Use a dark, restrained market-terminal style with clear axes and compact numerical labels. Include a ticker, price history, OHLC candles, and data-age/activity indicators. Begin with a documented, configurable mapping such as P = 100 + 100*x_normalised, with y visible separately. Explain that this is an artistic index, not a traded price. Do not silently change the mapping during a session.

Aggregate OHLC from genuine observed index values in fixed source-time intervals. An interval without observations is empty, or explicitly stale if a carry-forward display is enabled. Observation count is activity, not transaction volume. Compute any financial-style volatility from a documented return series with an explicit missing-data policy; show insufficient data when appropriate.

The artist is not attached to the existing effects. Prioritise lightweight 2D marker outlines and lines tracing successive sightings, with optional small ID labels. Omit the 3D spheres, lighting, orbit cameras and POP experiments from this build. Keep the market panel visually coherent with these restrained overlays.

## Stage 2 — prediction layer

Add transparent baseline models: last-observation persistence and timestamp-based constant velocity. Use configurable horizons in seconds, not frames. Forecasts require sufficient observations; after long gaps, stop extrapolation or show growing model uncertainty. Do not imply that a simple baseline knows collisions or hidden trajectories.

Store each forecast immutably with issue time, target time, entity/series, model version, inputs, and prediction. Later observations must never rewrite historical predictions. Evaluate only against an eligible actual observation within a declared tolerance around the target time. Otherwise mark unresolved; do not settle against another forecast or a held position.

Show competing forecasts, heuristic uncertainty envelopes clearly identified as such, and realised error when observable. Keep the prediction layer visually distinct from the observed index. This stage is a forecast display; it becomes a market only when bidding/trading rules are added.

## Stage 3 — speculative markets and derivatives

Design this stage before implementing it. Introduce small, reproducible simulated agents with stated forecasting/bidding rules, finite cash/inventory, and a documented price-formation rule. Separate market price from observed index value and model forecast. No real financial feeds or transactions.

A possible first contract pays 1 unit if a tracked subject is in a specified region at expiry, and 0 otherwise, subject to the actual-observation settlement policy. A later contract can pay based on whether a named, already-issued forecast's error exceeds a threshold. Give every instrument an explicit underlying, strike/threshold, issue time, expiry, payoff, and unresolved-data policy.

An error-based contract is an artistic instrument linked to forecast performance; do not claim it exhausts the meaning of financial derivatives. If I want a strict derivative-on-derivative layer, its underlying must instead be a specified first-layer contract value or payoff.

Let simulated quotes continue during observation gaps using declared model/agent rules. Keep the widening distance between new physical evidence and ongoing speculation visible. Do not generate decorative random financial numbers with no causal relationship to the system.

The eventual installation will convert market data into sound driving the speaker that makes the balls move. This physical feedback is explicitly outside the present scope: do not implement or design audio synthesis, speaker control, or feedback dynamics at this stage.

## Acceptance checks and delivery

Test meaningful risks: all IDs 0–4 accepted; ID 5 and all other IDs excluded from all outputs; simultaneous copies of an ID retained as raw observations and consolidated into one ball sample; spatially inconsistent copies flagged; absent data never becomes zero; irregular timing produces correct velocities; transformations keep overlays aligned; empty OHLC intervals stay empty; replay/seek resets work; forecasts have no future-data leakage; missing outcomes stay unresolved; histories remain bounded.

Deliver installation/run instructions, a simple config, architecture notes, data-field definitions, and observation logging/replay in JSONL. Provide stage-by-stage verification and report what was tested on real footage versus synthetic fixtures. First implement Stage 1 only, leaving clean extension points for Stages 2 and 3.

## Remaining setup details

IDs 0–4, five balls, six identical markings per ball, M4 Mac and camera-feed/split-screen presentation are confirmed. No further identity or projection-mapping clarification is needed.

Confirm final display resolution and the iPhone capture connection during installation setup. Start with the adjustable split-screen layout above. Codex running on the Mac should use the supplied absolute movie path; elsewhere, request the actual file only when footage testing is needed. Stage 1 uses position-derived market visuals; simulated trading belongs to Stage 3.
