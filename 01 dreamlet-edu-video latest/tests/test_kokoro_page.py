from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import uuid


ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = ROOT / "pages" / "07 Generate Audio with Kokoro.py"


def load_page_module():
    module_name = f"dreamlet_page_07_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_machine_profiles_define_expected_two_machine_profiles():
    module = load_page_module()
    assert sorted(module.MACHINE_PROFILES) == [
        "generic_fallback",
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_page_module()
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
    module = load_page_module()
    decision = module.resolve_existing_audio_action(True, module.ConflictPolicy.SKIP_SAFELY.value)
    assert decision["action"] == "skip"
    assert decision["status"] == "skipped"


def test_resolve_existing_audio_action_report_only_reports_existing():
    module = load_page_module()
    decision = module.resolve_existing_audio_action(True, module.ConflictPolicy.REPORT_ONLY.value)
    assert decision["action"] == "report"
    assert decision["status"] == "reported"


def test_build_audio_inventory_counts_ready_and_processed():
    module = load_page_module()
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        lecture_dir = root / "Course 01" / "Lecture 01"
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
    module = load_page_module()
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
    module = load_page_module()

    telemetry = module.create_run_telemetry(total_sections=5)
    summary = module.build_run_telemetry_summary(telemetry)

    assert summary["metrics"] == [
        ("Current Section Time", "—"),
        ("Average Section Time", "—"),
        ("Last File Size", "—"),
        ("Total Generated Size", "0 B"),
        ("Overall ETA", "Calculating..."),
    ]


def test_update_run_telemetry_tracks_success_metrics_and_sizes():
    module = load_page_module()

    with TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "01.mp3"
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
        assert telemetry["current_language"] == "English"
        assert telemetry["current_course"] == "Course 01"
        assert telemetry["current_lecture"] == "Lecture 01"
        assert summary["metrics"][0] == ("Current Section Time", "4.2s")
        assert summary["metrics"][1] == ("Average Section Time", "4.2s")
        assert summary["metrics"][2] == ("Last File Size", "2.0 KB")
        assert summary["metrics"][3] == ("Total Generated Size", "2.0 KB")
        assert summary["metrics"][4][0] == "Overall ETA"
        assert summary["metrics"][4][1] != "Calculating..."


def test_update_run_telemetry_skips_do_not_change_speed_or_size_averages():
    module = load_page_module()

    telemetry = module.create_run_telemetry(total_sections=4)
    telemetry["run_started_at"] -= 10
    telemetry["successful_sections"] = 1
    telemetry["current_section_time"] = 5.0
    telemetry["average_section_time"] = 5.0
    telemetry["total_successful_processing_time"] = 5.0
    telemetry["last_file_size_bytes"] = 4096
    telemetry["total_generated_size_bytes"] = 4096

    module.update_run_telemetry(
        telemetry,
        {
            "status": "skipped",
            "processing_time": 0,
            "file": "/tmp/02.txt",
        },
        language="English",
        course="Course 01",
        lecture="Lecture 02",
    )

    summary = module.build_run_telemetry_summary(telemetry)

    assert telemetry["handled_sections"] == 1
    assert telemetry["successful_sections"] == 1
    assert telemetry["skipped_sections"] == 1
    assert telemetry["current_section_time"] == 5.0
    assert telemetry["average_section_time"] == 5.0
    assert telemetry["last_file_size_bytes"] == 4096
    assert telemetry["total_generated_size_bytes"] == 4096
    assert summary["metrics"][0] == ("Current Section Time", "5.0s")
    assert summary["metrics"][1] == ("Average Section Time", "5.0s")
    assert summary["metrics"][2] == ("Last File Size", "4.0 KB")
    assert summary["metrics"][3] == ("Total Generated Size", "4.0 KB")


def test_generate_tts_for_sections_processed_results_include_source_file(monkeypatch):
    module = load_page_module()

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        section_file = root / "English text" / "01.txt"
        output_dir = root / "English audio"
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
