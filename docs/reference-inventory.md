# TouchDesigner reference inventory

Inspected `/Users/owenplanchart/Desktop/TD-export.zip` before implementation. The exported project is `ArucoDetector.PrecitiveMarket.AllMarkers.WithPOP.WithLIghtexperiment.14`. Python `.text` DATs have a binary prefix before their Python source; they were read as bytes and decoded after that prefix, not imported as Python files.

| Reference | Behaviour | Stage 1 decision |
|---|---|---|
| `script1_callbacks.onCook` | RGB float/uint8 conversion, optional vertical flip, default `DICT_4X4_50`, centres, apparent size, corners, fixed ID table, debug output | Preserve dictionary and default parameters; instantiate once. Preserve every allowed detection in a list. Filter IDs 0–4 before downstream output. Replace the per-ID overwrite, anonymous channels and TD-specific pixel mapping. |
| `switch1 → SRC → res1 → SRC_ANALYZE` | Movie / synthetic `ArucoTransformVid/out1` / camera; `res1` is half resolution | Preserve source choices and default half-resolution analysis. Source selected explicitly in the UI. |
| `level1` | Brightness .38, gamma 2.92, contrast 2.27, low .033 | Not detector preprocessing: its input is `feedback1`, and it is bypassed. Do not apply it to detection. |
| `aruco_hold_exec.onTableChange` | Fixed IDs 0–4, retain last numeric value | Preserve last seen value; add source-time age, observed/stale/lost/ambiguous states. Held points never become samples. |
| `aruco_predict.run`, `fmt`; `datexec1.onTableChange` | Constant-velocity forecasts, TD frame delta, rectangular bounds, speed named `vol` | Deferred to Stage 2. No prediction or velocity is represented as a measurement; no `vol` field. Timestamped samples provide the extension point. |
| `clearTextDAT.start`, `create`, `frameStart`, `frameEnd` | Clear held and forecast tables at startup; other callbacks no-op | Replace with explicit engine reset on source change, seek, loop/reset, backwards/equal timestamps or restarted frame sequence. |
| `replicator1_callbacks.onReplicate`, `onRemoveReplicant` | Duplicate ID text operators from channels | Simplify to 2D marker labels using explicit IDs. |
| `CameraControlScript.onOffToOn`, `whileOn`, `onOnToOff`, `whileOff`, `onValueChange` | Switch-dependent LFO/orbit/render camera control | Omit 3D presentation and orbit effects. Source selection is ordinary capture control. |
| `local/maps/replicator1_callbacks.replicate` | TD MIDI map scaffolding | Omit; unrelated to Stage 1. |
| CHOP trail/filter nodes, `aruco_pts_SOP`, `aruco_lines_SOP` and variants | Filtered geometric trails and line conversion | Simplify to straight segments between real sightings only, bounded by count and displayed persistence. Long gaps are dashed/faded. No smoothing invents measured vertices. |
| Text/rings/spheres, red/green geometry, purple paths, feedback TOPs | Presentation and prediction layers | Shared per-ball colour, lightweight outlines/trails, held dashed rings; omit 3D and forecast visuals. |
| Lighting, HDR, POP, camera experiments | Experimental rendering | Omitted. Audio/speaker feedback remains outside scope. |

The ZIP references a movie, marker JPGs and an HDR image that it does not contain. The specified movie exists locally and was sampled. No supplied still-image attachments were present in this workspace; the local movie establishes the inspected context.

## Pixel convention and limits of equivalence

OpenCV/PyAV supplies BGR, top-left-origin images. PyAV display-matrix rotation is applied first; this movie has a −90° rotation and becomes upright 2160×3840. Analysis resizes colour pixels before BGR-to-gray conversion, matching the reference's order of half-resolution TOP then grayscale. No independent vertical reflection is applied: TD's `numpyArray()` texture orientation and `FLIP_Y=True` are TD-specific. User presentation rotation/mirroring is applied to both image and corners after detection.

The original default detector settings and preprocessing structure are preserved. TD's exact GPU resampling and installed OpenCV build were not available as a live comparison. **Detection-rate parity with TD is unresolved**, especially given the sparse accepted detections in the sampled clips. No enhancement, segmentation, detector retuning or artistic thinning has been added.
