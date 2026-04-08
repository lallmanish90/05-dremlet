from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "pages/52_multilingual_folder_structure.py",
    "pages/53_Convert_Text_to_multiple_languages.py",
    "pages/54_Multilingual_TTS.py",
    "pages/55_TTS_Open_AI.py",
    "pages/60_mp4_CPU.py",
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
