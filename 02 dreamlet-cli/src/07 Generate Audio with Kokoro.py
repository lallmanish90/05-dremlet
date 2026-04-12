from __future__ import annotations

import argparse
import enum
import glob
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import tomllib
from typing import Any, Optional

import requests


KOKORO_API_URL = "http://localhost:8880/v1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "07 Generate Audio with Kokoro.toml"


class ConflictPolicy(str, enum.Enum):
    SKIP_SAFELY = "skip_safely"
    OVERWRITE = "overwrite"
    RENDER_NEW_OUTPUT = "render_new_output"
    REPORT_ONLY = "report_only"


CONFLICT_POLICY_LABELS = {
    ConflictPolicy.SKIP_SAFELY.value: "Skip safely",
    ConflictPolicy.OVERWRITE.value: "Re-generate and overwrite",
    ConflictPolicy.RENDER_NEW_OUTPUT.value: "Render to new output",
    ConflictPolicy.REPORT_ONLY.value: "Report only",
}


MACHINE_PROFILES = {
    "macbook_pro_m3_pro_18gb": {
        "name": "MacBook Pro M3 Pro (18GB)",
        "notes": "Host profile optimized for long local Kokoro runs on the MacBook.",
        "match_rules": {
            "platform": "darwin",
            "architecture": ["arm64"],
            "ram_gb_min": 16,
            "ram_gb_max": 20,
        },
        "optimization_settings": {
            "max_languages": 3,
            "max_sections_per_batch": 24,
            "request_timeout_sec": 180,
        },
    },
    "windows_i5_12450h_rtx3050_16gb": {
        "name": "Acer Windows laptop (i5-12450H + RTX 3050)",
        "notes": "Host profile optimized for GPU-backed Kokoro runs on the RTX laptop.",
        "match_rules": {
            "platform": "windows",
            "architecture": ["amd64", "x86_64"],
            "ram_gb_min": 14,
            "ram_gb_max": 18,
        },
        "optimization_settings": {
            "max_languages": 2,
            "max_sections_per_batch": 18,
            "request_timeout_sec": 180,
        },
    },
    "generic_fallback": {
        "name": "Generic fallback profile",
        "notes": "Fallback host profile for machines outside the two supported laptops.",
        "match_rules": {},
        "optimization_settings": {
            "max_languages": 1,
            "max_sections_per_batch": 12,
            "request_timeout_sec": 180,
        },
    },
}


class ConfigError(ValueError):
    """Raised when the Kokoro config is invalid."""


def load_config(config_path: os.PathLike[str] | str | None = None) -> dict[str, Any]:
    config_file = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    try:
        with config_file.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {config_file}") from exc

    paths = data.get("paths")
    machine = data.get("machine")
    run_table = data.get("run")
    languages = data.get("languages")
    if not isinstance(paths, dict):
        raise ConfigError("Missing required [paths] table")
    if not isinstance(machine, dict):
        raise ConfigError("Missing required [machine] table")
    if not isinstance(run_table, dict):
        raise ConfigError("Missing required [run] table")

    profile = str(machine.get("profile", "auto")).strip()
    allowed_profiles = {"auto", "macbook_pro_m3_pro_18gb", "windows_i5_12450h_rtx3050_16gb", "generic_fallback"}
    if profile not in allowed_profiles:
        raise ConfigError(f"Unsupported profile: {profile}")

    if not isinstance(languages, dict):
        raise ConfigError("Missing required [languages] table")

    conflict_policy = str(run_table.get("conflict_policy", ConflictPolicy.SKIP_SAFELY.value)).strip()
    if conflict_policy not in CONFLICT_POLICY_LABELS:
        raise ConfigError(f"Unsupported conflict_policy: {conflict_policy}")

    audio_format = str(run_table.get("audio_format", "mp3")).strip()
    if audio_format not in {"mp3", "wav"}:
        raise ConfigError(f"Unsupported audio_format: {audio_format}")

    def resolve_path(raw_value: Any) -> Path:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ConfigError("Missing required path: input_root")
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = (config_file.parent / candidate).resolve()
        return candidate

    normalized_languages: dict[str, dict[str, Any]] = {}
    for language_name, settings in languages.items():
        if not isinstance(settings, dict):
            raise ConfigError(f"Expected table for language {language_name}")
        voice = settings.get("voice")
        if not isinstance(voice, str) or not voice.strip():
            raise ConfigError(f"Missing voice for {language_name}")
        speed = settings.get("speed", 1.0)
        if not isinstance(speed, (int, float)):
            raise ConfigError(f"Expected numeric speed for {language_name}")
        normalize = settings.get("normalize", True)
        enabled = settings.get("enabled", False)
        if not isinstance(normalize, bool) or not isinstance(enabled, bool):
            raise ConfigError(f"Expected boolean enabled/normalize for {language_name}")
        normalized_languages[language_name] = {
            "enabled": enabled,
            "voice": voice.strip(),
            "speed": float(speed),
            "normalize": normalize,
        }

    return {
        "paths": {
            "input_root": resolve_path(paths.get("input_root")),
        },
        "machine": {"profile": profile},
        "run": {
            "conflict_policy": conflict_policy,
            "audio_format": audio_format,
            "generate_timestamps": bool(run_table.get("generate_timestamps", False)),
            "save_timestamps": bool(run_table.get("save_timestamps", False)),
        },
        "languages": normalized_languages,
    }


LANGUAGE_MAP = {
    "af": "English",
    "am": "English",
    "bf": "British English",
    "bm": "British English",
    "ef": "European English",
    "em": "European English",
    "ff": "French",
    "fm": "French",
    "df": "German",
    "dm": "German",
    "cf": "Chinese",
    "cm": "Chinese",
    "if": "Italian",
    "im": "Italian",
    "pf": "Portuguese",
    "pm": "Portuguese",
    "sf": "Spanish",
    "sm": "Spanish",
    "rf": "Russian",
    "rm": "Russian",
    "jf": "Japanese",
    "jm": "Japanese",
    "kf": "Korean",
    "km": "Korean",
    "hf": "Hindi",
    "hm": "Hindi",
    "nf": "Dutch",
    "nm": "Dutch",
    "tf": "Turkish",
    "tm": "Turkish",
}


def detect_apple_silicon_capability() -> bool:
    if platform.system() != "Darwin":
        return False
    try:  # pragma: no cover - platform specific
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except Exception:
        return False


def collect_host_system_info() -> dict[str, Any]:
    architecture = platform.machine().lower()
    if detect_apple_silicon_capability():
        architecture = "arm64"
    memory_gb = 0
    if hasattr(os, "sysconf"):
        try:
            memory_gb = round((os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024**3))
        except (ValueError, OSError):
            memory_gb = 0
    return {
        "hostname": platform.node().lower(),
        "platform": platform.system().lower(),
        "architecture": architecture,
        "memory_gb": memory_gb,
    }


def select_machine_profile(system_info: dict[str, Any], profiles: dict[str, dict[str, Any]], override_profile_id: Optional[str] = None) -> dict[str, Any]:
    if override_profile_id:
        profile = profiles.get(override_profile_id, profiles["generic_fallback"])
        return {
            "machine_id": override_profile_id if override_profile_id in profiles else "generic_fallback",
            "name": profile["name"],
            "notes": profile.get("notes", ""),
            "match_source": "manual",
            "match_reasons": ["Manual override selected"],
            "profile": profile,
            "system_info": system_info,
        }

    for machine_id, profile in profiles.items():
        if machine_id == "generic_fallback":
            continue
        rules = profile.get("match_rules", {})
        if rules.get("platform") and system_info.get("platform") != rules["platform"]:
            continue
        architectures = rules.get("architecture", [])
        if architectures and system_info.get("architecture") not in architectures:
            continue
        ram = system_info.get("memory_gb", 0)
        if rules.get("ram_gb_min") is not None and ram < rules["ram_gb_min"]:
            continue
        if rules.get("ram_gb_max") is not None and ram > rules["ram_gb_max"]:
            continue
        return {
            "machine_id": machine_id,
            "name": profile["name"],
            "notes": profile.get("notes", ""),
            "match_source": "auto",
            "match_reasons": [f"platform={system_info.get('platform')}", f"architecture={system_info.get('architecture')}", f"ram={ram}GB"],
            "profile": profile,
            "system_info": system_info,
        }

    profile = profiles["generic_fallback"]
    return {
        "machine_id": "generic_fallback",
        "name": profile["name"],
        "notes": profile.get("notes", ""),
        "match_source": "fallback",
        "match_reasons": ["No configured host profile matched"],
        "profile": profile,
        "system_info": system_info,
    }


def clean_text_for_tts(text: str) -> str:
    replacements = [
        (r"\*\*(.*?)\*\*", r"\1"),
        (r"\*(.*?)\*", r"\1"),
        (r"__(.*?)__", r"\1"),
        (r"~~(.*?)~~", r"\1"),
        (r"\[(.*?)\]\(.*?\)", r"\1"),
        (r"<.*?>", ""),
        (r"[#*_~`]", " "),
    ]
    cleaned = text
    for pattern, replacement in replacements:
        cleaned = __import__("re").sub(pattern, replacement, cleaned)
    return __import__("re").sub(r"\s+", " ", cleaned).strip()


def calculate_word_count(text: str) -> int:
    return len(clean_text_for_tts(text).split())


def check_connection(api_base: str = KOKORO_API_URL) -> tuple[bool, str]:
    try:
        response = requests.get(f"{api_base}/audio/voices", timeout=5)
        if response.status_code == 200:
            return True, "Connected to Kokoro API"
        return False, f"API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Connection error: Could not connect to Kokoro API ({api_base.rsplit('/v1', 1)[0]})"
    except requests.exceptions.Timeout:
        return False, "Connection timeout: Kokoro API did not respond in time"
    except Exception as exc:
        return False, f"Error checking Kokoro API connection: {exc}"


def inspect_kokoro_runtime(api_base: str = KOKORO_API_URL) -> dict[str, Any]:
    runtime_info = {
        "connected": False,
        "runtime_mode": "unknown",
        "gpu_available": False,
        "message": "Kokoro runtime not inspected",
    }
    try:
        response = requests.get(f"{api_base}/debug/system", timeout=5)
        if response.status_code != 200:
            runtime_info["message"] = f"Kokoro debug endpoint returned status {response.status_code}"
            return runtime_info

        system_info = response.json()
        gpu_info = system_info.get("gpu") or {}
        devices = gpu_info.get("devices") or []
        runtime_info["connected"] = True
        if devices:
            runtime_info["gpu_available"] = True
            runtime_info["runtime_mode"] = "gpu"
            device = devices[0]
            runtime_info["message"] = f"Using GPU: {device.get('name', 'Unknown')} with {device.get('memory_total', 'Unknown')} memory"
        else:
            runtime_info["runtime_mode"] = "cpu"
            runtime_info["message"] = "No GPU detected, using CPU for inference"
        return runtime_info
    except Exception as exc:
        runtime_info["message"] = f"Error checking Kokoro runtime: {exc}"
        return runtime_info


def get_available_voices(api_base: str = KOKORO_API_URL) -> list[dict[str, str]]:
    response = requests.get(f"{api_base}/audio/voices", timeout=10)
    response.raise_for_status()
    voices_data = response.json()
    voice_list: list[dict[str, str]] = []
    for voice_id in voices_data.get("voices", []):
        parts = voice_id.split("_")
        if len(parts) < 2:
            continue
        language_name = LANGUAGE_MAP.get(parts[0], "Unknown")
        gender = "Male" if parts[0].endswith("m") else "Female"
        voice_list.append(
            {
                "id": voice_id,
                "name": parts[1].capitalize(),
                "gender": gender,
                "language": language_name,
                "description": f"{language_name} voice",
            }
        )
    return sorted(voice_list, key=lambda item: (item["language"], item["name"]))


def get_voices_by_language(api_base: str = KOKORO_API_URL) -> dict[str, list[dict[str, str]]]:
    languages: dict[str, list[dict[str, str]]] = {}
    for voice in get_available_voices(api_base):
        languages.setdefault(voice["language"], []).append(voice)
    return languages


def validate_enabled_language_voices(config: dict[str, Any], available_voices: list[dict[str, str]]) -> tuple[bool, str]:
    available_voice_ids = {voice["id"] for voice in available_voices}
    for language, settings in config["languages"].items():
        if not settings.get("enabled"):
            continue
        configured_voice = settings["voice"]
        if configured_voice not in available_voice_ids:
            return False, f"Configured voice '{configured_voice}' for {language} is not available from the live Kokoro server"
    return True, "Configured voices are available"


def find_language_section_files(language: str, input_root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    language_files: dict[str, dict[str, dict[str, Any]]] = {}
    course_dirs = [path for path in input_root.glob("*") if path.is_dir()]
    for course_dir in course_dirs:
        course_name = course_dir.name
        lecture_dirs = [path for path in course_dir.glob("*Lecture*") if path.is_dir()]
        if not lecture_dirs:
            lecture_dirs = [path for path in course_dir.glob("*") if path.is_dir()]

        for lecture_dir in lecture_dirs:
            transcript_dir = lecture_dir / f"{language} text"
            summary_dir = lecture_dir / f"{language} Summary text"
            transcript_files = sorted(transcript_dir.glob("[0-9]*.txt")) or sorted(transcript_dir.glob("*.txt"))
            summary_files = sorted(summary_dir.glob("[0-9]*.txt")) or sorted(summary_dir.glob("*.txt"))
            if transcript_files or summary_files:
                language_files.setdefault(course_name, {})[lecture_dir.name] = {
                    "base_dir": str(lecture_dir),
                    "transcript": {"dir": str(transcript_dir) if transcript_dir.exists() else None, "section_files": [str(path) for path in transcript_files]},
                    "summary": {"dir": str(summary_dir) if summary_dir.exists() else None, "section_files": [str(path) for path in summary_files]},
                }
    return language_files


def resolve_existing_audio_action(existing_output_exists: bool, conflict_policy: str) -> dict[str, str]:
    if not existing_output_exists:
        return {"action": "process", "status": "ready", "message": "Audio does not exist yet"}
    if conflict_policy == ConflictPolicy.REPORT_ONLY.value:
        return {"action": "report", "status": "reported", "message": "Existing audio detected; report-only mode left it unchanged"}
    if conflict_policy == ConflictPolicy.RENDER_NEW_OUTPUT.value:
        return {"action": "render_new_output", "status": "ready", "message": "Existing audio detected; rendering to a new filename"}
    if conflict_policy == ConflictPolicy.OVERWRITE.value:
        return {"action": "process", "status": "ready", "message": "Existing audio detected; output will be overwritten"}
    return {"action": "skip", "status": "skipped", "message": "Existing audio detected; skipped safely"}


def build_audio_inventory(language_files: dict[str, dict[str, dict]], language: str, audio_format: str, conflict_policy: str) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    summary = {
        "ready_count": 0,
        "processed_count": 0,
        "language_count": 0,
        "section_count": 0,
    }

    for course, lectures in language_files.items():
        for lecture, lecture_data in lectures.items():
            lecture_base_dir = lecture_data["base_dir"]
            transcript_audio_dir = os.path.join(lecture_base_dir, f"{language} audio")
            summary_audio_dir = os.path.join(lecture_base_dir, f"{language} Summary audio")

            lecture_jobs: list[dict[str, Any]] = []
            for kind, target_dir in (("transcript", transcript_audio_dir), ("summary", summary_audio_dir)):
                section_files = lecture_data[kind]["section_files"]
                for file_path in section_files:
                    section_number = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = os.path.join(target_dir, f"{section_number}.{audio_format}")
                    existing = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                    decision = resolve_existing_audio_action(existing, conflict_policy)
                    lecture_jobs.append(
                        {
                            "course": course,
                            "lecture": lecture,
                            "kind": kind,
                            "file_path": file_path,
                            "output_path": output_path,
                            "decision": decision,
                            "existing_output_exists": existing,
                        }
                    )

            if lecture_jobs:
                summary["language_count"] = 1
                summary["section_count"] += len(lecture_jobs)
                summary["processed_count"] += sum(1 for job in lecture_jobs if job["existing_output_exists"])
                summary["ready_count"] += sum(1 for job in lecture_jobs if job["decision"]["action"] in {"process", "render_new_output"})
                jobs.extend(lecture_jobs)

    return {"jobs": jobs, "summary": summary}


def build_audio_top_summary(machine_info: dict[str, Any], runtime_info: dict[str, Any], inventory: dict[str, Any], conflict_policy_label: str) -> dict[str, Any]:
    return {
        "machine": machine_info["name"],
        "mode": "GPU-backed Kokoro" if runtime_info["gpu_available"] else "CPU Kokoro",
        "runtime_message": runtime_info["message"],
        "conflict_policy": conflict_policy_label,
        "metrics": [
            ("Ready", inventory["summary"]["ready_count"]),
            ("Processed", inventory["summary"]["processed_count"]),
            ("Languages", inventory["summary"]["language_count"]),
            ("Sections", inventory["summary"]["section_count"]),
        ],
    }


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def format_file_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return "—"
    if size_bytes == 0:
        return "0 B"
    value = float(size_bytes)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return "—"


def create_run_telemetry(total_sections: int) -> dict[str, Any]:
    return {
        "active": True,
        "run_started_at": time.time(),
        "handled_sections": 0,
        "total_sections": max(1, total_sections),
        "successful_sections": 0,
        "skipped_sections": 0,
        "failed_sections": 0,
        "current_section_time": None,
        "average_section_time": None,
        "total_successful_processing_time": 0.0,
        "last_file_size_bytes": None,
        "total_generated_size_bytes": 0,
        "overall_eta_seconds": None,
        "current_file_name": None,
        "current_language": None,
        "current_course": None,
        "current_lecture": None,
        "current_status": None,
    }


def update_run_telemetry(
    telemetry: dict[str, Any],
    result: dict[str, Any],
    *,
    language: str,
    course: str,
    lecture: str,
) -> dict[str, Any]:
    telemetry["handled_sections"] += 1
    telemetry["current_language"] = language
    telemetry["current_course"] = course
    telemetry["current_lecture"] = lecture
    telemetry["current_status"] = result.get("status")
    file_name_source = result.get("output") or result.get("file")
    if file_name_source:
        telemetry["current_file_name"] = os.path.basename(file_name_source)

    if result.get("status") == "processed":
        processing_time = float(result.get("processing_time", 0.0))
        telemetry["current_section_time"] = processing_time
        telemetry["successful_sections"] += 1
        telemetry["total_successful_processing_time"] += processing_time
        telemetry["average_section_time"] = telemetry["total_successful_processing_time"] / telemetry["successful_sections"]
        output_path = result.get("output")
        if output_path and os.path.exists(output_path):
            file_size_bytes = os.path.getsize(output_path)
            telemetry["last_file_size_bytes"] = file_size_bytes
            telemetry["total_generated_size_bytes"] += file_size_bytes
    elif result.get("status") in {"skipped", "reported"}:
        telemetry["skipped_sections"] += 1
    elif result.get("status") == "failed":
        telemetry["failed_sections"] += 1

    elapsed = max(0.001, time.time() - telemetry["run_started_at"])
    if telemetry["handled_sections"] > 0:
        remaining_sections = max(0, telemetry["total_sections"] - telemetry["handled_sections"])
        telemetry["overall_eta_seconds"] = (elapsed / telemetry["handled_sections"]) * remaining_sections
    else:
        telemetry["overall_eta_seconds"] = None
    return telemetry


def build_run_telemetry_summary(telemetry: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not telemetry:
        return {
            "metrics": [
                ("Current Section Time", "—"),
                ("Average Section Time", "—"),
                ("Last File Size", "—"),
                ("Total Generated Size", "0 B"),
                ("Overall ETA", "Calculating..."),
            ],
            "caption": "No active run telemetry yet.",
        }

    if not telemetry.get("active") and telemetry.get("handled_sections", 0) >= telemetry.get("total_sections", 0):
        eta_value = "Complete"
    elif telemetry.get("handled_sections", 0) == 0 or telemetry.get("overall_eta_seconds") is None:
        eta_value = "Calculating..."
    else:
        eta_value = format_duration(telemetry["overall_eta_seconds"])

    return {
        "metrics": [
            ("Current Section Time", format_duration(telemetry.get("current_section_time"))),
            ("Average Section Time", format_duration(telemetry.get("average_section_time"))),
            ("Last File Size", format_file_size(telemetry.get("last_file_size_bytes"))),
            ("Total Generated Size", format_file_size(telemetry.get("total_generated_size_bytes", 0))),
            ("Overall ETA", eta_value),
        ],
        "caption": " | ".join(
            part
            for part in [
                f"Handled: {telemetry.get('handled_sections', 0)}/{telemetry.get('total_sections', 0)}",
                f"Language: {telemetry['current_language']}" if telemetry.get("current_language") else "",
                f"Course: {telemetry['current_course']}" if telemetry.get("current_course") else "",
                f"Lecture: {telemetry['current_lecture']}" if telemetry.get("current_lecture") else "",
                f"File: {telemetry['current_file_name']}" if telemetry.get("current_file_name") else "",
                f"Status: {telemetry['current_status']}" if telemetry.get("current_status") else "",
            ]
            if part
        ),
    }


def convert_text_to_speech(
    *,
    text: str,
    output_path: str,
    voice: str = "af_bella",
    model: str = "kokoro",
    response_format: str = "mp3",
    speed: float = 1.0,
    enable_timestamps: bool = False,
    normalize_text: bool = True,
    save_timestamps: bool = False,
    request_timeout_sec: int = 180,
    api_base: str = KOKORO_API_URL,
) -> dict[str, Any]:
    del save_timestamps
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    params = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": response_format,
        "speed": speed,
        "normalization_options": {"normalize": normalize_text},
    }
    if enable_timestamps:
        params["timestamps"] = True

    response = requests.post(
        f"{api_base}/audio/speech",
        json=params,
        timeout=request_timeout_sec,
    )
    if response.status_code != 200:
        return {"success": False, "message": f"API request failed with status {response.status_code}: {response.text}"}

    timestamps = None
    if enable_timestamps and "x-timestamps" in response.headers:
        try:
            timestamps = json.loads(response.headers["x-timestamps"])
        except json.JSONDecodeError:
            timestamps = None

    with open(output_path, "wb") as handle:
        handle.write(response.content)
    return {"success": True, "message": "Text-to-speech conversion successful", "timestamps": timestamps}


def generate_tts_for_sections(
    *,
    section_files: list[str],
    voice: str,
    model: str,
    output_dir: str,
    response_format: str = "mp3",
    speed: float = 1.0,
    normalize_text: bool = True,
    enable_timestamps: bool = False,
    save_timestamps: bool = False,
    conflict_policy: str = ConflictPolicy.SKIP_SAFELY.value,
    request_timeout_sec: int = 180,
    max_sections_per_batch: int = 12,
    progress_callback=None,
    api_base: str = KOKORO_API_URL,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for batch_start in range(0, len(section_files), max_sections_per_batch):
        batch_files = section_files[batch_start : batch_start + max_sections_per_batch]
        for file_path in batch_files:
            section_number = os.path.splitext(os.path.basename(file_path))[0]
            output_filename = f"{section_number}.{response_format}"
            output_path = os.path.join(output_dir, output_filename)

            existing_output_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
            output_decision = resolve_existing_audio_action(existing_output_exists, conflict_policy)
            if output_decision["action"] == "skip":
                results.append({"success": True, "file": file_path, "output": output_path, "status": "skipped", "message": output_decision["message"], "processing_time": 0, "word_count": 0})
                if progress_callback:
                    progress_callback(results[-1])
                continue
            if output_decision["action"] == "report":
                results.append({"success": True, "file": file_path, "output": output_path, "status": "reported", "message": output_decision["message"], "processing_time": 0, "word_count": 0})
                if progress_callback:
                    progress_callback(results[-1])
                continue
            if output_decision["action"] == "render_new_output":
                output_filename = f"{section_number} (rerun {int(time.time())}).{response_format}"
                output_path = os.path.join(output_dir, output_filename)

            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                if normalize_text:
                    content = clean_text_for_tts(content)
                if not content.strip():
                    results.append({"success": True, "file": file_path, "output": output_path, "status": "skipped", "message": "Empty or whitespace-only file", "processing_time": 0, "word_count": 0})
                    if progress_callback:
                        progress_callback(results[-1])
                    continue

                word_count = calculate_word_count(content)
                started_at = time.time()
                result = convert_text_to_speech(
                    text=content,
                    voice=voice,
                    model=model,
                    output_path=output_path,
                    response_format=response_format,
                    speed=speed,
                    enable_timestamps=enable_timestamps,
                    normalize_text=normalize_text,
                    save_timestamps=save_timestamps,
                    request_timeout_sec=request_timeout_sec,
                    api_base=api_base,
                )
                processing_time = time.time() - started_at
                if result["success"]:
                    if enable_timestamps and save_timestamps and result.get("timestamps") is not None:
                        timestamps_path = f"{os.path.splitext(output_path)[0]}.json"
                        with open(timestamps_path, "w", encoding="utf-8") as handle:
                            json.dump(result["timestamps"], handle, indent=2)
                    result["file"] = file_path
                    result["processing_time"] = processing_time
                    result["word_count"] = word_count
                    result["output"] = output_path
                    result["status"] = "processed"
                    if not os.path.exists(output_path):
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as handle:
                            handle.write(b"")
                    results.append(result)
                else:
                    result["file"] = file_path
                    result["processing_time"] = processing_time
                    result["word_count"] = word_count
                    result["status"] = "failed"
                    results.append(result)
                if progress_callback:
                    progress_callback(results[-1])
            except Exception as exc:
                results.append({"success": False, "file": file_path, "status": "failed", "message": f"Error: {exc}", "processing_time": 0, "word_count": 0})
                if progress_callback:
                    progress_callback(results[-1])
    return results


def run(config: dict[str, Any]) -> int:
    connected, message = check_connection(KOKORO_API_URL)
    if not connected:
        print(f"Cannot connect to Kokoro API: {message}")
        return 1

    input_root = config["paths"]["input_root"]
    if not Path(input_root).exists():
        print(f"Input directory not found: {input_root}")
        return 1

    override_profile = config["machine"]["profile"]
    machine_info = select_machine_profile(
        collect_host_system_info(),
        MACHINE_PROFILES,
        None if override_profile == "auto" else override_profile,
    )
    runtime_info = inspect_kokoro_runtime(KOKORO_API_URL)
    available_voices = get_available_voices(KOKORO_API_URL)
    voices_ok, voices_message = validate_enabled_language_voices(config, available_voices)
    if not voices_ok:
        print(f"Configured Kokoro voice validation failed: {voices_message}")
        return 1
    enabled_languages = [name for name, settings in config["languages"].items() if settings.get("enabled")]
    if not enabled_languages:
        print("No languages enabled in config.")
        return 1

    current_audio_format = config["run"]["audio_format"]
    host_settings = machine_info["profile"]["optimization_settings"]
    inventory_summary = {"ready_count": 0, "processed_count": 0, "language_count": 0, "section_count": 0}
    all_results: list[dict[str, Any]] = []
    for language in enabled_languages:
        language_files = find_language_section_files(language, config["paths"]["input_root"])
        inventory = build_audio_inventory(language_files, language, current_audio_format, config["run"]["conflict_policy"])
        if inventory["jobs"]:
            inventory_summary["language_count"] += 1
        inventory_summary["ready_count"] += inventory["summary"]["ready_count"]
        inventory_summary["processed_count"] += inventory["summary"]["processed_count"]
        inventory_summary["section_count"] += inventory["summary"]["section_count"]

        settings = config["languages"][language]
        telemetry = create_run_telemetry(inventory["summary"]["section_count"])
        for course, lectures in language_files.items():
            for lecture, lecture_data in lectures.items():
                transcript_results = generate_tts_for_sections(
                    section_files=lecture_data["transcript"]["section_files"],
                    voice=settings["voice"],
                    model="kokoro",
                    output_dir=os.path.join(lecture_data["base_dir"], f"{language} audio"),
                    response_format=current_audio_format,
                    speed=float(settings["speed"]),
                    normalize_text=bool(settings["normalize"]),
                    enable_timestamps=config["run"]["generate_timestamps"],
                    save_timestamps=config["run"]["save_timestamps"],
                    conflict_policy=config["run"]["conflict_policy"],
                    request_timeout_sec=host_settings["request_timeout_sec"],
                    max_sections_per_batch=host_settings["max_sections_per_batch"],
                    api_base=KOKORO_API_URL,
                )
                summary_results = generate_tts_for_sections(
                    section_files=lecture_data["summary"]["section_files"],
                    voice=settings["voice"],
                    model="kokoro",
                    output_dir=os.path.join(lecture_data["base_dir"], f"{language} Summary audio"),
                    response_format=current_audio_format,
                    speed=float(settings["speed"]),
                    normalize_text=bool(settings["normalize"]),
                    enable_timestamps=config["run"]["generate_timestamps"],
                    save_timestamps=config["run"]["save_timestamps"],
                    conflict_policy=config["run"]["conflict_policy"],
                    request_timeout_sec=host_settings["request_timeout_sec"],
                    max_sections_per_batch=host_settings["max_sections_per_batch"],
                    api_base=KOKORO_API_URL,
                )
                for result in transcript_results + summary_results:
                    update_run_telemetry(telemetry, result, language=language, course=course, lecture=lecture)
                all_results.extend(transcript_results)
                all_results.extend(summary_results)

        telemetry["active"] = False
        telemetry_summary = build_run_telemetry_summary(telemetry)
        print(f"language={language} telemetry={telemetry_summary['caption']}")

    top_summary = build_audio_top_summary(machine_info, runtime_info, {"summary": inventory_summary}, CONFLICT_POLICY_LABELS[config["run"]["conflict_policy"]])
    processed_count = sum(1 for result in all_results if result["status"] == "processed")
    skipped_count = sum(1 for result in all_results if result["status"] in {"skipped", "reported"})
    failed_count = sum(1 for result in all_results if result["status"] == "failed")
    profile_source = "config" if config["machine"]["profile"] != "auto" else machine_info["match_source"]
    print(
        f"workflow=kokoro profile={machine_info['machine_id']} profile_source={profile_source} "
        f"runtime={runtime_info['runtime_mode']} voice_check=ok mode={top_summary['mode']} "
        f"ready={inventory_summary['ready_count']} processed={processed_count} skipped={skipped_count} failed={failed_count}"
    )
    return 0 if failed_count == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CLI version of 07 Generate Audio with Kokoro.")
    parser.add_argument("--config", help="Path to TOML config. Defaults to config/07 Generate Audio with Kokoro.toml")
    args = parser.parse_args(argv)
    try:
        return run(load_config(args.config))
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
