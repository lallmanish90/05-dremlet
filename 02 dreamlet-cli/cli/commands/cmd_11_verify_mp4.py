"""
CLI Command: MP4 Verification (Page 11)

Converts the Streamlit page 11_Verify_mp4.py to CLI interface
while maintaining 100% functional parity.

This command verifies MP4 files for completeness and correctness with 
auto-discovery of expected lecture counts and comprehensive validation.
"""

import click
import os
import sys
import re
import glob
import subprocess
import fnmatch
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

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

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def count_mp4_duration(mp4_path: str) -> Tuple[bool, float]:
    """Count the duration of an MP4 file in seconds"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', mp4_path
        ], capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return True, duration
    except Exception:
        return False, 0.0

def find_files(directory: str, pattern: str) -> List[str]:
    """Find all files matching a pattern in a directory (recursively)"""
    result = []
    for root, _, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            result.append(os.path.join(root, filename))
    return result

def extract_lecture_number(path: str) -> Optional[int]:
    """
    Extract lecture number from file path or filename
    
    Args:
        path: File path or filename
        
    Returns:
        Lecture number as integer, or None if not found
    """
    # Try to extract from filename directly
    filename = os.path.basename(path)
    
    # Common patterns for lecture numbers
    patterns = [
        r'lecture[\_\s-]*(\d+)',
        r'lec[\_\s-]*(\d+)', 
        r'^(\d+)[-\s]',
        r'(\d+)\.mp4$',
        r'(\d+)\s*\(',
        r'(\d+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    # Try to extract from parent directory names
    parts = path.split(os.path.sep)
    for part in parts:
        for pattern in patterns:
            match = re.search(pattern, part, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
    
    return None

def count_audio_duration(audio_path: str) -> Tuple[bool, float]:
    """
    Count the duration of an audio file
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Tuple of (success, duration_in_seconds)
    """
    try:
        # Use ffprobe to get duration
        ffprobe_command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        
        result = subprocess.run(
            ffprobe_command, 
            capture_output=True, 
            text=True,
            check=True
        )
        
        duration = float(result.stdout.strip())
        return True, duration
    except subprocess.CalledProcessError:
        return False, 0.0
    except Exception:
        return False, 0.0

def get_all_course_names() -> List[str]:
    """
    Get all course names from the input directory
    
    Returns:
        List of course names
    """
    course_names = []
    input_dir = get_input_directory()
    
    # Get all first-level directories in the input directory (courses)
    if os.path.exists(input_dir):
        for item in os.listdir(input_dir):
            item_path = os.path.join(input_dir, item)
            if os.path.isdir(item_path):
                # First-level directory is considered a course
                course_names.append(item)
    
    return sorted(course_names)

def auto_discover_expected_count(course_name: str, language: str = "English") -> Dict:
    """
    Auto-discover expected lecture count by scanning input directories and output MP4s
    
    Args:
        course_name: Name of the course
        language: Language to check for
        
    Returns:
        Dictionary with discovery results
    """
    input_dir = get_input_directory()
    output_dir = "output"
    
    result = {
        "expected_count": 0,
        "source": "none",
        "input_lectures": [],
        "output_lectures": [],
        "missing_lectures": [],
        "extra_lectures": []
    }
    
    lecture_numbers = set()
    
    # 1. Scan input directory for lecture directories
    course_dir = os.path.join(input_dir, course_name)
    if os.path.exists(course_dir):
        # Look for lecture directories
        for item in os.listdir(course_dir):
            item_path = os.path.join(course_dir, item)
            if os.path.isdir(item_path):
                lecture_num = extract_lecture_number(item)
                if lecture_num:
                    lecture_numbers.add(lecture_num)
                    result["input_lectures"].append(lecture_num)
        
        # Also scan for PPTX files
        pptx_files = find_files(course_dir, "*.pptx")
        for pptx_file in pptx_files:
            lecture_num = extract_lecture_number(pptx_file)
            if lecture_num:
                lecture_numbers.add(lecture_num)
                if lecture_num not in result["input_lectures"]:
                    result["input_lectures"].append(lecture_num)
        
        # Scan for audio directories
        for root, dirs, _ in os.walk(course_dir):
            for dir_name in dirs:
                if "audio" in dir_name.lower():
                    parent_dir = os.path.basename(root)
                    lecture_num = extract_lecture_number(parent_dir)
                    if lecture_num:
                        lecture_numbers.add(lecture_num)
                        if lecture_num not in result["input_lectures"]:
                            result["input_lectures"].append(lecture_num)
    
    # 2. Scan output directory for MP4 files
    output_course_dir = os.path.join(output_dir, language, course_name)
    if os.path.exists(output_course_dir):
        mp4_files = find_files(output_course_dir, "*.mp4")
        for mp4_file in mp4_files:
            # Skip summary videos for counting
            if "(summary)" not in mp4_file.lower():
                lecture_num = extract_lecture_number(mp4_file)
                if lecture_num:
                    lecture_numbers.add(lecture_num)
                    result["output_lectures"].append(lecture_num)
    
    # 3. Determine expected count
    if lecture_numbers:
        max_lecture = max(lecture_numbers)
        result["expected_count"] = max_lecture
        result["source"] = f"auto-detected (highest: Lecture {max_lecture})"
        
        # Generate expected range and find missing lectures
        expected_range = set(range(1, max_lecture + 1))
        result["missing_lectures"] = sorted(list(expected_range - lecture_numbers))
        result["extra_lectures"] = sorted(list(lecture_numbers - expected_range))
    else:
        result["source"] = "no lectures found"
    
    # Sort the lecture lists
    result["input_lectures"] = sorted(list(set(result["input_lectures"])))
    result["output_lectures"] = sorted(list(set(result["output_lectures"])))
    
    return result

def find_mp4_files_in_output(course_name: str, language: str = "English") -> Dict:
    """
    Find all MP4 files in the output directory for a specific course and language
    
    Args:
        course_name: Name of the course
        language: Language to search for
        
    Returns:
        Dictionary with regular and summary videos
    """
    output_dir = "output"
    
    result = {
        "regular": [],
        "summary": [],
        "total_count": 0
    }
    
    # Build the path to the course directory
    course_dir = os.path.join(output_dir, language, course_name)
    
    # Check if the course directory exists
    if not os.path.exists(course_dir):
        return result
    
    # Find all MP4 files in the course directory (recursively)
    mp4_files = glob.glob(os.path.join(course_dir, "**", "*.mp4"), recursive=True)
    
    # Categorize files as regular or summary
    for mp4_file in mp4_files:
        if "(summary)" in mp4_file.lower():
            result["summary"].append(mp4_file)
        else:
            result["regular"].append(mp4_file)
    
    # Update total count
    result["total_count"] = len(result["regular"]) + len(result["summary"])
    
    return result

def find_lecture_audio_files(lecture_path: str, language: str = "English", summary: bool = False) -> List[str]:
    """
    Find all audio files in a lecture directory for a specific language
    
    Args:
        lecture_path: Path to lecture directory
        language: Language to find audio for (default: English)
        summary: Whether to find summary audio files (default: False)
    
    Returns:
        List of sorted audio file paths
    """
    # Look in the "<Language> audio" or "<Language> Summary audio" folder
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_path, folder_name)
    
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        # Get all audio files in the directory
        audio_extensions = [".mp3", ".wav", ".ogg", ".aac", ".flac"]
        audio_files = []
        
        for ext in audio_extensions:
            audio_files.extend(glob.glob(os.path.join(lang_audio_dir, f"*{ext}")))
        
        # Sort files naturally (1.mp3, 2.mp3, ..., 10.mp3, etc.)
        audio_files = sorted(audio_files, key=lambda x: int(re.search(r'\d+', os.path.basename(x)).group()) if re.search(r'\d+', os.path.basename(x)) else 0)
        
        return audio_files
    
    # Return empty list if no audio folder or no files found
    return []

def calculate_total_audio_duration(audio_files: List[str]) -> Tuple[bool, float]:
    """
    Calculate the total duration of a list of audio files
    
    Args:
        audio_files: List of audio file paths
        
    Returns:
        Tuple of (success, total_duration_in_seconds)
    """
    total_duration = 0.0
    success = True
    
    for audio_file in audio_files:
        audio_success, audio_duration = count_audio_duration(audio_file)
        if audio_success:
            total_duration += audio_duration
        else:
            success = False
    
    return success, total_duration

def find_input_lecture_path(course_name: str, lecture_name: str) -> str:
    """
    Find the input lecture path for a specific course and lecture
    
    Args:
        course_name: Name of the course
        lecture_name: Name of the lecture (e.g., "Lecture 01")
        
    Returns:
        Path to the lecture directory or empty string if not found
    """
    input_dir = get_input_directory()
    
    # Build the path to the course directory
    course_dir = os.path.join(input_dir, course_name)
    
    # Check if the course directory exists
    if not os.path.exists(course_dir):
        return ""
    
    # Look for the lecture directory directly in the course directory
    lecture_path = os.path.join(course_dir, lecture_name)
    if os.path.exists(lecture_path) and os.path.isdir(lecture_path):
        return lecture_path
    
    # If not found, look in subdirectories of the course directory
    for item in os.listdir(course_dir):
        item_path = os.path.join(course_dir, item)
        if os.path.isdir(item_path):
            lecture_path = os.path.join(item_path, lecture_name)
            if os.path.exists(lecture_path) and os.path.isdir(lecture_path):
                return lecture_path
    
    # If not found anywhere, return empty string
    return ""
def verify_mp4_files(course_name: str, discovery_info: Dict, language: str = "English", duration_tolerance: float = 0.5) -> Dict:
    """
    Verify MP4 files for a specific course
    
    Args:
        course_name: Name of the course
        discovery_info: Auto-discovery information
        language: Language to verify
        duration_tolerance: Tolerance for duration differences in seconds
        
    Returns:
        Dictionary with verification results
    """
    expected_count = discovery_info["expected_count"]
    
    result = {
        "course_name": course_name,
        "expected_count": expected_count,
        "discovery_source": discovery_info["source"],
        "missing_lectures": discovery_info["missing_lectures"],
        "extra_lectures": discovery_info["extra_lectures"],
        "input_lectures": discovery_info["input_lectures"],
        "output_lectures": discovery_info["output_lectures"],
        "regular_count": 0,
        "summary_count": 0,
        "regular_videos": [],
        "summary_videos": [],
        "verification_results": []
    }
    
    # Find all MP4 files in the output directory
    mp4_files = find_mp4_files_in_output(course_name, language)
    
    # Update counts
    result["regular_count"] = len(mp4_files["regular"])
    result["summary_count"] = len(mp4_files["summary"])
    result["regular_videos"] = mp4_files["regular"]
    result["summary_videos"] = mp4_files["summary"]
    
    # Verify each regular video
    for mp4_file in mp4_files["regular"]:
        verification_result = {
            "video_path": mp4_file,
            "video_name": os.path.basename(mp4_file),
            "type": "regular",
            "video_exists": True,
            "video_playable": False,
            "video_duration": 0.0,
            "audio_duration": 0.0,
            "duration_match": False,
            "duration_difference": 0.0,
            "status": "error",
            "message": ""
        }
        
        # Get the lecture name from the file name
        lecture_name = os.path.splitext(os.path.basename(mp4_file))[0]
        
        # Find the corresponding input lecture path
        lecture_path = find_input_lecture_path(course_name, lecture_name)
        
        if not lecture_path:
            verification_result["status"] = "error"
            verification_result["message"] = f"Input lecture path not found for {lecture_name}"
            result["verification_results"].append(verification_result)
            continue
        
        # Verify that the video is playable and get its duration
        video_success, video_duration = count_mp4_duration(mp4_file)
        verification_result["video_playable"] = video_success
        verification_result["video_duration"] = video_duration
        
        if not video_success:
            verification_result["status"] = "error"
            verification_result["message"] = f"Video is not playable"
            result["verification_results"].append(verification_result)
            continue
        
        # Find all audio files in the input directory
        audio_files = find_lecture_audio_files(lecture_path, language, summary=False)
        
        if not audio_files:
            verification_result["status"] = "error"
            verification_result["message"] = f"No audio files found for {lecture_name}"
            result["verification_results"].append(verification_result)
            continue
        
        # Calculate total audio duration
        audio_success, audio_duration = calculate_total_audio_duration(audio_files)
        verification_result["audio_duration"] = audio_duration
        
        if not audio_success:
            verification_result["status"] = "error"
            verification_result["message"] = f"Failed to calculate audio duration"
            result["verification_results"].append(verification_result)
            continue
        
        # Compare durations
        # Allow a small difference (e.g., 0.5 seconds) for encoding/decoding differences
        duration_difference = abs(video_duration - audio_duration)
        verification_result["duration_difference"] = duration_difference
        
        if duration_difference <= duration_tolerance:
            verification_result["duration_match"] = True
            verification_result["status"] = "success"
            verification_result["message"] = f"Video duration matches audio duration"
        else:
            verification_result["duration_match"] = False
            verification_result["status"] = "warning"
            verification_result["message"] = f"Video duration ({video_duration:.2f}s) does not match audio duration ({audio_duration:.2f}s)"
        
        result["verification_results"].append(verification_result)
    
    # Verify each summary video
    for mp4_file in mp4_files["summary"]:
        verification_result = {
            "video_path": mp4_file,
            "video_name": os.path.basename(mp4_file),
            "type": "summary",
            "video_exists": True,
            "video_playable": False,
            "video_duration": 0.0,
            "audio_duration": 0.0,
            "duration_match": False,
            "duration_difference": 0.0,
            "status": "error",
            "message": ""
        }
        
        # Get the lecture name from the file name (remove "(summary)" suffix)
        lecture_name = os.path.splitext(os.path.basename(mp4_file))[0].replace("(summary)", "").strip()
        
        # Find the corresponding input lecture path
        lecture_path = find_input_lecture_path(course_name, lecture_name)
        
        if not lecture_path:
            verification_result["status"] = "error"
            verification_result["message"] = f"Input lecture path not found for {lecture_name}"
            result["verification_results"].append(verification_result)
            continue
        
        # Verify that the video is playable and get its duration
        video_success, video_duration = count_mp4_duration(mp4_file)
        verification_result["video_playable"] = video_success
        verification_result["video_duration"] = video_duration
        
        if not video_success:
            verification_result["status"] = "error"
            verification_result["message"] = f"Video is not playable"
            result["verification_results"].append(verification_result)
            continue
        
        # Find all audio files in the input directory
        audio_files = find_lecture_audio_files(lecture_path, language, summary=True)
        
        if not audio_files:
            verification_result["status"] = "error"
            verification_result["message"] = f"No summary audio files found for {lecture_name}"
            result["verification_results"].append(verification_result)
            continue
        
        # Calculate total audio duration
        audio_success, audio_duration = calculate_total_audio_duration(audio_files)
        verification_result["audio_duration"] = audio_duration
        
        if not audio_success:
            verification_result["status"] = "error"
            verification_result["message"] = f"Failed to calculate audio duration"
            result["verification_results"].append(verification_result)
            continue
        
        # Compare durations
        # Allow a small difference (e.g., 0.5 seconds) for encoding/decoding differences
        duration_difference = abs(video_duration - audio_duration)
        verification_result["duration_difference"] = duration_difference
        
        if duration_difference <= duration_tolerance:
            verification_result["duration_match"] = True
            verification_result["status"] = "success"
            verification_result["message"] = f"Video duration matches audio duration"
        else:
            verification_result["duration_match"] = False
            verification_result["status"] = "warning"
            verification_result["message"] = f"Video duration ({video_duration:.2f}s) does not match audio duration ({audio_duration:.2f}s)"
        
        result["verification_results"].append(verification_result)
    
    # Enhanced count validation with missing lecture details
    missing_count = len(result["missing_lectures"])
    
    if expected_count == 0:
        result["count_status"] = "warning"
        result["count_message"] = f"No lectures detected for this course"
    elif missing_count > 0:
        result["count_status"] = "error"
        missing_str = ", ".join([f"Lecture {num:02d}" for num in result["missing_lectures"]])
        result["count_message"] = f"Missing {missing_count} lectures: {missing_str}"
    elif result["regular_count"] < expected_count:
        result["count_status"] = "error"
        result["count_message"] = f"Missing regular videos. Expected: {expected_count}, Found: {result['regular_count']}"
    elif result["summary_count"] > 0 and result["summary_count"] < expected_count:
        result["count_status"] = "warning"
        result["count_message"] = f"Missing summary videos. Expected: {expected_count}, Found: {result['summary_count']}"
    else:
        result["count_status"] = "success"
        result["count_message"] = f"All expected videos found ({result['discovery_source']})"
    
    return result

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def run_mp4_verification_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the MP4 verification operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_11_verify_mp4')
    
    # Extract settings from config
    language = page_config.get('language', 'English')
    duration_tolerance = page_config.get('duration_tolerance', 0.5)
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_courses": 0, "verified_count": 0, "error_count": 1}
        }
    
    # Validate output directory
    output_dir = config.output_dir
    if not os.path.exists(output_dir):
        error_msg = f"Output directory not found: {output_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_courses": 0, "verified_count": 0, "error_count": 1}
        }
    
    console.print(f"[blue]ℹ[/blue] Scanning input directory: {input_dir}")
    console.print(f"[blue]ℹ[/blue] Verifying language: {language}")
    console.print(f"[blue]ℹ[/blue] Duration tolerance: {duration_tolerance}s")
    
    # Get all courses
    course_names = get_all_course_names()
    
    if not course_names:
        error_msg = "No courses found in the input directory"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_courses": 0, "verified_count": 0, "error_count": 0}
        }
    
    console.print(f"[green]✓[/green] Found {len(course_names)} courses to verify")
    
    # Auto-discover and verify each course
    all_results = []
    start_time = time.time()
    
    with DreamletProgress(description="Verifying MP4 files", total=len(course_names)) as progress:
        
        for i, course_name in enumerate(course_names):
            progress.update(description=f"Verifying {course_name}")
            
            # Auto-discover expected count
            discovery_info = auto_discover_expected_count(course_name, language)
            
            # Verify MP4 files
            result = verify_mp4_files(course_name, discovery_info, language, duration_tolerance)
            all_results.append(result)
            
            progress.update(advance=1)
    
    # Calculate final statistics
    total_processing_time = time.time() - start_time
    total_courses = len(all_results)
    courses_with_errors = sum(1 for r in all_results if r["count_status"] == "error")
    courses_with_warnings = sum(1 for r in all_results if r["count_status"] == "warning")
    courses_success = total_courses - courses_with_errors - courses_with_warnings
    
    # Calculate video statistics
    total_regular_videos = sum(r["regular_count"] for r in all_results)
    total_summary_videos = sum(r["summary_count"] for r in all_results)
    total_verification_results = sum(len(r["verification_results"]) for r in all_results)
    
    # Count verification statuses
    verification_success = 0
    verification_warnings = 0
    verification_errors = 0
    
    for result in all_results:
        for verification in result["verification_results"]:
            if verification["status"] == "success":
                verification_success += 1
            elif verification["status"] == "warning":
                verification_warnings += 1
            else:
                verification_errors += 1
    
    # Determine final status
    if courses_with_errors > 0:
        final_status = "error"
        status_message = f"Verified {total_courses} courses with {courses_with_errors} errors, {courses_with_warnings} warnings"
    elif courses_with_warnings > 0:
        final_status = "warning"
        status_message = f"Verified {total_courses} courses with {courses_with_warnings} warnings"
    else:
        final_status = "success"
        status_message = f"Successfully verified {total_courses} courses"
    
    # Show summary
    console.print(f"[green]✓[/green] {status_message}")
    console.print(f"[blue]ℹ[/blue] Total processing time: {total_processing_time:.1f} seconds")
    console.print(f"[blue]ℹ[/blue] Videos verified: {total_regular_videos} regular, {total_summary_videos} summary")
    
    # Display detailed results if verbose
    if ctx_obj.get('verbose', False) and all_results:
        # Course summary table
        course_table = Table(title="Course Verification Summary")
        course_table.add_column("Course", style="cyan")
        course_table.add_column("Expected", justify="right")
        course_table.add_column("Regular", justify="right")
        course_table.add_column("Summary", justify="right")
        course_table.add_column("Missing", style="red")
        course_table.add_column("Status", style="bold")
        
        for result in all_results[:10]:  # Show first 10 courses
            status_style = "green" if result["count_status"] == "success" else "red" if result["count_status"] == "error" else "yellow"
            status_text = result["count_status"].upper()
            
            missing_str = f"L{result['missing_lectures'][0]:02d}" if result["missing_lectures"] else ""
            if len(result["missing_lectures"]) > 1:
                missing_str += f"+{len(result['missing_lectures'])-1}"
            
            course_table.add_row(
                result["course_name"][:30] + "..." if len(result["course_name"]) > 30 else result["course_name"],
                str(result["expected_count"]),
                str(result["regular_count"]),
                str(result["summary_count"]),
                missing_str,
                f"[{status_style}]{status_text}[/{status_style}]"
            )
        
        console.print(course_table)
        
        if len(all_results) > 10:
            console.print(f"... and {len(all_results) - 10} more courses")
        
        # Video verification table (show problematic videos only)
        problem_videos = []
        for result in all_results:
            for verification in result["verification_results"]:
                if verification["status"] != "success":
                    problem_videos.append({
                        "course": result["course_name"],
                        "video": verification["video_name"],
                        "type": verification["type"],
                        "status": verification["status"],
                        "message": verification["message"]
                    })
        
        if problem_videos:
            video_table = Table(title="Problem Videos")
            video_table.add_column("Course", style="cyan")
            video_table.add_column("Video", style="magenta")
            video_table.add_column("Type", style="blue")
            video_table.add_column("Status", style="bold")
            video_table.add_column("Issue", style="dim")
            
            for video in problem_videos[:20]:  # Show first 20 problem videos
                status_style = "red" if video["status"] == "error" else "yellow"
                status_text = video["status"].upper()
                
                video_table.add_row(
                    video["course"][:20] + "..." if len(video["course"]) > 20 else video["course"],
                    video["video"][:25] + "..." if len(video["video"]) > 25 else video["video"],
                    video["type"].title(),
                    f"[{status_style}]{status_text}[/{status_style}]",
                    video["message"][:50] + "..." if len(video["message"]) > 50 else video["message"]
                )
            
            console.print(video_table)
            
            if len(problem_videos) > 20:
                console.print(f"... and {len(problem_videos) - 20} more problem videos")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "output_directory": output_dir,
            "language": language,
            "duration_tolerance": f"{duration_tolerance}s",
            "courses_found": len(course_names)
        },
        "statistics": {
            "total_courses": total_courses,
            "courses_success": courses_success,
            "courses_with_warnings": courses_with_warnings,
            "courses_with_errors": courses_with_errors,
            "total_regular_videos": total_regular_videos,
            "total_summary_videos": total_summary_videos,
            "verification_success": verification_success,
            "verification_warnings": verification_warnings,
            "verification_errors": verification_errors,
            "processing_time": f"{total_processing_time:.1f}s"
        },
        "course_results": [
            {
                "course_name": result["course_name"],
                "expected_count": result["expected_count"],
                "regular_count": result["regular_count"],
                "summary_count": result["summary_count"],
                "missing_lectures": result["missing_lectures"],
                "count_status": result["count_status"],
                "count_message": result["count_message"],
                "discovery_source": result["discovery_source"]
            }
            for result in all_results
        ],
        "verification_results": [
            {
                "course_name": result["course_name"],
                "video_name": verification["video_name"],
                "type": verification["type"],
                "status": verification["status"],
                "video_playable": verification["video_playable"],
                "video_duration": verification["video_duration"],
                "audio_duration": verification["audio_duration"],
                "duration_difference": verification["duration_difference"],
                "message": verification["message"]
            }
            for result in all_results
            for verification in result["verification_results"]
        ],
        "errors": [
            f"{result['course_name']}: {result['count_message']}"
            for result in all_results
            if result["count_status"] == "error"
        ]
    }
    
    # Generate report
    report_path = generate_report("11", "MP4 Verification", report_results)
    console.print(f"[blue]ℹ[/blue] Report saved to: {report_path}", style="dim")
    
    report_results["report_path"] = report_path
    return report_results

@click.command()
@click.pass_context
def verify_mp4(ctx):
    """
    Verify MP4 files for completeness and correctness with auto-discovery
    
    This command performs comprehensive verification of MP4 files with intelligent 
    auto-discovery of expected lecture counts. It verifies video playability, 
    compares durations with source audio files, and identifies missing lectures.
    
    Features:
    - Auto-discovery of expected lecture counts from input directories and existing MP4s
    - MP4 playability verification using ffprobe
    - Duration comparison between videos and source audio files
    - Missing lecture detection with specific identification
    - Support for both regular and summary videos
    - Comprehensive reporting with detailed statistics
    
    Auto-Discovery Process:
    1. Scans input directories for lecture folders and PPTX files
    2. Scans output directories for existing MP4 files
    3. Determines expected count from highest lecture number found
    4. Identifies specific missing lectures in the sequence
    
    All settings are configured in config.json under "page_11_verify_mp4":
    - language: Language to verify (default: "English")
    - duration_tolerance: Tolerance for duration differences in seconds (default: 0.5)
    
    Examples:
        dreamlet run 11                    # Verify MP4s with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No verification will be performed[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_11_verify_mp4')
        language = page_config.get('language', 'English')
        duration_tolerance = page_config.get('duration_tolerance', 0.5)
        
        console.print(f"Would verify MP4s for language: {language}")
        console.print(f"Would use duration tolerance: {duration_tolerance}s")
        console.print("Would auto-discover expected lecture counts")
        console.print("Would verify video playability and duration matching")
        return
    
    # Run the MP4 verification operation
    try:
        results = run_mp4_verification_processing(ctx.obj)
        
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
    verify_mp4()