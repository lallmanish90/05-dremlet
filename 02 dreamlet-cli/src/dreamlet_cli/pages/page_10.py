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

from dreamlet_cli.compat import st
import os
import re
import time
import glob
import platform
import subprocess
import tempfile
import gc
import psutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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

MACHINE_PROFILES = {
    "macbook_m3_pro": {
        "name": "MacBook Pro M3 Pro (18GB)",
        "gpu_acceleration": {
            "optimization_settings": {
                "max_threads": 8,
                "batch_size": 6,
                "memory_limit_gb": 14,
            }
        },
    },
    "windows_i5_rtx3050": {
        "name": "Acer Windows laptop (i5-12450H + RTX 3050)",
        "gpu_acceleration": {
            "optimization_settings": {
                "max_threads": 6,
                "batch_size": 4,
                "memory_limit_gb": 12,
            }
        },
    },
    "generic": {
        "name": "Generic fallback profile",
        "gpu_acceleration": {
            "optimization_settings": {
                "max_threads": 4,
                "batch_size": 2,
                "memory_limit_gb": 6,
            }
        },
    },
}

class BalancedMachineConfig:
    """Load and apply balanced machine configurations"""
    
    def __init__(self):
        self.config = self.get_fallback_config()
        self.performance_monitor = SystemPerformanceMonitor(self.get_memory_limit())
    
    def get_fallback_config(self) -> Dict:
        """Embedded machine configuration for the two supported machines"""
        return {"laptop_profiles": MACHINE_PROFILES}
    
    def detect_current_machine(self) -> str:
        """Detect current machine profile"""
        system = platform.system()
        machine = platform.machine()
        
        if system == "Darwin" and "arm" in machine.lower():
            return "macbook_m3_pro"
        elif system == "Windows":
            return "windows_i5_rtx3050"
        else:
            return "generic"

    def get_profile_name(self) -> str:
        machine_id = self.detect_current_machine()
        profiles = self.config.get("laptop_profiles", {})
        return profiles.get(machine_id, profiles["generic"]).get("name", machine_id)
    
    def get_base_optimization_settings(self) -> Dict:
        """Get base optimization settings for current machine"""
        machine_id = self.detect_current_machine()
        profiles = self.config.get("laptop_profiles", {})
        
        if machine_id in profiles:
            return profiles[machine_id]["gpu_acceleration"]["optimization_settings"]
        else:
            return {
                "max_threads": 4,
                "batch_size": 2,
                "memory_limit_gb": 6
            }
    
    def get_adaptive_optimization_settings(self) -> Dict:
        """Get adaptive optimization settings based on current system state"""
        base_settings = self.get_base_optimization_settings()
        return self.performance_monitor.get_adaptive_settings(base_settings)
    
    def get_memory_limit(self) -> float:
        """Get memory limit for current machine"""
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

def generate_output_path(lecture_path: str, language: str = "English") -> str:
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
    output_file = os.path.join(output_dir_path, f"{lecture_name}.mp4")

    return output_file

def detect_hardware_acceleration() -> Tuple[str, str, Dict]:
    """Detect available hardware acceleration and capabilities"""
    system = platform.system()
    machine = platform.machine()

    encoder = 'libx264'
    decoder = None
    capabilities = {
        "hardware_encoding": False,
        "hardware_decoding": False,
        "performance_tier": "basic"
    }

    try:
        encoders_output = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except Exception:
        encoders_output = ""

    if system == 'Windows' and 'h264_nvenc' in encoders_output:
        encoder = 'h264_nvenc'
        decoder = 'cuda'
        capabilities.update({
            "hardware_encoding": True,
            "hardware_decoding": True,
            "performance_tier": "high"
        })
    elif system == 'Darwin' and 'arm' in machine.lower():
        encoder = 'h264_videotoolbox'
        decoder = 'videotoolbox'
        capabilities.update({
            "hardware_encoding": True,
            "hardware_decoding": True,
            "performance_tier": "high"
        })
    elif system == 'Linux':
        if 'h264_nvenc' in encoders_output:
            encoder = 'h264_nvenc'
            decoder = 'cuda'
            capabilities.update({
                "hardware_encoding": True,
                "hardware_decoding": True,
                "performance_tier": "high"
            })
        elif 'h264_qsv' in encoders_output:
            encoder = 'h264_qsv'
            decoder = 'qsv'
            capabilities.update({
                "hardware_encoding": True,
                "hardware_decoding": True,
                "performance_tier": "medium"
            })
        elif 'h264_vaapi' in encoders_output:
            encoder = 'h264_vaapi'
            decoder = 'vaapi'
            capabilities.update({
                "hardware_encoding": True,
                "hardware_decoding": True,
                "performance_tier": "medium"
            })
    
    return encoder, decoder, capabilities

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
        self.encoder, self.decoder, self.capabilities = detect_hardware_acceleration()
        
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

def generate_mp4_for_lecture(lecture_data: Dict, fps: int, language: str = "English", summary: bool = False, force_create: bool = False, config: BalancedMachineConfig = None) -> Dict:
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

        output_path = generate_output_path(lecture_path, language)

        if summary:
            output_dir = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}(summary){ext}"
            output_path = os.path.join(output_dir, new_filename)

        if not force_create and os.path.exists(output_path):
            result["status"] = "skipped"
            result["message"] = "MP4 file already exists (use 'Force Create MP4s' to recreate)"
            result["output_path"] = output_path
            return result

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
    st.title("MP4 GPU - Final")
    st.write("Single final MP4 page tuned for your MacBook Pro M3 Pro and Windows RTX 3050 laptop.")

    # Load machine configuration
    config = BalancedMachineConfig()
    adaptive_settings = config.get_adaptive_optimization_settings()
    
    # Display system metrics and optimization info
    with st.expander("System Profile & Optimization Settings"):
        metrics = config.performance_monitor.get_system_metrics()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("System Metrics")
            st.json({
                "Machine Profile": config.get_profile_name(),
                "Profile ID": config.detect_current_machine(),
                "Memory Usage (GB)": round(metrics["memory_usage_gb"], 2),
                "Memory Available (GB)": round(metrics["memory_available_gb"], 2),
                "Memory Usage (%)": round(metrics["memory_percent"], 1),
                "CPU Usage (%)": round(metrics["cpu_percent"], 1),
                "CPU Cores": metrics["cpu_count"]
            })
        
        with col2:
            st.subheader("Adaptive Settings")
            st.json({
                "Quality Preset": adaptive_settings.get("quality_preset", "balanced"),
                "Processing Mode": adaptive_settings.get("processing_mode", "balanced"),
                "Batch Size": adaptive_settings.get("batch_size", 4),
                "Max Threads": adaptive_settings.get("max_threads", 4),
                "Memory Limit (GB)": adaptive_settings.get("memory_limit_gb", 8)
            })

    ensure_directory_exists(INPUT_DIR)
    ensure_directory_exists(OUTPUT_DIR)

    organized_data = find_processed_lectures()

    if not organized_data:
        st.warning("No lectures with matching image and audio files found.")
        return

    # Hardware acceleration info
    encoder, decoder, capabilities = detect_hardware_acceleration()
    st.header("Hardware Acceleration")
    
    if capabilities["hardware_encoding"]:
        st.success(f"✅ Hardware acceleration detected: Using {encoder} for video encoding")
        st.info(f"🎯 Performance Tier: {capabilities['performance_tier'].title()}")
        if decoder:
            st.info(f"🔍 Using {decoder} hardware acceleration for decoding")
        if config.detect_current_machine() == "windows_i5_rtx3050":
            st.info("🌙 Recommended for overnight bulk jobs on the RTX laptop.")
    else:
        st.info("ℹ️ No hardware acceleration detected. Using CPU encoding (libx264)")

    # Language selection
    st.header("Video Settings")
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
    selected_language = st.selectbox("Select Language for MP4 Generation", sorted_languages, index=sorted_languages.index(default_language) if default_language else 0)

    fps = 3
    st.info(f"Using frame rate: {fps} FPS with adaptive quality/performance tuning.")

    # Lecture selection
    st.header("Select Lectures for MP4 Generation")
    
    selected_lectures = {}
    
    # Quick selection interface
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✓ Select All"):
            st.session_state.select_all = True
            st.rerun()
    with col2:
        if st.button("✗ Unselect All"):
            st.session_state.select_all = False
            st.rerun()

    select_all = st.session_state.get('select_all', False)

    # Course selection
    for subject in organized_data:
        for course in organized_data[subject]:
            with st.expander(f"Course: {course}"):
                all_in_course = st.checkbox(f"Select all in {course}", key=f"all_{subject}_{course}", value=select_all)
                
                for section in organized_data[subject][course]:
                    for lecture in organized_data[subject][course][section]:
                        lecture_data = organized_data[subject][course][section][lecture]
                        
                        has_language = selected_language in lecture_data.get("languages", [])
                        if selected_language in lecture_data.get("language_data", {}):
                            lang_data = lecture_data["language_data"][selected_language]
                            count_match = lang_data["count_match"]
                        else:
                            count_match = False

                        if all_in_course and has_language and count_match:
                            selected_lectures[(subject, course, section, lecture)] = lecture_data
                        elif not all_in_course:
                            selected = st.checkbox(
                                f"{lecture}: {lecture_data.get('audio_count', 0)} audio, {lecture_data.get('image_count', 0)} images",
                                key=f"{subject}_{course}_{section}_{lecture}_{selected_language}",
                                disabled=not (has_language and count_match)
                            )
                            if selected:
                                selected_lectures[(subject, course, section, lecture)] = lecture_data

    # Generate MP4s
    st.header("Generate MP4s")
    
    col1, col2 = st.columns(2)
    with col1:
        generate_regular = st.checkbox("Generate Regular Videos", value=True)
    with col2:
        generate_summary = st.checkbox("Generate Summary Videos", value=True)

    force_create = st.checkbox("Force Create MP4s", value=False)

    if st.button("Generate MP4s", disabled=len(selected_lectures) == 0 or not (generate_regular or generate_summary)):
        if not selected_lectures:
            st.warning("No lectures selected for MP4 generation.")
            return

        if not (generate_regular or generate_summary):
            st.warning("Please select at least one video type to generate.")
            return

        # Process with progress tracking and adaptive monitoring
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_text = st.empty()
        results_container = st.container()

        results = []
        start_time = time.time()
        total_videos = len(selected_lectures) * ((1 if generate_regular else 0) + (1 if generate_summary else 0))
        video_count = 0

        for _, ((subject, course, section, lecture), lecture_data) in enumerate(selected_lectures.items()):
            # Update adaptive settings based on current system state
            config.performance_monitor = SystemPerformanceMonitor(config.get_memory_limit())
            current_settings = config.get_adaptive_optimization_settings()
            
            if generate_regular:
                status_text.info(f"Processing {video_count+1}/{total_videos}: {lecture} (Regular)")
                
                # Update system metrics display
                metrics = config.performance_monitor.get_system_metrics()
                metrics_text.info(f"CPU: {metrics['cpu_percent']:.1f}% | Memory: {metrics['memory_usage_gb']:.1f}GB | Mode: {current_settings['processing_mode']}")
                
                result = generate_mp4_for_lecture(lecture_data, fps, selected_language, summary=False, force_create=force_create, config=config)
                result.update({"subject": subject, "course": course, "section": section, "lecture": lecture, "type": "Regular"})
                results.append(result)
                
                video_count += 1
                progress_bar.progress(video_count / total_videos)

            if generate_summary:
                status_text.info(f"Processing {video_count+1}/{total_videos}: {lecture} (Summary)")
                
                # Update system metrics display
                metrics = config.performance_monitor.get_system_metrics()
                metrics_text.info(f"CPU: {metrics['cpu_percent']:.1f}% | Memory: {metrics['memory_usage_gb']:.1f}GB | Mode: {current_settings['processing_mode']}")
                
                result = generate_mp4_for_lecture(lecture_data, fps, selected_language, summary=True, force_create=force_create, config=config)
                result.update({"subject": subject, "course": course, "section": section, "lecture": lecture, "type": "Summary"})
                results.append(result)
                
                video_count += 1
                progress_bar.progress(video_count / total_videos)

        # Display results
        metrics_text.empty()
        status_text.success(f"Processed {video_count} videos for {len(selected_lectures)} lectures")
        
        with results_container:
            st.subheader("Processing Results")
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = sum(1 for r in results if r["status"] == "error")
            skipped_count = sum(1 for r in results if r["status"] == "skipped")

            st.write(f"✅ Successfully generated: {success_count}")
            st.write(f"⏭️ Skipped (already exists): {skipped_count}")
            st.write(f"❌ Errors: {error_count}")

            for result in results:
                status_icon = "✅" if result["status"] == "success" else "⏭️" if result["status"] == "skipped" else "❌"
                video_type = result.get("type", "")
                display_name = f"{result['subject']} - {result['course']} - {result['section']} - {result['lecture']} ({video_type})"

                with st.expander(f"{status_icon} {display_name}"):
                    st.write(f"**Status:** {result['status']}")
                    st.write(f"**Type:** {video_type}")
                    st.write(f"**Message:** {result['message']}")
                    if result["status"] in ["success", "skipped"]:
                        st.write(f"**Output:** {result['output_path']}")

if __name__ == "__main__":
    main()
