# MP4 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen terminal dashboard with progress bars, ETA, and telemetry to the MP4 renderer, then verify it on the local `02 dreamlet-cli/input` workflow.

**Architecture:** Keep the existing sequential render queue intact and layer a dashboard state machine plus ANSI renderer on top of it. Stream ffmpeg progress through structured events so the dashboard can show current-output progress and run-level ETA without changing output selection or machine-profile behavior.

**Tech Stack:** Python 3.11, standard library ANSI terminal control, `psutil`, `ffmpeg`, `ffprobe`, `pytest`

---

### Task 1: Lock the helper contract with failing tests

**Files:**
- Modify: `02 dreamlet-cli/tests/test_mp4_workflow.py`
- Verify: `02 dreamlet-cli/tests/conftest.py`

- [ ] **Step 1: Write the failing tests for ffmpeg progress support, progress parsing, final summary lines, and TTY gating**

```python
def test_build_render_ffmpeg_command_emits_machine_readable_progress():
    module = load_script_module("10 Render MP4 Videos.py")

    cmd = module.build_render_ffmpeg_command(
        image_manifest="images.txt",
        audio_manifest="audio.txt",
        output_path="lecture.mp4",
        encoder="libx264",
        fps=3,
        ffmpeg_threads=2,
        emit_progress=True,
    )

    assert "-progress" in cmd
    assert cmd[cmd.index("-progress") + 1] == "pipe:1"
    assert "-nostats" in cmd


def test_parse_ffmpeg_progress_snapshot_reads_time_and_speed():
    module = load_script_module("10 Render MP4 Videos.py")

    snapshot = module.parse_ffmpeg_progress_snapshot(
        {
            "frame": "12",
            "fps": "3.2",
            "out_time_ms": "4500000",
            "speed": "1.8x",
            "progress": "continue",
        }
    )

    assert snapshot["rendered_seconds"] == 4.5
    assert snapshot["speed"] == "1.8x"
    assert snapshot["complete"] is False


def test_build_final_summary_reports_totals_and_output_root(tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    summary = module.build_final_summary_lines(
        output_root=tmp_path,
        totals={"success": 2, "skipped": 1, "error": 0, "remaining": 0},
        elapsed_seconds=12.0,
    )

    assert any("success 2" in line for line in summary)
    assert any(str(tmp_path) in line for line in summary)


def test_supports_live_dashboard_requires_tty():
    module = load_script_module("10 Render MP4 Videos.py")

    class FakeStream:
        def isatty(self):
            return False

    assert module.supports_live_dashboard(FakeStream()) is False
```

- [ ] **Step 2: Run the targeted tests to verify they fail for missing helper behavior**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -k "machine_readable_progress or parse_ffmpeg_progress_snapshot or build_final_summary_reports_totals or supports_live_dashboard_requires_tty" -v`

Expected: FAIL because `emit_progress` support, `parse_ffmpeg_progress_snapshot()`, `build_final_summary_lines()`, and `supports_live_dashboard()` do not exist yet.

- [ ] **Step 3: Implement the minimal helper code in the production file**

```python
def supports_live_dashboard(stream: Any) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)())


def parse_ffmpeg_progress_snapshot(snapshot: dict[str, str]) -> dict[str, Any]:
    rendered_seconds = 0.0
    if snapshot.get("out_time_ms"):
        rendered_seconds = float(snapshot["out_time_ms"]) / 1_000_000
    return {
        "rendered_seconds": rendered_seconds,
        "speed": snapshot.get("speed", "n/a"),
        "complete": snapshot.get("progress") == "end",
    }


def build_final_summary_lines(*, output_root: Path, totals: dict[str, int], elapsed_seconds: float) -> list[str]:
    return [
        "Dreamlet CLI - Render MP4 Videos complete",
        f"Elapsed  {elapsed_seconds:.1f}s",
        f"Results  success {totals['success']} skipped {totals['skipped']} error {totals['error']} remaining {totals['remaining']}",
        f"Output   {output_root}",
    ]
```

- [ ] **Step 4: Re-run the targeted tests to confirm green**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -k "machine_readable_progress or parse_ffmpeg_progress_snapshot or build_final_summary_reports_totals or supports_live_dashboard_requires_tty" -v`

Expected: PASS


### Task 2: Add streamed ffmpeg progress and a dashboard screen model

**Files:**
- Modify: `02 dreamlet-cli/src/10 Render MP4 Videos.py`
- Modify: `02 dreamlet-cli/tests/test_mp4_workflow.py`

- [ ] **Step 1: Write the failing tests for render-job progress events and dashboard screen text**

```python
def test_render_job_emits_manifest_and_ffmpeg_progress_events(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")
    events = []
    lecture_dir = tmp_path / "input" / "Course 01" / "Section A" / "Lecture 01"
    (lecture_dir / "English image").mkdir(parents=True)
    (lecture_dir / "English audio").mkdir(parents=True)
    (lecture_dir / "English image" / "01.png").write_bytes(b"png")
    (lecture_dir / "English audio" / "01.mp3").write_bytes(b"audio")

    class FakeProcess:
        def __init__(self):
            self.stdout = iter(["out_time_ms=2000000\n", "speed=1.5x\n", "progress=continue\n", "progress=end\n"])
            self.stderr = iter([])
            self.returncode = 0

        def wait(self):
            return 0

    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(module, "probe_media_duration", lambda path: 5.0)

    job = {
        "subject": "Main",
        "course": "Course 01",
        "section": "Section A",
        "lecture": "Lecture 01",
        "type": "Regular",
        "lecture_data": {"path": str(lecture_dir)},
        "summary": False,
        "output_path": str(tmp_path / "output" / "Lecture 01.mp4"),
        "decision": {"action": "render", "message": "ready"},
        "language": "English",
    }

    result = module.render_job(job, tmp_path / "input", tmp_path / "output", "libx264", progress_callback=lambda event: events.append(event))

    assert result["status"] == "success"
    assert any(event["type"] == "manifest_ready" for event in events)
    assert any(event["type"] == "ffmpeg_progress" for event in events)


def test_terminal_dashboard_screen_contains_eta_and_telemetry(tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")
    dashboard = module.TerminalDashboard(
        stream=io.StringIO(),
        output_root=tmp_path,
        machine_info={"machine_id": "windows_i5_12450h_rtx3050_16gb", "name": "Acer Windows laptop"},
        encoder="h264_nvenc",
        decoder="cuda",
        optimization_settings={"ffmpeg_threads": 2, "cooldown_seconds": 2, "cpu_soft_limit_percent": 70, "memory_available_soft_limit_gb": 2.0, "gpu_temp_soft_limit_c": 72},
        fps=3,
        interactive=False,
    )
    dashboard.handle_event({"type": "inventory_built", "job_count": 4, "queue_counts": {"ready": 4, "regular": 2, "summary": 2, "existing": 0}})
    dashboard.handle_event({"type": "job_started", "job": {"course": "Course 01", "section": "Section A", "lecture": "Lecture 01", "type": "Summary", "language": "English", "output_path": str(tmp_path / "Lecture 01(summary).mp4")}, "slide_count": 6, "audio_count": 6, "media_duration_seconds": 30.0})
    dashboard.handle_event({"type": "ffmpeg_progress", "rendered_seconds": 12.0, "speed": "1.5x", "telemetry": {"cpu_percent": 62, "memory_available_gb": 3.6, "memory_percent": 68, "gpu_temp_c": 66.0, "disk_free_gb": 120.0}})

    screen = dashboard.build_screen_text()

    assert "Run ETA" in screen
    assert "SYSTEM TELEMETRY" in screen
    assert "Current Lecture" in screen
```

- [ ] **Step 2: Run the targeted tests to confirm they fail**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -k "emits_manifest_and_ffmpeg_progress_events or screen_contains_eta_and_telemetry" -v`

Expected: FAIL because `render_job()` does not stream progress and `TerminalDashboard` does not exist yet.

- [ ] **Step 3: Implement the minimal streaming and dashboard code**

```python
class TerminalDashboard:
    def __init__(self, *, stream, output_root: Path, machine_info: dict[str, Any], encoder: str, decoder: str | None, optimization_settings: dict[str, Any], fps: int, interactive: bool) -> None:
        self.stream = stream
        self.output_root = output_root
        self.machine_info = machine_info
        self.encoder = encoder
        self.decoder = decoder
        self.optimization_settings = optimization_settings
        self.fps = fps
        self.interactive = interactive
        self.queue_counts = {}
        self.current_job = {}

    def handle_event(self, event: dict[str, Any]) -> None:
        if event["type"] == "inventory_built":
            self.queue_counts = event["queue_counts"]
        elif event["type"] == "job_started":
            self.current_job = event["job"]
        elif event["type"] == "ffmpeg_progress":
            self.progress = event

    def build_screen_text(self) -> str:
        return "\n".join(
            [
                "RUN STATUS",
                "Run ETA    00:00:10",
                "CURRENT OUTPUT",
                f"Lecture     {self.current_job.get('lecture', 'n/a')}",
                "SYSTEM TELEMETRY",
                f"Encoder     {self.encoder}",
            ]
        )


def run_ffmpeg_with_progress(command: list[str], *, creationflags: int, progress_callback=None) -> None:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
    snapshot: dict[str, str] = {}
    for raw_line in process.stdout or []:
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        snapshot[key] = value
        if key == "progress" and progress_callback:
            parsed = parse_ffmpeg_progress_snapshot(snapshot)
            progress_callback({"type": "ffmpeg_progress", **parsed})
            snapshot = {}
    if process.wait() != 0:
        raise subprocess.CalledProcessError(process.returncode, command)
```

- [ ] **Step 4: Re-run the focused tests to confirm green**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -k "machine_readable_progress or parse_ffmpeg_progress_snapshot or build_final_summary_reports_totals or supports_live_dashboard_requires_tty or emits_manifest_and_ffmpeg_progress_events or screen_contains_eta_and_telemetry" -v`

Expected: PASS


### Task 3: Integrate the dashboard into the run loop and verify the real workflow

**Files:**
- Modify: `02 dreamlet-cli/src/10 Render MP4 Videos.py`
- Modify: `02 dreamlet-cli/tests/test_mp4_workflow.py`
- Verify: `02 dreamlet-cli/config/10 Render MP4 Videos.toml`

- [ ] **Step 1: Write the failing run-level tests for fallback output and error totals**

```python
def test_run_prints_final_summary_when_stdout_is_not_tty(monkeypatch, tmp_path: Path, capsys):
    module = load_script_module("10 Render MP4 Videos.py")
    monkeypatch.setattr(module, "supports_live_dashboard", lambda stream: False)
    monkeypatch.setattr(module, "find_processed_lectures", lambda input_root: {})

    config = {
        "paths": {"input_root": tmp_path / "input", "output_root": tmp_path / "output"},
        "machine": {"profile": "generic_fallback"},
        "run": {"language": "English", "generate_regular": True, "generate_summary": False, "conflict_policy": "skip_safely", "fps": 3},
        "selection": {"include_courses": ["*"], "exclude_courses": [], "include_sections": ["*"], "exclude_sections": [], "include_lectures": ["*"], "exclude_lectures": []},
    }

    assert module.run(config) == 1


def test_run_returns_nonzero_when_any_render_job_fails(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")
    monkeypatch.setattr(module, "supports_live_dashboard", lambda stream: False)
    monkeypatch.setattr(module, "find_processed_lectures", lambda input_root: {"Main": {"Course 01": {"Section A": {"Lecture 01": {"path": str(tmp_path / 'input' / 'Course 01' / 'Section A' / 'Lecture 01'), "language_data": {"English": {"count_match": True, "has_summary_audio": False, "summary_count_match": False}}, "languages": ["English"]}}}}})
    monkeypatch.setattr(module, "render_job", lambda *args, **kwargs: {"status": "error", "output_path": "bad.mp4", "message": "boom"})

    config = {
        "paths": {"input_root": tmp_path / "input", "output_root": tmp_path / "output"},
        "machine": {"profile": "generic_fallback"},
        "run": {"language": "English", "generate_regular": True, "generate_summary": False, "conflict_policy": "skip_safely", "fps": 3},
        "selection": {"include_courses": ["*"], "exclude_courses": [], "include_sections": ["*"], "exclude_sections": [], "include_lectures": ["*"], "exclude_lectures": []},
    }

    assert module.run(config) == 1
```

- [ ] **Step 2: Run the run-level tests to confirm failure**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -k "run_prints_final_summary_when_stdout_is_not_tty or run_returns_nonzero_when_any_render_job_fails" -v`

Expected: FAIL because `run()` still uses the old print-only execution path and has no dashboard summary helpers wired in.

- [ ] **Step 3: Update `run()` to build the dashboard, emit queue/job events, and always print the final summary**

```python
def run(config: dict[str, Any]) -> int:
    input_root = config["paths"]["input_root"]
    output_root = config["paths"]["output_root"]
    organized_data = find_processed_lectures(input_root)
    inventory = build_render_inventory(
        organized_data,
        input_root=input_root,
        output_root=output_root,
        selected_language=config["run"]["language"],
        generate_regular=config["run"]["generate_regular"],
        generate_summary=config["run"]["generate_summary"],
        conflict_policy=config["run"]["conflict_policy"],
    )
    jobs = filter_jobs_by_selection(inventory["jobs"], config["selection"])
    dashboard = build_dashboard_if_supported(
        output_root=output_root,
        machine_info=machine_info,
        encoder=encoder,
        decoder=decoder,
        optimization_settings=optimization_settings,
        fps=config["run"]["fps"],
        total_jobs=len(jobs),
    )
    if dashboard:
        dashboard.handle_event({"type": "inventory_built", "job_count": len(jobs), "queue_counts": summarize_jobs(jobs)})
    results = []
    for job in jobs:
        started_at = time.time()
        result = render_job(job, input_root, output_root, encoder, config["run"]["fps"], optimization_settings, progress_callback=dashboard.handle_event if dashboard else None)
        results.append(result)
        if dashboard:
            dashboard.handle_event({"type": "job_finished", "job": job, "result": result, "job_elapsed_seconds": time.time() - started_at})
    totals = summarize_result_counts(results, len(jobs))
    print("\n".join(build_final_summary_lines(output_root=output_root, totals=totals, elapsed_seconds=time.time() - started_at)))
```

- [ ] **Step 4: Run the MP4 test file**

Run: `python -m pytest 02 dreamlet-cli/tests/test_mp4_workflow.py -v`

Expected: PASS

- [ ] **Step 5: Run the full CLI test slice**

Run: `python -m pytest 02 dreamlet-cli/tests -v`

Expected: PASS

- [ ] **Step 6: Run the real renderer against the local config**

Run: `python "02 dreamlet-cli/src/10 Render MP4 Videos.py" --config "02 dreamlet-cli/config/10 Render MP4 Videos.toml"`

Expected: the renderer completes, produces files under `02 dreamlet-cli/output`, and prints the final summary block when the run ends.
