# MP4 Render Dashboard Design

Date: 2026-04-12
Status: Approved for planning
Scope: `02 dreamlet-cli/src/10 Render MP4 Videos.py`

## Goal

Add a terminal-native full-screen dashboard to the MP4 renderer so a run is understandable while it is happening, without changing the underlying rendering workflow. The dashboard must redraw in place, show a proper run ETA plus current-output ETA, expose all sensible available telemetry, and print a final summary only after the run ends.

## User-Facing Outcome

During `10 Render MP4 Videos.py`, the terminal becomes a live single-screen monitor instead of a stream of plain log lines. The screen shows:

- run identity and configured paths
- overall render progress with a progress bar and run ETA
- current lecture/output details and current-output progress
- queue totals and result counts
- machine telemetry including CPU, RAM, GPU temperature when available, encoder, thread count, cooldown state, and disk free space
- a compact recent-events strip for the latest state changes

When the run finishes, the dashboard is replaced by a final static summary with totals, duration, errors, and output location information.

## Constraints

- Stay terminal-only; no browser or GUI view.
- Avoid new dependencies unless implementation proves impossible without them.
- Preserve current render semantics, config behavior, selection filters, and machine-profile logic.
- Keep the renderer single-owner and sequential as it is today.
- Work on Windows-first behavior because the current configured profile targets the Windows laptop.

## Chosen Approach

Use a zero-dependency ANSI redraw dashboard in the existing CLI process.

Why this approach:

- it matches the requested full-screen terminal experience
- it fits the existing script structure without introducing a UI framework
- it keeps deployment simple for the local CLI
- it can be layered on top of the current job loop by introducing structured progress events instead of changing render logic

Rejected options:

- external browser dashboard: rejected because the user explicitly wants terminal-only
- third-party terminal UI package: rejected for now because the CLI currently has no dashboard dependency and the required layout is achievable with ANSI control codes plus standard library output

## Screen Layout

The live screen is a fixed dashboard with these sections in order:

1. Header
   Shows workflow name, current wall-clock time, input path, output path, and dashboard mode.

2. Run Status
   Shows current state, overall completed outputs, percentage, run ETA, elapsed time, and aggregated result counters.

3. Progress Bars
   Shows one overall progress bar and one current-output progress bar.

4. Current Output
   Shows course, section, lecture, variant, language, stage, and output file path.

5. Lecture Timing
   Shows slide count, audio clip count, total media duration, rendered duration so far, render speed relative to realtime, and current-output ETA.

6. Queue
   Shows ready, active, regular, summary, existing, reported, skipped, failed, and remaining counts as applicable.

7. System Telemetry
   Shows CPU percent, RAM used, RAM available, GPU temperature, encoder, decoder, ffmpeg thread count, FPS, selected machine profile, cooldown status, and disk free space. Fields that cannot be detected stay visible as `n/a`.

8. Recent Events
   Shows a short rolling window of recent timestamped events such as queue creation, cooldown start/end, job start, job complete, ffmpeg phase changes, and errors.

9. Exit Replacement
   The live dashboard does not remain on screen after completion. It is replaced by a final summary block.

## Runtime Model

Introduce an internal dashboard state object owned by `run()`. The renderer emits structured events into that state at lifecycle boundaries rather than printing ad hoc lines.

Expected lifecycle:

- startup: config loaded, system profile chosen, encoder chosen
- inventory: lectures scanned, candidate outputs counted, filtered queue built
- job start: a specific output becomes active
- cooldown: system is waiting for metrics to fall below soft limits
- manifest prep: concat manifests and durations are being prepared
- ffmpeg render: current output is actively rendering
- job finish: output succeeded, skipped, reported, or failed
- complete: final summary replaces the live view

The dashboard refresh loop should be driven by event updates plus light periodic redraws while a render is active so the clock, ETA, ffmpeg progress, and telemetry remain current.

## ETA and Progress Rules

### Overall Progress

Overall progress is based on output jobs, not lectures. The denominator is the filtered queue length after selection rules are applied. Completed statuses that should count as done are:

- `success`
- `skipped`
- `reported`
- `failed`

### Run ETA

Run ETA is derived from completed job timings plus live progress for the active job:

- before any timed completion exists, show `estimating...`
- after one or more timed completions, use average seconds per completed output
- if an active ffmpeg render provides better live data, combine historical average for remaining jobs with current-output remaining duration
- cooldown time contributes naturally because it affects observed job timings

### Current-Output Progress

Current-output progress is driven by ffmpeg progress when available. The planned implementation is to invoke ffmpeg with machine-readable progress output and compare rendered media time to the probed target duration.

If live ffmpeg progress is unavailable for a specific run:

- retain stage and heartbeat updates
- keep the current-output bar in an indeterminate or coarse-grained mode rather than showing false precision

## Data and Event Shape

The existing `render_job()` path will be extended to surface structured progress callbacks. The callback contract should be simple and append-only from the renderer's point of view. Event categories should include:

- `run_started`
- `inventory_built`
- `job_started`
- `cooldown_wait`
- `cooldown_resumed`
- `manifest_ready`
- `ffmpeg_progress`
- `job_finished`
- `job_failed`
- `run_finished`

Each event should include only the data the dashboard needs, such as timestamps, active job identity, counts, durations, telemetry snapshot, and result status.

## Telemetry Rules

Telemetry should be gathered from existing helpers where possible and expanded only where it is low-risk and available locally.

Included telemetry:

- CPU percent
- RAM percent and available GB
- GPU temperature from `nvidia-smi` when available
- disk free space for the output root drive
- selected machine profile
- chosen encoder and decoder
- ffmpeg thread count
- configured FPS
- cooldown active or idle state

Optional telemetry that may be added only if straightforward and stable:

- rolling average outputs per hour
- active output size once the target file exists

Telemetry collection must never be allowed to break rendering. Every probe failure is non-fatal and should degrade to `n/a`.

## Error Handling

- Input/config failures should skip dashboard startup and print a normal error message.
- If ANSI redraw is unsupported or stdout is not interactive, fall back to the current non-dashboard CLI behavior with a final summary.
- If telemetry probes fail, keep rendering and display `n/a`.
- If ffmpeg progress parsing fails, keep rendering and downgrade the current-output section to coarse status updates.
- Job failures must be shown in recent events immediately and included in final summary totals.

## Verification Strategy

The implementation plan should preserve or add automated checks for:

- queue counting and result aggregation still matching current behavior
- ETA formatter and progress math on empty, partial, and complete queues
- dashboard event/state reducer behavior for job start, progress, cooldown, completion, and failure
- fallback behavior when GPU telemetry or ffmpeg progress is unavailable
- final summary replacing the live dashboard on completion

Manual verification should cover a real run on the Windows profile against the local `02 dreamlet-cli/input` folder.

## Non-Goals

- parallel rendering
- interactive keyboard controls
- per-slide thumbnails or rich media previews
- persistent log file viewer inside the dashboard
- changing how jobs are selected or how outputs are named

## Implementation Boundary

This design intentionally keeps the change localized to the MP4 render CLI and its tests. It does not require redesigning the audio or image stages, though the event/callback shape should be compatible with future reuse if desired.
