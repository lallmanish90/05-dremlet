"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Generate final MP4 lecture videos from image/audio pairs with machine-aware acceleration.
MAIN INPUTS:
- lecture image folders
- lecture audio folders
MAIN OUTPUTS:
- MP4 files written under `output/`
REQUIRED CONFIG / ASSETS:
- `input/` and `output/` directories
EXTERNAL SERVICES:
- local `ffmpeg` / `ffprobe`
HARDWARE ASSUMPTIONS:
- VideoToolbox on the MacBook Pro M3 Pro
- NVENC when available on the RTX machine

MP4 GPU - FINAL
Single final MP4 page tuned for:
- MacBook Pro M3 Pro (18GB) with VideoToolbox
- Acer Windows laptop with i5-12450H + RTX 3050 using NVENC when available
"""

import streamlit as st
import os
import re
import time
import glob
import enum
import platform
import subprocess
import tempfile
import gc
import psutil
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
import cv2
from PIL import Image
try:
    # For newer PIL versions
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    # For older PIL versions
    LANCZOS = Image.LANCZOS

# System Performance Monitor
class SystemPerformanceMonitor:
    """Monitor system performance and adapt processing accordingly"""
    
    def __init__(self, memory_limit_gb: float = 8.0):
        self.memory_limit_bytes = memory_limit_gb * 1024 * 1024 * 1024
        self.process = psutil.Process()
        self.cpu_count = psutil.cpu_count()
        self.total_memory = psutil.virtual_memory().total
        
    def get_system_metrics(self) -> Dict:
        """Get current system performance metrics"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        return {
            "memory_usage_gb": self.process.memory_info().rss / (1024 * 1024 * 1024),
            "memory_available_gb": memory.available / (1024 * 1024 * 1024),
            "memory_percent": memory.percent,
            "cpu_percent": cpu_percent,
            "cpu_count": self.cpu_count
        }
    
    def get_adaptive_settings(self, base_settings: Dict) -> Dict:
        """Get adaptive settings based on current system performance"""
        metrics = self.get_system_metrics()
        
        # Adaptive batch size based on available memory
        if metrics["memory_available_gb"] > 8:
            batch_multiplier = 2.0
        elif metrics["memory_available_gb"] > 4:
            batch_multiplier = 1.5
        elif metrics["memory_available_gb"] > 2:
            batch_multiplier = 1.0
        else:
            batch_multiplier = 0.5
        
        # Adaptive thread count based on CPU usage
        if metrics["cpu_percent"] < 50:
            thread_multiplier = 1.0
        elif metrics["cpu_percent"] < 75:
            thread_multiplier = 0.75
        else:
            thread_multiplier = 0.5
        
        # Calculate adaptive settings
        adaptive_batch_size = max(1, int(base_settings.get("batch_size", 4) * batch_multiplier))
        adaptive_threads = max(1, int(base_settings.get("max_threads", 4) * thread_multiplier))
        
        return {
            "batch_size": adaptive_batch_size,
            "max_threads": adaptive_threads,
            "memory_limit_gb": base_settings.get("memory_limit_gb", 8),
            "quality_preset": self._get_quality_preset(metrics),
            "processing_mode": self._get_processing_mode(metrics)
        }
    
    def _get_quality_preset(self, metrics: Dict) -> str:
        """Determine quality preset based on system capabilities"""
        if metrics["memory_available_gb"] > 6 and metrics["cpu_percent"] < 60:
            return "high_quality"
        elif metrics["memory_available_gb"] > 3 and metrics["cpu_percent"] < 80:
            return "balanced"
        else:
            return "fast"
    
    def _get_processing_mode(self, metrics: Dict) -> str:
        """Determine processing mode based on system load"""
        if metrics["cpu_percent"] > 85 or metrics["memory_percent"] > 85:
            return "conservative"
        elif metrics["cpu_percent"] < 50 and metrics["memory_available_gb"] > 4:
            return "aggressive"
        else:
            return "balanced"

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
        },
    },
}


def detect_apple_silicon_capability() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except Exception:
        return False


def detect_gpu_info() -> Dict[str, Any]:
    gpu_info: Dict[str, Any] = {"gpu_detected": False}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip().splitlines()[0]
            gpu_info.update({
                "gpu_detected": True,
                "gpu_type": "nvidia",
                "gpu_name": gpu_name,
            })
    except Exception:
        pass

    if detect_apple_silicon_capability():
        gpu_info.update({
            "gpu_detected": True,
            "gpu_type": "apple_silicon",
            "gpu_name": "Apple Silicon GPU",
        })

    return gpu_info


def collect_system_info() -> Dict[str, Any]:
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


def evaluate_profile_match(profile: Dict[str, Any], system_info: Dict[str, Any]) -> Optional[Tuple[int, List[str]]]:
    rules = profile.get("match_rules", {})
    reasons: List[str] = []
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


def select_machine_profile(system_info: Dict[str, Any], profiles: Dict[str, Dict[str, Any]], override_profile_id: Optional[str] = None) -> Dict[str, Any]:
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

    matches: List[Tuple[int, str, List[str]]] = []
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


def select_video_encoder(machine_id: str, system: str, machine: str, encoders_output: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
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


class BalancedMachineConfig:
    """Load and apply balanced machine configurations"""

    def __init__(self, override_profile_id: Optional[str] = None):
        self.override_profile_id = override_profile_id
        self.machine_config = select_machine_profile(collect_system_info(), MACHINE_PROFILES, override_profile_id)
        self.performance_monitor = SystemPerformanceMonitor(self.get_memory_limit())

    def detect_current_machine(self) -> str:
        return self.machine_config["machine_id"]

    def get_profile_name(self) -> str:
        return self.machine_config["name"]

    def get_machine_info(self) -> Dict[str, Any]:
        return self.machine_config

    def get_base_optimization_settings(self) -> Dict[str, Any]:
        return dict(self.machine_config["profile"]["optimization_settings"])

    def get_adaptive_optimization_settings(self) -> Dict:
        base_settings = self.get_base_optimization_settings()
        adaptive = self.performance_monitor.get_adaptive_settings(base_settings)
        adaptive["quality_preset"] = base_settings.get("quality_preset", adaptive.get("quality_preset", "balanced"))
        return adaptive

    def get_memory_limit(self) -> float:
        settings = self.get_base_optimization_settings()
        return settings.get("memory_limit_gb", 8.0)

# Local utility functions
def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

# Define fixed input and output directories
INPUT_DIR = os.path.join(os.getcwd(), "input")
OUTPUT_DIR = os.path.join(os.getcwd(), "output")

def find_language_folders(lecture_dir: str) -> List[str]:
    """Find all language folders in a lecture directory"""
    languages = []
    for folder in os.listdir(lecture_dir):
        if folder.endswith(" audio") or folder.endswith(" image"):
            lang = folder.split(" ")[0]
            if lang and lang not in languages:
                languages.append(lang)
    return languages

def find_image_files(lecture_dir: str, language: str = "English") -> List[str]:
    """Find all image files in a lecture directory for a specific language"""
    lang_images_dir = os.path.join(lecture_dir, f"{language} image")
    if os.path.exists(lang_images_dir) and os.path.isdir(lang_images_dir):
        image_files = get_sorted_files(lang_images_dir, file_type="image", full_path=True)
        if image_files:
            return image_files
    
    # Fallback to English if not English and no images found
    if language != "English":
        english_images_dir = os.path.join(lecture_dir, "English image")
        if os.path.exists(english_images_dir) and os.path.isdir(english_images_dir):
            image_files = get_sorted_files(english_images_dir, file_type="image", full_path=True)
            if image_files:
                return image_files
    
    return []

def find_audio_files(lecture_dir: str, language: str = "English", summary: bool = False) -> List[str]:
    """Find all audio files in a lecture directory for a specific language"""
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_dir, folder_name)
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        audio_files = get_sorted_files(lang_audio_dir, file_type="audio", full_path=True)
        if audio_files:
            return audio_files
    return []

def get_sorted_files(directory: str, file_type: str, full_path: bool = False) -> List[str]:
    """Get sorted list of files of a specific type"""
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
    else:
        raise ValueError("Invalid file_type. Use 'image' or 'audio'.")

    if not os.path.exists(directory):
        return []

    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and f.lower().endswith(extensions)
    ]

    sorted_files = sorted(files, key=lambda f: int(os.path.splitext(f)[0]) if os.path.splitext(f)[0].isdigit() else 999)

    if full_path:
        return [os.path.join(directory, f) for f in sorted_files]
    else:
        return sorted_files

def find_processed_lectures() -> Dict[str, Dict[str, Dict]]:
    """Find all lectures with audio and image files ready for MP4 generation"""
    if not os.path.exists(INPUT_DIR):
        return {}

    organized_data = {}

    for root, dirs, files in os.walk(INPUT_DIR):
        if any(util_folder in root for util_folder in ["all_pptx", "all_slides", "all_transcripts"]):
            continue

        has_english_images = "English image" in dirs
        has_english_audio = "English audio" in dirs

        if not (has_english_images and has_english_audio):
            continue

        lecture_dir = root
        languages = find_language_folders(lecture_dir)
        english_image_files = find_image_files(lecture_dir, "English")
        english_audio_files = find_audio_files(lecture_dir, "English")

        if not english_image_files or not english_audio_files:
            continue

        rel_path = os.path.relpath(lecture_dir, INPUT_DIR)
        path_components = rel_path.split(os.sep)
        lecture_name = path_components[-1]

        subject = None
        course = None
        section = None

        if len(path_components) > 3:
            subject = path_components[0]
            course = path_components[1]
            section = path_components[2]
        elif len(path_components) > 2:
            if any(section_keyword in path_components[1].lower() for section_keyword in ["section", "part", "module"]):
                course = path_components[0]
                section = path_components[1]
            else:
                subject = path_components[0]
                course = path_components[1]
        elif len(path_components) > 1:
            course = path_components[0]

        lecture_match = re.search(r'lecture\s*(\d+)', lecture_name, re.IGNORECASE)
        if lecture_match:
            lecture_display = f"Lecture {lecture_match.group(1)}"
        else:
            number_match = re.match(r'^\s*(\d+)\s*$', lecture_name)
            if number_match:
                lecture_display = f"Lecture {number_match.group(1)}"
            else:
                lecture_display = lecture_name

        subject_key = subject if subject else "Main"
        course_key = course if course else "Main Course"
        section_key = section if section else "Main Section"

        if subject_key not in organized_data:
            organized_data[subject_key] = {}
        if course_key not in organized_data[subject_key]:
            organized_data[subject_key][course_key] = {}
        if section_key not in organized_data[subject_key][course_key]:
            organized_data[subject_key][course_key][section_key] = {}

        language_data = {}
        for language in languages:
            image_files = find_image_files(lecture_dir, language)
            audio_files = find_audio_files(lecture_dir, language, summary=False)
            summary_audio_files = find_audio_files(lecture_dir, language, summary=True)

            has_regular_audio = len(audio_files) > 0
            has_summary_audio = len(summary_audio_files) > 0

            if image_files and audio_files:
                language_data[language] = {
                    "image_files": image_files,
                    "audio_files": audio_files,
                    "audio_count": len(audio_files),
                    "image_count": len(image_files),
                    "count_match": len(audio_files) == len(image_files),
                    "has_summary_audio": has_summary_audio,
                    "summary_audio_files": summary_audio_files,
                    "summary_audio_count": len(summary_audio_files),
                    "summary_count_match": len(summary_audio_files) == len(image_files)
                }

        has_english_summary = "English Summary audio" in dirs
        english_summary_audio_files = find_audio_files(lecture_dir, "English", summary=True)

        organized_data[subject_key][course_key][section_key][lecture_display] = {
            "path": lecture_dir,
            "image_files": english_image_files,
            "audio_files": english_audio_files,
            "audio_count": len(english_audio_files),
            "image_count": len(english_image_files),
            "count_match": len(english_audio_files) == len(english_image_files),
            "has_summary_audio": has_english_summary,
            "summary_audio_files": english_summary_audio_files,
            "summary_audio_count": len(english_summary_audio_files),
            "summary_count_match": len(english_summary_audio_files) == len(english_image_files),
            "output_name": f"{lecture_name}.mp4",
            "languages": languages,
            "language_data": language_data
        }

    return organized_data

def generate_output_path(lecture_path: str, language: str = "English", summary: bool = False, suffix: str = "") -> str:
    """Generate the output path for the MP4 file"""
    rel_path = os.path.relpath(lecture_path, INPUT_DIR)
    path_components = rel_path.split(os.sep)
    lecture_name = path_components[-1]

    course = None
    section = None

    if len(path_components) >= 3:
        course = path_components[-3]
        section = path_components[-2]
    elif len(path_components) == 2:
        course = path_components[0]
        section = "Main Section"
    else:
        course = "Main Course"
        section = "Main Section"

    output_dir_path = os.path.join(OUTPUT_DIR, language, course, section)
    ensure_directory_exists(output_dir_path)
    filename = f"{lecture_name}.mp4"
    if summary:
        filename = f"{lecture_name}(summary).mp4"
    if suffix:
        name, ext = os.path.splitext(filename)
        filename = f"{name}{suffix}{ext}"
    output_file = os.path.join(output_dir_path, filename)

    return output_file


def build_rerun_output_path(output_path: str) -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = Path(output_path)
    return str(path.with_name(f"{path.stem} (rerun {timestamp}){path.suffix}"))


def resolve_existing_output_action(existing_output_exists: bool, conflict_policy: str) -> Dict[str, str]:
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
    organized_data: Dict[str, Dict[str, Dict]],
    selected_language: str,
    generate_regular: bool,
    generate_summary: bool,
    conflict_policy: str,
) -> Dict[str, Any]:
    jobs: List[Dict[str, Any]] = []
    lecture_inventory: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    summary = {
        "ready_count": 0,
        "processed_count": 0,
        "lecture_count": 0,
        "output_count": 0,
    }

    for subject, courses in organized_data.items():
        for course, sections in courses.items():
            for section, section_lectures in sections.items():
                for lecture, lecture_data in section_lectures.items():
                    lang_data = lecture_data.get("language_data", {}).get(selected_language)
                    if not lang_data:
                        continue

                    lecture_key = (subject, course, section, lecture)
                    lecture_summary = {
                        "lecture_data": lecture_data,
                        "ready_outputs": 0,
                        "processed_outputs": 0,
                        "output_count": 0,
                        "jobs": [],
                    }
                    lecture_jobs: List[Dict[str, Any]] = []

                    if generate_regular and lang_data.get("count_match"):
                        output_path = generate_output_path(lecture_data["path"], selected_language, summary=False)
                        existing = os.path.exists(output_path)
                        decision = resolve_existing_output_action(existing, conflict_policy)
                        lecture_jobs.append({
                            "subject": subject,
                            "course": course,
                            "section": section,
                            "lecture": lecture,
                            "type": "Regular",
                            "summary": False,
                            "lecture_data": lecture_data,
                            "output_path": output_path,
                            "existing_output_exists": existing,
                            "decision": decision,
                        })

                    if generate_summary and lang_data.get("has_summary_audio") and lang_data.get("summary_count_match"):
                        output_path = generate_output_path(lecture_data["path"], selected_language, summary=True)
                        existing = os.path.exists(output_path)
                        decision = resolve_existing_output_action(existing, conflict_policy)
                        lecture_jobs.append({
                            "subject": subject,
                            "course": course,
                            "section": section,
                            "lecture": lecture,
                            "type": "Summary",
                            "summary": True,
                            "lecture_data": lecture_data,
                            "output_path": output_path,
                            "existing_output_exists": existing,
                            "decision": decision,
                        })

                    if not lecture_jobs:
                        continue

                    summary["lecture_count"] += 1
                    summary["output_count"] += len(lecture_jobs)
                    summary["processed_count"] += sum(1 for job in lecture_jobs if job["existing_output_exists"])
                    summary["ready_count"] += sum(
                        1 for job in lecture_jobs if job["decision"]["action"] in {"render", "render_new_output"}
                    )
                    lecture_summary["jobs"] = lecture_jobs
                    lecture_summary["output_count"] = len(lecture_jobs)
                    lecture_summary["processed_outputs"] = sum(1 for job in lecture_jobs if job["existing_output_exists"])
                    lecture_summary["ready_outputs"] = sum(
                        1 for job in lecture_jobs if job["decision"]["action"] in {"render", "render_new_output"}
                    )
                    jobs.extend(lecture_jobs)
                    lecture_inventory[lecture_key] = lecture_summary

    return {
        "jobs": jobs,
        "lectures": lecture_inventory,
        "summary": summary,
    }


def build_top_summary(machine_info: Dict[str, Any], encoder: str, inventory: Dict[str, Any], conflict_policy_label: str) -> Dict[str, Any]:
    encoder_labels = {
        "h264_videotoolbox": "VideoToolbox",
        "h264_nvenc": "NVENC",
        "h264_qsv": "Intel Quick Sync",
        "h264_vaapi": "VAAPI",
        "libx264": "CPU (libx264)",
    }
    return {
        "machine": machine_info["name"],
        "mode": "Hardware quality-first" if encoder != "libx264" else "CPU quality-first",
        "recommended_encoder": encoder_labels.get(encoder, encoder),
        "conflict_policy": conflict_policy_label,
        "metrics": [
            ("Ready", inventory["summary"]["ready_count"]),
            ("Processed", inventory["summary"]["processed_count"]),
            ("Lectures", inventory["summary"]["lecture_count"]),
            ("Outputs", inventory["summary"]["output_count"]),
        ],
    }

def detect_hardware_acceleration(config: Optional[BalancedMachineConfig] = None) -> Tuple[str, Optional[str], Dict]:
    """Detect available hardware acceleration and capabilities"""
    system = platform.system()
    machine = platform.machine()

    try:
        encoders_output = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except Exception:
        encoders_output = ""
    machine_id = config.detect_current_machine() if config else "generic_fallback"
    return select_video_encoder(machine_id, system, machine, encoders_output)

class BalancedImageProcessor:
    """Balanced image processor with adaptive quality settings"""
    
    def __init__(self, config: BalancedMachineConfig):
        self.config = config
        self.settings = config.get_adaptive_optimization_settings()
        
    def process_images_adaptively(self, image_paths: List[str], target_resolution: Tuple[int, int] = (3840, 2160)) -> List[np.ndarray]:
        """Process images with adaptive quality and performance settings"""
        quality_preset = self.settings.get("quality_preset", "balanced")
        processing_mode = self.settings.get("processing_mode", "balanced")
        
        if processing_mode == "aggressive" and len(image_paths) > 4:
            return self._process_parallel(image_paths, target_resolution, quality_preset)
        elif processing_mode == "conservative":
            return self._process_sequential(image_paths, target_resolution, quality_preset)
        else:
            return self._process_balanced(image_paths, target_resolution, quality_preset)
    
    def _process_parallel(self, image_paths: List[str], target_resolution: Tuple[int, int], quality_preset: str) -> List[np.ndarray]:
        """Process images in parallel for maximum speed"""
        import concurrent.futures
        
        max_workers = min(self.settings.get("max_threads", 4), len(image_paths))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda path: self._process_single_image(path, target_resolution, quality_preset),
                    image_paths,
                )
            )
        
        return results
    
    def _process_sequential(self, image_paths: List[str], target_resolution: Tuple[int, int], quality_preset: str) -> List[np.ndarray]:
        """Process images sequentially for memory efficiency"""
        results = []
        for image_path in image_paths:
            result = self._process_single_image(image_path, target_resolution, quality_preset)
            results.append(result)
            # Force cleanup after each image in conservative mode
            gc.collect()
        return results
    
    def _process_balanced(self, image_paths: List[str], target_resolution: Tuple[int, int], quality_preset: str) -> List[np.ndarray]:
        """Process images in balanced batches"""
        batch_size = self.settings.get("batch_size", 4)
        results = []
        
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            batch_results = []
            
            for image_path in batch:
                result = self._process_single_image(image_path, target_resolution, quality_preset)
                batch_results.append(result)
            
            results.extend(batch_results)
            
            # Cleanup after each batch
            gc.collect()
        
        return results
    
    def _process_single_image(self, image_path: str, target_resolution: Tuple[int, int], quality_preset: str) -> np.ndarray:
        """Process a single image with quality-specific settings"""
        img = Image.open(image_path)
        
        # Adjust resampling based on quality preset
        if quality_preset == "high_quality":
            resampling = LANCZOS
        elif quality_preset == "balanced":
            resampling = LANCZOS
        else:  # fast
            resampling = Image.BILINEAR
        
        img_resized = img.resize(target_resolution, resampling)
        img_array = np.array(img_resized)
        
        if len(img_array.shape) == 3 and img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        # Clean up PIL image
        img.close()
        del img, img_resized
        
        return img_array

class BalancedFFmpegProcessor:
    """Balanced FFmpeg processor with adaptive encoding settings"""
    
    def __init__(self, config: BalancedMachineConfig):
        self.config = config
        self.settings = config.get_adaptive_optimization_settings()
        self.encoder, self.decoder, self.capabilities = detect_hardware_acceleration(config)
        
    def create_balanced_video(self, image_files: List[str], audio_files: List[str], output_path: str, fps: int = 3) -> Tuple[bool, str]:
        """Create video with balanced performance and quality settings"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                return self._create_video_balanced(image_files, audio_files, output_path, temp_dir, fps)
                
        except Exception as e:
            return False, f"Error generating video: {str(e)}"
    
    def _create_video_balanced(self, image_files: List[str], audio_files: List[str], output_path: str, temp_dir: str, fps: int) -> Tuple[bool, str]:
        """Create video using balanced approach"""
        try:
            # Initialize image processor
            image_processor = BalancedImageProcessor(self.config)
            
            # Determine processing strategy based on system capabilities
            processing_mode = self.settings.get("processing_mode", "balanced")
            
            if processing_mode == "aggressive" and self.capabilities["performance_tier"] == "high":
                return self._create_video_fast_path(image_files, audio_files, output_path, temp_dir, fps, image_processor)
            elif processing_mode == "conservative":
                return self._create_video_safe_path(image_files, audio_files, output_path, temp_dir, fps, image_processor)
            else:
                return self._create_video_balanced_path(image_files, audio_files, output_path, temp_dir, fps, image_processor)
                
        except Exception as e:
            return False, f"Balanced processing error: {str(e)}"
    
    def _create_video_fast_path(self, image_files: List[str], audio_files: List[str], output_path: str, temp_dir: str, fps: int, image_processor: BalancedImageProcessor) -> Tuple[bool, str]:
        """Fast processing path for high-performance systems"""
        # Process all images at once for maximum speed
        processed_images = image_processor.process_images_adaptively(image_files)
        
        # Create segments in parallel
        segment_files = []
        batch_size = self.settings.get("batch_size", 6)
        
        for i in range(0, len(image_files), batch_size):
            batch_images = processed_images[i:i+batch_size]
            batch_audio = audio_files[i:i+batch_size]
            
            batch_segments = self._create_segments_parallel(batch_images, batch_audio, temp_dir, i, fps)
            segment_files.extend(batch_segments)
        
        # Fast concatenation
        return self._concatenate_segments_fast(segment_files, output_path, temp_dir)
    
    def _create_video_safe_path(self, image_files: List[str], audio_files: List[str], output_path: str, temp_dir: str, fps: int, image_processor: BalancedImageProcessor) -> Tuple[bool, str]:
        """Safe processing path for resource-constrained systems"""
        segment_files = []
        
        # Process one image at a time
        for i, (img_file, audio_file) in enumerate(zip(image_files, audio_files)):
            # Process single image
            processed_img = image_processor._process_single_image(img_file, (3840, 2160), "fast")
            
            # Save and create segment immediately
            img_path = os.path.join(temp_dir, f"safe_img_{i:03d}.png")
            cv2.imwrite(img_path, cv2.cvtColor(processed_img, cv2.COLOR_RGB2BGR))
            
            duration = self._get_audio_duration(audio_file)
            segment_path = os.path.join(temp_dir, f"safe_segment_{i:03d}.mp4")
            
            self._create_single_segment(img_path, audio_file, segment_path, duration, fps, "fast")
            segment_files.append(segment_path)
            
            # Cleanup immediately
            os.remove(img_path)
            del processed_img
            gc.collect()
        
        return self._concatenate_segments_safe(segment_files, output_path, temp_dir)
    
    def _create_video_balanced_path(self, image_files: List[str], audio_files: List[str], output_path: str, temp_dir: str, fps: int, image_processor: BalancedImageProcessor) -> Tuple[bool, str]:
        """Balanced processing path"""
        segment_files = []
        batch_size = self.settings.get("batch_size", 4)
        quality_preset = self.settings.get("quality_preset", "balanced")
        
        for i in range(0, len(image_files), batch_size):
            batch_images = image_files[i:i+batch_size]
            batch_audio = audio_files[i:i+batch_size]
            
            # Process batch of images
            processed_batch = []
            for img_file in batch_images:
                processed_img = image_processor._process_single_image(img_file, (3840, 2160), quality_preset)
                processed_batch.append(processed_img)
            
            # Create segments for this batch
            for j, (processed_img, audio_file) in enumerate(zip(processed_batch, batch_audio)):
                img_path = os.path.join(temp_dir, f"balanced_batch_{i}_img_{j:03d}.png")
                cv2.imwrite(img_path, cv2.cvtColor(processed_img, cv2.COLOR_RGB2BGR))
                
                duration = self._get_audio_duration(audio_file)
                segment_path = os.path.join(temp_dir, f"balanced_batch_{i}_segment_{j:03d}.mp4")
                
                self._create_single_segment(img_path, audio_file, segment_path, duration, fps, quality_preset)
                segment_files.append(segment_path)
                
                # Cleanup
                os.remove(img_path)
            
            # Cleanup batch
            del processed_batch
            gc.collect()
        
        return self._concatenate_segments_balanced(segment_files, output_path, temp_dir)
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """Get audio file duration"""
        duration_cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file
        ]
        result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def _create_single_segment(self, image_path: str, audio_path: str, output_path: str, duration: float, fps: int, quality_preset: str):
        """Create a single video segment with adaptive quality settings"""
        cmd = ['ffmpeg', '-y', '-loglevel', 'warning']
        
        # Add hardware acceleration
        if self.decoder:
            if self.decoder == 'cuda':
                cmd += ['-hwaccel', 'cuda']
            elif self.decoder == 'videotoolbox':
                cmd += ['-hwaccel', 'videotoolbox']
            elif self.decoder == 'qsv':
                cmd += ['-hwaccel', 'qsv']
            elif self.decoder == 'vaapi':
                cmd += ['-hwaccel', 'vaapi', '-vaapi_device', '/dev/dri/renderD128']
        
        # Input parameters
        cmd += [
            '-loop', '1', 
            '-framerate', str(fps), 
            '-i', image_path, 
            '-i', audio_path,
            '-c:v', self.encoder
        ]
        
        # Quality-adaptive encoder settings
        if self.encoder == 'h264_nvenc':
            if quality_preset == "high_quality":
                cmd += ['-preset', 'p4', '-rc', 'vbr', '-cq', '21', '-b:v', '10M', '-maxrate', '15M', '-bufsize', '20M']
            elif quality_preset == "balanced":
                cmd += ['-preset', 'p5', '-rc', 'vbr', '-cq', '23', '-b:v', '7M', '-maxrate', '10M', '-bufsize', '14M']
            else:  # fast
                cmd += ['-preset', 'p6', '-rc', 'vbr', '-cq', '25', '-b:v', '5M', '-maxrate', '7M', '-bufsize', '10M']
        elif self.encoder == 'h264_videotoolbox':
            if quality_preset == "high_quality":
                cmd += ['-b:v', '12M', '-maxrate', '18M', '-profile:v', 'high']
            elif quality_preset == "balanced":
                cmd += ['-b:v', '8M', '-maxrate', '12M', '-profile:v', 'main']
            else:  # fast
                cmd += ['-b:v', '6M', '-maxrate', '9M', '-profile:v', 'baseline']
        elif self.encoder == 'h264_qsv':
            preset_map = {"high_quality": "slow", "balanced": "medium", "fast": "fast"}
            cmd += ['-preset', preset_map[quality_preset], '-b:v', '7M', '-maxrate', '10M']
        elif self.encoder == 'h264_vaapi':
            quality_map = {"high_quality": "best", "balanced": "good", "fast": "fast"}
            cmd += ['-quality', quality_map[quality_preset], '-b:v', '7M']
        else:  # libx264
            preset_map = {"high_quality": "slow", "balanced": "medium", "fast": "fast"}
            crf_map = {"high_quality": "21", "balanced": "23", "fast": "25"}
            cmd += ['-tune', 'stillimage', '-preset', preset_map[quality_preset], '-crf', crf_map[quality_preset]]
        
        # Audio and output settings
        audio_bitrate = "192k" if quality_preset == "high_quality" else "128k"
        cmd += [
            '-c:a', 'aac', '-b:a', audio_bitrate,
            '-pix_fmt', 'yuv420p',
            '-shortest', '-t', str(duration),
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def _create_segments_parallel(self, processed_images: List[np.ndarray], audio_files: List[str], temp_dir: str, batch_index: int, fps: int) -> List[str]:
        """Create segments in parallel for fast processing"""
        import concurrent.futures
        
        max_workers = min(self.settings.get("max_threads", 4), len(processed_images))
        
        def create_segment_task(i, img, audio_file):
            img_path = os.path.join(temp_dir, f"fast_batch_{batch_index}_img_{i:03d}.png")
            cv2.imwrite(img_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            
            duration = self._get_audio_duration(audio_file)
            segment_path = os.path.join(temp_dir, f"fast_batch_{batch_index}_segment_{i:03d}.mp4")
            
            self._create_single_segment(img_path, audio_file, segment_path, duration, fps, "balanced")
            
            os.remove(img_path)
            return segment_path
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            segments = list(
                executor.map(
                    lambda item: create_segment_task(item[0], item[1][0], item[1][1]),
                    enumerate(zip(processed_images, audio_files)),
                )
            )
        
        return segments
    
    def _concatenate_segments_fast(self, segment_files: List[str], output_path: str, temp_dir: str) -> Tuple[bool, str]:
        """Fast concatenation for high-performance systems"""
        return self._concatenate_segments_with_settings(segment_files, output_path, temp_dir, "fast")
    
    def _concatenate_segments_safe(self, segment_files: List[str], output_path: str, temp_dir: str) -> Tuple[bool, str]:
        """Safe concatenation for resource-constrained systems"""
        return self._concatenate_segments_with_settings(segment_files, output_path, temp_dir, "safe")
    
    def _concatenate_segments_balanced(self, segment_files: List[str], output_path: str, temp_dir: str) -> Tuple[bool, str]:
        """Balanced concatenation"""
        return self._concatenate_segments_with_settings(segment_files, output_path, temp_dir, "balanced")
    
    def _concatenate_segments_with_settings(self, segment_files: List[str], output_path: str, temp_dir: str, mode: str) -> Tuple[bool, str]:
        """Concatenate segments with mode-specific settings"""
        try:
            # Create concat file
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")
            
            # Concatenate with appropriate settings
            concat_cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-f", "concat", "-safe", "0", "-i", concat_file]
            
            if mode == "fast":
                concat_cmd += ["-c", "copy", "-movflags", "faststart", output_path]
            elif mode == "safe":
                concat_cmd += ["-c", "copy", output_path]
            else:  # balanced
                concat_cmd += ["-c", "copy", "-movflags", "faststart", output_path]
            
            subprocess.run(concat_cmd, check=True, capture_output=True)
            
            performance_tier = self.capabilities["performance_tier"]
            return True, f"Video successfully generated at {output_path} using {self.encoder} encoder (Balanced - {performance_tier} tier)"
            
        except subprocess.CalledProcessError as e:
            return False, f"FFmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"

def generate_mp4_for_lecture(
    lecture_data: Dict,
    fps: int,
    language: str = "English",
    summary: bool = False,
    conflict_policy: str = ConflictPolicy.SKIP_SAFELY.value,
    config: Optional[BalancedMachineConfig] = None,
) -> Dict:
    """Generate MP4 for a lecture with balanced processing"""
    result = {
        "lecture_path": lecture_data["path"],
        "status": "error",
        "message": "",
        "output_path": "",
        "language": language,
        "summary": summary
    }

    try:
        lecture_path = lecture_data["path"]
        image_files = find_image_files(lecture_path, language)
        audio_files = find_audio_files(lecture_path, language, summary)

        if not image_files:
            result["message"] = f"No {language} image files found for this lecture"
            return result

        if not audio_files:
            audio_type = "Summary audio" if summary else "audio"
            result["message"] = f"No {language} {audio_type} files found for this lecture"
            return result

        if len(image_files) != len(audio_files):
            audio_type = "Summary audio" if summary else "audio"
            result["message"] = f"Count mismatch: {len(image_files)} images, {len(audio_files)} {audio_type} files"
            return result

        output_path = generate_output_path(lecture_path, language, summary=summary)
        existing_output_exists = os.path.exists(output_path)
        output_decision = resolve_existing_output_action(existing_output_exists, conflict_policy)

        if output_decision["action"] == "skip":
            result["status"] = "skipped"
            result["message"] = output_decision["message"]
            result["output_path"] = output_path
            return result

        if output_decision["action"] == "report":
            result["status"] = "reported"
            result["message"] = output_decision["message"]
            result["output_path"] = output_path
            return result

        if output_decision["action"] == "render_new_output":
            output_path = build_rerun_output_path(output_path)

        # Use balanced processor
        if config is None:
            config = BalancedMachineConfig()
        
        processor = BalancedFFmpegProcessor(config)
        success, message = processor.create_balanced_video(image_files, audio_files, output_path, fps)

        if not success:
            result["message"] = message
            return result

        result["status"] = "success"
        video_type = "summary video" if summary else "video"
        result["message"] = f"Successfully generated {language} {video_type}: {message}"
        result["output_path"] = output_path

        return result
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        return result

def main():
    st.title("10 Render MP4 Videos")

    ensure_directory_exists(INPUT_DIR)
    ensure_directory_exists(OUTPUT_DIR)

    organized_data = find_processed_lectures()
    if not organized_data:
        st.warning("No lectures with matching image and audio files found.")
        return

    all_languages = set()
    for subject in organized_data.values():
        for course in subject.values():
            for section in course.values():
                for lecture in section.values():
                    if "languages" in lecture:
                        all_languages.update(lecture["languages"])

    sorted_languages = sorted(all_languages)
    if "English" in sorted_languages:
        sorted_languages.remove("English")
        sorted_languages = ["English"] + sorted_languages

    default_language = "English" if "English" in sorted_languages else sorted_languages[0] if sorted_languages else None
    selected_language = st.session_state.get("mp4_selected_language", default_language)
    generate_regular = st.session_state.get("mp4_generate_regular", True)
    generate_summary = st.session_state.get("mp4_generate_summary", True)

    profile_options = {"Auto detect": None}
    for profile_id, profile in MACHINE_PROFILES.items():
        if profile_id == "generic_fallback":
            continue
        profile_options[profile["name"]] = profile_id
    profile_options["Generic fallback"] = "generic_fallback"

    top_cols = st.columns([1.1, 1.1, 1.1, 0.9])
    with top_cols[0]:
        selected_profile_label = st.selectbox(
            "Machine profile",
            options=list(profile_options.keys()),
            index=0,
            help="Use Auto detect for the current computer, or force a known machine profile.",
            key="mp4_machine_profile_label",
        )
        selected_profile_id = profile_options[selected_profile_label]

    with top_cols[1]:
        conflict_policy = st.selectbox(
            "Conflict policy",
            options=list(CONFLICT_POLICY_LABELS.keys()),
            format_func=lambda value: CONFLICT_POLICY_LABELS[value],
            index=0,
            help="Applied automatically during bulk runs. Default is safe and non-blocking for unattended runs.",
            key="mp4_conflict_policy",
        )

    with top_cols[2]:
        selected_language = st.selectbox(
            "Language",
            sorted_languages,
            index=sorted_languages.index(selected_language) if selected_language in sorted_languages else 0,
            key="mp4_selected_language",
        )

    config = BalancedMachineConfig(selected_profile_id)
    machine_info = config.get_machine_info()
    adaptive_settings = config.get_adaptive_optimization_settings()
    encoder, decoder, capabilities = detect_hardware_acceleration(config)

    inventory = build_render_inventory(
        organized_data,
        selected_language=selected_language,
        generate_regular=generate_regular,
        generate_summary=generate_summary,
        conflict_policy=conflict_policy,
    )
    top_summary = build_top_summary(machine_info, encoder, inventory, CONFLICT_POLICY_LABELS[conflict_policy])

    with top_cols[3]:
        button_label = f"Run {inventory['summary']['output_count']} MP4 jobs"
        run_clicked = st.button(
            button_label,
            disabled=inventory["summary"]["output_count"] == 0,
            use_container_width=True,
        )

    metric_cols = st.columns(4)
    for column, (label, value) in zip(metric_cols, top_summary["metrics"]):
        with column:
            st.metric(label, value)

    st.caption(
        f"Machine: {top_summary['machine']} | Mode: {top_summary['mode']} | Recommended encoder: {top_summary['recommended_encoder']}"
    )
    st.caption(
        f"Language: {selected_language} | Conflict policy: {top_summary['conflict_policy']} | "
        f"Outputs found: {inventory['summary']['output_count']}"
    )

    st.subheader("Settings")
    settings_left, settings_right = st.columns(2)
    with settings_left:
        generate_regular = st.checkbox("Generate Regular Videos", value=generate_regular, key="mp4_generate_regular")
        generate_summary = st.checkbox("Generate Summary Videos", value=generate_summary, key="mp4_generate_summary")

    with settings_right:
        st.write(f"Hardware encoder: {top_summary['recommended_encoder']}")
        if capabilities["hardware_encoding"]:
            st.success(f"Using {encoder} for encoding")
        else:
            st.info("Using CPU encoding (libx264)")

    inventory = build_render_inventory(
        organized_data,
        selected_language=selected_language,
        generate_regular=generate_regular,
        generate_summary=generate_summary,
        conflict_policy=conflict_policy,
    )
    top_summary = build_top_summary(machine_info, encoder, inventory, CONFLICT_POLICY_LABELS[conflict_policy])

    st.subheader("Lecture Selection")
    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        if st.button("Select All", key="mp4_select_all"):
            st.session_state.mp4_select_all = True
            st.rerun()
    with sel_col2:
        if st.button("Unselect All", key="mp4_unselect_all"):
            st.session_state.mp4_select_all = False
            st.rerun()

    select_all = st.session_state.get("mp4_select_all", False)
    selected_lectures: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

    for subject in organized_data:
        for course in organized_data[subject]:
            with st.expander(f"Course: {course}"):
                all_in_course = st.checkbox(f"Select all in {course}", key=f"mp4_all_{subject}_{course}", value=select_all)

                for section in organized_data[subject][course]:
                    for lecture in organized_data[subject][course][section]:
                        lecture_key = (subject, course, section, lecture)
                        lecture_summary = inventory["lectures"].get(lecture_key)
                        if not lecture_summary:
                            continue

                        label = (
                            f"{lecture}: ready {lecture_summary['ready_outputs']}, "
                            f"processed {lecture_summary['processed_outputs']}, "
                            f"outputs {lecture_summary['output_count']}"
                        )

                        if all_in_course and lecture_summary["ready_outputs"] > 0:
                            selected_lectures[lecture_key] = lecture_summary
                        elif not all_in_course:
                            selected = st.checkbox(
                                label,
                                key=f"mp4_{subject}_{course}_{section}_{lecture}_{selected_language}",
                                disabled=lecture_summary["ready_outputs"] == 0,
                            )
                            if selected:
                                selected_lectures[lecture_key] = lecture_summary

    with st.expander("Technical Details", expanded=False):
        metrics = config.performance_monitor.get_system_metrics()
        st.write(f"Profile: {machine_info['machine_id']}")
        st.write(f"Source: {machine_info['match_source']}")
        st.write(f"Threads: {adaptive_settings.get('max_threads', 4)}")
        st.write(f"Batch size: {adaptive_settings.get('batch_size', 4)}")
        st.write(f"Memory limit (GB): {adaptive_settings.get('memory_limit_gb', 8)}")
        st.write(f"Encoder: {encoder}")
        st.write(f"Decoder: {decoder or 'CPU'}")
        st.write(f"CPU Usage (%): {metrics['cpu_percent']:.1f}")
        st.write(f"Memory Usage (GB): {metrics['memory_usage_gb']:.1f}")

    if run_clicked:
        if not selected_lectures:
            st.warning("No lectures selected for MP4 generation.")
            return
        if not (generate_regular or generate_summary):
            st.warning("Please select at least one video type to generate.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_text = st.empty()
        results_container = st.container()

        actionable_jobs: List[Dict[str, Any]] = []
        for lecture_summary in selected_lectures.values():
            actionable_jobs.extend(
                job for job in lecture_summary["jobs"] if job["decision"]["action"] in {"render", "render_new_output", "report", "skip"}
            )

        total_jobs = len(actionable_jobs)
        completed_jobs = 0
        results: List[Dict[str, Any]] = []
        start_time = time.time()

        for job in actionable_jobs:
            lecture_data = job["lecture_data"]
            status_text.info(f"Processing {completed_jobs + 1}/{total_jobs}: {job['lecture']} ({job['type']})")
            metrics = config.performance_monitor.get_system_metrics()
            metrics_text.info(f"CPU: {metrics['cpu_percent']:.1f}% | Memory: {metrics['memory_usage_gb']:.1f}GB | Encoder: {encoder}")

            result = generate_mp4_for_lecture(
                lecture_data,
                fps=3,
                language=selected_language,
                summary=job["summary"],
                conflict_policy=conflict_policy,
                config=config,
            )
            result.update({
                "subject": job["subject"],
                "course": job["course"],
                "section": job["section"],
                "lecture": job["lecture"],
                "type": job["type"],
            })
            results.append(result)

            completed_jobs += 1
            progress_bar.progress(completed_jobs / total_jobs if total_jobs else 1.0)

        metrics_text.empty()
        status_text.success(f"Processed {completed_jobs} MP4 jobs")

        with results_container:
            st.subheader("Results")
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = sum(1 for r in results if r["status"] == "error")
            skipped_count = sum(1 for r in results if r["status"] in {"skipped", "reported"})

            result_cols = st.columns(4)
            result_cols[0].metric("Successful", success_count)
            result_cols[1].metric("Skipped / Reported", skipped_count)
            result_cols[2].metric("Errors", error_count)
            elapsed = time.time() - start_time
            result_cols[3].metric("Time (sec)", f"{elapsed:.1f}")

            for result in results:
                status_icon = "✅" if result["status"] == "success" else "⏭️" if result["status"] in {"skipped", "reported"} else "❌"
                display_name = f"{result['course']} - {result['lecture']} ({result.get('type', '')})"
                with st.expander(f"{status_icon} {display_name}"):
                    st.write(f"**Status:** {result['status']}")
                    st.write(f"**Message:** {result['message']}")
                    if result.get("output_path"):
                        st.write(f"**Output:** {result['output_path']}")

if __name__ == "__main__":
    main()
