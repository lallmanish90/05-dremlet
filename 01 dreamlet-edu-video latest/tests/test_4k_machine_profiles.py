from __future__ import annotations

import io
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import uuid


ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = ROOT / "pages" / "06 Generate 4K Images.py"


def load_page_module():
    module_name = f"dreamlet_page_06_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, PAGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_page_module_with_stdout(stdout):
    original_stdout = sys.stdout
    try:
        sys.stdout = stdout
        return load_page_module()
    finally:
        sys.stdout = original_stdout


def test_page_import_does_not_crash_with_cp1252_stdout():
    stdout_buffer = io.BytesIO()
    stdout = io.TextIOWrapper(stdout_buffer, encoding="cp1252", errors="strict")

    module = load_page_module_with_stdout(stdout)

    stdout.flush()
    output = stdout_buffer.getvalue().decode("cp1252")

    assert module is not None
    assert "CUDA framework" in output


def test_machine_profiles_define_expected_two_machine_profiles():
    module = load_page_module()
    profiles = module.MACHINE_PROFILES

    assert sorted(profiles) == [
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]
    mac_profile = profiles["macbook_pro_m3_pro_18gb"]
    windows_profile = profiles["windows_i5_12450h_rtx3050_16gb"]

    assert mac_profile["name"] == "MacBook Pro M3 Pro (18GB)"
    assert mac_profile["match_rules"]["platform"] == "darwin"
    assert mac_profile["optimization_settings"]["default_conversion_method"] == module.ConversionMethod.LIBREOFFICE.value

    assert windows_profile["match_rules"]["gpu_name_contains"] == "rtx 3050"
    assert windows_profile["optimization_settings"]["preferred_image_processing"] == "cuda"


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_page_module()
    profiles = module.MACHINE_PROFILES

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

    selected = module.select_machine_profile(system_info, profiles)

    assert selected["machine_id"] == "windows_i5_12450h_rtx3050_16gb"
    assert selected["match_source"] == "auto"
    assert any("rtx 3050" in reason.lower() for reason in selected["match_reasons"])


def test_select_machine_profile_honors_manual_override():
    module = load_page_module()
    profiles = module.MACHINE_PROFILES

    system_info = {
        "hostname": "my-macbook",
        "platform": "darwin",
        "architecture": "arm64",
        "cpu": "apple m3 pro",
        "memory_gb": 18,
        "cpu_count": 12,
        "gpu_detected": True,
        "gpu_type": "apple_silicon",
        "gpu_name": "Apple Silicon GPU",
    }

    selected = module.select_machine_profile(
        system_info,
        profiles,
        override_profile_id="windows_i5_12450h_rtx3050_16gb",
    )

    assert selected["machine_id"] == "windows_i5_12450h_rtx3050_16gb"
    assert selected["match_source"] == "manual"
    assert selected["match_reasons"] == ["Manual override selected"]


def test_select_pdf_rasterizer_prefers_pdftocairo_when_available():
    module = load_page_module()

    backend = module.select_pdf_rasterizer({
        "pdftocairo": True,
        "pdftoppm": True,
    })

    assert backend == "pdftocairo"


def test_get_recommended_conversion_method_prefers_libreoffice_pipeline():
    module = load_page_module()

    recommended = module.get_recommended_conversion_method(
        "macbook_pro_m3_pro_18gb",
        {
            "libreoffice": True,
            "pdftocairo": True,
            "pdftoppm": True,
            "pdf2image": True,
        },
    )

    assert recommended == module.ConversionMethod.LIBREOFFICE


def test_get_recommended_conversion_method_falls_back_to_python_pptx_without_tooling():
    module = load_page_module()

    recommended = module.get_recommended_conversion_method(
        "generic_fallback",
        {
            "libreoffice": False,
            "pdftocairo": False,
            "pdftoppm": False,
            "pdf2image": False,
        },
    )

    assert recommended == module.ConversionMethod.PYTHON_PPTX


def test_build_pdf2image_kwargs_prefers_paths_only_and_pdftocairo():
    module = load_page_module()

    kwargs = module.build_pdf2image_kwargs(
        "/tmp/output",
        {
            "pdftocairo": True,
        },
    )

    assert kwargs["output_folder"] == "/tmp/output"
    assert kwargs["fmt"] == "png"
    assert kwargs["dpi"] == 300
    assert kwargs["paths_only"] is True
    assert kwargs["use_pdftocairo"] is True


def test_resolve_existing_processing_skip_safely_skips_when_outputs_exist():
    module = load_page_module()

    decision = module.resolve_existing_processing_action(
        archived_source_exists=True,
        output_folder_exists=True,
        existing_png_count=12,
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert decision["action"] == "skip"
    assert decision["status"] == "skipped"


def test_resolve_existing_processing_skip_safely_reprocesses_when_outputs_missing():
    module = load_page_module()

    decision = module.resolve_existing_processing_action(
        archived_source_exists=True,
        output_folder_exists=True,
        existing_png_count=0,
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert decision["action"] == "reprocess"
    assert decision["status"] == "repair"


def test_resolve_existing_processing_report_only_does_not_process():
    module = load_page_module()

    decision = module.resolve_existing_processing_action(
        archived_source_exists=True,
        output_folder_exists=True,
        existing_png_count=8,
        conflict_policy=module.ConflictPolicy.REPORT_ONLY.value,
    )

    assert decision["action"] == "report"
    assert decision["status"] == "reported"


def test_find_presentation_inventory_excludes_archived_all_pptx_files():
    module = load_page_module()

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        course = root / "Course 01"
        lecture = course / "Lecture 01"
        archived = course / "all_pptx"
        lecture.mkdir(parents=True)
        archived.mkdir(parents=True)

        (course / "Lecture 01.pptx").write_text("pptx", encoding="utf-8")
        (course / "Lecture 02.zip").write_text("zip", encoding="utf-8")
        (archived / "Lecture 03.pptx").write_text("archived", encoding="utf-8")

        inventory = module.find_presentation_inventory(str(root))

        assert len(inventory["actionable"]) == 2
        assert len(inventory["archived"]) == 1
        assert inventory["summary"]["total_found"] == 3
        assert inventory["summary"]["actionable_count"] == 2
        assert inventory["summary"]["archived_count"] == 1


def test_build_run_summary_uses_actionable_counts_for_processing():
    module = load_page_module()

    inventory = {
        "actionable": [
            "/tmp/Course/Lecture 01.pptx",
            "/tmp/Course/Lecture 02.zip",
        ],
        "archived": [
            "/tmp/Course/all_pptx/Lecture 03.pptx",
        ],
        "summary": {
            "total_found": 3,
            "actionable_count": 2,
            "archived_count": 1,
            "pptx_actionable_count": 1,
            "zip_actionable_count": 1,
        },
    }

    summary = module.build_run_summary(inventory, "Skip safely")

    assert summary["actionable_count"] == 2
    assert summary["archived_count"] == 1
    assert summary["button_label"] == "Extract 2 Presentations"


def test_build_top_summary_uses_user_facing_processed_wording():
    module = load_page_module()

    summary = module.build_top_summary(
        machine_info={"name": "MacBook Pro M3 Pro (18GB)", "machine_id": "macbook_pro_m3_pro_18gb"},
        runtime_acceleration="cpu",
        run_summary={
            "actionable_count": 2,
            "archived_count": 1,
            "pptx_actionable_count": 1,
            "zip_actionable_count": 1,
            "total_found": 3,
        },
        conversion_tooling={
            "libreoffice": True,
            "pdftocairo": True,
            "pdftoppm": True,
            "pdf2image": True,
        },
        conflict_policy_label="Skip safely",
    )

    assert summary["mode"] == "CPU quality-first"
    assert summary["recommended_engine"].startswith("LibreOffice + Poppler")
    assert summary["metrics"] == [
        ("Ready", 2),
        ("Processed", 1),
        ("PPTX", 1),
        ("ZIP", 1),
    ]
