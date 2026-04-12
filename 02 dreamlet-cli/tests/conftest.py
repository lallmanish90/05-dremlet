from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def script_path(name: str) -> Path:
    return SRC / name


def load_script_module(name: str):
    path = script_path(name)
    module_name = f"dreamlet_{path.stem.replace(' ', '_')}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path(name)), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
