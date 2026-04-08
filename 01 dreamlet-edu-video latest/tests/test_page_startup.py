from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "pages/06 Generate 4K Images.py",
    "pages/07 Generate Audio with Kokoro.py",
    "pages/10 Render MP4 Videos.py",
    "pages/52 Create Multilingual Folder Structure.py",
    "pages/53 Convert Text to Multiple Languages.py",
    "pages/54 Generate Multilingual Audio.py",
    "pages/55 Generate Audio with OpenAI.py",
    "pages/60 Legacy MP4 CPU.py",
]


def _prepare_runtime_tree(base: Path) -> None:
    (base / "input").mkdir()
    (base / "output").mkdir()
    (base / "config").mkdir()
    (base / "config" / "prompt.txt").write_text(
        "Translate the following text to {TARGET_LANGUAGE}: {TEXT_CONTENT}\n",
        encoding="utf-8",
    )


def test_problem_pages_start_without_import_or_name_errors(monkeypatch, tmp_path: Path):
    _prepare_runtime_tree(tmp_path)
    monkeypatch.chdir(tmp_path)

    for relative_path in PAGES:
        runpy.run_path(str(ROOT / relative_path), run_name="__main__")
