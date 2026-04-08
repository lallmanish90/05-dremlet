from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_python_files_have_no_streamlit_imports():
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "import streamlit" in text or "from streamlit" in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_python_files_have_no_runtime_dependency_on_source_project():
    offenders = []
    needles = [
        "01 dreamlet-edu-video latest",
        "from pages import",
        "import pages.",
    ]
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []
