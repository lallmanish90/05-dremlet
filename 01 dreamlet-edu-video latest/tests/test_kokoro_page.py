from __future__ import annotations

import importlib.util
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
