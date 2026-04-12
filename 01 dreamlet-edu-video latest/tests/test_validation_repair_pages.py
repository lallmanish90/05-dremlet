from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PAGE_PATH = ROOT / "pages" / "08 Validate File Counts.py"
REPAIR_PAGE_PATH = ROOT / "pages" / "09 Repair MP4 Inputs.py"


def load_validate_module():
    module_name = f"dreamlet_page_08_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, VALIDATE_PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_repair_module():
    module_name = f"dreamlet_page_09_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, REPAIR_PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_course_info_prefers_course_under_input_root(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "11 Udemy - claude code"
    lecture_file = (
        project_root
        / "input"
        / "7 Effective Communication Skills for Work and Life"
        / "Lecture 07"
        / "English text"
        / "01.txt"
    )
    lecture_file.parent.mkdir(parents=True)
    lecture_file.write_text("hello", encoding="utf-8")

    monkeypatch.chdir(project_root)
    module = load_validate_module()

    course_info = module.extract_course_info(str(lecture_file))

    assert course_info.course_name == "7 Effective Communication Skills for Work and Life"
    assert course_info.course_number == "7"


def test_build_mismatch_buckets_reports_missing_summary_audio_reason():
    module = load_repair_module()

    organized_data = {
        "Main": {
            "Course 07": {
                "Main Section": {
                    "Lecture 07": {
                        "path": "/tmp/course/Lecture 07",
                        "languages": ["English"],
                        "language_data": {
                            "English": {
                                "audio_count": 8,
                                "image_count": 8,
                                "summary_audio_count": 0,
                                "image_files": [f"/tmp/course/Lecture 07/English image/{i:02d}.png" for i in range(1, 9)],
                            }
                        },
                    }
                }
            }
        }
    }

    fixable, not_fixable = module.build_mismatch_buckets(organized_data, "English")

    assert fixable == []
    assert len(not_fixable) == 1
    assert not_fixable[0]["display"] == "Lecture 07 (Course 07)"
    assert "summary audio" in not_fixable[0]["reason"].lower()


def test_build_mismatch_buckets_keeps_plus_two_image_case_fixable():
    module = load_repair_module()

    organized_data = {
        "Main": {
            "Course 10": {
                "Main Section": {
                    "Lecture 10": {
                        "path": "/tmp/course/Lecture 10",
                        "languages": ["English"],
                        "language_data": {
                            "English": {
                                "audio_count": 8,
                                "image_count": 10,
                                "summary_audio_count": 8,
                                "image_files": [f"/tmp/course/Lecture 10/English image/{i:02d}.png" for i in range(1, 11)],
                            }
                        },
                    }
                }
            }
        }
    }

    fixable, not_fixable = module.build_mismatch_buckets(organized_data, "English")

    assert len(fixable) == 1
    assert not not_fixable
    assert fixable[0]["fix_type"] == "remove_excess"
