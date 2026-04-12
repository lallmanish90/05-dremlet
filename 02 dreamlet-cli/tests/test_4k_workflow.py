from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from conftest import load_script_module, run_script
from PIL import Image


def test_machine_profiles_define_expected_two_machine_profiles():
    module = load_script_module("06 Generate 4K Images.py")

    assert sorted(module.MACHINE_PROFILES) == [
        "macbook_pro_m3_pro_18gb",
        "windows_i5_12450h_rtx3050_16gb",
    ]
    mac_profile = module.MACHINE_PROFILES["macbook_pro_m3_pro_18gb"]
    windows_profile = module.MACHINE_PROFILES["windows_i5_12450h_rtx3050_16gb"]

    assert mac_profile["name"] == "MacBook Pro M3 Pro (18GB)"
    assert mac_profile["match_rules"]["platform"] == "darwin"
    assert mac_profile["optimization_settings"]["default_conversion_method"] == module.ConversionMethod.LIBREOFFICE.value

    assert windows_profile["match_rules"]["gpu_name_contains"] == "rtx 3050"
    assert windows_profile["optimization_settings"]["preferred_image_processing"] == "cuda"


def test_select_machine_profile_prefers_matching_windows_profile():
    module = load_script_module("06 Generate 4K Images.py")

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
    assert any("rtx 3050" in reason.lower() for reason in selected["match_reasons"])


def test_select_pdf_rasterizer_prefers_pdftocairo_when_available():
    module = load_script_module("06 Generate 4K Images.py")

    backend = module.select_pdf_rasterizer({"pdftocairo": True, "pdftoppm": True})

    assert backend == "pdftocairo"


def test_get_libreoffice_path_uses_standard_windows_install_when_not_in_path(monkeypatch):
    module = load_script_module("06 Generate 4K Images.py")

    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        module.os.path,
        "exists",
        lambda path: path == r"C:\Program Files\LibreOffice\program\soffice.exe",
    )

    detected = module.get_libreoffice_path()

    assert detected == r"C:\Program Files\LibreOffice\program\soffice.exe"


def test_get_libreoffice_path_returns_none_when_not_installed(monkeypatch):
    module = load_script_module("06 Generate 4K Images.py")

    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module.os.path, "exists", lambda path: False)

    detected = module.get_libreoffice_path()

    assert detected is None


def test_get_recommended_conversion_method_falls_back_to_python_pptx_without_tooling():
    module = load_script_module("06 Generate 4K Images.py")

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


def test_resolve_existing_processing_skip_safely_reprocesses_when_outputs_missing():
    module = load_script_module("06 Generate 4K Images.py")

    decision = module.resolve_existing_processing_action(
        archived_source_exists=True,
        output_folder_exists=True,
        existing_png_count=0,
        conflict_policy=module.ConflictPolicy.SKIP_SAFELY.value,
    )

    assert decision["action"] == "reprocess"
    assert decision["status"] == "repair"


def test_find_presentation_inventory_excludes_archived_all_pptx_files(tmp_path: Path):
    module = load_script_module("06 Generate 4K Images.py")

    course = tmp_path / "Course 01"
    lecture = course / "Lecture 01"
    archived = course / "all_pptx"
    lecture.mkdir(parents=True)
    archived.mkdir(parents=True)

    (course / "Lecture 01.pptx").write_text("pptx", encoding="utf-8")
    (course / "Lecture 02.zip").write_text("zip", encoding="utf-8")
    (archived / "Lecture 03.pptx").write_text("archived", encoding="utf-8")

    inventory = module.find_presentation_inventory(tmp_path)

    assert len(inventory["actionable"]) == 2
    assert len(inventory["archived"]) == 1
    assert inventory["summary"]["total_found"] == 3
    assert inventory["summary"]["actionable_count"] == 2
    assert inventory["summary"]["archived_count"] == 1


def test_build_run_summary_uses_actionable_counts_for_processing():
    module = load_script_module("06 Generate 4K Images.py")

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

    assert summary["button_label"] == "Extract 2 Presentations"
    assert summary["conflict_policy_label"] == "Skip safely"


def test_run_fails_when_input_root_is_missing(tmp_path: Path, capsys):
    module = load_script_module("06 Generate 4K Images.py")

    config = {
        "paths": {
            "input_root": tmp_path / "missing-input",
            "config_root": tmp_path,
        },
        "machine": {"profile": "windows_i5_12450h_rtx3050_16gb"},
        "run": {
            "conflict_policy": "skip_safely",
            "keep_raw_without_logo": False,
        },
        "conversion": {
            "method": "libreoffice",
            "enable_auto_fallback": True,
        },
    }

    assert module.run(config) == 1
    captured = capsys.readouterr()
    assert "Input directory not found" in captured.out


def test_cli_4k_report_only_run_reports_conflicts_without_mutation(tmp_path: Path):
    course = tmp_path / "Course 01"
    course.mkdir()
    source_file = course / "Lecture 01.pptx"
    source_file.write_text("source", encoding="utf-8")
    archived_dir = course / "all_pptx"
    archived_dir.mkdir()
    (archived_dir / "Lecture 01.pptx").write_text("archived", encoding="utf-8")
    image_dir = course / "Lecture 01" / "English image"
    image_dir.mkdir(parents=True)
    (image_dir / "01.png").write_bytes(b"png")

    config_root = tmp_path / "assets"
    config_root.mkdir()
    (config_root / "copyright.txt").write_text("copyright", encoding="utf-8")

    config_path = tmp_path / "4k.toml"
    config_path.write_text(
        f"""
[paths]
input_root = "{tmp_path.as_posix()}"
config_root = "{config_root.as_posix()}"

[machine]
profile = "windows_i5_12450h_rtx3050_16gb"

[run]
conflict_policy = "report_only"
keep_raw_without_logo = false

[conversion]
method = "python-pptx"
enable_auto_fallback = true
""".strip(),
        encoding="utf-8",
    )

    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = run_script("06 Generate 4K Images.py", "--config", str(config_path))

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    assert result.returncode == 0
    assert "profile=windows_i5_12450h_rtx3050_16gb" in result.stdout
    assert "reported=1" in result.stdout
    assert before == after


def test_load_config_reads_optional_runtime_processing_overrides(tmp_path: Path):
    module = load_script_module("06 Generate 4K Images.py")

    config_root = tmp_path / "assets"
    config_root.mkdir()
    config_path = tmp_path / "4k.toml"
    config_path.write_text(
        f"""
[paths]
input_root = "{tmp_path.as_posix()}"
config_root = "{config_root.as_posix()}"

[machine]
profile = "generic_fallback"

[run]
conflict_policy = "skip_safely"
keep_raw_without_logo = false
max_threads = 3
batch_size = 2
image_processing = "cuda"

[conversion]
method = "python-pptx"
enable_auto_fallback = true
""".strip(),
        encoding="utf-8",
    )

    loaded = module.load_config(config_path)

    assert loaded["run"]["max_threads"] == 3
    assert loaded["run"]["batch_size"] == 2
    assert loaded["run"]["image_processing"] == "cuda"


def test_extract_slides_from_zip_uses_batched_thread_pool(tmp_path: Path, monkeypatch):
    module = load_script_module("06 Generate 4K Images.py")

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index, size in enumerate(((800, 600), (1280, 720), (1024, 768)), start=1):
        Image.new("RGB", size, (20 * index, 40 * index, 60 * index)).save(source_dir / f"{index}_slide.png")

    zip_path = tmp_path / "slides.zip"
    with ZipFile(zip_path, "w") as archive:
        for image_path in sorted(source_dir.glob("*.png")):
            archive.write(image_path, arcname=image_path.name)

    executor_calls: list[int] = []

    class RecordingExecutor:
        def __init__(self, max_workers: int):
            executor_calls.append(max_workers)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, func, iterable):
            return [func(item) for item in iterable]

    monkeypatch.setattr(module.concurrent.futures, "ThreadPoolExecutor", RecordingExecutor)

    success, output_paths, slide_count = module.extract_slides_from_zip(
        zip_path,
        tmp_path / "out",
        {
            "max_threads": 4,
            "batch_size": 2,
            "preferred_image_processing": "cpu",
            "runtime_acceleration": "cpu",
        },
    )

    assert success is True
    assert slide_count == 3
    assert [path.name for path in output_paths] == ["01.png", "02.png", "03.png"]
    assert executor_calls == [2, 1]


def test_process_presentation_brands_images_in_parallel_batches(tmp_path: Path, monkeypatch):
    module = load_script_module("06 Generate 4K Images.py")

    course = tmp_path / "Course 01"
    course.mkdir()
    source_path = course / "Lecture 01.pptx"
    source_path.write_text("pptx", encoding="utf-8")

    extracted_dir = tmp_path / "extracted"
    extracted_dir.mkdir()
    extracted_images = []
    for index in range(1, 4):
        image_path = extracted_dir / f"{index:02d}.png"
        Image.new("RGB", (1200, 800), (15 * index, 30 * index, 45 * index)).save(image_path)
        extracted_images.append(image_path)

    config_root = tmp_path / "assets"
    config_root.mkdir()
    (config_root / "copyright.txt").write_text("copyright", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "extract_slides_with_method",
        lambda *args, **kwargs: (True, extracted_images, len(extracted_images)),
    )

    executor_calls: list[int] = []

    class RecordingExecutor:
        def __init__(self, max_workers: int):
            executor_calls.append(max_workers)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, func, iterable):
            return [func(item) for item in iterable]

    monkeypatch.setattr(module.concurrent.futures, "ThreadPoolExecutor", RecordingExecutor)

    result = module.process_presentation(
        source_path,
        {
            "paths": {"config_root": config_root},
            "run": {
                "conflict_policy": module.ConflictPolicy.SKIP_SAFELY.value,
                "keep_raw_without_logo": False,
                "max_threads": None,
                "batch_size": None,
                "image_processing": "auto",
            },
            "conversion": {
                "method": module.ConversionMethod.PYTHON_PPTX.value,
                "enable_auto_fallback": True,
            },
        },
        {
            "max_threads": 4,
            "batch_size": 2,
            "preferred_image_processing": "cpu",
            "runtime_acceleration": "cpu",
        },
    )

    output_dir = Path(result["output_dir"])

    assert result["status"] == "success"
    assert result["slide_count"] == 3
    assert sorted(path.name for path in output_dir.glob("*.png")) == ["01.png", "02.png", "03.png"]
    assert executor_calls == [2, 1]
