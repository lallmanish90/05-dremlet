from __future__ import annotations

from pathlib import Path
from conftest import load_script_module


def test_machine_profiles_define_expected_three_machine_profiles():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    assert sorted(module.MACHINE_PROFILES) == [
        "generic_fallback",
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    system_info = {
        "hostname": "acer-lab-machine",
        "platform": "windows",
        "architecture": "amd64",
        "memory_gb": 16,
    }

    selected = module.select_machine_profile(system_info, module.MACHINE_PROFILES)

    assert selected["machine_id"] == "windows_i5_12450h_rtx3050_16gb"
    assert selected["match_source"] == "auto"


def test_resolve_existing_audio_action_skip_safely_skips_existing():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    decision = module.resolve_existing_audio_action(True, module.ConflictPolicy.SKIP_SAFELY.value)

    assert decision["action"] == "skip"
    assert decision["status"] == "skipped"


def test_resolve_existing_audio_action_report_only_reports_existing():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    decision = module.resolve_existing_audio_action(True, module.ConflictPolicy.REPORT_ONLY.value)

    assert decision["action"] == "report"
    assert decision["status"] == "reported"


def test_build_audio_inventory_counts_ready_and_processed(tmp_path: Path):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    lecture_dir = tmp_path / "Course 01" / "Lecture 01"
    transcript_dir = lecture_dir / "English text"
    summary_dir = lecture_dir / "English Summary text"
    audio_dir = lecture_dir / "English audio"
    transcript_dir.mkdir(parents=True)
    summary_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)

    section_file = transcript_dir / "01.txt"
    summary_file = summary_dir / "01.txt"
    section_file.write_text("hello world", encoding="utf-8")
    summary_file.write_text("summary text", encoding="utf-8")
    (audio_dir / "01.mp3").write_text("existing", encoding="utf-8")

    language_files = {
        "Course 01": {
            "Lecture 01": {
                "base_dir": str(lecture_dir),
                "transcript": {"section_files": [str(section_file)]},
                "summary": {"section_files": [str(summary_file)]},
            }
        }
    }

    inventory = module.build_audio_inventory(
        language_files,
        language="English",
        audio_format="mp3",
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert inventory["summary"]["section_count"] == 2
    assert inventory["summary"]["processed_count"] == 1
    assert inventory["summary"]["ready_count"] == 1


def test_build_audio_top_summary_uses_processed_wording():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    summary = module.build_audio_top_summary(
        machine_info={"name": "MacBook Pro M3 Pro (18GB)"},
        runtime_info={"gpu_available": False, "message": "No GPU detected, using CPU for inference"},
        inventory={"summary": {"ready_count": 2, "processed_count": 1, "language_count": 1, "section_count": 3}},
        conflict_policy_label="Skip safely",
    )

    assert summary["mode"] == "CPU Kokoro"
    assert summary["metrics"] == [
        ("Ready", 2),
        ("Processed", 1),
        ("Languages", 1),
        ("Sections", 3),
    ]


def test_build_run_telemetry_summary_uses_placeholders_when_nothing_processed():
    module = load_script_module("07 Generate Audio with Kokoro.py")

    telemetry = module.create_run_telemetry(total_sections=5)
    summary = module.build_run_telemetry_summary(telemetry)

    assert summary["metrics"] == [
        ("Current Section Time", "—"),
        ("Average Section Time", "—"),
        ("Last File Size", "—"),
        ("Total Generated Size", "0 B"),
        ("Overall ETA", "Calculating..."),
    ]


def test_update_run_telemetry_tracks_success_metrics_and_sizes(tmp_path: Path):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    output_path = tmp_path / "01.mp3"
    output_path.write_bytes(b"x" * 2048)

    telemetry = module.create_run_telemetry(total_sections=4)
    telemetry["run_started_at"] -= 10

    module.update_run_telemetry(
        telemetry,
        {
            "status": "processed",
            "processing_time": 4.25,
            "output": str(output_path),
        },
        language="English",
        course="Course 01",
        lecture="Lecture 01",
    )

    summary = module.build_run_telemetry_summary(telemetry)

    assert telemetry["handled_sections"] == 1
    assert telemetry["successful_sections"] == 1
    assert telemetry["current_section_time"] == 4.25
    assert telemetry["average_section_time"] == 4.25
    assert telemetry["last_file_size_bytes"] == 2048
    assert telemetry["total_generated_size_bytes"] == 2048
    assert telemetry["current_file_name"] == "01.mp3"
    assert summary["metrics"][0] == ("Current Section Time", "4.2s")
    assert summary["metrics"][1] == ("Average Section Time", "4.2s")
    assert summary["metrics"][2] == ("Last File Size", "2.0 KB")
    assert summary["metrics"][3] == ("Total Generated Size", "2.0 KB")
    assert summary["metrics"][4][0] == "Overall ETA"
    assert summary["metrics"][4][1] != "Calculating..."


def test_generate_tts_for_sections_processed_results_include_source_file(monkeypatch, tmp_path: Path):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    section_file = tmp_path / "English text" / "01.txt"
    output_dir = tmp_path / "English audio"
    section_file.parent.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    section_file.write_text("hello world from kokoro", encoding="utf-8")

    def fake_convert_text_to_speech(**kwargs):
        return {
            "success": True,
            "message": "Text-to-speech conversion successful",
            "timestamps": None,
        }

    monkeypatch.setattr(module, "convert_text_to_speech", fake_convert_text_to_speech)

    results = module.generate_tts_for_sections(
        section_files=[str(section_file)],
        voice="af_bella",
        model="kokoro",
        output_dir=str(output_dir),
        response_format="mp3",
    )

    assert results[0]["status"] == "processed"
    assert results[0]["file"] == str(section_file)


def test_run_fails_fast_when_connection_unavailable(monkeypatch, tmp_path: Path):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    monkeypatch.setattr(module, "check_connection", lambda api_base: (False, "offline"))

    config = {
        "paths": {"input_root": tmp_path},
        "machine": {"profile": "windows_i5_12450h_rtx3050_16gb"},
        "run": {
            "conflict_policy": "skip_safely",
            "audio_format": "mp3",
            "generate_timestamps": False,
            "save_timestamps": False,
        },
        "languages": {
            "English": {
                "enabled": True,
                "voice": "af_heart",
                "speed": 1.0,
                "normalize": True,
            }
        },
    }

    assert module.run(config) == 1


def test_run_fails_when_input_root_is_missing(monkeypatch, tmp_path: Path, capsys):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    monkeypatch.setattr(module, "check_connection", lambda api_base: (True, "Connected"))
    monkeypatch.setattr(
        module,
        "inspect_kokoro_runtime",
        lambda api_base: {"connected": True, "runtime_mode": "gpu", "gpu_available": True, "message": "GPU active"},
    )
    monkeypatch.setattr(
        module,
        "get_available_voices",
        lambda api_base=module.KOKORO_API_URL: [
            {"id": "af_heart", "name": "Heart", "gender": "Female", "language": "English", "description": "English voice"},
        ],
    )

    config = {
        "paths": {"input_root": tmp_path / "missing-input"},
        "machine": {"profile": "windows_i5_12450h_rtx3050_16gb"},
        "run": {
            "conflict_policy": "skip_safely",
            "audio_format": "mp3",
            "generate_timestamps": False,
            "save_timestamps": False,
        },
        "languages": {
            "English": {
                "enabled": True,
                "voice": "af_heart",
                "speed": 1.0,
                "normalize": True,
            }
        },
    }

    assert module.run(config) == 1
    captured = capsys.readouterr()
    assert "Input directory not found" in captured.out


def test_run_fails_when_configured_voice_is_missing_from_live_voice_list(monkeypatch, tmp_path: Path, capsys):
    module = load_script_module("07 Generate Audio with Kokoro.py")

    monkeypatch.setattr(module, "check_connection", lambda api_base: (True, "Connected"))
    monkeypatch.setattr(
        module,
        "inspect_kokoro_runtime",
        lambda api_base: {"connected": True, "runtime_mode": "gpu", "gpu_available": True, "message": "GPU active"},
    )
    monkeypatch.setattr(
        module,
        "get_available_voices",
        lambda api_base=module.KOKORO_API_URL: [
            {"id": "af_bella", "name": "Bella", "gender": "Female", "language": "English", "description": "English voice"},
        ],
    )

    config = {
        "paths": {"input_root": tmp_path},
        "machine": {"profile": "windows_i5_12450h_rtx3050_16gb"},
        "run": {
            "conflict_policy": "skip_safely",
            "audio_format": "mp3",
            "generate_timestamps": False,
            "save_timestamps": False,
        },
        "languages": {
            "English": {
                "enabled": True,
                "voice": "af_heart",
                "speed": 1.0,
                "normalize": True,
            }
        },
    }

    assert module.run(config) == 1
    captured = capsys.readouterr()
    assert "Configured Kokoro voice validation failed" in captured.out
