from __future__ import annotations

from pathlib import Path

import pytest
from conftest import load_script_module


def test_load_4k_config_requires_input_root(tmp_path: Path):
    config_path = tmp_path / "4k.toml"
    config_path.write_text(
        """
[paths]
config_root = "assets"

[machine]
profile = "auto"

[run]
conflict_policy = "skip_safely"
keep_raw_without_logo = false

[conversion]
method = "libreoffice"
enable_auto_fallback = true
""".strip(),
        encoding="utf-8",
    )

    module = load_script_module("06 Generate 4K Images.py")

    with pytest.raises(module.ConfigError, match="input_root"):
        module.load_config(config_path)


def test_load_kokoro_config_rejects_unknown_profile(tmp_path: Path):
    config_path = tmp_path / "kokoro.toml"
    config_path.write_text(
        """
[paths]
input_root = "input"

[machine]
profile = "wrong"

[run]
conflict_policy = "skip_safely"
audio_format = "mp3"
generate_timestamps = false
save_timestamps = false
""".strip(),
        encoding="utf-8",
    )

    module = load_script_module("07 Generate Audio with Kokoro.py")

    with pytest.raises(module.ConfigError, match="profile"):
        module.load_config(config_path)


def test_load_mp4_config_resolves_paths_relative_to_config_file(tmp_path: Path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    input_dir = tmp_path / "shared-input"
    output_dir = tmp_path / "shared-output"
    input_dir.mkdir()
    output_dir.mkdir()
    config_path = config_dir / "mp4.toml"
    config_path.write_text(
        """
[paths]
input_root = "../shared-input"
output_root = "../shared-output"

[machine]
profile = "auto"

[run]
conflict_policy = "skip_safely"
language = "English"
generate_regular = true
generate_summary = true

[selection]
include_courses = ["Course *"]
exclude_courses = []
include_sections = []
exclude_sections = []
include_lectures = []
exclude_lectures = []
""".strip(),
        encoding="utf-8",
    )

    module = load_script_module("10 Render MP4 Videos.py")

    config = module.load_config(config_path)

    assert config["paths"]["input_root"] == input_dir.resolve()
    assert config["paths"]["output_root"] == output_dir.resolve()


def test_load_4k_config_rejects_unknown_conversion_method(tmp_path: Path):
    config_path = tmp_path / "4k.toml"
    config_path.write_text(
        """
[paths]
input_root = "input"
config_root = "config"

[machine]
profile = "auto"

[run]
conflict_policy = "skip_safely"
keep_raw_without_logo = false

[conversion]
method = "wrong"
enable_auto_fallback = true
""".strip(),
        encoding="utf-8",
    )

    module = load_script_module("06 Generate 4K Images.py")

    with pytest.raises(module.ConfigError, match="method"):
        module.load_config(config_path)


def test_load_kokoro_config_requires_language_voice_settings(tmp_path: Path):
    config_path = tmp_path / "kokoro.toml"
    config_path.write_text(
        """
[paths]
input_root = "input"

[machine]
profile = "auto"

[run]
conflict_policy = "skip_safely"
audio_format = "mp3"
generate_timestamps = false
save_timestamps = false

[languages.English]
enabled = true
speed = 1.0
normalize = true
""".strip(),
        encoding="utf-8",
    )

    module = load_script_module("07 Generate Audio with Kokoro.py")

    with pytest.raises(module.ConfigError, match="voice"):
        module.load_config(config_path)
