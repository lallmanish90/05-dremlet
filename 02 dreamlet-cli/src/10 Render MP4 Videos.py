from __future__ import annotations

import argparse
from collections import deque
import enum
import fnmatch
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
import sys
import tomllib
from typing import Any, Optional

import psutil
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "10 Render MP4 Videos.toml"
DEFAULT_MP4_FPS = 3


class ConflictPolicy(str, enum.Enum):
    SKIP_SAFELY = "skip_safely"
    OVERWRITE = "overwrite"
    RENDER_NEW_OUTPUT = "render_new_output"
    REPORT_ONLY = "report_only"


CONFLICT_POLICY_LABELS = {
    ConflictPolicy.SKIP_SAFELY.value: "Skip safely",
    ConflictPolicy.OVERWRITE.value: "Re-render and overwrite",
    ConflictPolicy.RENDER_NEW_OUTPUT.value: "Render to new output",
    ConflictPolicy.REPORT_ONLY.value: "Report only",
}


MACHINE_PROFILES = {
    "macbook_pro_m3_pro_18gb": {
        "name": "MacBook Pro M3 Pro (18GB)",
        "notes": "Quality-first macOS profile using VideoToolbox when available.",
        "match_rules": {
            "platform": "darwin",
            "architecture": ["arm64"],
            "ram_gb_min": 16,
            "ram_gb_max": 20,
            "gpu_type": "apple_silicon",
            "cpu_contains": None,
            "gpu_name_contains": None,
        },
        "encoder_preferences": ["h264_videotoolbox", "libx264"],
        "optimization_settings": {
            "max_threads": 8,
            "batch_size": 6,
            "memory_limit_gb": 14,
            "quality_preset": "high_quality",
            "processing_mode": "balanced",
            "ffmpeg_threads": 4,
            "cooldown_seconds": 0,
            "cpu_soft_limit_percent": 85,
            "memory_available_soft_limit_gb": 1.5,
            "gpu_temp_soft_limit_c": 78,
        },
    },
    "windows_i5_12450h_rtx3050_16gb": {
        "name": "Acer Windows laptop (i5-12450H + RTX 3050)",
        "notes": "Quality-first Windows profile using NVENC when available.",
        "match_rules": {
            "platform": "windows",
            "architecture": ["amd64", "x86_64"],
            "ram_gb_min": 14,
            "ram_gb_max": 18,
            "gpu_type": "nvidia",
            "cpu_contains": "i5-12450h",
            "gpu_name_contains": "rtx 3050",
        },
        "encoder_preferences": ["h264_nvenc", "libx264"],
        "optimization_settings": {
            "max_threads": 6,
            "batch_size": 4,
            "memory_limit_gb": 12,
            "quality_preset": "high_quality",
            "processing_mode": "balanced",
            "ffmpeg_threads": 2,
            "cooldown_seconds": 2,
            "cpu_soft_limit_percent": 70,
            "memory_available_soft_limit_gb": 2.0,
            "gpu_temp_soft_limit_c": 72,
        },
    },
    "generic_fallback": {
        "name": "Generic fallback profile",
        "notes": "Fallback profile for machines outside the two supported laptops.",
        "match_rules": {},
        "encoder_preferences": ["libx264"],
        "optimization_settings": {
            "max_threads": 4,
            "batch_size": 2,
            "memory_limit_gb": 6,
            "quality_preset": "balanced",
            "processing_mode": "balanced",
            "ffmpeg_threads": 2,
            "cooldown_seconds": 0,
            "cpu_soft_limit_percent": 85,
            "memory_available_soft_limit_gb": 1.5,
            "gpu_temp_soft_limit_c": 78,
        },
    },
}


class ConfigError(ValueError):
    """Raised when the MP4 config is invalid."""


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
    selection = data.get("selection")
    if not isinstance(paths, dict):
        raise ConfigError("Missing required [paths] table")
    if not isinstance(machine, dict):
        raise ConfigError("Missing required [machine] table")
    if not isinstance(run_table, dict):
        raise ConfigError("Missing required [run] table")
    if not isinstance(selection, dict):
        raise ConfigError("Missing required [selection] table")

    profile = str(machine.get("profile", "auto")).strip()
    allowed_profiles = {"auto", "macbook_pro_m3_pro_18gb", "windows_i5_12450h_rtx3050_16gb", "generic_fallback"}
    if profile not in allowed_profiles:
        raise ConfigError(f"Unsupported profile: {profile}")

    conflict_policy = str(run_table.get("conflict_policy", ConflictPolicy.SKIP_SAFELY.value)).strip()
    if conflict_policy not in CONFLICT_POLICY_LABELS:
        raise ConfigError(f"Unsupported conflict_policy: {conflict_policy}")

    language = run_table.get("language")
    if not isinstance(language, str) or not language.strip():
        raise ConfigError("Missing required language")
    fps = run_table.get("fps", DEFAULT_MP4_FPS)
    if not isinstance(fps, int) or fps <= 0:
        raise ConfigError("run.fps must be a positive integer")

    def resolve_path(raw_value: Any, key: str) -> Path:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ConfigError(f"Missing required path: {key}")
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = (config_file.parent / candidate).resolve()
        return candidate

    def ensure_list(key: str) -> list[str]:
        value = selection.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ConfigError(f"Expected string list for {key}")
        return value

    return {
        "paths": {
            "input_root": resolve_path(paths.get("input_root"), "input_root"),
            "output_root": resolve_path(paths.get("output_root"), "output_root"),
        },
        "machine": {"profile": profile},
        "run": {
            "conflict_policy": conflict_policy,
            "language": language.strip(),
            "fps": fps,
            "generate_regular": bool(run_table.get("generate_regular", True)),
            "generate_summary": bool(run_table.get("generate_summary", True)),
        },
        "selection": {
            "include_courses": ensure_list("include_courses"),
            "exclude_courses": ensure_list("exclude_courses"),
            "include_sections": ensure_list("include_sections"),
            "exclude_sections": ensure_list("exclude_sections"),
            "include_lectures": ensure_list("include_lectures"),
            "exclude_lectures": ensure_list("exclude_lectures"),
        },
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


def detect_gpu_info() -> dict[str, Any]:
    gpu_info: dict[str, Any] = {"gpu_detected": False}
    try:  # pragma: no cover - hardware specific
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip().splitlines()[0]
            gpu_info.update({"gpu_detected": True, "gpu_type": "nvidia", "gpu_name": gpu_name})
    except Exception:
        pass
    if detect_apple_silicon_capability():  # pragma: no cover
        gpu_info.update({"gpu_detected": True, "gpu_type": "apple_silicon", "gpu_name": "Apple Silicon GPU"})
    return gpu_info


def collect_system_info() -> dict[str, Any]:
    architecture = platform.machine().lower()
    cpu = (platform.processor() or "").lower()
    if detect_apple_silicon_capability():
        architecture = "arm64"
        if not cpu or cpu == "i386":
            cpu = "apple silicon"

    system_info = {
        "hostname": platform.node().lower(),
        "platform": platform.system().lower(),
        "architecture": architecture,
        "cpu": cpu,
        "memory_gb": round(psutil.virtual_memory().total / (1024**3)),
        "cpu_count": psutil.cpu_count() or 1,
    }
    system_info.update(detect_gpu_info())
    return system_info


def evaluate_profile_match(profile: dict[str, Any], system_info: dict[str, Any]) -> Optional[tuple[int, list[str]]]:
    rules = profile.get("match_rules", {})
    reasons: list[str] = []
    score = 0
    platform_rule = rules.get("platform")
    if platform_rule:
        if system_info.get("platform") != platform_rule:
            return None
        score += 20
        reasons.append(f"platform={platform_rule}")
    architecture_rules = rules.get("architecture", [])
    if architecture_rules:
        if system_info.get("architecture") not in architecture_rules:
            return None
        score += 15
        reasons.append(f"architecture={system_info.get('architecture')}")
    cpu_rule = rules.get("cpu_contains")
    if cpu_rule:
        if cpu_rule not in system_info.get("cpu", ""):
            return None
        score += 10
        reasons.append(f"cpu contains {cpu_rule}")
    ram_gb = int(system_info.get("memory_gb") or 0)
    ram_min = rules.get("ram_gb_min")
    ram_max = rules.get("ram_gb_max")
    if ram_min is not None and ram_gb < ram_min:
        return None
    if ram_max is not None and ram_gb > ram_max:
        return None
    if ram_min is not None or ram_max is not None:
        score += 10
        reasons.append(f"ram={ram_gb}GB")
    gpu_type_rule = rules.get("gpu_type")
    if gpu_type_rule:
        if system_info.get("gpu_type") != gpu_type_rule:
            return None
        score += 20
        reasons.append(f"gpu_type={gpu_type_rule}")
    gpu_name_rule = rules.get("gpu_name_contains")
    if gpu_name_rule:
        gpu_name = (system_info.get("gpu_name") or "").lower()
        if gpu_name_rule not in gpu_name:
            return None
        score += 25
        reasons.append(f"gpu name contains {gpu_name_rule}")
    return score, reasons


def select_machine_profile(system_info: dict[str, Any], profiles: dict[str, dict[str, Any]], override_profile_id: Optional[str] = None) -> dict[str, Any]:
    if override_profile_id:
        profile = profiles.get(override_profile_id, profiles["generic_fallback"])
        return {
            "machine_id": override_profile_id if override_profile_id in profiles else "generic_fallback",
            "name": profile["name"],
            "notes": profile.get("notes", ""),
            "match_source": "manual",
            "match_reasons": ["Manual override selected"],
            "system_info": system_info,
            "profile": profile,
        }

    matches: list[tuple[int, str, list[str]]] = []
    for machine_id, profile in profiles.items():
        if machine_id == "generic_fallback":
            continue
        result = evaluate_profile_match(profile, system_info)
        if result is not None:
            score, reasons = result
            matches.append((score, machine_id, reasons))

    if matches:
        matches.sort(key=lambda item: item[0], reverse=True)
        _, machine_id, reasons = matches[0]
        profile = profiles[machine_id]
        return {
            "machine_id": machine_id,
            "name": profile["name"],
            "notes": profile.get("notes", ""),
            "match_source": "auto",
            "match_reasons": reasons,
            "system_info": system_info,
            "profile": profile,
        }

    profile = profiles["generic_fallback"]
    return {
        "machine_id": "generic_fallback",
        "name": profile["name"],
        "notes": profile.get("notes", ""),
        "match_source": "fallback",
        "match_reasons": ["No configured machine profile matched"],
        "system_info": system_info,
        "profile": profile,
    }


def select_video_encoder(machine_id: str, system: str, machine: str, encoders_output: str) -> tuple[str, Optional[str], dict[str, Any]]:
    del machine
    encoders_output = encoders_output or ""
    if machine_id == "windows_i5_12450h_rtx3050_16gb" and "h264_nvenc" in encoders_output:
        return "h264_nvenc", "cuda", {"hardware_encoding": True, "hardware_decoding": True, "performance_tier": "high"}
    if machine_id == "macbook_pro_m3_pro_18gb" and "h264_videotoolbox" in encoders_output:
        return "h264_videotoolbox", "videotoolbox", {"hardware_encoding": True, "hardware_decoding": True, "performance_tier": "high"}
    if system == "Linux":
        if "h264_nvenc" in encoders_output:
            return "h264_nvenc", "cuda", {"hardware_encoding": True, "hardware_decoding": True, "performance_tier": "high"}
        if "h264_qsv" in encoders_output:
            return "h264_qsv", "qsv", {"hardware_encoding": True, "hardware_decoding": True, "performance_tier": "medium"}
        if "h264_vaapi" in encoders_output:
            return "h264_vaapi", "vaapi", {"hardware_encoding": True, "hardware_decoding": True, "performance_tier": "medium"}
    return "libx264", None, {"hardware_encoding": False, "hardware_decoding": False, "performance_tier": "basic"}


def get_sorted_files(directory: str, file_type: str, full_path: bool = True) -> list[str]:
    patterns = {
        "image": ("*.png", "*.jpg", "*.jpeg"),
        "audio": ("*.mp3", "*.wav", "*.m4a"),
    }
    matches: list[Path] = []
    for pattern in patterns[file_type]:
        matches.extend(Path(directory).glob(pattern))
    matches.sort(key=lambda path: [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)])
    if full_path:
        return [str(path) for path in matches]
    return [path.name for path in matches]


def find_language_folders(lecture_dir: str) -> list[str]:
    languages: list[str] = []
    for folder in os.listdir(lecture_dir):
        if folder.endswith(" audio") or folder.endswith(" image"):
            lang = folder.split(" ")[0]
            if lang and lang not in languages:
                languages.append(lang)
    return languages


def find_image_files(lecture_dir: str, language: str = "English") -> list[str]:
    lang_images_dir = os.path.join(lecture_dir, f"{language} image")
    if os.path.exists(lang_images_dir) and os.path.isdir(lang_images_dir):
        image_files = get_sorted_files(lang_images_dir, "image", full_path=True)
        if image_files:
            return image_files
    if language != "English":
        english_images_dir = os.path.join(lecture_dir, "English image")
        if os.path.exists(english_images_dir) and os.path.isdir(english_images_dir):
            image_files = get_sorted_files(english_images_dir, "image", full_path=True)
            if image_files:
                return image_files
    return []


def find_audio_files(lecture_dir: str, language: str = "English", summary: bool = False) -> list[str]:
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_dir, folder_name)
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        audio_files = get_sorted_files(lang_audio_dir, "audio", full_path=True)
        if audio_files:
            return audio_files
    return []


def find_processed_lectures(input_root: Path) -> dict[str, dict[str, dict]]:
    organized_data: dict[str, dict[str, dict]] = {}
    if not input_root.exists():
        return organized_data

    for root, dirs, _ in os.walk(input_root):
        if any(util_folder in root for util_folder in ["all_pptx", "all_slides", "all_transcripts"]):
            continue
        if not ("English image" in dirs and "English audio" in dirs):
            continue

        lecture_dir = root
        languages = find_language_folders(lecture_dir)
        english_image_files = find_image_files(lecture_dir, "English")
        english_audio_files = find_audio_files(lecture_dir, "English")
        if not english_image_files or not english_audio_files:
            continue

        rel_path = os.path.relpath(lecture_dir, input_root)
        path_components = rel_path.split(os.sep)
        lecture_name = path_components[-1]
        subject = None
        course = None
        section = None
        if len(path_components) > 3:
            subject, course, section = path_components[0], path_components[1], path_components[2]
        elif len(path_components) > 2:
            if any(keyword in path_components[1].lower() for keyword in ["section", "part", "module"]):
                course, section = path_components[0], path_components[1]
            else:
                subject, course = path_components[0], path_components[1]
        elif len(path_components) > 1:
            course = path_components[0]

        lecture_match = re.search(r"lecture\s*(\d+)", lecture_name, re.IGNORECASE)
        if lecture_match:
            lecture_display = f"Lecture {lecture_match.group(1)}"
        else:
            number_match = re.match(r"^\s*(\d+)\s*$", lecture_name)
            lecture_display = f"Lecture {number_match.group(1)}" if number_match else lecture_name

        subject_key = subject if subject else "Main"
        course_key = course if course else "Main Course"
        section_key = section if section else "Main Section"

        organized_data.setdefault(subject_key, {}).setdefault(course_key, {}).setdefault(section_key, {})

        language_data = {}
        for language in languages:
            image_files = find_image_files(lecture_dir, language)
            audio_files = find_audio_files(lecture_dir, language, summary=False)
            summary_audio_files = find_audio_files(lecture_dir, language, summary=True)
            if image_files and audio_files:
                language_data[language] = {
                    "image_files": image_files,
                    "audio_files": audio_files,
                    "audio_count": len(audio_files),
                    "image_count": len(image_files),
                    "count_match": len(audio_files) == len(image_files),
                    "has_summary_audio": len(summary_audio_files) > 0,
                    "summary_audio_files": summary_audio_files,
                    "summary_audio_count": len(summary_audio_files),
                    "summary_count_match": len(summary_audio_files) == len(image_files),
                }

        english_summary_audio_files = find_audio_files(lecture_dir, "English", summary=True)
        organized_data[subject_key][course_key][section_key][lecture_display] = {
            "path": lecture_dir,
            "image_files": english_image_files,
            "audio_files": english_audio_files,
            "audio_count": len(english_audio_files),
            "image_count": len(english_image_files),
            "count_match": len(english_audio_files) == len(english_image_files),
            "has_summary_audio": len(english_summary_audio_files) > 0,
            "summary_audio_files": english_summary_audio_files,
            "summary_audio_count": len(english_summary_audio_files),
            "summary_count_match": len(english_summary_audio_files) == len(english_image_files),
            "output_name": f"{lecture_name}.mp4",
            "languages": languages,
            "language_data": language_data,
        }

    return organized_data


def generate_output_path(lecture_path: str, input_root: str, output_root: str, language: str = "English", summary: bool = False, suffix: str = "") -> str:
    rel_path = os.path.relpath(lecture_path, input_root)
    path_components = rel_path.split(os.sep)
    lecture_name = path_components[-1]
    if len(path_components) >= 3:
        course = path_components[-3]
        section = path_components[-2]
    elif len(path_components) == 2:
        course = path_components[0]
        section = "Main Section"
    else:
        course = "Main Course"
        section = "Main Section"
    output_dir_path = os.path.join(output_root, language, course, section)
    os.makedirs(output_dir_path, exist_ok=True)
    filename = f"{lecture_name}.mp4"
    if summary:
        filename = f"{lecture_name}(summary).mp4"
    if suffix:
        name, ext = os.path.splitext(filename)
        filename = f"{name}{suffix}{ext}"
    return os.path.join(output_dir_path, filename)


def build_rerun_output_path(output_path: str) -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = Path(output_path)
    return str(path.with_name(f"{path.stem} (rerun {timestamp}){path.suffix}"))


def resolve_existing_output_action(existing_output_exists: bool, conflict_policy: str) -> dict[str, str]:
    if not existing_output_exists:
        return {"action": "render", "status": "ready", "message": "Output does not exist yet"}
    if conflict_policy == ConflictPolicy.REPORT_ONLY.value:
        return {"action": "report", "status": "reported", "message": "Existing output detected; report-only mode left it unchanged"}
    if conflict_policy == ConflictPolicy.RENDER_NEW_OUTPUT.value:
        return {"action": "render_new_output", "status": "ready", "message": "Existing output detected; rendering to a new output path"}
    if conflict_policy == ConflictPolicy.OVERWRITE.value:
        return {"action": "render", "status": "ready", "message": "Existing output detected; output will be overwritten"}
    return {"action": "skip", "status": "skipped", "message": "Existing output detected; skipped safely"}


def build_render_inventory(
    organized_data: dict[str, dict[str, dict]],
    *,
    input_root: Path,
    output_root: Path,
    selected_language: str,
    generate_regular: bool,
    generate_summary: bool,
    conflict_policy: str,
) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    lecture_inventory: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    summary = {"ready_count": 0, "processed_count": 0, "lecture_count": 0, "output_count": 0}
    for subject, courses in organized_data.items():
        for course, sections in courses.items():
            for section, section_lectures in sections.items():
                for lecture, lecture_data in section_lectures.items():
                    lang_data = lecture_data.get("language_data", {}).get(selected_language)
                    if not lang_data:
                        continue
                    lecture_key = (subject, course, section, lecture)
                    lecture_summary = {"lecture_data": lecture_data, "ready_outputs": 0, "processed_outputs": 0, "output_count": 0, "jobs": []}
                    lecture_jobs: list[dict[str, Any]] = []
                    if generate_regular and lang_data.get("count_match"):
                        output_path = generate_output_path(lecture_data["path"], str(input_root), str(output_root), selected_language, summary=False)
                        existing = os.path.exists(output_path)
                        decision = resolve_existing_output_action(existing, conflict_policy)
                        lecture_jobs.append({"subject": subject, "course": course, "section": section, "lecture": lecture, "type": "Regular", "summary": False, "language": selected_language, "lecture_data": lecture_data, "output_path": output_path, "existing_output_exists": existing, "decision": decision})
                    if generate_summary and lang_data.get("has_summary_audio") and lang_data.get("summary_count_match"):
                        output_path = generate_output_path(lecture_data["path"], str(input_root), str(output_root), selected_language, summary=True)
                        existing = os.path.exists(output_path)
                        decision = resolve_existing_output_action(existing, conflict_policy)
                        lecture_jobs.append({"subject": subject, "course": course, "section": section, "lecture": lecture, "type": "Summary", "summary": True, "language": selected_language, "lecture_data": lecture_data, "output_path": output_path, "existing_output_exists": existing, "decision": decision})
                    if not lecture_jobs:
                        continue
                    summary["lecture_count"] += 1
                    summary["output_count"] += len(lecture_jobs)
                    summary["processed_count"] += sum(1 for job in lecture_jobs if job["existing_output_exists"])
                    summary["ready_count"] += sum(1 for job in lecture_jobs if job["decision"]["action"] in {"render", "render_new_output"})
                    lecture_summary["jobs"] = lecture_jobs
                    lecture_summary["ready_outputs"] = sum(1 for job in lecture_jobs if job["decision"]["action"] in {"render", "render_new_output"})
                    lecture_summary["processed_outputs"] = sum(1 for job in lecture_jobs if job["existing_output_exists"])
                    lecture_summary["output_count"] = len(lecture_jobs)
                    lecture_inventory[lecture_key] = lecture_summary
                    jobs.extend(lecture_jobs)
    return {"jobs": jobs, "lectures": lecture_inventory, "summary": summary}


def build_course_selection_state_key(subject: str, course: str) -> str:
    return f"mp4_course_{subject}_{course}"


def set_global_course_selection(session_state: dict[str, Any], organized_data: dict[str, dict[str, dict]], selected: bool) -> None:
    session_state["mp4_select_all"] = selected
    for subject, courses in organized_data.items():
        for course in courses:
            session_state[build_course_selection_state_key(subject, course)] = selected


def _matches_patterns(value: str, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    include_ok = True if not include_patterns else any(fnmatch.fnmatch(value, pattern) for pattern in include_patterns)
    exclude_hit = any(fnmatch.fnmatch(value, pattern) for pattern in exclude_patterns)
    return include_ok and not exclude_hit


def filter_jobs_by_selection(jobs: list[dict[str, Any]], selection: dict[str, list[str]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for job in jobs:
        if not _matches_patterns(job["course"], selection.get("include_courses", []), selection.get("exclude_courses", [])):
            continue
        if not _matches_patterns(job["section"], selection.get("include_sections", []), selection.get("exclude_sections", [])):
            continue
        if not _matches_patterns(job["lecture"], selection.get("include_lectures", []), selection.get("exclude_lectures", [])):
            continue
        filtered.append(job)
    return filtered


def detect_ffmpeg_encoders() -> str:
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=15)
        return result.stdout
    except Exception:
        return ""


def get_ffmpeg_creationflags(system: str) -> int:
    if system == "Windows":
        return getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    return 0


def enable_windows_virtual_terminal(stream: Any) -> bool:
    if os.name != "nt":
        return True
    try:  # pragma: no cover - Windows console specific
        import ctypes
        import msvcrt

        fileno = stream.fileno()
        handle = msvcrt.get_osfhandle(fileno)
        kernel32 = ctypes.windll.kernel32
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        enable_virtual_terminal_processing = 0x0004
        if mode.value & enable_virtual_terminal_processing:
            return True
        return kernel32.SetConsoleMode(handle, mode.value | enable_virtual_terminal_processing) != 0
    except Exception:
        return False


def supports_live_dashboard(stream: Any) -> bool:
    if not bool(getattr(stream, "isatty", lambda: False)()):
        return False
    if os.name == "nt":
        return enable_windows_virtual_terminal(stream)
    return True


def parse_ffmpeg_progress_snapshot(snapshot: dict[str, str]) -> dict[str, Any]:
    rendered_seconds = 0.0
    out_time_ms = snapshot.get("out_time_ms")
    if out_time_ms:
        rendered_seconds = float(out_time_ms) / 1_000_000
    return {
        "rendered_seconds": rendered_seconds,
        "speed": snapshot.get("speed", "n/a"),
        "complete": snapshot.get("progress") == "end",
    }


def build_final_summary_lines(*, output_root: Path, totals: dict[str, int], elapsed_seconds: float) -> list[str]:
    return [
        "Dreamlet CLI - Render MP4 Videos complete",
        f"Elapsed  {elapsed_seconds:.1f}s",
        f"Results  success {totals['success']} skipped {totals['skipped']} error {totals['error']} remaining {totals['remaining']}",
        f"success={totals['success']} skipped={totals['skipped']} error={totals['error']}",
        f"Output   {output_root}",
    ]


def format_duration(seconds: Optional[float], *, fallback: str = "estimating...") -> str:
    if seconds is None:
        return fallback
    total_seconds = max(int(round(seconds)), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_progress_bar(completed: float, total: float, width: int = 40) -> str:
    if total <= 0:
        return "[" + ("." * width) + "]"
    ratio = max(0.0, min(completed / total, 1.0))
    filled = min(width, max(0, int(round(ratio * width))))
    return "[" + ("#" * filled) + ("." * (width - filled)) + "]"


def parse_speed_multiplier(speed_text: str | None) -> Optional[float]:
    if not speed_text:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)x", speed_text)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value if value > 0 else None


def summarize_jobs(jobs: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"ready": 0, "regular": 0, "summary": 0, "existing": 0}
    for job in jobs:
        if job.get("decision", {}).get("action") in {"render", "render_new_output"}:
            summary["ready"] += 1
        if job.get("type") == "Regular":
            summary["regular"] += 1
        if job.get("type") == "Summary":
            summary["summary"] += 1
        if job.get("existing_output_exists"):
            summary["existing"] += 1
    return summary


def summarize_result_counts(results: list[dict[str, Any]], total_jobs: int) -> dict[str, int]:
    summary = {"success": 0, "skipped": 0, "error": 0, "remaining": max(total_jobs - len(results), 0)}
    for result in results:
        status = result.get("status")
        if status == "success":
            summary["success"] += 1
        elif status in {"skipped", "reported"}:
            summary["skipped"] += 1
        elif status in {"error", "failed"}:
            summary["error"] += 1
    return summary


def collect_dashboard_telemetry(output_root: Path) -> dict[str, Any]:
    metrics = get_system_metrics()
    disk_usage = shutil.disk_usage(output_root if output_root.exists() else output_root.parent)
    return {
        "cpu_percent": metrics["cpu_percent"],
        "memory_percent": metrics["memory_percent"],
        "memory_available_gb": metrics["memory_available_gb"],
        "gpu_temp_c": get_gpu_temperature_c(),
        "disk_free_gb": round(disk_usage.free / (1024**3), 1),
    }


class TerminalDashboard:
    def __init__(
        self,
        *,
        stream: Any,
        input_root: Path | None = None,
        output_root: Path,
        machine_info: dict[str, Any],
        encoder: str,
        decoder: str | None,
        optimization_settings: dict[str, Any],
        fps: int,
        total_jobs: int,
        interactive: bool,
    ) -> None:
        self.stream = stream
        self.input_root = input_root
        self.output_root = output_root
        self.machine_info = machine_info
        self.encoder = encoder
        self.decoder = decoder
        self.optimization_settings = optimization_settings
        self.fps = fps
        self.total_jobs = total_jobs
        self.interactive = interactive
        self.started_at = time.time()
        self.completed_jobs = 0
        self.queue_counts: dict[str, int] = {"ready": total_jobs, "regular": 0, "summary": 0, "existing": 0}
        self.result_counts = {"success": 0, "skipped": 0, "error": 0}
        self.current_job: dict[str, Any] = {}
        self.language = "n/a"
        self.stage = "startup"
        self.output_path = "n/a"
        self.slide_count = 0
        self.audio_count = 0
        self.media_duration_seconds = 0.0
        self.rendered_seconds = 0.0
        self.speed = "n/a"
        self.cooldown_status = "idle"
        self.telemetry = {"cpu_percent": 0, "memory_percent": 0, "memory_available_gb": 0.0, "gpu_temp_c": None, "disk_free_gb": 0.0}
        self.recent_events: deque[str] = deque(maxlen=5)
        self.job_durations: list[float] = []
        self._entered_alt_screen = False

    def handle_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type", "")
        if event_type == "inventory_built":
            self.total_jobs = int(event.get("job_count", self.total_jobs))
            self.queue_counts.update(event.get("queue_counts", {}))
            self.recent_events.append(f"Queue ready with {self.total_jobs} outputs")
        elif event_type == "run_started":
            self.recent_events.append("Run started")
            self.stage = "queue build"
        elif event_type == "job_started":
            self.current_job = dict(event.get("job", {}))
            self.language = str(self.current_job.get("language", "n/a"))
            self.output_path = str(self.current_job.get("output_path", "n/a"))
            self.slide_count = int(event.get("slide_count", 0))
            self.audio_count = int(event.get("audio_count", 0))
            self.media_duration_seconds = float(event.get("media_duration_seconds", 0.0))
            self.rendered_seconds = 0.0
            self.speed = "n/a"
            self.stage = "starting"
            lecture_name = self.current_job.get("lecture", "n/a")
            self.recent_events.append(f"Started {lecture_name}")
        elif event_type == "manifest_ready":
            self.slide_count = int(event.get("slide_count", self.slide_count))
            self.audio_count = int(event.get("audio_count", self.audio_count))
            self.media_duration_seconds = float(event.get("media_duration_seconds", self.media_duration_seconds))
            self.language = str(event.get("language", self.language))
            self.output_path = str(event.get("output_path", self.output_path))
            self.stage = "manifest prep"
        elif event_type == "ffmpeg_progress":
            self.rendered_seconds = float(event.get("rendered_seconds", self.rendered_seconds))
            self.speed = str(event.get("speed", self.speed))
            self.stage = "ffmpeg render"
            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                self.telemetry.update(telemetry)
        elif event_type == "cooldown_wait":
            self.cooldown_status = "active"
            self.stage = "cooldown"
            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                self.telemetry.update(telemetry)
            self.recent_events.append("Cooldown active")
        elif event_type == "cooldown_resumed":
            self.cooldown_status = "idle"
            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                self.telemetry.update(telemetry)
            self.recent_events.append("Cooldown cleared")
        elif event_type == "job_failed":
            self.stage = "failed"
            self.recent_events.append(str(event.get("message", "Job failed")))
        elif event_type == "job_finished":
            result = event.get("result", {})
            status = result.get("status")
            if status == "success":
                self.result_counts["success"] += 1
            elif status in {"skipped", "reported"}:
                self.result_counts["skipped"] += 1
            elif status in {"error", "failed"}:
                self.result_counts["error"] += 1
            self.completed_jobs += 1
            elapsed = event.get("job_elapsed_seconds")
            if isinstance(elapsed, (int, float)):
                self.job_durations.append(float(elapsed))
            self.recent_events.append(f"Finished {self.current_job.get('lecture', 'output')} with {status}")
            self.cooldown_status = "idle"
        elif event_type == "run_finished":
            self.recent_events.append("Run finished")
            self.stage = "complete"
        if self.interactive:
            self.render()

    def estimate_current_eta_seconds(self) -> Optional[float]:
        speed_multiplier = parse_speed_multiplier(self.speed)
        if not speed_multiplier or self.media_duration_seconds <= 0:
            return None
        remaining_media_seconds = max(self.media_duration_seconds - self.rendered_seconds, 0.0)
        return remaining_media_seconds / speed_multiplier

    def estimate_run_eta_seconds(self) -> Optional[float]:
        remaining_jobs = max(self.total_jobs - self.completed_jobs, 0)
        current_eta = self.estimate_current_eta_seconds()
        if self.job_durations:
            average_job_seconds = sum(self.job_durations) / len(self.job_durations)
            if self.current_job:
                return max(remaining_jobs - 1, 0) * average_job_seconds + (current_eta if current_eta is not None else average_job_seconds)
            return remaining_jobs * average_job_seconds
        if current_eta is not None and remaining_jobs <= 1:
            return current_eta
        return None

    def build_screen_text(self) -> str:
        overall_bar = build_progress_bar(self.completed_jobs, self.total_jobs)
        current_bar = build_progress_bar(self.rendered_seconds, self.media_duration_seconds)
        total_remaining = max(self.total_jobs - self.completed_jobs, 0)
        lecture_name = self.current_job.get("lecture", "n/a")
        course = self.current_job.get("course", "n/a")
        section = self.current_job.get("section", "n/a")
        variant = self.current_job.get("type", "n/a")
        lines = [
            f"Dreamlet CLI - Render MP4 Videos    {time.strftime('%H:%M:%S')}",
            f"Input  {self.input_root or 'n/a'}",
            f"Output {self.output_root}",
            "Mode   full-screen live dashboard",
            "",
            "RUN STATUS",
            f"Completed  {self.completed_jobs} / {self.total_jobs}",
            f"Run ETA    {format_duration(self.estimate_run_eta_seconds())}",
            f"Remaining  {total_remaining}",
            f"Results    success {self.result_counts['success']} skipped {self.result_counts['skipped']} error {self.result_counts['error']}",
            "",
            f"Overall Progress  {overall_bar}",
            f"Current Lecture   {current_bar}",
            "",
            "CURRENT OUTPUT",
            f"Course      {course}",
            f"Section     {section}",
            f"Lecture     {lecture_name}",
            f"Language    {self.language}",
            f"Variant     {variant}",
            f"Stage       {self.stage}",
            f"Output file {self.output_path}",
            "",
            "LECTURE TIMING",
            f"Slides      {self.slide_count}",
            f"Audio clips {self.audio_count}",
            f"Media len   {format_duration(self.media_duration_seconds, fallback='00:00:00')}",
            f"Rendered    {format_duration(self.rendered_seconds, fallback='00:00:00')}",
            f"Speed       {self.speed}",
            f"Lecture ETA {format_duration(self.estimate_current_eta_seconds())}",
            "",
            "QUEUE",
            f"Ready       {self.queue_counts.get('ready', 0)}",
            f"Active      {1 if self.current_job else 0}",
            f"Regular     {self.queue_counts.get('regular', 0)}",
            f"Summary     {self.queue_counts.get('summary', 0)}",
            f"Existing    {self.queue_counts.get('existing', 0)}",
            f"Remaining   {total_remaining}",
            "",
            "SYSTEM TELEMETRY",
            f"CPU         {self.telemetry.get('cpu_percent', 'n/a')}",
            f"RAM avail   {self.telemetry.get('memory_available_gb', 'n/a')} GB",
            f"RAM used    {self.telemetry.get('memory_percent', 'n/a')}%",
            f"GPU temp    {self.telemetry.get('gpu_temp_c', 'n/a')}",
            f"Disk free   {self.telemetry.get('disk_free_gb', 'n/a')} GB",
            f"Profile     {self.machine_info.get('machine_id', 'n/a')}",
            f"Encoder     {self.encoder}",
            f"Decoder     {self.decoder or 'cpu'}",
            f"FFmpeg thr  {self.optimization_settings.get('ffmpeg_threads', 'n/a')}",
            f"FPS         {self.fps}",
            f"Cooldown    {self.cooldown_status}",
        ]
        if self.recent_events:
            lines.extend(["", "RECENT EVENTS"])
            lines.extend(self.recent_events)
        return "\n".join(lines)

    def render(self) -> None:
        if not self.interactive:
            return
        if not self._entered_alt_screen:
            self.stream.write("\x1b[?1049h\x1b[?25l")
            self._entered_alt_screen = True
        self.stream.write("\x1b[H\x1b[2J")
        self.stream.write(self.build_screen_text())
        self.stream.flush()

    def close(self) -> None:
        if self._entered_alt_screen:
            self.stream.write("\x1b[?25h\x1b[?1049l")
            self.stream.flush()
            self._entered_alt_screen = False


def build_dashboard_if_supported(
    *,
    stream: Any,
    input_root: Path,
    output_root: Path,
    machine_info: dict[str, Any],
    encoder: str,
    decoder: str | None,
    optimization_settings: dict[str, Any],
    fps: int,
    total_jobs: int,
) -> TerminalDashboard | None:
    if not supports_live_dashboard(stream):
        return None
    dashboard = TerminalDashboard(
        stream=stream,
        input_root=input_root,
        output_root=output_root,
        machine_info=machine_info,
        encoder=encoder,
        decoder=decoder,
        optimization_settings=optimization_settings,
        fps=fps,
        total_jobs=total_jobs,
        interactive=True,
    )
    if hasattr(dashboard, "telemetry") and isinstance(dashboard.telemetry, dict):
        dashboard.telemetry.update(collect_dashboard_telemetry(output_root))
    if hasattr(dashboard, "render"):
        dashboard.render()
    return dashboard


def run_ffmpeg_with_progress(command: list[str], *, creationflags: int, progress_callback=None) -> None:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )
    snapshot: dict[str, str] = {}
    diagnostic_lines: list[str] = []
    progress_keys = {
        "bitrate",
        "drop_frames",
        "dup_frames",
        "fps",
        "frame",
        "out_time",
        "out_time_ms",
        "out_time_us",
        "progress",
        "speed",
        "stream_0_0_q",
        "total_size",
    }
    for raw_line in process.stdout or []:
        line = raw_line.strip()
        if "=" not in line:
            if line:
                diagnostic_lines.append(line)
            continue
        key, value = line.split("=", 1)
        if key not in progress_keys:
            diagnostic_lines.append(line)
            continue
        snapshot[key] = value
        if key == "progress" and progress_callback:
            progress_callback({"type": "ffmpeg_progress", **parse_ffmpeg_progress_snapshot(snapshot)})
            snapshot = {}
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command, stderr="\n".join(diagnostic_lines))


def build_segment_ffmpeg_command(
    *,
    image_file: str,
    audio_file: str,
    segment_path: str,
    encoder: str,
    fps: int,
    ffmpeg_threads: int,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-threads",
        str(ffmpeg_threads),
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-i",
        image_file,
        "-i",
        audio_file,
        "-c:v",
        encoder,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        segment_path,
    ]


def build_render_ffmpeg_command(
    *,
    image_manifest: str,
    audio_manifest: str,
    output_path: str,
    encoder: str,
    fps: int,
    ffmpeg_threads: int,
    emit_progress: bool = False,
) -> list[str]:
    command = [
        "ffmpeg",
        "-y",
        "-threads",
        str(ffmpeg_threads),
    ]
    if emit_progress:
        command.extend(["-progress", "pipe:1", "-nostats"])
    command.extend(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            image_manifest,
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            audio_manifest,
            "-c:v",
            encoder,
            "-r",
            str(fps),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "faststart",
            "-shortest",
            output_path,
        ]
    )
    return command


def get_system_metrics() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024**3), 2),
    }


def get_gpu_temperature_c() -> Optional[float]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return float(result.stdout.strip().splitlines()[0])
    except Exception:
        return None


def needs_cooldown(metrics: dict[str, Any], gpu_temp_c: Optional[float], settings: dict[str, Any]) -> bool:
    if metrics.get("cpu_percent", 0) >= settings.get("cpu_soft_limit_percent", 85):
        return True
    if metrics.get("memory_available_gb", 999) <= settings.get("memory_available_soft_limit_gb", 1.5):
        return True
    if gpu_temp_c is not None and gpu_temp_c >= settings.get("gpu_temp_soft_limit_c", 78):
        return True
    return False


def apply_cooldown_if_needed(settings: dict[str, Any], progress_callback=None) -> None:
    cooldown_seconds = int(settings.get("cooldown_seconds", 0) or 0)
    if cooldown_seconds <= 0:
        return
    was_waiting = False
    while True:
        metrics = get_system_metrics()
        gpu_temp_c = get_gpu_temperature_c()
        if not needs_cooldown(metrics, gpu_temp_c, settings):
            if was_waiting and progress_callback:
                progress_callback(
                    {
                        "type": "cooldown_resumed",
                        "telemetry": {
                            "cpu_percent": metrics["cpu_percent"],
                            "memory_percent": metrics["memory_percent"],
                            "memory_available_gb": metrics["memory_available_gb"],
                            "gpu_temp_c": gpu_temp_c,
                        },
                    }
                )
            break
        was_waiting = True
        if progress_callback:
            progress_callback(
                {
                    "type": "cooldown_wait",
                    "telemetry": {
                        "cpu_percent": metrics["cpu_percent"],
                        "memory_percent": metrics["memory_percent"],
                        "memory_available_gb": metrics["memory_available_gb"],
                        "gpu_temp_c": gpu_temp_c,
                    },
                }
            )
        time.sleep(cooldown_seconds)


def probe_media_duration(media_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            media_path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return float(result.stdout.strip())


def write_image_concat_manifest(
    image_files: list[str],
    audio_files: list[str],
    manifest_path: Path,
    *,
    durations: Optional[list[float]] = None,
) -> None:
    durations = durations or [probe_media_duration(audio_file) for audio_file in audio_files]
    lines: list[str] = []
    for image_file, duration in zip(image_files, durations):
        lines.append(f"file '{Path(image_file).as_posix()}'")
        lines.append(f"duration {duration:.6f}")
    lines.append(f"file '{Path(image_files[-1]).as_posix()}'")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audio_concat_manifest(audio_files: list[str], manifest_path: Path) -> None:
    manifest_path.write_text("".join(f"file '{Path(audio_file).as_posix()}'\n" for audio_file in audio_files), encoding="utf-8")


def render_job(
    job: dict[str, Any],
    input_root: Path,
    output_root: Path,
    encoder: str,
    fps: int = DEFAULT_MP4_FPS,
    optimization_settings: Optional[dict[str, Any]] = None,
    progress_callback=None,
) -> dict[str, Any]:
    del input_root, output_root
    lecture_data = job["lecture_data"]
    lecture_path = lecture_data["path"]
    language = job.get("language", "English")
    summary = job["summary"]
    optimization_settings = optimization_settings or MACHINE_PROFILES["generic_fallback"]["optimization_settings"]
    ffmpeg_threads = int(optimization_settings.get("ffmpeg_threads", 2))
    creationflags = get_ffmpeg_creationflags(platform.system())
    image_files = find_image_files(lecture_path, language)
    audio_files = find_audio_files(lecture_path, language, summary)
    output_path = job["output_path"]
    if job["decision"]["action"] == "skip":
        return {"status": "skipped", "output_path": output_path, "message": job["decision"]["message"]}
    if job["decision"]["action"] == "report":
        return {"status": "reported", "output_path": output_path, "message": job["decision"]["message"]}
    if job["decision"]["action"] == "render_new_output":
        output_path = build_rerun_output_path(output_path)

    if len(image_files) != len(audio_files) or not image_files:
        return {"status": "error", "output_path": output_path, "message": "Image/audio inputs are missing or mismatched"}

    durations = [probe_media_duration(audio_file) for audio_file in audio_files]
    media_duration_seconds = sum(durations)
    with tempfile.TemporaryDirectory() as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        image_manifest = tmp_dir / "images.txt"
        audio_manifest = tmp_dir / "audio.txt"
        write_image_concat_manifest(image_files, audio_files, image_manifest, durations=durations)
        write_audio_concat_manifest(audio_files, audio_manifest)
        output_parent = Path(output_path).parent
        output_parent.mkdir(parents=True, exist_ok=True)
        if progress_callback:
            progress_callback(
                {
                    "type": "manifest_ready",
                    "job": job,
                    "slide_count": len(image_files),
                    "audio_count": len(audio_files),
                    "media_duration_seconds": media_duration_seconds,
                    "language": language,
                    "output_path": output_path,
                }
            )
        apply_cooldown_if_needed(optimization_settings, progress_callback=progress_callback)
        concat_cmd = build_render_ffmpeg_command(
            image_manifest=str(image_manifest),
            audio_manifest=str(audio_manifest),
            output_path=output_path,
            encoder=encoder,
            fps=fps,
            ffmpeg_threads=ffmpeg_threads,
            emit_progress=progress_callback is not None,
        )
        if progress_callback:
            def emit_dashboard_event(event: dict[str, Any]) -> None:
                if event.get("type") == "ffmpeg_progress":
                    progress_callback(
                        {
                            **event,
                            "telemetry": collect_dashboard_telemetry(Path(output_path).parent),
                        }
                    )
                else:
                    progress_callback(event)

            run_ffmpeg_with_progress(concat_cmd, creationflags=creationflags, progress_callback=emit_dashboard_event)
        else:
            subprocess.run(concat_cmd, check=True, capture_output=True, creationflags=creationflags)
    return {"status": "success", "output_path": output_path, "message": "Video successfully generated"}


def run(config: dict[str, Any]) -> int:
    input_root = config["paths"]["input_root"]
    output_root = config["paths"]["output_root"]
    organized_data = find_processed_lectures(input_root)
    if not organized_data:
        print("No lectures with matching image and audio files found.")
        return 1

    override_profile = config["machine"]["profile"]
    machine_info = select_machine_profile(collect_system_info(), MACHINE_PROFILES, None if override_profile == "auto" else override_profile)
    encoders_output = detect_ffmpeg_encoders()
    encoder, decoder, capabilities = select_video_encoder(machine_info["machine_id"], platform.system(), platform.machine(), encoders_output)
    profile_source = "config" if config["machine"]["profile"] != "auto" else machine_info["match_source"]
    encoder_fallback = "none" if capabilities["hardware_encoding"] else "software_encoder"

    inventory = build_render_inventory(
        organized_data,
        input_root=input_root,
        output_root=output_root,
        selected_language=config["run"]["language"],
        generate_regular=config["run"]["generate_regular"],
        generate_summary=config["run"]["generate_summary"],
        conflict_policy=config["run"]["conflict_policy"],
    )
    jobs = filter_jobs_by_selection(inventory["jobs"], config["selection"])
    optimization_settings = dict(machine_info["profile"]["optimization_settings"])
    dashboard = build_dashboard_if_supported(
        stream=sys.stdout,
        input_root=input_root,
        output_root=output_root,
        machine_info=machine_info,
        encoder=encoder,
        decoder=decoder,
        optimization_settings=optimization_settings,
        fps=config["run"]["fps"],
        total_jobs=len(jobs),
    )
    if dashboard is None:
        print(
            f"workflow=mp4 profile={machine_info['machine_id']} profile_source={profile_source} "
            f"encoder={encoder} decoder={decoder or 'cpu'} encoder_fallback={encoder_fallback} "
            f"fps={config['run']['fps']} "
            f"ffmpeg_threads={optimization_settings.get('ffmpeg_threads')} cooldown={optimization_settings.get('cooldown_seconds')}s "
            f"outputs={len(jobs)} hardware={capabilities['hardware_encoding']}"
        )
    results: list[dict[str, Any]] = []
    run_started_at = time.time()
    totals = {"success": 0, "skipped": 0, "error": 0, "remaining": len(jobs)}
    try:
        if dashboard is not None:
            dashboard.handle_event({"type": "run_started", "input_root": str(input_root), "output_root": str(output_root)})
            dashboard.handle_event({"type": "inventory_built", "job_count": len(jobs), "queue_counts": summarize_jobs(jobs)})
        for job in jobs:
            if dashboard is not None:
                dashboard.handle_event({"type": "job_started", "job": job})
            job_started_at = time.time()
            try:
                result = render_job(
                    job,
                    input_root,
                    output_root,
                    encoder,
                    config["run"]["fps"],
                    optimization_settings,
                    progress_callback=dashboard.handle_event if dashboard is not None else None,
                )
            except Exception as exc:
                result = {
                    "status": "error",
                    "output_path": job.get("output_path", ""),
                    "message": str(exc),
                }
                if dashboard is not None:
                    dashboard.handle_event({"type": "job_failed", "job": job, "message": str(exc)})
            results.append(result)
            if dashboard is not None:
                dashboard.handle_event({"type": "job_finished", "job": job, "result": result, "job_elapsed_seconds": time.time() - job_started_at})
    finally:
        totals = summarize_result_counts(results, len(jobs))
        if dashboard is not None:
            dashboard.handle_event({"type": "run_finished", "totals": totals, "elapsed_seconds": time.time() - run_started_at})
            if hasattr(dashboard, "close"):
                dashboard.close()
        print("\n".join(build_final_summary_lines(output_root=output_root, totals=totals, elapsed_seconds=time.time() - run_started_at)))
    return 0 if totals["error"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CLI version of 10 Render MP4 Videos.")
    parser.add_argument("--config", help="Path to TOML config. Defaults to config/10 Render MP4 Videos.toml")
    args = parser.parse_args(argv)
    try:
        return run(load_config(args.config))
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
