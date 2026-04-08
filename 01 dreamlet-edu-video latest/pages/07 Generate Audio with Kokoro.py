"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Generate lecture audio from section text using the local Kokoro TTS service.
MAIN INPUTS:
- section text files under lecture folders in `input/`
MAIN OUTPUTS:
- generated audio files for regular and summary narration
REQUIRED CONFIG / ASSETS:
- running Kokoro TTS service
EXTERNAL SERVICES:
- Kokoro API at `http://localhost:8880`
HARDWARE ASSUMPTIONS:
- local machine may use CPU or GPU depending on Kokoro server setup
"""

import streamlit as st
import os
import re
import time
import json
import enum
import platform
import requests
import fnmatch
from pathlib import Path
import glob
from typing import Any, Dict, List, Tuple, Optional

# Local utility functions (moved from multiple utils modules)
def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def get_output_directory() -> str:
    """Get the path to the output directory"""
    return get_input_directory()

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


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


def detect_apple_silicon_capability() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        import subprocess
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except Exception:
        return False


def collect_host_system_info() -> Dict[str, Any]:
    architecture = platform.machine().lower()
    if detect_apple_silicon_capability():
        architecture = "arm64"
    return {
        "hostname": platform.node().lower(),
        "platform": platform.system().lower(),
        "architecture": architecture,
        "memory_gb": round((os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024**3)) if hasattr(os, "sysconf") else 0,
    }


def select_machine_profile(system_info: Dict[str, Any], profiles: Dict[str, Dict[str, Any]], override_profile_id: Optional[str] = None) -> Dict[str, Any]:
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
    """Clean text for TTS processing"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'__(.*?)__', r'\1', text)      # Underline
    text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # URLs
    text = re.sub(r'<.*?>', '', text)             # HTML tags
    text = re.sub(r'[#*_~`]', ' ', text)          # Special characters
    text = re.sub(r'\s+', ' ', text).strip()      # Normalize whitespace
    return text

def calculate_word_count(text: str) -> int:
    """Calculate the word count in a text"""
    cleaned_text = clean_text_for_tts(text)
    words = cleaned_text.split()
    return len(words)

def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate audio duration based on word count"""
    word_count = calculate_word_count(text)
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60

# Kokoro API integration functions
KOKORO_API_URL = "http://localhost:8880/v1"

def get_available_voices() -> List[Dict[str, str]]:
    """Get available voices from the Kokoro API"""
    try:
        response = requests.get(f"{KOKORO_API_URL}/audio/voices")
        voices_data = response.json()
        
        voice_list = []
        for voice_id in voices_data.get("voices", []):
            parts = voice_id.split('_')
            
            if len(parts) >= 2:
                language_code = parts[0]
                voice_name = parts[1]
                
                language_name = "English"
                gender = "Female"
                
                if language_code == "am" or language_code == "bm" or language_code == "em" or language_code == "hm" or language_code == "im" or language_code == "jm" or language_code == "pm" or language_code == "zm":
                    gender = "Male"
                
                if language_code == "bf" or language_code == "bm":
                    language_name = "British English"
                elif language_code == "ef" or language_code == "em":
                    language_name = "European English"
                elif language_code == "ff":
                    language_name = "French"
                elif language_code == "hf" or language_code == "hm":
                    language_name = "Hindi"
                elif language_code == "if" or language_code == "im":
                    language_name = "Italian"
                elif language_code == "jf" or language_code == "jm":
                    language_name = "Japanese"
                elif language_code == "pf" or language_code == "pm":
                    language_name = "Portuguese"
                elif language_code == "zf" or language_code == "zm":
                    language_name = "Chinese"
                
                description = f"{language_name} voice"
                
                voice_list.append({
                    "id": voice_id,
                    "name": voice_name.capitalize(),
                    "gender": gender,
                    "language": language_name,
                    "description": description
                })
        
        return sorted(voice_list, key=lambda x: (x["language"], x["name"]))
    
    except Exception as e:
        st.error(f"Error retrieving voices from Kokoro API: {str(e)}")
        return []

def tts_cost_estimation(word_count: int, model: str = "kokoro") -> float:
    """Estimate cost for TTS processing (always returns 0 for local Kokoro TTS)"""
    return 0.0

def generate_combined_voice(voice_weights: Dict[str, float]) -> Tuple[bool, str, Optional[str]]:
    """Generate a combined voice string for direct use in TTS API"""
    if not voice_weights:
        return False, "No voices specified for combination", None
    
    try:
        voice_combination = "+".join([f"{voice}({int(weight)})" for voice, weight in voice_weights.items()])
        return True, "Voice combination created successfully", voice_combination
    
    except Exception as e:
        return False, f"Error in voice combination: {str(e)}", None


def inspect_kokoro_runtime() -> Dict[str, Any]:
    runtime_info = {
        "connected": False,
        "runtime_mode": "unknown",
        "gpu_available": False,
        "message": "Kokoro runtime not inspected",
    }
    try:
        response = requests.get(f"{KOKORO_API_URL}/debug/system", timeout=5)
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
        runtime_info["message"] = f"Error checking Kokoro runtime: {str(exc)}"
        return runtime_info


def convert_text_to_speech(
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
) -> Dict[str, Any]:
    """Convert text to speech using Kokoro's TTS API"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        params = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": response_format,
            "speed": speed,
            "normalization_options": {
                "normalize": normalize_text
            }
        }
        
        if enable_timestamps:
            params["timestamps"] = True
        
        response = requests.post(
            f"{KOKORO_API_URL}/audio/speech",
            json=params,
            timeout=request_timeout_sec,
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"API request failed with status {response.status_code}: {response.text}",
                "timestamps": None,
            }
        
        timestamps = None
        if enable_timestamps and 'x-timestamps' in response.headers:
            try:
                timestamps = json.loads(response.headers['x-timestamps'])
                
                if save_timestamps:
                    timestamps_path = os.path.splitext(output_path)[0] + '.json'
                    with open(timestamps_path, 'w', encoding='utf-8') as f:
                        json.dump(timestamps, f, indent=2)
            except Exception as e:
                st.warning(f"Generated audio successfully, but could not parse timestamps: {str(e)}")
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return {
            "success": True,
            "message": "Text-to-speech conversion successful",
            "timestamps": timestamps,
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error in text-to-speech conversion: {str(e)}",
            "timestamps": None,
        }

def check_connection() -> Tuple[bool, str]:
    """Check if the Kokoro API is accessible"""
    try:
        response = requests.get(f"{KOKORO_API_URL}/audio/voices", timeout=5)
        if response.status_code == 200:
            return True, "Connected to Kokoro API"
        else:
            return False, f"API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection error: Could not connect to Kokoro API (http://localhost:8880)"
    except requests.exceptions.Timeout:
        return False, "Connection timeout: Kokoro API did not respond in time"
    except Exception as e:
        return False, f"Error checking Kokoro API connection: {str(e)}"
        
def check_gpu_availability() -> Tuple[bool, str]:
    """Check if the Kokoro API is using GPU"""
    runtime_info = inspect_kokoro_runtime()
    return runtime_info["gpu_available"], runtime_info["message"]

st.set_page_config(page_title="07 TTS Kokoro - Multi-Language", page_icon="📝")

# Language code mapping for voice IDs
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
    "af": "English",
    "am": "English"
}

def get_language_from_voice_id(voice_id: str) -> str:
    """
    Extract the language name from a voice ID
    
    Args:
        voice_id: Voice ID (e.g., 'af_bella', 'pm_antonio')
        
    Returns:
        The language name (e.g., 'English', 'Portuguese')
    """
    prefix = voice_id.split('_')[0]
    return LANGUAGE_MAP.get(prefix, "Unknown")

def get_voices_by_language():
    """
    Group available voices by language to make selection easier
    
    Returns:
        Dict mapping language names to lists of voice dictionaries
    """
    all_voices = get_available_voices()
    languages = {}
    
    for voice in all_voices:
        language = get_language_from_voice_id(voice["id"])
        if language not in languages:
            languages[language] = []
        languages[language].append(voice)
    
    return languages

def find_language_section_files(language: str = "English") -> Dict[str, Dict[str, Dict]]:
    """
    Find all section files for a specific language created by the previous step
    
    Args:
        language: The language to find files for (default: "English")
        
    Returns:
        Nested dictionary of course -> lecture -> section files with type indicators
    """
    input_dir = get_input_directory()
    language_files = {}
    
    # Get all course directories (can be any name now, not just numeric)
    course_dirs = glob.glob(os.path.join(input_dir, "*"))
    course_dirs = [d for d in course_dirs if os.path.isdir(d)]
    
    for course_dir in course_dirs:
        course_name = os.path.basename(course_dir)
        
        # Get all lecture directories (any name containing 'Lecture')
        lecture_dirs = glob.glob(os.path.join(course_dir, "*Lecture*"))
        if not lecture_dirs:
            # If no 'Lecture' folders found, try all subdirectories
            lecture_dirs = glob.glob(os.path.join(course_dir, "*"))
            lecture_dirs = [d for d in lecture_dirs if os.path.isdir(d)]
        
        for lecture_dir in lecture_dirs:
            lecture_name = os.path.basename(lecture_dir)
            
            # Check for language-specific transcript folder
            transcript_folder = f"{language} text"
            transcript_dir = os.path.join(lecture_dir, transcript_folder)
            
            # Check for language-specific summary folder
            summary_folder = f"{language} Summary text"
            summary_dir = os.path.join(lecture_dir, summary_folder)
            
            transcript_files = []
            summary_files = []
            
            # Get transcript section files if folder exists
            if os.path.exists(transcript_dir):
                # Try numbered files first, then any .txt files
                transcript_files = glob.glob(os.path.join(transcript_dir, "[0-9]*.txt"))
                if not transcript_files:
                    transcript_files = glob.glob(os.path.join(transcript_dir, "*.txt"))
                transcript_files.sort()
            
            # Get summary section files if folder exists
            if os.path.exists(summary_dir):
                # Try numbered files first, then any .txt files
                summary_files = glob.glob(os.path.join(summary_dir, "[0-9]*.txt"))
                if not summary_files:
                    summary_files = glob.glob(os.path.join(summary_dir, "*.txt"))
                summary_files.sort()
            
            # Add to results if there are files for this lecture
            if transcript_files or summary_files:
                if course_name not in language_files:
                    language_files[course_name] = {}
                
                language_files[course_name][lecture_name] = {
                    "base_dir": lecture_dir,
                    "transcript": {
                        "dir": transcript_dir if os.path.exists(transcript_dir) else None,
                        "section_files": transcript_files
                    },
                    "summary": {
                        "dir": summary_dir if os.path.exists(summary_dir) else None,
                        "section_files": summary_files
                    }
                }
    
    return language_files


def resolve_existing_audio_action(existing_output_exists: bool, conflict_policy: str) -> Dict[str, str]:
    if not existing_output_exists:
        return {"action": "process", "status": "ready", "message": "Audio does not exist yet"}
    if conflict_policy == ConflictPolicy.REPORT_ONLY.value:
        return {"action": "report", "status": "reported", "message": "Existing audio detected; report-only mode left it unchanged"}
    if conflict_policy == ConflictPolicy.RENDER_NEW_OUTPUT.value:
        return {"action": "render_new_output", "status": "ready", "message": "Existing audio detected; rendering to a new filename"}
    if conflict_policy == ConflictPolicy.OVERWRITE.value:
        return {"action": "process", "status": "ready", "message": "Existing audio detected; output will be overwritten"}
    return {"action": "skip", "status": "skipped", "message": "Existing audio detected; skipped safely"}


def build_audio_inventory(language_files: Dict[str, Dict[str, Dict]], language: str, audio_format: str, conflict_policy: str) -> Dict[str, Any]:
    jobs: List[Dict[str, Any]] = []
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

            lecture_jobs: List[Dict[str, Any]] = []
            for kind, target_dir in (("transcript", transcript_audio_dir), ("summary", summary_audio_dir)):
                section_files = lecture_data[kind]["section_files"]
                for file_path in section_files:
                    section_number = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = os.path.join(target_dir, f"{section_number}.{audio_format}")
                    existing = os.path.exists(output_path) and os.path.getsize(output_path) > 0
                    decision = resolve_existing_audio_action(existing, conflict_policy)
                    lecture_jobs.append({
                        "course": course,
                        "lecture": lecture,
                        "kind": kind,
                        "file_path": file_path,
                        "output_path": output_path,
                        "decision": decision,
                        "existing_output_exists": existing,
                    })

            if lecture_jobs:
                summary["language_count"] = 1  # per-language inventory
                summary["section_count"] += len(lecture_jobs)
                summary["processed_count"] += sum(1 for job in lecture_jobs if job["existing_output_exists"])
                summary["ready_count"] += sum(1 for job in lecture_jobs if job["decision"]["action"] in {"process", "render_new_output"})
                jobs.extend(lecture_jobs)

    return {"jobs": jobs, "summary": summary}


def build_audio_top_summary(machine_info: Dict[str, Any], runtime_info: Dict[str, Any], inventory: Dict[str, Any], conflict_policy_label: str) -> Dict[str, Any]:
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


def build_selected_language_inventory(selected_languages: List[str], audio_format: str, conflict_policy: str) -> Dict[str, Any]:
    combined_jobs: List[Dict[str, Any]] = []
    summary = {
        "ready_count": 0,
        "processed_count": 0,
        "language_count": 0,
        "section_count": 0,
    }

    for language in selected_languages:
        language_files = find_language_section_files(language=language)
        inventory = build_audio_inventory(language_files, language, audio_format, conflict_policy)
        if inventory["jobs"]:
            summary["language_count"] += 1
        summary["ready_count"] += inventory["summary"]["ready_count"]
        summary["processed_count"] += inventory["summary"]["processed_count"]
        summary["section_count"] += inventory["summary"]["section_count"]
        combined_jobs.extend([{**job, "language": language} for job in inventory["jobs"]])

    return {"jobs": combined_jobs, "summary": summary}

def generate_tts_for_sections(
    section_files: List[str],
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
) -> List[Dict]:
    """
    Generate TTS for a list of section files
    
    Args:
        section_files: List of section file paths
        voice: Voice to use for TTS
        model: Model to use for TTS (kokoro)
        output_dir: Directory to save audio files
        response_format: Audio format (mp3, wav)
        speed: Speech speed (default: 1.0)
        normalize_text: Apply text normalization
        enable_timestamps: Generate word-level timestamps
        save_timestamps: Save timestamps to a JSON file alongside the audio
        
    Returns:
        List of processing results
    """
    results = []
    
    for batch_start in range(0, len(section_files), max_sections_per_batch):
        batch_files = section_files[batch_start:batch_start + max_sections_per_batch]
        for file_path in batch_files:
        # Extract section number from filename
            section_file = os.path.basename(file_path)
            section_number = os.path.splitext(section_file)[0]
        
        # Determine output filename
            output_filename = f"{section_number}.{response_format}"
            output_path = os.path.join(output_dir, output_filename)

            existing_output_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
            output_decision = resolve_existing_audio_action(existing_output_exists, conflict_policy)

            if output_decision["action"] == "skip":
                results.append({
                    "success": True,
                    "file": file_path,
                    "output": output_path,
                    "status": "skipped",
                    "message": output_decision["message"],
                    "processing_time": 0,
                    "word_count": 0
                })
                continue
            if output_decision["action"] == "report":
                results.append({
                    "success": True,
                    "file": file_path,
                    "output": output_path,
                    "status": "reported",
                    "message": output_decision["message"],
                    "processing_time": 0,
                    "word_count": 0
                })
                continue
            if output_decision["action"] == "render_new_output":
                output_filename = f"{section_number} (rerun {int(time.time())}).{response_format}"
                output_path = os.path.join(output_dir, output_filename)
        
        # Read the content of the section file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Clean the text
                if normalize_text:
                    content = clean_text_for_tts(content)
            
            # Skip empty files
                if not content.strip():
                    results.append({
                        "success": True,
                        "file": file_path,
                        "output": output_path,
                        "status": "skipped",
                        "message": "Empty or whitespace-only file",
                        "processing_time": 0,
                        "word_count": 0
                    })
                    continue
            
            # Count words for statistics
                word_count = calculate_word_count(content)
            
            # Start timing
                start_time = time.time()
            
            # Generate speech from text
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
                )
            
            # Stop timing
                processing_time = time.time() - start_time
            
                if result["success"]:
                # Save timestamps if requested
                    if enable_timestamps and save_timestamps and "timestamps" in result:
                        timestamps_path = f"{os.path.splitext(output_path)[0]}.json"
                        with open(timestamps_path, 'w', encoding='utf-8') as f:
                            json.dump(result["timestamps"], f, indent=2)
                
                # Add additional statistics
                    result["processing_time"] = processing_time
                    result["word_count"] = word_count
                    result["output"] = output_path
                    result["status"] = "processed"
                
                # Add to results list
                    results.append(result)
                else:
                # Add failure information
                    result["file"] = file_path
                    result["processing_time"] = processing_time
                    result["word_count"] = word_count
                    result["status"] = "failed"
                    results.append(result)
        
            except Exception as e:
            # Handle any other exceptions
                results.append({
                    "success": False,
                    "file": file_path,
                    "status": "failed",
                    "message": f"Error: {str(e)}",
                    "processing_time": 0,
                    "word_count": 0
                })
    
    return results

def main():
    st.title("TTS Kokoro")
    st.write("Convert transcript and summary sections to audio files using local Kokoro Text-to-Speech API.")
    
    # Check for Kokoro API connection
    connection_status, connection_message = check_connection()
    
    if not connection_status:
        st.error(f"Cannot connect to Kokoro API: {connection_message}")
        st.info("Please ensure the Kokoro TTS server is running at http://localhost:8880")
        return
    
    # Check GPU availability
    gpu_available, gpu_message = check_gpu_availability()
    if gpu_available:
        st.success(f"🚀 {gpu_message}")
    else:
        st.warning(f"💻 {gpu_message} - Processing may be slower")
        st.info("For better performance, ensure CUDA and PyTorch GPU support are properly configured")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Get available voices and organize by language
    voices_by_language = get_voices_by_language()
    all_voices = get_available_voices()
    
    # Create mapping of voice_id to voice display name
    voice_options = {v["id"]: f"{v['name']} ({v['gender']})" for v in all_voices}
    
    # List of supported languages (only those with available voices)
    supported_languages = [lang for lang in voices_by_language.keys() if voices_by_language[lang]]
    
    # Model and format settings
    selected_model = "kokoro"
    st.header("TTS Settings")
    st.info("Using Kokoro Text-to-Speech (Local) with GPU acceleration")
    
    # Initialize session state for language settings if not already present
    if "language_settings" not in st.session_state:
        # Start with an empty dictionary - user will select languages directly
        st.session_state.language_settings = {}
    
    # STEP 1: Language Selection
    st.subheader("1️⃣ Select Languages")
    st.write("Choose which languages you want to process. Only languages with available voices are shown.")
    
    # Create a grid of checkboxes for language selection
    language_cols = st.columns(3)
    selected_languages = []
    
    for i, lang in enumerate(supported_languages):
        with language_cols[i % 3]:
            is_selected = st.checkbox(
                lang, 
                value=lang in st.session_state.language_settings,
                key=f"lang_select_{lang}"
            )
            
            if is_selected:
                selected_languages.append(lang)
    
    # Sync language settings based on selected languages
    # Add new languages
    for lang in selected_languages:
        if lang not in st.session_state.language_settings:
            # Find a suitable default voice for this language
            lang_voices = voices_by_language.get(lang, [])
            default_voice = lang_voices[0]["id"] if lang_voices else list(voice_options.keys())[0]
            
            # Add the language with default settings
            st.session_state.language_settings[lang] = {
                "voice": default_voice,
                "speed": 1.0,
                "normalize": True
            }
    
    # Remove deselected languages
    for lang in list(st.session_state.language_settings.keys()):
        if lang not in selected_languages:
            del st.session_state.language_settings[lang]
    
    # STEP 2: Common Settings
    st.subheader("2️⃣ Common Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        audio_format = st.selectbox(
            "Audio Format",
            options=["mp3", "wav"],
            index=0,
            key="audio_format",
            help="Select audio output format for all languages"
        )
    
    with col2:
        generate_timestamps = st.checkbox(
            "Generate Word Timestamps",
            value=False,
            key="generate_timestamps",
            help="Generate timing information for all languages"
        )
        
        save_timestamps = False
        if generate_timestamps:
            save_timestamps = st.checkbox(
                "Save Timestamps to JSON",
                value=True,
                key="save_timestamps",
                help="Save word timing information for all languages"
            )
    
    # STEP 3: Language-Specific Settings
    if st.session_state.language_settings:
        st.subheader("3️⃣ Language-Specific Settings")
        
        # Display all configured languages
        for language, settings in list(st.session_state.language_settings.items()):
            with st.expander(f"{language} Settings", expanded=True):
                # Get available voices for this language
                language_voice_options = {}
                for voice in voices_by_language.get(language, []):
                    language_voice_options[voice["id"]] = f"{voice['name']} ({voice['gender']})"
                
                # If no voices available for this language, use all voices
                if not language_voice_options:
                    language_voice_options = voice_options
                
                # Find the index of the currently selected voice
                voice_options_list = list(language_voice_options.keys())
                selected_index = 0
                
                if settings["voice"] in voice_options_list:
                    selected_index = voice_options_list.index(settings["voice"])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    voice = st.selectbox(
                        f"Voice",
                        options=voice_options_list,
                        format_func=lambda x: language_voice_options[x],
                        index=selected_index,
                        key=f"voice_{language}"
                    )
                    st.session_state.language_settings[language]["voice"] = voice
                
                with col2:
                    speed = st.slider(
                        f"Speed",
                        min_value=0.5,
                        max_value=2.0,
                        value=settings["speed"],
                        step=0.1,
                        key=f"speed_{language}"
                    )
                    st.session_state.language_settings[language]["speed"] = speed
                
                normalize = st.checkbox(
                    "Normalize Text", 
                    value=settings["normalize"],
                    key=f"normalize_{language}",
                    help="Convert numbers, dates, etc. to spoken form"
                )
                st.session_state.language_settings[language]["normalize"] = normalize
    
    # STEP 4: Process Button
    st.subheader("4️⃣ Process Selected Languages")
    if st.button("Process Selected Languages", type="primary", key="process_languages"):
        # Get list of selected languages
        enabled_languages = list(st.session_state.language_settings.keys())
        
        if not enabled_languages:
            st.error("No languages selected. Please select at least one language.")
        else:
            # Progress tracking
            main_progress_container = st.container()
            with main_progress_container:
                main_progress_bar = st.progress(0)
                main_stats = st.empty()
                eta_display = st.empty()
            
            # Current language status
            language_status_container = st.container()
            
            # Results accumulator
            all_language_results = {}
            
            # Track overall progress across all languages
            total_languages = len(enabled_languages)
            processed_languages = 0
            
            # Overall start time
            overall_start_time = time.time()
            
            st.info(f"Processing {total_languages} languages: {', '.join(enabled_languages)}")
            
            # Process each selected language
            for language in enabled_languages:
                # Language settings
                lang_settings = st.session_state.language_settings[language]
                
                with language_status_container:
                    st.subheader(f"Processing {language}")
                    language_progress = st.progress(0)
                    language_status = st.empty()
                
                # Find files for this language
                language_files = find_language_section_files(language=language)
                
                if not language_files:
                    language_status.warning(f"No files found for {language}. Skipping.")
                    continue
                
                # Create results container for this language
                language_results = []
                
                # Count total sections for this language
                total_sections = 0
                for course, lectures in language_files.items():
                    for lecture, lecture_data in lectures.items():
                        total_sections += len(lecture_data["transcript"]["section_files"])
                        total_sections += len(lecture_data["summary"]["section_files"])
                
                # Track processed sections for this language
                processed_sections = 0
                
                # Language start time
                language_start_time = time.time()
                
                # Process each lecture for this language
                for course, lectures in language_files.items():
                    for lecture, lecture_data in lectures.items():
                        # Update status
                        language_status.info(f"Processing {course} - {lecture}")
                        
                        # Create audio directories for this language
                        lecture_base_dir = lecture_data["base_dir"]
                        
                        # For transcript files
                        transcript_audio_folder = f"{language} audio"
                        transcript_audio_dir = os.path.join(lecture_base_dir, transcript_audio_folder)
                        os.makedirs(transcript_audio_dir, exist_ok=True)
                        
                        # For summary files
                        summary_audio_folder = f"{language} Summary audio"
                        summary_audio_dir = os.path.join(lecture_base_dir, summary_audio_folder)
                        os.makedirs(summary_audio_dir, exist_ok=True)
                        
                        # Process transcript files
                        if lecture_data["transcript"]["section_files"]:
                            transcript_results = generate_tts_for_sections(
                                section_files=lecture_data["transcript"]["section_files"],
                                voice=lang_settings["voice"],
                                model=selected_model,
                                output_dir=transcript_audio_dir,
                                response_format=audio_format,
                                speed=lang_settings["speed"],
                                normalize_text=lang_settings["normalize"],
                                enable_timestamps=generate_timestamps,
                                save_timestamps=save_timestamps
                            )
                            language_results.extend(transcript_results)
                            processed_sections += len(transcript_results)
                        
                        # Process summary files
                        if lecture_data["summary"]["section_files"]:
                            summary_results = generate_tts_for_sections(
                                section_files=lecture_data["summary"]["section_files"],
                                voice=lang_settings["voice"],
                                model=selected_model,
                                output_dir=summary_audio_dir,
                                response_format=audio_format,
                                speed=lang_settings["speed"],
                                normalize_text=lang_settings["normalize"],
                                enable_timestamps=generate_timestamps,
                                save_timestamps=save_timestamps
                            )
                            language_results.extend(summary_results)
                            processed_sections += len(summary_results)
                        
                        # Update language progress
                        language_progress.progress(processed_sections / total_sections)
                        
                        # Calculate ETA for this language
                        elapsed_language_time = time.time() - language_start_time
                        if processed_sections > 0:
                            sections_per_second = processed_sections / elapsed_language_time
                            remaining_sections = total_sections - processed_sections
                            eta_seconds = remaining_sections / sections_per_second if sections_per_second > 0 else 0
                            minutes, seconds = divmod(int(eta_seconds), 60)
                            language_status.text(f"Progress: {processed_sections}/{total_sections} sections. ETA: {minutes}m {seconds}s")
                
                # Language complete
                language_progress.progress(1.0)
                language_status.success(f"{language} processing complete: {processed_sections} sections processed")
                
                # Store results for this language
                all_language_results[language] = language_results
                
                # Update overall progress
                processed_languages += 1
                main_progress_bar.progress(processed_languages / total_languages)
                
                # Calculate overall ETA
                elapsed_overall_time = time.time() - overall_start_time
                if processed_languages > 0:
                    languages_per_second = processed_languages / elapsed_overall_time
                    remaining_languages = total_languages - processed_languages
                    eta_overall_seconds = remaining_languages / languages_per_second if languages_per_second > 0 else 0
                    eta_minutes, eta_seconds = divmod(int(eta_overall_seconds), 60)
                    main_stats.text(f"Overall progress: {processed_languages}/{total_languages} languages. ETA: {eta_minutes}m {eta_seconds}s")
            
            # All languages processed
            main_progress_bar.progress(1.0)
            main_stats.success(f"All {total_languages} languages processed successfully!")
            
            # Display results summary
            st.header("Processing Results")
            
            for language, results in all_language_results.items():
                with st.expander(f"{language} Results"):
                    # Count successes and failures
                    success_count = sum(1 for r in results if r["success"])
                    failure_count = sum(1 for r in results if not r["success"])
                    total_count = len(results)
                    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
                    
                    # Calculate total words and processing time
                    total_words = sum(r["word_count"] for r in results if "word_count" in r)
                    total_processing_time = sum(r["processing_time"] for r in results if "processing_time" in r)
                    
                    # Average processing speed
                    words_per_second = total_words / total_processing_time if total_processing_time > 0 else 0
                    
                    # Display summary
                    st.write(f"**Summary for {language}:**")
                    st.write(f"- Processed: {success_count}/{total_count} files ({success_rate:.1f}% success rate)")
                    st.write(f"- Total words: {total_words:,}")
                    st.write(f"- Total processing time: {total_processing_time:.2f} seconds")
                    st.write(f"- Average speed: {words_per_second:.1f} words per second")
                    
                    # Display failures if any
                    if failure_count > 0:
                        st.write("**Failed files:**")
                        for result in results:
                            if not result["success"]:
                                st.error(f"{os.path.basename(result['file'])}: {result['message']}")
            
            # Overall summary
            st.subheader("Overall Summary")
            total_files = sum(len(results) for results in all_language_results.values())
            total_successes = sum(sum(1 for r in results if r["success"]) for results in all_language_results.values())
            overall_success_rate = (total_successes / total_files) * 100 if total_files > 0 else 0
            
            st.write(f"- Total languages processed: {total_languages}")
            st.write(f"- Total files processed: {total_files}")
            st.write(f"- Overall success rate: {overall_success_rate:.1f}%")
            st.write(f"- Total processing time: {(time.time() - overall_start_time):.2f} seconds")

def main():
    st.title("07 Generate Audio with Kokoro")

    connection_status, connection_message = check_connection()
    if not connection_status:
        st.error(f"Cannot connect to Kokoro API: {connection_message}")
        st.info("Please ensure the Kokoro TTS server is running at http://localhost:8880")
        return

    runtime_info = inspect_kokoro_runtime()
    all_voices = get_available_voices()
    voices_by_language = get_voices_by_language()
    voice_options = {v["id"]: f"{v['name']} ({v['gender']})" for v in all_voices}
    supported_languages = [lang for lang in voices_by_language.keys() if voices_by_language[lang]]

    if "language_settings" not in st.session_state:
        st.session_state.language_settings = {}

    current_audio_format = st.session_state.get("audio_format", "mp3")

    top_cols = st.columns([1.2, 1.2, 0.9])
    profile_options = {"Auto detect": None}
    for profile_id, profile in MACHINE_PROFILES.items():
        if profile_id == "generic_fallback":
            continue
        profile_options[profile["name"]] = profile_id
    profile_options["Generic fallback"] = "generic_fallback"

    with top_cols[0]:
        selected_profile_label = st.selectbox(
            "Machine profile",
            options=list(profile_options.keys()),
            index=0,
            key="kokoro_machine_profile_label",
        )
        selected_profile_id = profile_options[selected_profile_label]

    machine_info = select_machine_profile(collect_host_system_info(), MACHINE_PROFILES, selected_profile_id)
    host_settings = machine_info["profile"]["optimization_settings"]

    with top_cols[1]:
        conflict_policy = st.selectbox(
            "Conflict policy",
            options=list(CONFLICT_POLICY_LABELS.keys()),
            format_func=lambda value: CONFLICT_POLICY_LABELS[value],
            index=0,
            key="kokoro_conflict_policy",
        )

    selected_languages = []
    for lang in supported_languages:
        if st.session_state.get(f"lang_select_{lang}", lang in st.session_state.language_settings):
            selected_languages.append(lang)

    for lang in selected_languages:
        if lang not in st.session_state.language_settings:
            lang_voices = voices_by_language.get(lang, [])
            default_voice = lang_voices[0]["id"] if lang_voices else list(voice_options.keys())[0]
            st.session_state.language_settings[lang] = {
                "voice": default_voice,
                "speed": 1.0,
                "normalize": True,
            }
    for lang in list(st.session_state.language_settings.keys()):
        if lang not in selected_languages:
            del st.session_state.language_settings[lang]

    inventory = build_selected_language_inventory(selected_languages, current_audio_format, conflict_policy)
    top_summary = build_audio_top_summary(
        machine_info=machine_info,
        runtime_info=runtime_info,
        inventory=inventory,
        conflict_policy_label=CONFLICT_POLICY_LABELS[conflict_policy],
    )

    with top_cols[2]:
        button_label = f"Process {inventory['summary']['ready_count']} Sections"
        run_clicked = st.button(button_label, disabled=inventory["summary"]["section_count"] == 0, use_container_width=True)

    metric_cols = st.columns(4)
    for column, (label, value) in zip(metric_cols, top_summary["metrics"]):
        with column:
            st.metric(label, value)

    st.caption(
        f"Machine: {top_summary['machine']} | Mode: {top_summary['mode']} | "
        f"Kokoro runtime: {runtime_info['runtime_mode'].upper()} | Conflict policy: {top_summary['conflict_policy']}"
    )
    st.caption(top_summary["runtime_message"])

    st.subheader("Settings")
    settings_left, settings_right = st.columns([1, 1])
    with settings_left:
        st.write("**Languages**")
        language_cols = st.columns(3)
        for i, lang in enumerate(supported_languages):
            with language_cols[i % 3]:
                st.checkbox(
                    lang,
                    value=lang in st.session_state.language_settings,
                    key=f"lang_select_{lang}",
                )

        audio_format = st.selectbox(
            "Audio format",
            options=["mp3", "wav"],
            index=0 if current_audio_format == "mp3" else 1,
            key="audio_format",
        )
        generate_timestamps = st.checkbox("Generate word timestamps", value=st.session_state.get("generate_timestamps", False), key="generate_timestamps")
        save_timestamps = False
        if generate_timestamps:
            save_timestamps = st.checkbox("Save timestamps to JSON", value=st.session_state.get("save_timestamps", True), key="save_timestamps")

    with settings_right:
        st.write("**Per-language settings**")
        if st.session_state.language_settings:
            for language, settings in list(st.session_state.language_settings.items()):
                with st.expander(f"{language} Settings", expanded=False):
                    language_voice_options = {voice["id"]: f"{voice['name']} ({voice['gender']})" for voice in voices_by_language.get(language, [])}
                    if not language_voice_options:
                        language_voice_options = voice_options
                    voice_options_list = list(language_voice_options.keys())
                    selected_index = voice_options_list.index(settings["voice"]) if settings["voice"] in voice_options_list else 0

                    voice = st.selectbox(
                        "Voice",
                        options=voice_options_list,
                        format_func=lambda x: language_voice_options[x],
                        index=selected_index,
                        key=f"voice_{language}",
                    )
                    st.session_state.language_settings[language]["voice"] = voice

                    speed = st.slider(
                        "Speed",
                        min_value=0.5,
                        max_value=2.0,
                        value=settings["speed"],
                        step=0.1,
                        key=f"speed_{language}",
                    )
                    st.session_state.language_settings[language]["speed"] = speed

                    normalize = st.checkbox(
                        "Normalize Text",
                        value=settings["normalize"],
                        key=f"normalize_{language}",
                    )
                    st.session_state.language_settings[language]["normalize"] = normalize
        else:
            st.info("Select at least one language to configure per-language voice settings.")

    with st.expander("Technical Details", expanded=False):
        st.write(f"Host profile: {machine_info['machine_id']}")
        st.write(f"Match source: {machine_info['match_source']}")
        st.write(f"Max languages: {host_settings['max_languages']}")
        st.write(f"Max sections per batch: {host_settings['max_sections_per_batch']}")
        st.write(f"Request timeout (sec): {host_settings['request_timeout_sec']}")
        if machine_info["match_reasons"]:
            st.write("Match reasons:")
            for reason in machine_info["match_reasons"]:
                st.write(f"• {reason}")

    with st.expander("Help", expanded=False):
        st.write("The page generates transcript and summary audio for the selected languages using the local Kokoro API.")
        st.write("Default conflict behavior is safe for unattended overnight runs.")

    if run_clicked:
        enabled_languages = list(st.session_state.language_settings.keys())
        if not enabled_languages:
            st.error("No languages selected. Please select at least one language.")
            return

        main_progress_bar = st.progress(0)
        main_status = st.empty()
        language_status_container = st.container()
        results_container = st.container()

        all_language_results: Dict[str, List[Dict[str, Any]]] = {}
        total_sections = max(1, inventory["summary"]["section_count"])
        processed_sections = 0
        overall_start_time = time.time()

        for language in enabled_languages:
            lang_settings = st.session_state.language_settings[language]
            language_files = find_language_section_files(language=language)
            language_inventory = build_audio_inventory(language_files, language, audio_format, conflict_policy)
            language_results: List[Dict[str, Any]] = []
            language_total = max(1, language_inventory["summary"]["section_count"])
            language_processed = 0
            language_start = time.time()

            with language_status_container:
                st.subheader(f"Processing {language}")
                language_progress = st.progress(0)
                language_status = st.empty()

            for course, lectures in language_files.items():
                for lecture, lecture_data in lectures.items():
                    language_status.info(f"Processing {course} - {lecture}")
                    lecture_base_dir = lecture_data["base_dir"]
                    transcript_audio_dir = os.path.join(lecture_base_dir, f"{language} audio")
                    summary_audio_dir = os.path.join(lecture_base_dir, f"{language} Summary audio")
                    os.makedirs(transcript_audio_dir, exist_ok=True)
                    os.makedirs(summary_audio_dir, exist_ok=True)

                    if lecture_data["transcript"]["section_files"]:
                        transcript_results = generate_tts_for_sections(
                            section_files=lecture_data["transcript"]["section_files"],
                            voice=lang_settings["voice"],
                            model="kokoro",
                            output_dir=transcript_audio_dir,
                            response_format=audio_format,
                            speed=lang_settings["speed"],
                            normalize_text=lang_settings["normalize"],
                            enable_timestamps=generate_timestamps,
                            save_timestamps=save_timestamps,
                            conflict_policy=conflict_policy,
                            request_timeout_sec=host_settings["request_timeout_sec"],
                            max_sections_per_batch=host_settings["max_sections_per_batch"],
                        )
                        language_results.extend(transcript_results)
                        language_processed += len(transcript_results)
                        processed_sections += len(transcript_results)

                    if lecture_data["summary"]["section_files"]:
                        summary_results = generate_tts_for_sections(
                            section_files=lecture_data["summary"]["section_files"],
                            voice=lang_settings["voice"],
                            model="kokoro",
                            output_dir=summary_audio_dir,
                            response_format=audio_format,
                            speed=lang_settings["speed"],
                            normalize_text=lang_settings["normalize"],
                            enable_timestamps=generate_timestamps,
                            save_timestamps=save_timestamps,
                            conflict_policy=conflict_policy,
                            request_timeout_sec=host_settings["request_timeout_sec"],
                            max_sections_per_batch=host_settings["max_sections_per_batch"],
                        )
                        language_results.extend(summary_results)
                        language_processed += len(summary_results)
                        processed_sections += len(summary_results)

                    language_progress.progress(language_processed / language_total)
                    main_progress_bar.progress(processed_sections / total_sections)

                    elapsed_language_time = time.time() - language_start
                    if language_processed > 0:
                        sections_per_second = language_processed / elapsed_language_time
                        remaining_sections = language_total - language_processed
                        eta_seconds = remaining_sections / sections_per_second if sections_per_second > 0 else 0
                        minutes, seconds = divmod(int(eta_seconds), 60)
                        language_status.text(f"Progress: {language_processed}/{language_total} sections. ETA: {minutes}m {seconds}s")

                    elapsed_overall = time.time() - overall_start_time
                    if processed_sections > 0:
                        sections_per_second = processed_sections / elapsed_overall
                        remaining = total_sections - processed_sections
                        eta_seconds = remaining / sections_per_second if sections_per_second > 0 else 0
                        eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                        main_status.text(f"Overall progress: {processed_sections}/{total_sections} sections. ETA: {eta_minutes}m {eta_seconds}s")

            language_progress.progress(1.0)
            language_status.success(f"{language} processing complete: {language_processed} sections handled")
            all_language_results[language] = language_results

        main_progress_bar.progress(1.0)
        main_status.success(f"All {len(enabled_languages)} languages handled successfully")

        with results_container:
            st.subheader("Results")
            total_files = sum(len(results) for results in all_language_results.values())
            total_processed = sum(sum(1 for r in results if r["status"] == "processed") for results in all_language_results.values())
            total_skipped = sum(sum(1 for r in results if r["status"] in {"skipped", "reported"}) for results in all_language_results.values())
            total_failed = sum(sum(1 for r in results if r["status"] == "failed") for results in all_language_results.values())

            result_cols = st.columns(4)
            result_cols[0].metric("Processed", total_processed)
            result_cols[1].metric("Skipped / Reported", total_skipped)
            result_cols[2].metric("Failed", total_failed)
            result_cols[3].metric("Files handled", total_files)

            for language, results in all_language_results.items():
                with st.expander(f"{language} Results"):
                    for result in results:
                        status_icon = "✅" if result["status"] == "processed" else "⏭️" if result["status"] in {"skipped", "reported"} else "❌"
                        file_name = os.path.basename(result["file"])
                        st.write(f"{status_icon} {file_name}: {result['message']}")


if __name__ == "__main__":
    main()
