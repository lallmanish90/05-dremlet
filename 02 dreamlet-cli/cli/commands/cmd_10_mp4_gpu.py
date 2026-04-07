"""
CLI Command: MP4 GPU Video Generation (Page 10)

Converts the Streamlit page 10_mp4_GPU.py to CLI interface
while maintaining 100% functional parity.

This command generates MP4 videos from images and audio files using hardware 
acceleration when available, supporting multiple languages and both regular 
and summary video generation.
"""

import click
import os
import sys
import re
import time
import glob
import tempfile
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2
from PIL import Image
import ffmpeg

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress
from cli.reports import generate_report
from cli.config import load_config
from rich.console import Console
from rich.table import Table

console = Console()

# ============================================================================
# UTILITY FUNCTIONS (copied from original page)
# ============================================================================

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def find_language_folders(lecture_dir: str) -> List[str]:
    """
    Find all language folders in a lecture directory (like 'English', 'Spanish', etc.)
    
    Args:
        lecture_dir: Path to lecture directory
    
    Returns:
        List of language names
    """
    languages = []

    for folder in os.listdir(lecture_dir):
        # Check for folders ending with 'audio' or 'image'
        if folder.endswith(" audio") or folder.endswith(" image"):
            # Extract language name (everything before ' audio' or ' image')
            lang = folder.split(" ")[0]
            if lang and lang not in languages:
                languages.append(lang)

    return languages
def find_image_files(lecture_dir: str, language: str = "English") -> List[str]:
    """
    Find all image files in a lecture directory for a specific language
    If language-specific images are not found, fall back to English images
    
    Args:
        lecture_dir: Path to lecture directory
        language: Language to find images for (default: English)
    
    Returns:
        List of sorted image file paths
    """
    # Look in the "<Language> image" folder
    lang_images_dir = os.path.join(lecture_dir, f"{language} image")
    if os.path.exists(lang_images_dir) and os.path.isdir(lang_images_dir):
        image_files = get_sorted_files(lang_images_dir,
                                      file_type="image",
                                      full_path=True)
        if image_files:
            return image_files
    
    # If not English and no images found, fall back to English images
    if language != "English":
        english_images_dir = os.path.join(lecture_dir, "English image")
        if os.path.exists(english_images_dir) and os.path.isdir(english_images_dir):
            image_files = get_sorted_files(english_images_dir,
                                          file_type="image",
                                          full_path=True)
            if image_files:
                return image_files

    # Return empty list if no image folder or no files found
    return []

def find_audio_files(lecture_dir: str,
                    language: str = "English",
                    summary: bool = False) -> List[str]:
    """
    Find all audio files in a lecture directory for a specific language
    
    Args:
        lecture_dir: Path to lecture directory
        language: Language to find audio for (default: English)
        summary: Whether to find summary audio files (default: False)
    
    Returns:
        List of sorted audio file paths
    """
    # Look in the "<Language> audio" or "<Language> Summary audio" folder
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_dir, folder_name)
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        audio_files = get_sorted_files(lang_audio_dir,
                                      file_type="audio",
                                      full_path=True)
        if audio_files:
            return audio_files

    # Return empty list if no audio folder or no files found
    return []

def get_sorted_files(directory: str,
                    file_type: str,
                    full_path: bool = False) -> List[str]:
    """
    Get sorted list of files of a specific type
    
    Args:
        directory: Directory to search in
        file_type: Type of files to search for ('image' or 'audio')
        full_path: Whether to return full file paths or just filenames
        
    Returns:
        List of sorted filenames or file paths
    """
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
    else:
        raise ValueError("Invalid file_type. Use 'image' or 'audio'.")

    if not os.path.exists(directory):
        return []

    # Get all files with matching extensions
    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and f.lower().endswith(extensions)
    ]

    # Sort numerically by the number in the filename
    sorted_files = sorted(files,
                         key=lambda f: int(os.path.splitext(f)[0])
                         if os.path.splitext(f)[0].isdigit() else 999)

    # Return full paths if requested
    if full_path:
        return [os.path.join(directory, f) for f in sorted_files]
    else:
        return sorted_files
def generate_output_path(lecture_path: str, language: str = "English") -> str:
    """
    Generate the output path for the MP4 file
    
    Args:
        lecture_path: Path to the lecture directory
        language: Language for the MP4 file (default: English)
        
    Returns:
        Output path for the MP4 file
    """
    # Get the relative path from the input directory
    input_dir = os.path.join(os.getcwd(), "input")
    rel_path = os.path.relpath(lecture_path, input_dir)

    # Split the path into components
    path_components = rel_path.split(os.sep)

    # Get the lecture name (last component)
    lecture_name = path_components[-1]

    # For the output structure, we need to correctly identify the course and section
    course = None
    section = None

    # Based on the screenshot: input/3 Course/Section 01/Lecture 01
    # Should generate: output/<Language>/3 Course/Section 01/Lecture 01.mp4

    # Extract components - we care about finding the course and section names
    # from the input path, regardless of other path components
    if len(path_components) >= 3:  # At least course/section/lecture
        # The course is typically 2 levels up from the lecture (-3)
        course = path_components[-3]
        # The section is typically 1 level up from the lecture (-2)
        section = path_components[-2]
    elif len(path_components) == 2:  # Just course/lecture
        course = path_components[0]
        section = "Main Section"  # Default section name
    else:  # Just lecture
        course = "Main Course"  # Default course name
        section = "Main Section"  # Default section name

    # Create the output directory path with language-specific folder
    output_dir = os.path.join(os.getcwd(), "output")
    output_dir_path = os.path.join(output_dir, language, course, section)

    # Create the output directory
    ensure_directory_exists(output_dir_path)

    # Generate the output file path
    output_file = os.path.join(output_dir_path, f"{lecture_name}.mp4")

    return output_file

def upscale_image(
    image_path: str, target_resolution: Tuple[int, int] = (3840, 2160)
) -> np.ndarray:
    """
    Load and upscale an image to target resolution
    
    Args:
        image_path: Path to the image file
        target_resolution: Target resolution (width, height)
        
    Returns:
        Upscaled image as numpy array
    """
    # Load the image using PIL for high-quality upscaling
    img = Image.open(image_path)

    # Resize the image to 4K using high-quality Lanczos resampling
    img_resized = img.resize(target_resolution, Image.LANCZOS)

    # Convert to numpy array for OpenCV compatibility
    img_array = np.array(img_resized)

    # Convert to RGB if the image is in RGBA mode
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

    return img_array

def detect_hardware_acceleration() -> Tuple[str, str]:
    """
    Detect available hardware acceleration for video encoding/decoding
    
    Returns:
        Tuple of (encoder, decoder) names
    """
    system = platform.system()
    machine = platform.machine()

    # Default to CPU encoding/decoding
    encoder = 'libx264'
    decoder = None

    if system == 'Windows':
        # Check if NVIDIA GPU with NVENC is available
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'h264_nvenc' in result.stdout:
            encoder = 'h264_nvenc'
            decoder = 'cuda'
        
    elif system == 'Darwin' and 'arm' in machine.lower():
        # Apple Silicon (M1, M2, etc.)
        encoder = 'h264_videotoolbox'
        decoder = 'videotoolbox'
        
    elif system == 'Linux':
        # Check for NVIDIA on Linux
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'h264_nvenc' in result.stdout:
            encoder = 'h264_nvenc'
            decoder = 'cuda'
        # Check for Intel QuickSync
        elif 'h264_qsv' in result.stdout:
            encoder = 'h264_qsv'
            decoder = 'qsv'
        # Check for VAAPI
        elif 'h264_vaapi' in result.stdout:
            encoder = 'h264_vaapi'
            decoder = 'vaapi'
    
    return encoder, decoder
def create_video_from_images_and_audio(
    image_files: List[str],
    audio_files: List[str],
    output_path: str,
    fps: int = 3
) -> Tuple[bool, str]:
    """
    Generate an MP4 video from images and audio files using hardware acceleration
    
    Args:
        image_files: List of image file paths
        audio_files: List of audio file paths
        output_path: Path to save the output video
        fps: Frames per second (default: 3)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Detect hardware acceleration capabilities
        encoder, decoder = detect_hardware_acceleration()
        
        # Create a temporary directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare output video file for temporary segments
            temp_video = os.path.join(temp_dir, "temp_video.mp4")
            temp_audio = os.path.join(temp_dir, "temp_audio.wav")
            segments_dir = os.path.join(temp_dir, "segments")
            os.makedirs(segments_dir, exist_ok=True)

            # Create temporary video segments
            segment_files = []

            # Process each image and corresponding audio
            for i, (img_file, audio_file) in enumerate(zip(image_files, audio_files)):
                # Upscale image to 4K
                img = upscale_image(img_file)
                upscaled_img_path = os.path.join(temp_dir, f"upscaled_{i:03d}.png")
                cv2.imwrite(upscaled_img_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

                # Get audio duration
                duration_cmd = [
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of",
                    "default=noprint_wrappers=1:nokey=1", audio_file
                ]

                duration_result = subprocess.run(duration_cmd,
                                                capture_output=True,
                                                text=True,
                                                check=True)

                duration = float(duration_result.stdout.strip())

                # Create segment with image and audio
                segment_path = os.path.join(segments_dir, f"segment_{i:03d}.mp4")
                segment_files.append(segment_path)

                # Build the segment command with hardware acceleration
                segment_cmd = ['ffmpeg', '-y']
                
                # Add hardware acceleration if available
                if decoder:
                    if decoder == 'cuda':
                        segment_cmd += ['-hwaccel', 'cuda']
                    elif decoder == 'videotoolbox':
                        segment_cmd += ['-hwaccel', 'videotoolbox']
                    elif decoder == 'qsv':
                        segment_cmd += ['-hwaccel', 'qsv']
                    elif decoder == 'vaapi':
                        segment_cmd += ['-hwaccel', 'vaapi', '-vaapi_device', '/dev/dri/renderD128']
                
                # Add input files and output parameters
                segment_cmd += [
                    '-loop', '1', 
                    '-framerate', str(fps), 
                    '-i', upscaled_img_path, 
                    '-i', audio_file,
                    '-c:v', encoder
                ]
                
                # Add encoder-specific options
                if encoder == 'h264_nvenc':
                    segment_cmd += ['-preset', 'p5', '-rc', 'vbr', '-cq', '23', '-b:v', '5M']
                elif encoder == 'h264_videotoolbox':
                    segment_cmd += ['-b:v', '5M']  # VideoToolbox doesn't support CRF
                elif encoder == 'h264_qsv':
                    segment_cmd += ['-preset', 'medium', '-b:v', '5M']
                elif encoder == 'h264_vaapi':
                    segment_cmd += ['-quality', 'good', '-b:v', '5M']
                else:  # libx264 or other software encoders
                    segment_cmd += ['-tune', 'stillimage', '-preset', 'medium', '-crf', '23']
                
                # Add common parameters
                segment_cmd += [
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-pix_fmt', 'yuv420p',
                    '-shortest',
                    '-t', str(duration),
                    segment_path
                ]

                subprocess.run(segment_cmd, check=True, capture_output=True)

            # Create a file list for concatenation
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")

            # Concatenate all segments (hardware acceleration not important here since we're just copying streams)
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                concat_file, "-c", "copy", temp_video
            ]

            subprocess.run(concat_cmd, check=True, capture_output=True)

            # Final encoding with hardware acceleration
            final_cmd = ['ffmpeg', '-y']
            
            # Add hardware acceleration if available
            if decoder:
                if decoder == 'cuda':
                    final_cmd += ['-hwaccel', 'cuda']
                elif decoder == 'videotoolbox':
                    final_cmd += ['-hwaccel', 'videotoolbox']
                elif decoder == 'qsv':
                    final_cmd += ['-hwaccel', 'qsv']
                elif decoder == 'vaapi':
                    final_cmd += ['-hwaccel', 'vaapi', '-vaapi_device', '/dev/dri/renderD128']
            
            # Add input file
            final_cmd += ['-i', temp_video, '-c:v', encoder]
            
            # Add encoder-specific options
            if encoder == 'h264_nvenc':
                final_cmd += ['-preset', 'p5', '-rc', 'vbr', '-cq', '23', '-b:v', '5M']
            elif encoder == 'h264_videotoolbox':
                final_cmd += ['-b:v', '5M']  # VideoToolbox doesn't support CRF
            elif encoder == 'h264_qsv':
                final_cmd += ['-preset', 'medium', '-b:v', '5M']
            elif encoder == 'h264_vaapi':
                final_cmd += ['-quality', 'good', '-b:v', '5M']
            else:  # libx264 or other software encoders
                final_cmd += ['-preset', 'medium', '-crf', '22']
            
            # Add common parameters
            final_cmd += [
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', 'faststart',
                output_path
            ]

            subprocess.run(final_cmd, check=True, capture_output=True)

            return True, f"Video successfully generated at {output_path} using {encoder} encoder"

    except subprocess.CalledProcessError as e:
        return False, f"FFmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
    except Exception as e:
        return False, f"Error generating video: {str(e)}"
def find_processed_lectures() -> Dict[str, Dict[str, Dict]]:
    """
    Find all lectures with audio and image files ready for MP4 generation
    
    Returns:
        Nested dictionary of subject -> course -> section -> lecture -> data
    """
    input_dir = os.path.join(os.getcwd(), "input")
    
    if not os.path.exists(input_dir):
        return {}

    # Dictionary to store all found lectures
    organized_data = {}

    # Recursively walk through the input directory
    for root, dirs, files in os.walk(input_dir):
        # Skip utility folders
        if any(util_folder in root for util_folder in
              ["all_pptx", "all_slides", "all_transcripts"]):
            continue

        # Skip non-lecture folders (must contain at least English language folders)
        has_english_images = "English image" in dirs
        has_english_audio = "English audio" in dirs

        # Skip if doesn't have both English image and English audio folders
        if not (has_english_images and has_english_audio):
            continue

        # Get the lecture folder path (the current root)
        lecture_dir = root

        # Find all available languages in this lecture folder
        languages = find_language_folders(lecture_dir)

        # Find English files as base requirement (for backward compatibility)
        english_image_files = find_image_files(lecture_dir, "English")
        english_audio_files = find_audio_files(lecture_dir, "English")

        # Skip if no English image or audio files found (minimum requirement)
        if not english_image_files or not english_audio_files:
            continue

        # Extract path components for proper organization
        # Remove the input directory prefix to get the relative path
        rel_path = os.path.relpath(lecture_dir, input_dir)
        path_components = rel_path.split(os.sep)

        # The last component is the lecture name
        lecture_name = path_components[-1]

        # Extract subject, course, and section if available
        subject = None
        course = None
        section = None

        # Determine subject, course, and section based on folder hierarchy
        if len(path_components) > 3:  # subject/course/section/lecture
            subject = path_components[0]
            course = path_components[1]
            section = path_components[2]
        elif len(path_components
                ) > 2:  # subject/course/lecture or course/section/lecture
            # Try to determine if the second component is a course or a section
            if any(section_keyword in path_components[1].lower()
                  for section_keyword in ["section", "part", "module"]):
                course = path_components[0]
                section = path_components[1]
            else:
                subject = path_components[0]
                course = path_components[1]
        elif len(path_components) > 1:  # course/lecture
            course = path_components[0]

        # If lecture name doesn't contain "Lecture", try to identify lecture number from folder name
        lecture_match = re.search(r'lecture\s*(\d+)', lecture_name,
                                 re.IGNORECASE)
        if lecture_match:
            lecture_display = f"Lecture {lecture_match.group(1)}"
        else:
            # Check if the name is just a number (e.g., "01", "02")
            number_match = re.match(r'^\s*(\d+)\s*$', lecture_name)
            if number_match:
                lecture_display = f"Lecture {number_match.group(1)}"
            else:
                lecture_display = lecture_name

        # Organize by subject and course
        subject_key = subject if subject else "Main"
        course_key = course if course else "Main Course"
        section_key = section if section else "Main Section"

        # Add entries to the dictionary at appropriate levels
        if subject_key not in organized_data:
            organized_data[subject_key] = {}

        if course_key not in organized_data[subject_key]:
            organized_data[subject_key][course_key] = {}

        if section_key not in organized_data[subject_key][course_key]:
            organized_data[subject_key][course_key][section_key] = {}

        # Build language data
        language_data = {}
        for language in languages:
            # Find regular audio and image files
            image_files = find_image_files(lecture_dir, language)
            audio_files = find_audio_files(lecture_dir,
                                          language,
                                          summary=False)

            # Find summary audio files
            summary_audio_files = find_audio_files(lecture_dir,
                                                  language,
                                                  summary=True)

            # Check if we have both regular and summary audio files
            has_regular_audio = len(audio_files) > 0
            has_summary_audio = len(summary_audio_files) > 0

            # Add data for this language if at least regular files are available
            if image_files and audio_files:
                language_data[language] = {
                    "image_files":
                    image_files,
                    "audio_files":
                    audio_files,
                    "audio_count":
                    len(audio_files),
                    "image_count":
                    len(image_files),
                    "count_match":
                    len(audio_files) == len(image_files),
                    "has_summary_audio":
                    has_summary_audio,
                    "summary_audio_files":
                    summary_audio_files,
                    "summary_audio_count":
                    len(summary_audio_files),
                    "summary_count_match":
                    len(summary_audio_files) == len(image_files)
                }

        # Add lecture data with English as default language
        has_english_summary = "English Summary audio" in dirs
        english_summary_audio_files = find_audio_files(lecture_dir,
                                                      "English",
                                                      summary=True)

        organized_data[subject_key][course_key][section_key][
            lecture_display] = {
                "path":
                lecture_dir,
                "image_files":
                english_image_files,  # Default to English files
                "audio_files":
                english_audio_files,  # Default to English files
                "audio_count":
                len(english_audio_files),
                "image_count":
                len(english_image_files),
                "count_match":
                len(english_audio_files) == len(english_image_files),
                "has_summary_audio":
                has_english_summary,
                "summary_audio_files":
                english_summary_audio_files,
                "summary_audio_count":
                len(english_summary_audio_files),
                "summary_count_match":
                len(english_summary_audio_files) == len(english_image_files),
                "output_name":
                f"{lecture_name}.mp4",
                "languages":
                languages,
                "language_data":
                language_data
            }

    return organized_data
def generate_mp4_for_lecture(lecture_data: Dict,
                            fps: int,
                            language: str = "English",
                            summary: bool = False,
                            force_create: bool = False) -> Dict:
    """
    Generate MP4 for a lecture in the specified language
    
    Args:
        lecture_data: Dictionary with lecture data
        fps: Frames per second
        language: Language for the MP4 (default: English)
        summary: Whether to generate a summary video (default: False)
        force_create: Whether to force create the MP4 even if it already exists (default: False)
        
    Returns:
        Dictionary with processing results
    """
    result = {
        "lecture_path": lecture_data["path"],
        "status": "error",
        "message": "",
        "output_path": "",
        "language": language,
        "summary": summary
    }

    try:
        # Get lecture path
        lecture_path = lecture_data["path"]

        # Find language-specific files
        image_files = find_image_files(lecture_path, language)
        audio_files = find_audio_files(lecture_path, language, summary)

        # Check if we have files for this language
        if not image_files:
            result[
                "message"] = f"No {language} image files found for this lecture"
            return result

        if not audio_files:
            audio_type = "Summary audio" if summary else "audio"
            result[
                "message"] = f"No {language} {audio_type} files found for this lecture"
            return result

        # Check if counts match
        if len(image_files) != len(audio_files):
            audio_type = "Summary audio" if summary else "audio"
            result[
                "message"] = f"Count mismatch: {len(image_files)} images, {len(audio_files)} {audio_type} files"
            return result

        # Get the lecture name (last component of path)
        input_dir = os.path.join(os.getcwd(), "input")
        rel_path = os.path.relpath(lecture_path, input_dir)
        path_components = rel_path.split(os.sep)
        lecture_name = path_components[-1]

        # Generate output path with language
        output_path = generate_output_path(lecture_path, language)

        # If summary video, modify the output filename to include "(summary)"
        if summary:
            # Extract directory and filename
            output_dir = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            name, ext = os.path.splitext(filename)

            # Create new filename with "(summary)" suffix
            new_filename = f"{name}(summary){ext}"
            output_path = os.path.join(output_dir, new_filename)

        # Check if MP4 already exists and skip if not forcing recreation
        if not force_create and os.path.exists(output_path):
            result["status"] = "skipped"
            result[
                "message"] = "MP4 file already exists (use 'Force Create MP4s' to recreate)"
            result["output_path"] = output_path
            return result

        # Generate MP4 with hardware acceleration
        success, message = create_video_from_images_and_audio(
            image_files, audio_files, output_path, fps)

        if not success:
            result["message"] = message
            return result

        # Update result
        result["status"] = "success"
        video_type = "summary video" if summary else "video"
        result[
            "message"] = f"Successfully generated {language} {video_type}: {message}"
        result["output_path"] = output_path

        return result
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        return result

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def run_mp4_gpu_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the MP4 GPU processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_10_mp4_gpu')
    
    # Extract settings from config
    languages = page_config.get('languages', ['English'])
    fps = page_config.get('fps', 3)
    generate_regular = page_config.get('generate_regular', True)
    generate_summary = page_config.get('generate_summary', False)
    force_create = page_config.get('force_create', False)
    target_resolution = tuple(page_config.get('target_resolution', [3840, 2160]))
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_lectures": 0, "processed_count": 0, "error_count": 1}
        }
    
    # Ensure output directory exists
    output_dir = config.output_dir
    ensure_directory_exists(output_dir)
    
    console.print(f"[blue]ℹ[/blue] Scanning input directory: {input_dir}")
    console.print(f"[blue]ℹ[/blue] Target languages: {', '.join(languages)}")
    console.print(f"[blue]ℹ[/blue] Frame rate: {fps} FPS")
    console.print(f"[blue]ℹ[/blue] Target resolution: {target_resolution[0]}x{target_resolution[1]}")
    
    # Detect hardware acceleration
    encoder, decoder = detect_hardware_acceleration()
    if encoder != 'libx264':
        console.print(f"[green]✓[/green] Hardware acceleration detected: Using {encoder} for video encoding")
        if decoder:
            console.print(f"[blue]ℹ[/blue] Using {decoder} hardware acceleration for decoding")
    else:
        console.print(f"[blue]ℹ[/blue] No hardware acceleration detected. Using CPU encoding (libx264)")
    
    # Find processed lectures
    console.print(f"[blue]ℹ[/blue] Discovering lectures with audio and image files...")
    organized_data = find_processed_lectures()
    
    if not organized_data:
        error_msg = "No lectures with matching image and audio files found"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_lectures": 0, "processed_count": 0, "error_count": 0}
        }
    
    # Collect all lectures that match the criteria
    selected_lectures = {}
    total_lectures = 0
    
    for subject in organized_data.values():
        for course in subject.values():
            for section in course.values():
                for lecture_name, lecture_data in section.items():
                    total_lectures += 1
                    
                    # Check if any of the target languages are available
                    for language in languages:
                        if language in lecture_data.get("languages", []):
                            # Check if language data exists and has count match
                            if language in lecture_data.get("language_data", {}):
                                lang_data = lecture_data["language_data"][language]
                                if lang_data.get("count_match", False):
                                    key = (subject, course, section, lecture_name, language)
                                    selected_lectures[key] = lecture_data
                                    break
    
    if not selected_lectures:
        error_msg = f"No lectures found with matching audio/image files for languages: {', '.join(languages)}"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_lectures": total_lectures, "processed_count": 0, "error_count": 0}
        }
    
    console.print(f"[green]✓[/green] Found {len(selected_lectures)} lectures ready for MP4 generation")
    
    # Calculate total videos to generate
    total_videos = len(selected_lectures) * (
        (1 if generate_regular else 0) + (1 if generate_summary else 0)
    )
    
    console.print(f"[blue]ℹ[/blue] Will generate {total_videos} videos total")
    
    # Process lectures with progress tracking
    results = []
    start_time = time.time()
    
    with DreamletProgress(description="Generating MP4 videos", total=total_videos) as progress:
        video_count = 0
        
        for (subject, course, section, lecture_name, language), lecture_data in selected_lectures.items():
            
            # Generate regular video if selected
            if generate_regular:
                progress.update(description=f"Processing {lecture_name} ({language}) - Regular")
                
                result = generate_mp4_for_lecture(
                    lecture_data,
                    fps,
                    language,
                    summary=False,
                    force_create=force_create
                )
                
                # Add metadata for reporting
                result.update({
                    "subject": subject,
                    "course": course,
                    "section": section,
                    "lecture": lecture_name,
                    "type": "Regular"
                })
                results.append(result)
                
                video_count += 1
                progress.update(advance=1)
            
            # Generate summary video if selected
            if generate_summary:
                progress.update(description=f"Processing {lecture_name} ({language}) - Summary")
                
                result = generate_mp4_for_lecture(
                    lecture_data,
                    fps,
                    language,
                    summary=True,
                    force_create=force_create
                )
                
                # Add metadata for reporting
                result.update({
                    "subject": subject,
                    "course": course,
                    "section": section,
                    "lecture": lecture_name,
                    "type": "Summary"
                })
                results.append(result)
                
                video_count += 1
                progress.update(advance=1)
    
    # Calculate final statistics
    total_processing_time = time.time() - start_time
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    
    # Determine final status
    if error_count > 0 and success_count == 0:
        final_status = "error"
        status_message = f"MP4 generation failed with {error_count} errors"
    elif error_count > 0:
        final_status = "warning"
        status_message = f"Generated {success_count} MP4s with {error_count} errors, {skipped_count} skipped"
    elif success_count == 0 and skipped_count > 0:
        final_status = "warning"
        status_message = f"All {skipped_count} MP4s already exist (use force_create to regenerate)"
    else:
        final_status = "success"
        status_message = f"Successfully generated {success_count} MP4s, {skipped_count} skipped"
    
    # Show summary
    console.print(f"[green]✓[/green] {status_message}")
    console.print(f"[blue]ℹ[/blue] Total processing time: {total_processing_time:.1f} seconds")
    
    # Display detailed results if verbose
    if ctx_obj.get('verbose', False) and results:
        table = Table(title="MP4 Generation Results")
        table.add_column("Course", style="cyan")
        table.add_column("Lecture", style="magenta")
        table.add_column("Language", style="blue")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="bold")
        table.add_column("Output Path", style="dim")
        
        for result in results[:20]:  # Show first 20 results
            status_style = "green" if result["status"] == "success" else "red" if result["status"] == "error" else "yellow"
            status_text = result["status"].upper()
            
            table.add_row(
                result["course"][:20] + "..." if len(result["course"]) > 20 else result["course"],
                result["lecture"],
                result["language"],
                result["type"],
                f"[{status_style}]{status_text}[/{status_style}]",
                os.path.basename(result.get("output_path", "")) if result.get("output_path") else ""
            )
        
        console.print(table)
        
        if len(results) > 20:
            console.print(f"... and {len(results) - 20} more results")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "output_directory": output_dir,
            "target_languages": languages,
            "fps": fps,
            "target_resolution": f"{target_resolution[0]}x{target_resolution[1]}",
            "hardware_encoder": encoder,
            "hardware_decoder": decoder or "None"
        },
        "statistics": {
            "total_lectures_found": total_lectures,
            "lectures_processed": len(selected_lectures),
            "videos_generated": success_count,
            "videos_skipped": skipped_count,
            "errors": error_count,
            "processing_time": f"{total_processing_time:.1f}s"
        },
        "settings": {
            "generate_regular": generate_regular,
            "generate_summary": generate_summary,
            "force_create": force_create,
            "target_resolution": target_resolution
        },
        "processing_results": [
            {
                "course": result["course"],
                "lecture": result["lecture"],
                "language": result["language"],
                "type": result["type"],
                "status": result["status"],
                "message": result["message"],
                "output_path": result.get("output_path", "")
            }
            for result in results
        ],
        "errors": [result["message"] for result in results if result["status"] == "error"]
    }
    
    # Generate report
    report_path = generate_report("10", "MP4 GPU Video Generation", report_results)
    console.print(f"[blue]ℹ[/blue] Report saved to: {report_path}", style="dim")
    
    report_results["report_path"] = report_path
    return report_results
@click.command()
@click.pass_context
def mp4_gpu(ctx):
    """
    Generate MP4 videos from images and audio using hardware acceleration
    
    This command combines slide images with audio files to create educational 
    videos while using hardware acceleration when available. Supports multiple 
    languages and both regular and summary video generation.
    
    Features:
    - Automatic hardware acceleration detection (NVIDIA, Apple Silicon, Intel)
    - Multi-language support with fallback to English
    - Regular and summary video generation
    - 4K upscaling of images
    - Structured output organization
    
    All settings are configured in config.json under "page_10_mp4_gpu":
    - languages: List of target languages (default: ["English"])
    - fps: Frame rate for videos (default: 3)
    - generate_regular: Generate regular videos (default: true)
    - generate_summary: Generate summary videos (default: false)
    - force_create: Overwrite existing MP4s (default: false)
    - target_resolution: Video resolution (default: [3840, 2160])
    
    Examples:
        dreamlet run 10                    # Generate MP4s with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No videos will be generated[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_10_mp4_gpu')
        languages = page_config.get('languages', ['English'])
        fps = page_config.get('fps', 3)
        generate_regular = page_config.get('generate_regular', True)
        generate_summary = page_config.get('generate_summary', False)
        
        console.print(f"Would generate MP4s for languages: {', '.join(languages)}")
        console.print(f"Would use frame rate: {fps} FPS")
        console.print(f"Would generate regular videos: {generate_regular}")
        console.print(f"Would generate summary videos: {generate_summary}")
        return
    
    # Run the MP4 GPU processing operation
    try:
        results = run_mp4_gpu_processing(ctx.obj)
        
        # Exit with appropriate code based on results
        if results["status"] == "error":
            sys.exit(1)
        elif results["status"] == "warning":
            sys.exit(2)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    mp4_gpu()