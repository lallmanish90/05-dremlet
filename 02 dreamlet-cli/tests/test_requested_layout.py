from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_src_contains_only_the_three_requested_page_files():
    src = ROOT / "src"
    files = sorted(path.name for path in src.iterdir() if path.is_file())
    ignored_directories = {"__pycache__", "dreamlet_cli.egg-info"}
    directories = sorted(path.name for path in src.iterdir() if path.is_dir() and path.name not in ignored_directories)

    assert files == [
        "06 Generate 4K Images.py",
        "07 Generate Audio with Kokoro.py",
        "10 Render MP4 Videos.py",
    ]
    assert directories == []


def test_config_contains_same_named_toml_files():
    config = ROOT / "config"
    tomls = sorted(path.name for path in config.glob("*.toml"))

    assert tomls == [
        "06 Generate 4K Images.toml",
        "07 Generate Audio with Kokoro.toml",
        "10 Render MP4 Videos.toml",
    ]
