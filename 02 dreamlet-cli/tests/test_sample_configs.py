from __future__ import annotations

from pathlib import Path
from conftest import load_script_module


ROOT = Path(__file__).resolve().parents[1]


def test_sample_workflow_configs_exist_and_load():
    four_k = ROOT / "config" / "06 Generate 4K Images.toml"
    kokoro = ROOT / "config" / "07 Generate Audio with Kokoro.toml"
    mp4 = ROOT / "config" / "10 Render MP4 Videos.toml"

    assert four_k.exists()
    assert kokoro.exists()
    assert mp4.exists()

    four_k_config = load_script_module("06 Generate 4K Images.py").load_config(four_k)
    kokoro_config = load_script_module("07 Generate Audio with Kokoro.py").load_config(kokoro)
    mp4_config = load_script_module("10 Render MP4 Videos.py").load_config(mp4)

    assert four_k_config["machine"]["profile"] == "windows_i5_12450h_rtx3050_16gb"
    assert kokoro_config["languages"]["English"]["enabled"] is True
    assert kokoro_config["machine"]["profile"] == "windows_i5_12450h_rtx3050_16gb"
    assert kokoro_config["languages"]["English"]["voice"] == "af_heart"
    assert mp4_config["run"]["language"] == "English"
    assert mp4_config["machine"]["profile"] == "windows_i5_12450h_rtx3050_16gb"
