from __future__ import annotations

import io
from pathlib import Path
import subprocess
import sys

from conftest import load_script_module, run_script


def test_machine_profiles_define_expected_three_machine_profiles():
    module = load_script_module("10 Render MP4 Videos.py")

    assert sorted(module.MACHINE_PROFILES) == [
        "generic_fallback",
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]
    assert module.MACHINE_PROFILES["macbook_pro_m3_pro_18gb"]["name"] == "MacBook Pro M3 Pro (18GB)"
    assert module.MACHINE_PROFILES["windows_i5_12450h_rtx3050_16gb"]["encoder_preferences"][0] == "h264_nvenc"


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_script_module("10 Render MP4 Videos.py")

    system_info = {
        "hostname": "acer-lab-machine",
        "platform": "windows",
        "architecture": "amd64",
        "cpu": "intel core i5-12450h",
        "memory_gb": 16,
        "cpu_count": 12,
        "gpu_detected": True,
        "gpu_type": "nvidia",
        "gpu_name": "NVIDIA GeForce RTX 3050 Laptop GPU",
    }

    selected = module.select_machine_profile(system_info, module.MACHINE_PROFILES)

    assert selected["machine_id"] == "windows_i5_12450h_rtx3050_16gb"
    assert selected["match_source"] == "auto"


def test_select_video_encoder_prefers_videotoolbox_on_mac():
    module = load_script_module("10 Render MP4 Videos.py")

    encoder, decoder, capabilities = module.select_video_encoder(
        "macbook_pro_m3_pro_18gb",
        "Darwin",
        "arm64",
        " ... h264_videotoolbox ... ",
    )

    assert encoder == "h264_videotoolbox"
    assert decoder == "videotoolbox"
    assert capabilities["hardware_encoding"] is True


def test_select_video_encoder_falls_back_to_libx264_when_nvenc_missing():
    module = load_script_module("10 Render MP4 Videos.py")

    encoder, decoder, capabilities = module.select_video_encoder(
        "windows_i5_12450h_rtx3050_16gb",
        "Windows",
        "amd64",
        "",
    )

    assert encoder == "libx264"
    assert decoder is None
    assert capabilities["hardware_encoding"] is False


def test_acer_profile_includes_thermal_friendly_runtime_settings():
    module = load_script_module("10 Render MP4 Videos.py")

    settings = module.MACHINE_PROFILES["windows_i5_12450h_rtx3050_16gb"]["optimization_settings"]

    assert settings["ffmpeg_threads"] == 2
    assert settings["cooldown_seconds"] >= 1
    assert settings["cpu_soft_limit_percent"] == 70
    assert settings["memory_available_soft_limit_gb"] == 2.0
    assert settings["gpu_temp_soft_limit_c"] == 72


def test_get_ffmpeg_creationflags_uses_below_normal_on_windows():
    module = load_script_module("10 Render MP4 Videos.py")

    flags = module.get_ffmpeg_creationflags("Windows")

    assert flags == getattr(module.subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)


def test_build_segment_ffmpeg_command_limits_threads():
    module = load_script_module("10 Render MP4 Videos.py")

    cmd = module.build_segment_ffmpeg_command(
        image_file="slide.png",
        audio_file="audio.mp3",
        segment_path="segment.mp4",
        encoder="h264_nvenc",
        fps=3,
        ffmpeg_threads=2,
    )

    assert "-threads" in cmd
    assert cmd[cmd.index("-threads") + 1] == "2"
    assert "-framerate" in cmd
    assert cmd[cmd.index("-framerate") + 1] == "3"
    assert cmd[-1] == "segment.mp4"


def test_build_render_ffmpeg_command_sets_explicit_output_fps():
    module = load_script_module("10 Render MP4 Videos.py")

    cmd = module.build_render_ffmpeg_command(
        image_manifest="images.txt",
        audio_manifest="audio.txt",
        output_path="lecture.mp4",
        encoder="libx264",
        fps=3,
        ffmpeg_threads=2,
    )

    assert "-r" in cmd
    assert cmd[cmd.index("-r") + 1] == "3"
    assert cmd[-1] == "lecture.mp4"


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


def test_supports_live_dashboard_requires_windows_vt_support(monkeypatch):
    module = load_script_module("10 Render MP4 Videos.py")

    class FakeStream:
        def isatty(self):
            return True

    monkeypatch.setattr(module.os, "name", "nt", raising=False)
    monkeypatch.setattr(module, "enable_windows_virtual_terminal", lambda stream: False)

    assert module.supports_live_dashboard(FakeStream()) is False


def test_run_ffmpeg_with_progress_emits_progress_events(monkeypatch):
    module = load_script_module("10 Render MP4 Videos.py")
    events = []

    class FakeProcess:
        def __init__(self):
            self.stdout = iter(
                [
                    "out_time_ms=2000000\n",
                    "speed=1.5x\n",
                    "progress=continue\n",
                    "out_time_ms=5000000\n",
                    "speed=1.8x\n",
                    "progress=end\n",
                ]
            )
            self.stderr = io.StringIO("")
            self.returncode = 0

        def wait(self):
            return 0

    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    module.run_ffmpeg_with_progress(["ffmpeg", "-progress", "pipe:1"], creationflags=0, progress_callback=lambda event: events.append(event))

    assert [event["type"] for event in events] == ["ffmpeg_progress", "ffmpeg_progress"]
    assert events[0]["rendered_seconds"] == 2.0
    assert events[-1]["complete"] is True


def test_run_ffmpeg_with_progress_ignores_non_progress_lines(monkeypatch):
    module = load_script_module("10 Render MP4 Videos.py")
    events = []

    class FakeProcess:
        def __init__(self):
            self.stdout = iter(
                [
                    "ffmpeg version 7.1.1\n",
                    "out_time_ms=3000000\n",
                    "speed=1.2x\n",
                    "progress=continue\n",
                ]
            )
            self.returncode = 0

        def wait(self):
            return 0

    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    module.run_ffmpeg_with_progress(["ffmpeg", "-progress", "pipe:1"], creationflags=0, progress_callback=lambda event: events.append(event))

    assert len(events) == 1
    assert events[0]["rendered_seconds"] == 3.0


def test_terminal_dashboard_screen_contains_eta_and_telemetry(tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    dashboard = module.TerminalDashboard(
        stream=io.StringIO(),
        output_root=tmp_path,
        machine_info={"machine_id": "windows_i5_12450h_rtx3050_16gb", "name": "Acer Windows laptop"},
        encoder="h264_nvenc",
        decoder="cuda",
        optimization_settings={
            "ffmpeg_threads": 2,
            "cooldown_seconds": 2,
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
        fps=3,
        total_jobs=4,
        interactive=False,
    )
    dashboard.handle_event({"type": "inventory_built", "job_count": 4, "queue_counts": {"ready": 4, "regular": 2, "summary": 2, "existing": 0}})
    dashboard.handle_event(
        {
            "type": "job_started",
            "job": {
                "course": "Course 01",
                "section": "Section A",
                "lecture": "Lecture 01",
                "type": "Summary",
                "language": "English",
                "output_path": str(tmp_path / "Lecture 01(summary).mp4"),
            },
            "slide_count": 6,
            "audio_count": 6,
            "media_duration_seconds": 30.0,
        }
    )
    dashboard.handle_event(
        {
            "type": "ffmpeg_progress",
            "rendered_seconds": 12.0,
            "speed": "1.5x",
            "complete": False,
            "telemetry": {
                "cpu_percent": 62,
                "memory_available_gb": 3.6,
                "memory_percent": 68,
                "gpu_temp_c": 66.0,
                "disk_free_gb": 120.0,
            },
        }
    )

    screen = dashboard.build_screen_text()

    assert "Run ETA" in screen
    assert "SYSTEM TELEMETRY" in screen
    assert "Lecture 01" in screen
    assert "Language" in screen
    assert "Stage" in screen
    assert "Output file" in screen
    assert "QUEUE" in screen
    assert "Profile" in screen
    assert "Cooldown" in screen


def test_render_job_emits_manifest_and_ffmpeg_progress_events(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")
    events = []
    lecture_dir = tmp_path / "input" / "Course 01" / "Section A" / "Lecture 01"
    image_dir = lecture_dir / "English image"
    audio_dir = lecture_dir / "English audio"
    image_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)
    (image_dir / "01.png").write_bytes(b"png")
    (audio_dir / "01.mp3").write_bytes(b"audio")

    def fake_run_ffmpeg_with_progress(command, *, creationflags, progress_callback=None):
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"video")
        if progress_callback:
            progress_callback({"type": "ffmpeg_progress", "rendered_seconds": 5.0, "speed": "1.5x", "complete": True})

    monkeypatch.setattr(module, "probe_media_duration", lambda path: 5.0)
    monkeypatch.setattr(module, "run_ffmpeg_with_progress", fake_run_ffmpeg_with_progress)
    monkeypatch.setattr(module, "apply_cooldown_if_needed", lambda settings, progress_callback=None: None)

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

    result = module.render_job(
        job,
        tmp_path / "input",
        tmp_path / "output",
        "libx264",
        progress_callback=lambda event: events.append(event),
    )

    assert result["status"] == "success"
    assert any(event["type"] == "manifest_ready" for event in events)
    assert any(event["type"] == "ffmpeg_progress" for event in events)


def test_apply_cooldown_emits_wait_and_resume_events(monkeypatch):
    module = load_script_module("10 Render MP4 Videos.py")
    metrics = iter(
        [
            {"cpu_percent": 80, "memory_percent": 70, "memory_available_gb": 1.0},
            {"cpu_percent": 40, "memory_percent": 60, "memory_available_gb": 4.0},
        ]
    )
    gpu_temps = iter([75.0, 60.0])
    events = []

    monkeypatch.setattr(module, "get_system_metrics", lambda: next(metrics))
    monkeypatch.setattr(module, "get_gpu_temperature_c", lambda: next(gpu_temps))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    module.apply_cooldown_if_needed(
        {
            "cooldown_seconds": 1,
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
        progress_callback=lambda event: events.append(event),
    )

    assert any(event["type"] == "cooldown_wait" for event in events)
    assert any(event["type"] == "cooldown_resumed" for event in events)


def test_run_prints_final_summary_when_stdout_is_not_tty(monkeypatch, tmp_path: Path, capsys):
    module = load_script_module("10 Render MP4 Videos.py")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    lecture_dir = input_root / "Course 01" / "Section A" / "Lecture 01"

    monkeypatch.setattr(module, "supports_live_dashboard", lambda stream: False)
    monkeypatch.setattr(
        module,
        "find_processed_lectures",
        lambda path: {
            "Main": {
                "Course 01": {
                    "Section A": {
                        "Lecture 01": {
                            "path": str(lecture_dir),
                            "languages": ["English"],
                            "language_data": {
                                "English": {
                                    "count_match": True,
                                    "has_summary_audio": False,
                                    "summary_count_match": False,
                                }
                            },
                        }
                    }
                }
            }
        },
    )
    monkeypatch.setattr(
        module,
        "select_machine_profile",
        lambda system_info, profiles, override_profile_id=None: {
            "machine_id": "generic_fallback",
            "match_source": "manual",
            "profile": module.MACHINE_PROFILES["generic_fallback"],
        },
    )
    monkeypatch.setattr(module, "detect_ffmpeg_encoders", lambda: "")
    monkeypatch.setattr(module, "select_video_encoder", lambda *args: ("libx264", None, {"hardware_encoding": False}))
    monkeypatch.setattr(module, "render_job", lambda *args, **kwargs: {"status": "success", "output_path": str(output_root / "Lecture 01.mp4"), "message": "done"})

    config = {
        "paths": {"input_root": input_root, "output_root": output_root},
        "machine": {"profile": "generic_fallback"},
        "run": {"language": "English", "generate_regular": True, "generate_summary": False, "conflict_policy": "skip_safely", "fps": 3},
        "selection": {"include_courses": ["*"], "exclude_courses": [], "include_sections": ["*"], "exclude_sections": [], "include_lectures": ["*"], "exclude_lectures": []},
    }

    assert module.run(config) == 0

    captured = capsys.readouterr()

    assert "Dreamlet CLI - Render MP4 Videos complete" in captured.out
    assert "success 1" in captured.out


def test_run_drives_dashboard_events_when_stdout_is_tty(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    lecture_dir = input_root / "Course 01" / "Section A" / "Lecture 01"
    seen_events = []

    class FakeDashboard:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def handle_event(self, event):
            seen_events.append(event)

        def build_screen_text(self):
            return "screen"

    def fake_render_job(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback({"type": "manifest_ready", "slide_count": 1, "audio_count": 1, "media_duration_seconds": 5.0})
            progress_callback({"type": "ffmpeg_progress", "rendered_seconds": 5.0, "speed": "1.0x", "complete": True})
        return {"status": "success", "output_path": str(output_root / "Lecture 01.mp4"), "message": "done"}

    monkeypatch.setattr(module, "supports_live_dashboard", lambda stream: True)
    monkeypatch.setattr(module, "TerminalDashboard", FakeDashboard)
    monkeypatch.setattr(
        module,
        "find_processed_lectures",
        lambda path: {
            "Main": {
                "Course 01": {
                    "Section A": {
                        "Lecture 01": {
                            "path": str(lecture_dir),
                            "languages": ["English"],
                            "language_data": {
                                "English": {
                                    "count_match": True,
                                    "has_summary_audio": False,
                                    "summary_count_match": False,
                                }
                            },
                        }
                    }
                }
            }
        },
    )
    monkeypatch.setattr(
        module,
        "select_machine_profile",
        lambda system_info, profiles, override_profile_id=None: {
            "machine_id": "generic_fallback",
            "match_source": "manual",
            "profile": module.MACHINE_PROFILES["generic_fallback"],
        },
    )
    monkeypatch.setattr(module, "detect_ffmpeg_encoders", lambda: "")
    monkeypatch.setattr(module, "select_video_encoder", lambda *args: ("libx264", None, {"hardware_encoding": False}))
    monkeypatch.setattr(module, "render_job", fake_render_job)

    config = {
        "paths": {"input_root": input_root, "output_root": output_root},
        "machine": {"profile": "generic_fallback"},
        "run": {"language": "English", "generate_regular": True, "generate_summary": False, "conflict_policy": "skip_safely", "fps": 3},
        "selection": {"include_courses": ["*"], "exclude_courses": [], "include_sections": ["*"], "exclude_sections": [], "include_lectures": ["*"], "exclude_lectures": []},
    }

    assert module.run(config) == 0
    assert any(event["type"] == "run_started" for event in seen_events)
    assert any(event["type"] == "inventory_built" for event in seen_events)
    assert any(event["type"] == "manifest_ready" for event in seen_events)
    assert any(event["type"] == "job_finished" for event in seen_events)
    assert any(event["type"] == "run_finished" for event in seen_events)


def test_run_prints_final_summary_and_closes_dashboard_when_render_job_raises(monkeypatch, tmp_path: Path, capsys):
    module = load_script_module("10 Render MP4 Videos.py")
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    lecture_dir = input_root / "Course 01" / "Section A" / "Lecture 01"
    seen_events = []
    closed = {"value": False}

    class FakeDashboard:
        def handle_event(self, event):
            seen_events.append(event)

        def close(self):
            closed["value"] = True

    monkeypatch.setattr(
        module,
        "build_dashboard_if_supported",
        lambda **kwargs: FakeDashboard(),
    )
    monkeypatch.setattr(
        module,
        "find_processed_lectures",
        lambda path: {
            "Main": {
                "Course 01": {
                    "Section A": {
                        "Lecture 01": {
                            "path": str(lecture_dir),
                            "languages": ["English"],
                            "language_data": {
                                "English": {
                                    "count_match": True,
                                    "has_summary_audio": False,
                                    "summary_count_match": False,
                                }
                            },
                        }
                    }
                }
            }
        },
    )
    monkeypatch.setattr(
        module,
        "select_machine_profile",
        lambda system_info, profiles, override_profile_id=None: {
            "machine_id": "generic_fallback",
            "match_source": "manual",
            "profile": module.MACHINE_PROFILES["generic_fallback"],
        },
    )
    monkeypatch.setattr(module, "detect_ffmpeg_encoders", lambda: "")
    monkeypatch.setattr(module, "select_video_encoder", lambda *args: ("libx264", None, {"hardware_encoding": False}))
    monkeypatch.setattr(
        module,
        "render_job",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "ffmpeg", stderr="boom")),
    )

    config = {
        "paths": {"input_root": input_root, "output_root": output_root},
        "machine": {"profile": "generic_fallback"},
        "run": {"language": "English", "generate_regular": True, "generate_summary": False, "conflict_policy": "skip_safely", "fps": 3},
        "selection": {"include_courses": ["*"], "exclude_courses": [], "include_sections": ["*"], "exclude_sections": [], "include_lectures": ["*"], "exclude_lectures": []},
    }

    assert module.run(config) == 1
    assert closed["value"] is True
    assert any(event["type"] == "job_failed" for event in seen_events)
    assert any(event["type"] == "run_finished" for event in seen_events)

    captured = capsys.readouterr()

    assert "Dreamlet CLI - Render MP4 Videos complete" in captured.out
    assert "error 1" in captured.out


def test_needs_cooldown_when_metrics_cross_soft_limits():
    module = load_script_module("10 Render MP4 Videos.py")

    should_pause = module.needs_cooldown(
        metrics={"cpu_percent": 74, "memory_available_gb": 3.5},
        gpu_temp_c=73,
        settings={
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
    )

    assert should_pause is True


def test_needs_cooldown_allows_progress_below_soft_limits():
    module = load_script_module("10 Render MP4 Videos.py")

    should_pause = module.needs_cooldown(
        metrics={"cpu_percent": 42, "memory_available_gb": 5.5},
        gpu_temp_c=61,
        settings={
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
    )

    assert should_pause is False


def test_needs_cooldown_when_available_memory_is_too_low():
    module = load_script_module("10 Render MP4 Videos.py")

    should_pause = module.needs_cooldown(
        metrics={"cpu_percent": 35, "memory_available_gb": 1.2},
        gpu_temp_c=60,
        settings={
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
    )

    assert should_pause is True


def test_resolve_existing_output_action_skip_safely_skips_existing():
    module = load_script_module("10 Render MP4 Videos.py")

    decision = module.resolve_existing_output_action(True, module.ConflictPolicy.SKIP_SAFELY.value)

    assert decision["action"] == "skip"
    assert decision["status"] == "skipped"


def test_resolve_existing_output_action_report_only_reports_existing():
    module = load_script_module("10 Render MP4 Videos.py")

    decision = module.resolve_existing_output_action(True, module.ConflictPolicy.REPORT_ONLY.value)

    assert decision["action"] == "report"
    assert decision["status"] == "reported"


def test_build_render_inventory_counts_ready_and_processed_outputs(tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    lecture_dir = input_dir / "Course 01" / "Section A" / "Lecture 01"
    lecture_dir.mkdir(parents=True)
    output_dir.mkdir()

    existing_output = Path(module.generate_output_path(str(lecture_dir), str(input_dir), str(output_dir), "English", summary=False))
    existing_output.parent.mkdir(parents=True, exist_ok=True)
    existing_output.write_text("existing", encoding="utf-8")

    organized_data = {
        "Main": {
            "Course 01": {
                "Section A": {
                    "Lecture 01": {
                        "path": str(lecture_dir),
                        "languages": ["English"],
                        "language_data": {
                            "English": {
                                "count_match": True,
                                "summary_count_match": True,
                                "has_summary_audio": True,
                            }
                        },
                    }
                }
            }
        }
    }

    inventory = module.build_render_inventory(
        organized_data,
        input_root=input_dir,
        output_root=output_dir,
        selected_language="English",
        generate_regular=True,
        generate_summary=False,
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert inventory["summary"]["lecture_count"] == 1
    assert inventory["summary"]["output_count"] == 1
    assert inventory["summary"]["ready_count"] == 0
    assert inventory["summary"]["processed_count"] == 1


def test_set_global_course_selection_updates_all_course_flags():
    module = load_script_module("10 Render MP4 Videos.py")

    session_state: dict[str, bool] = {}
    organized_data = {
        "Main": {
            "Course 01": {"Section A": {}},
            "Course 02": {"Section B": {}},
        },
        "Archive": {
            "Course 03": {"Section C": {}},
        },
    }

    module.set_global_course_selection(session_state, organized_data, True)

    assert session_state["mp4_select_all"] is True
    assert session_state[module.build_course_selection_state_key("Main", "Course 01")] is True
    assert session_state[module.build_course_selection_state_key("Main", "Course 02")] is True
    assert session_state[module.build_course_selection_state_key("Archive", "Course 03")] is True


def test_filter_jobs_honors_include_and_exclude_globs():
    module = load_script_module("10 Render MP4 Videos.py")

    jobs = [
        {"course": "Course 01", "section": "Section A", "lecture": "Lecture 01"},
        {"course": "Course 02", "section": "Section B", "lecture": "Lecture 02"},
        {"course": "Course 02", "section": "Section Z", "lecture": "Lecture 99"},
    ]

    filtered = module.filter_jobs_by_selection(
        jobs,
        {
            "include_courses": ["Course 0*"],
            "exclude_courses": [],
            "include_sections": ["Section *"],
            "exclude_sections": ["Section Z"],
            "include_lectures": ["Lecture 0*"],
            "exclude_lectures": [],
        },
    )

    assert filtered == [
        {"course": "Course 01", "section": "Section A", "lecture": "Lecture 01"},
        {"course": "Course 02", "section": "Section B", "lecture": "Lecture 02"},
    ]


def test_cli_mp4_report_only_run_is_non_mutating(tmp_path: Path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    lecture_dir = input_root / "Course 01" / "Section A" / "Lecture 01"
    (lecture_dir / "English image").mkdir(parents=True)
    (lecture_dir / "English audio").mkdir(parents=True)
    (lecture_dir / "English Summary audio").mkdir(parents=True)
    (lecture_dir / "English image" / "01.png").write_bytes(b"png")
    (lecture_dir / "English audio" / "01.mp3").write_bytes(b"audio")
    (lecture_dir / "English Summary audio" / "01.mp3").write_bytes(b"audio")
    output_root.mkdir()

    existing_output = output_root / "English" / "Course 01" / "Section A" / "Lecture 01.mp4"
    existing_output.parent.mkdir(parents=True, exist_ok=True)
    existing_output.write_bytes(b"existing")

    config_path = tmp_path / "mp4.toml"
    config_path.write_text(
        f"""
[paths]
input_root = "{input_root.as_posix()}"
output_root = "{output_root.as_posix()}"

[machine]
profile = "windows_i5_12450h_rtx3050_16gb"

[run]
conflict_policy = "report_only"
language = "English"
generate_regular = true
generate_summary = false

[selection]
include_courses = ["Course *"]
exclude_courses = []
include_sections = []
exclude_sections = []
include_lectures = []
exclude_lectures = []
""".strip(),
        encoding="utf-8",
    )

    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = run_script("10 Render MP4 Videos.py", "--config", str(config_path))

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    assert result.returncode == 0
    assert "profile=windows_i5_12450h_rtx3050_16gb" in result.stdout
    assert "success=0 skipped=1 error=0" in result.stdout
    assert before == after


def test_load_config_defaults_mp4_fps_to_three(tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    config_path = tmp_path / "mp4.toml"
    config_path.write_text(
        f"""
[paths]
input_root = "{(tmp_path / 'input').as_posix()}"
output_root = "{(tmp_path / 'output').as_posix()}"

[machine]
profile = "generic_fallback"

[run]
conflict_policy = "skip_safely"
language = "English"
generate_regular = true
generate_summary = false

[selection]
include_courses = []
exclude_courses = []
include_sections = []
exclude_sections = []
include_lectures = []
exclude_lectures = []
""".strip(),
        encoding="utf-8",
    )

    config = module.load_config(config_path)

    assert config["run"]["fps"] == 3


def test_render_job_uses_selected_job_language(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    lecture_dir = tmp_path / "input" / "Course 01" / "Section A" / "Lecture 01"
    (lecture_dir / "Spanish image").mkdir(parents=True)
    (lecture_dir / "Spanish audio").mkdir(parents=True)
    (lecture_dir / "Spanish image" / "01.png").write_bytes(b"png")
    (lecture_dir / "Spanish audio" / "01.mp3").write_bytes(b"audio")
    output_path = tmp_path / "output" / "Spanish" / "Course 01" / "Section A" / "Lecture 01.mp4"

    def fake_run(command, check, capture_output, text=False, timeout=None, creationflags=0):
        command_strings = [str(part) for part in command]
        if command_strings[-1].endswith(".mp4"):
            Path(command_strings[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(command_strings[-1]).write_bytes(b"video")
        return None

    monkeypatch.setattr(module, "probe_media_duration", lambda media_path: 5.0)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    job = {
        "lecture_data": {"path": str(lecture_dir)},
        "summary": False,
        "output_path": str(output_path),
        "decision": {"action": "render", "message": "ready"},
        "language": "Spanish",
    }

    result = module.render_job(job, tmp_path / "input", tmp_path / "output", "libx264")

    assert result["status"] == "success"


def test_render_job_uses_single_ffmpeg_encode_pipeline(monkeypatch, tmp_path: Path):
    module = load_script_module("10 Render MP4 Videos.py")

    lecture_dir = tmp_path / "input" / "Course 01" / "Section A" / "Lecture 01"
    image_dir = lecture_dir / "English image"
    audio_dir = lecture_dir / "English audio"
    image_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)

    for index in range(1, 4):
        (image_dir / f"{index:02d}.png").write_bytes(b"png")
        (audio_dir / f"{index:02d}.mp3").write_bytes(b"audio")

    commands = []

    def fake_probe(path):
        return 5.0

    def fake_run(command, check, capture_output, text=False, timeout=None, creationflags=0):
        commands.append(command)
        if command[0] == "ffmpeg":
            output_path = Path(command[-1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"video")
        return None

    monkeypatch.setattr(module, "probe_media_duration", fake_probe)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    job = {
        "lecture_data": {"path": str(lecture_dir)},
        "summary": False,
        "output_path": str(tmp_path / "output" / "Lecture 01.mp4"),
        "decision": {"action": "render", "message": "ready"},
        "language": "English",
    }

    result = module.render_job(job, tmp_path / "input", tmp_path / "output", "h264_nvenc")

    ffmpeg_commands = [command for command in commands if command[0] == "ffmpeg"]

    assert result["status"] == "success"
    assert len(ffmpeg_commands) == 1
    assert ffmpeg_commands[0].count("-f") == 2
    assert "concat" in ffmpeg_commands[0]
    assert "h264_nvenc" in ffmpeg_commands[0]
    assert "-r" in ffmpeg_commands[0]
    assert ffmpeg_commands[0][ffmpeg_commands[0].index("-r") + 1] == "3"
