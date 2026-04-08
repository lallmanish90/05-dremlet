"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Verify generated MP4 files and surface mismatches, missing outputs, or duration problems.
MAIN INPUTS:
- generated MP4 files under `output/`
- source lecture structure under `input/`
MAIN OUTPUTS:
- verification summaries and mismatch reports shown in the UI
REQUIRED CONFIG / ASSETS:
- `input/` and `output/` directories
- optional `config/mp4_verification.json`
EXTERNAL SERVICES:
- local `ffmpeg` / `ffprobe`
HARDWARE ASSUMPTIONS:
- none
"""

import streamlit as st
import os
import subprocess
import glob
import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Local utility functions (moved from utils modules)
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

# Define constants
INPUT_DIR = get_input_directory()
OUTPUT_DIR = "output"

# Set page config
st.set_page_config(page_title="11 Verify MP4 - Dreamlet", page_icon="📊", layout="wide")

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
    
    # Get all first-level directories in the input directory (courses)
    if os.path.exists(INPUT_DIR):
        for item in os.listdir(INPUT_DIR):
            item_path = os.path.join(INPUT_DIR, item)
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
    course_dir = os.path.join(INPUT_DIR, course_name)
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
    output_course_dir = os.path.join(OUTPUT_DIR, language, course_name)
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
    result = {
        "regular": [],
        "summary": [],
        "total_count": 0
    }
    
    # Build the path to the course directory
    course_dir = os.path.join(OUTPUT_DIR, language, course_name)
    
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
    # Build the path to the course directory
    course_dir = os.path.join(INPUT_DIR, course_name)
    
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

def verify_mp4_files(course_name: str, discovery_info: Dict, language: str = "English") -> Dict:
    """
    Verify MP4 files for a specific course
    
    Args:
        course_name: Name of the course
        discovery_info: Auto-discovery information
        language: Language to verify
        
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
        
        if duration_difference <= 0.5:
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
        
        if duration_difference <= 0.5:
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

def main():
    st.title("verify - mp4")
    st.write("Verify MP4 files for completeness and correctness with auto-discovery")
    
    # Instructions
    with st.expander("Instructions & Information", expanded=False):
        st.markdown("""
        This tool performs comprehensive verification of MP4 files with intelligent auto-discovery:
        
        1. **Auto-Discovery**: Automatically detects expected lecture count by scanning:
           - Input directory lecture folders
           - PPTX presentation files
           - Audio directories
           - Existing MP4 files in output
        
        2. **Missing Lecture Detection**: Identifies specific missing lectures (e.g., "Missing: Lecture 02, Lecture 05")
        
        3. **Playability Verification**: Tests if each MP4 file can be properly decoded
        
        4. **Duration Verification**: Compares video duration with audio file durations
        
        ### How Auto-Discovery Works
        - Scans all sources to find the highest lecture number
        - Uses that as the expected total (e.g., if Lecture 48 exists, expects 48 lectures)
        - Generates a complete list of missing lectures from 1 to the highest number
        
        ### Regular vs. Summary Videos
        - Regular videos are created from "English audio" files
        - Summary videos (with "(summary)" in filename) are created from "English Summary audio" files
        """)
    
    # Get all courses
    course_names = get_all_course_names()
    
    if not course_names:
        st.warning("No courses found in the input directory.")
        return
    
    # Auto-discovery section
    st.header("Auto-Discovery Results")
    
    with st.expander("View Auto-Discovery Details", expanded=False):
        discovery_results = {}
        for course_name in course_names:
            discovery_info = auto_discover_expected_count(course_name)
            discovery_results[course_name] = discovery_info
            
            st.subheader(f"{course_name}")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Expected Count", discovery_info["expected_count"])
            with col2:
                st.metric("Input Lectures", len(discovery_info["input_lectures"]))
            with col3:
                st.metric("Output MP4s", len(discovery_info["output_lectures"]))
            
            st.write(f"**Source**: {discovery_info['source']}")
            
            if discovery_info["input_lectures"]:
                st.write(f"**Input lectures found**: {', '.join([f'L{n:02d}' for n in discovery_info['input_lectures']])}")
            
            if discovery_info["output_lectures"]:
                st.write(f"**Output MP4s found**: {', '.join([f'L{n:02d}' for n in discovery_info['output_lectures']])}")
            
            if discovery_info["missing_lectures"]:
                st.write(f"**Missing lectures**: {', '.join([f'L{n:02d}' for n in discovery_info['missing_lectures']])}")
            
            st.write("---")
    
    # Verify button
    if st.button("Verify MP4 Files", type="primary"):
        with st.spinner("Verifying MP4 files..."):
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Auto-discover and verify each course
            all_results = []
            for i, course_name in enumerate(course_names):
                # Update progress
                progress = (i / len(course_names))
                progress_bar.progress(progress)
                status_text.info(f"Auto-discovering and verifying {course_name}...")
                
                # Auto-discover expected count
                discovery_info = auto_discover_expected_count(course_name)
                
                # Verify MP4 files
                result = verify_mp4_files(course_name, discovery_info)
                all_results.append(result)
            
            # Complete progress
            progress_bar.progress(1.0)
            status_text.success("Verification complete!")
            
            # Display results
            st.header("Verification Results")
            
            # Display summary
            total_courses = len(all_results)
            courses_with_errors = sum(1 for r in all_results if r["count_status"] == "error")
            courses_with_warnings = sum(1 for r in all_results if r["count_status"] == "warning")
            courses_success = total_courses - courses_with_errors - courses_with_warnings
            
            # Create summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Courses Verified", total_courses)
            with col2:
                st.metric("Courses with Issues", courses_with_errors + courses_with_warnings, 
                         delta=f"{courses_with_errors} errors, {courses_with_warnings} warnings")
            with col3:
                st.metric("Courses Success", courses_success)
            
            # Create detailed results per course
            for result in all_results:
                course_name = result["course_name"]
                expected_count = result["expected_count"]
                regular_count = result["regular_count"]
                summary_count = result["summary_count"]
                count_status = result["count_status"]
                count_message = result["count_message"]
                
                # Display course header with status
                if count_status == "error":
                    st.error(f"**{course_name}**: {count_message}")
                elif count_status == "warning":
                    st.warning(f"**{course_name}**: {count_message}")
                else:
                    st.success(f"**{course_name}**: {count_message}")
                
                # Display count information with discovery details
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Expected**: {expected_count} ({result['discovery_source']})")
                    st.write(f"**Regular Videos**: {regular_count}")
                    st.write(f"**Summary Videos**: {summary_count}")
                
                with col2:
                    if result["missing_lectures"]:
                        missing_str = ", ".join([f"L{n:02d}" for n in result["missing_lectures"]])
                        st.write(f"**Missing**: {missing_str}")
                    
                    if result["input_lectures"]:
                        input_str = ", ".join([f"L{n:02d}" for n in result["input_lectures"]])
                        st.write(f"**Input Found**: {input_str}")
                
                # Create an expander for detailed verification results
                with st.expander(f"Detailed Verification Results for {course_name}"):
                    # Create a dataframe for regular videos
                    if result["regular_videos"]:
                        st.subheader("Regular Videos")
                        
                        # Create data for the table
                        table_data = []
                        for verification in result["verification_results"]:
                            if verification["type"] == "regular":
                                status_icon = "✅" if verification["status"] == "success" else "⚠️" if verification["status"] == "warning" else "❌"
                                table_data.append({
                                    "Video": verification["video_name"],
                                    "Status": status_icon,
                                    "Playable": "Yes" if verification["video_playable"] else "No",
                                    "Video Duration": f"{verification['video_duration']:.2f}s",
                                    "Audio Duration": f"{verification['audio_duration']:.2f}s",
                                    "Difference": f"{verification['duration_difference']:.2f}s",
                                    "Message": verification["message"]
                                })
                        
                        # Display the table
                        if table_data:
                            import pandas as pd
                            st.table(pd.DataFrame(table_data))
                        else:
                            st.info("No regular videos found")
                    
                    # Create a dataframe for summary videos
                    if result["summary_videos"]:
                        st.subheader("Summary Videos")
                        
                        # Create data for the table
                        table_data = []
                        for verification in result["verification_results"]:
                            if verification["type"] == "summary":
                                status_icon = "✅" if verification["status"] == "success" else "⚠️" if verification["status"] == "warning" else "❌"
                                table_data.append({
                                    "Video": verification["video_name"],
                                    "Status": status_icon,
                                    "Playable": "Yes" if verification["video_playable"] else "No",
                                    "Video Duration": f"{verification['video_duration']:.2f}s",
                                    "Audio Duration": f"{verification['audio_duration']:.2f}s",
                                    "Difference": f"{verification['duration_difference']:.2f}s",
                                    "Message": verification["message"]
                                })
                        
                        # Display the table
                        if table_data:
                            import pandas as pd
                            st.table(pd.DataFrame(table_data))
                        else:
                            st.info("No summary videos found")
            
            # Store results in session state
            st.session_state.verification_results = all_results

if __name__ == "__main__":
    main()
