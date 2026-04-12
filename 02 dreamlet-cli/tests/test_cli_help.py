from __future__ import annotations

from pathlib import Path

from conftest import run_script

def test_subcommand_help_mentions_config_flag():
    result = run_script("06 Generate 4K Images.py", "--help")

    assert result.returncode == 0
    assert "--config" in result.stdout

    kokoro = run_script("07 Generate Audio with Kokoro.py", "--help")
    mp4 = run_script("10 Render MP4 Videos.py", "--help")

    assert kokoro.returncode == 0
    assert mp4.returncode == 0
    assert "--config" in kokoro.stdout
    assert "--config" in mp4.stdout


def test_missing_config_fails_cleanly():
    result = run_script("06 Generate 4K Images.py", "--config", "C:/missing.toml")

    assert result.returncode == 1
    assert "Config error:" in result.stderr


def test_invalid_config_fails_cleanly(tmp_path: Path):
    config_path = tmp_path / "bad.toml"
    config_path.write_text(
        """
[paths]
config_root = "missing"
""".strip(),
        encoding="utf-8",
    )

    result = run_script("06 Generate 4K Images.py", "--config", str(config_path))

    assert result.returncode == 1
    assert "Config error:" in result.stderr
