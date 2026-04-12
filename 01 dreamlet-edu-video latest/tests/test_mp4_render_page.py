from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import uuid


ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = ROOT / "pages" / "10 Render MP4 Videos.py"


def load_page_module():
    module_name = f"dreamlet_page_10_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_machine_profiles_define_expected_two_machine_profiles():
    module = load_page_module()
    profiles = module.MACHINE_PROFILES

    assert sorted(profiles) == [
        "generic_fallback",
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]
    assert profiles["macbook_pro_m3_pro_18gb"]["name"] == "MacBook Pro M3 Pro (18GB)"
    assert profiles["windows_i5_12450h_rtx3050_16gb"]["encoder_preferences"][0] == "h264_nvenc"


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_page_module()

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
    module = load_page_module()

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
    module = load_page_module()

    encoder, decoder, capabilities = module.select_video_encoder(
        "windows_i5_12450h_rtx3050_16gb",
        "Windows",
        "amd64",
        "",
    )

    assert encoder == "libx264"
    assert decoder is None
    assert capabilities["hardware_encoding"] is False


def test_resolve_existing_output_action_skip_safely_skips_existing():
    module = load_page_module()

    decision = module.resolve_existing_output_action(
        existing_output_exists=True,
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert decision["action"] == "skip"
    assert decision["status"] == "skipped"


def test_resolve_existing_output_action_report_only_reports_existing():
    module = load_page_module()

    decision = module.resolve_existing_output_action(
        existing_output_exists=True,
        conflict_policy=module.ConflictPolicy.REPORT_ONLY.value,
    )

    assert decision["action"] == "report"
    assert decision["status"] == "reported"


def test_build_render_inventory_counts_ready_and_processed_outputs():
    module = load_page_module()

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        lecture_dir = input_dir / "Course 01" / "Section A" / "Lecture 01"
        lecture_dir.mkdir(parents=True)
        output_dir.mkdir()

        module.INPUT_DIR = str(input_dir)
        module.OUTPUT_DIR = str(output_dir)

        existing_output = Path(module.generate_output_path(str(lecture_dir), "English", summary=False))
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
    module = load_page_module()

    session_state = {}
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

    module.set_global_course_selection(session_state, organized_data, False)

    assert session_state["mp4_select_all"] is False
    assert session_state[module.build_course_selection_state_key("Main", "Course 01")] is False
    assert session_state[module.build_course_selection_state_key("Main", "Course 02")] is False
    assert session_state[module.build_course_selection_state_key("Archive", "Course 03")] is False
