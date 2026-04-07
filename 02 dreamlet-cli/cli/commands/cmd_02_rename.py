"""
CLI Command: Rename Files (Page 02)

Converts the Streamlit page 02_Rename.py to CLI interface
while maintaining 100% functional parity.
"""

import click
import os
import sys
import re
import time
import pandas as pd
import fnmatch
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress, StatusManager
from cli.reports import generate_report
from cli.config import load_config

console = Console()

# ===== BUSINESS LOGIC EXTRACTED FROM STREAMLIT PAGE =====
# All functions below are extracted from pages/02_Rename.py

def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def get_output_directory() -> str:
    """Get the path to the output directory"""
    return get_input_directory()

def find_files(directory: str, pattern: str) -> List[str]:
    """Find all files matching a pattern in a directory (recursively)"""
    result = []
    for root, _, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            result.append(os.path.join(root, filename))
    return result

def find_transcript_files(directory: str) -> List[str]:
    """Find all transcript files in a directory"""
    transcripts = []
    transcript_patterns = [
        "Lecture*.txt", "Lecture*.md", 
        "*lecture*.txt", "*lecture*.md",
        "*transcript*.txt", "*transcript*.md",
        "*artifact_b*.txt", "*artifact_b*.md",
        "*artifact-b*.txt", "*artifact-b*.md",
        "*.txt", "*.md"
    ]
    
    for pattern in transcript_patterns:
        transcripts.extend(find_files(directory, pattern))
    
    transcripts = [f for f in transcripts if "slide" not in os.path.basename(f).lower()]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-s\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'summary', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-d\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-artifact-d\.(md|txt)$', os.path.basename(f).lower())]
    
    return list(set(transcripts))

def find_slide_files(directory: str) -> List[str]:
    """Find all slide description files in a directory"""
    slides = []
    slide_patterns = [
        "*-slides.txt", "*-slides.md",
        "*-slide.txt", "*-slide.md",
        "*slides*.txt", "*slides*.md",
        "*slide*.txt", "*slide*.md",
        "*-s.txt", "*-s.md",
        "*artifact_c*.txt", "*artifact_c*.md",
        "*artifact-c*.txt", "*artifact-c*.md",
        "*slide_content*.txt", "*slide_content*.md"
    ]
    
    for pattern in slide_patterns:
        slides.extend(find_files(directory, pattern))
    
    all_text_files = find_files(directory, "*.txt") + find_files(directory, "*.md")
    for file_path in all_text_files:
        filename = os.path.basename(file_path)
        if re.search(r'^\d+-s\.(md|txt)$', filename.lower()):
            if file_path not in slides:
                slides.append(file_path)
    
    return list(set(slides))

def find_summary_files(directory: str) -> List[str]:
    """Find all summary files in a directory"""
    summaries = []
    summary_patterns = [
        "*-summary.txt", "*-summary.md",
        "*-d.txt", "*-d.md",
        "*-artifact-d.txt", "*-artifact-d.md",
        "*artifact_d*.txt", "*artifact_d*.md",
        "*_summary*.txt", "*_summary*.md",
        "*video_summary*.txt", "*video_summary*.md"
    ]
    
    for pattern in summary_patterns:
        summaries.extend(find_files(directory, pattern))
    
    return list(set(summaries))

def find_presentation_files(directory: str) -> List[str]:
    """Find all presentation files in a directory"""
    return find_files(directory, "*.pptx")

def extract_course_lecture_section(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract course, lecture, and section information from a file path"""
    dir_parts = os.path.normpath(file_path).split(os.sep)
    
    course = None
    lecture = None
    section = None
    
    for part in dir_parts:
        course_match = re.search(r'course\s*(\d+)', part.lower())
        if course_match:
            course = course_match.group(1)
            break
        number_start_match = re.match(r'^(\d+)\s+', part)
        if number_start_match:
            course = number_start_match.group(1)
            break
        bracket_match = re.search(r'[(\[]\s*(\d+)\s*[)\]]', part)
        if bracket_match:
            course = bracket_match.group(1)
            break
    
    filename = os.path.basename(file_path)
    lecture_patterns = [
        r'lecture\s*(\d+)',
        r'lec\s*(\d+)',
        r'^(\d+)[-\s]',
        r'^\w+\s*(\d+)'
    ]
    
    for pattern in lecture_patterns:
        lecture_match = re.search(pattern, filename.lower())
        if lecture_match:
            lecture = lecture_match.group(1)
            break
    
    if not lecture:
        for part in dir_parts:
            for pattern in lecture_patterns:
                lecture_match = re.search(pattern, part.lower())
                if lecture_match:
                    lecture = lecture_match.group(1)
                    break
            if lecture:
                break
    
    section_patterns = [
        r'section\s*(\d+)',
        r'sec\s*(\d+)'
    ]
    
    for part in dir_parts:
        for pattern in section_patterns:
            section_match = re.search(pattern, part.lower())
            if section_match:
                section = section_match.group(1)
                break
        if section:
            break
    
    return course, lecture, section

def standardize_lecture_number(lecture: str) -> str:
    """Standardize lecture number to two-digit format"""
    if lecture and lecture.isdigit():
        return f"{int(lecture):02d}"
    return lecture or "00"

def analyze_filename_for_renaming(filename: str) -> Dict:
    """Analyze a filename and suggest corrected naming or deletion"""
    base_name, ext = os.path.splitext(filename)
    
    # Initialize result
    result = {
        "original": filename,
        "corrected": filename,
        "needs_renaming": False,
        "should_delete": False,
        "type": "unknown",
        "reason": ""
    }
    
    # Check for files that should be deleted first
    
    # 1. Outline files (always delete)
    if re.search(r'.*outline.*', base_name.lower()):
        result["should_delete"] = True
        result["reason"] = "Outline files not supported"
        result["type"] = "delete"
        return result
    
    # 2. Hybrid transcript-summary files (always delete)
    if re.search(r'.*transcript.*summary.*', base_name.lower()) or re.search(r'.*video.*transcript.*summary.*', base_name.lower()):
        result["should_delete"] = True
        result["reason"] = "Hybrid transcript-summary files not supported"
        result["type"] = "delete"
        return result
    
    # 3. Files with duplicate indicators like (1), (2), etc. (always delete)
    if re.search(r'\(\d+\)', base_name):
        result["should_delete"] = True
        result["reason"] = "Duplicate file indicator found"
        result["type"] = "delete"
        return result
    
    # 4. Files without lecture numbers (delete only if no numbers found)
    if not re.search(r'\d+', base_name):
        generic_patterns = [
            (r'^video_transcript$', "Generic name without lecture number"),
            (r'^video_transcript_summary$', "Generic name without lecture number, hybrid type"),
            (r'^artifact_b_transcript$', "No clear lecture number extractable"),
            (r'^artifact_d_summary$', "No clear lecture number extractable"),
            (r'^artifact[-_][a-z]$', "Artifact type without clear lecture number"),
        ]
        
        for pattern, reason in generic_patterns:
            if re.search(pattern, base_name.lower()):
                result["should_delete"] = True
                result["reason"] = reason
                result["type"] = "delete"
                return result
    
    # Check for transcript patterns
    transcript_patterns = [
        # Basic lecture transcript patterns
        r'^(.*)lec(\d+)[-_]*transcript(.*)$',
        r'^(.*)lecture(\d+)[-_]*transcript(.*)$',
        r'^(.*)lecture(\d+)[-_]*script(.*)$',
        r'^lecture[_\s]*(\d+)$',  # Already correct format
        # Lecture underscore transcript patterns (like lecture_05_transcript.md)
        r'^lecture[_\s]*(\d+)[_\s]*transcript$',
        # Lecture video transcript patterns (like lecture74_video_transcript.md)
        r'^lecture[_\s]*(\d+)[_\s]*video[_\s]*transcript$',
        r'^lecture(\d+)[_\s]*video[_\s]*transcript$',
        # Number_transcript patterns (like 10_transcript.md)
        r'^(\d+)[-_]*transcript$',
        # Artifact patterns
        r'^(\d+)[-_]*b$',
        r'^(\d+)[-_]*artifact[-_]*b$',
        r'^lecture[_\s]*(\d+)[_\s]*artifact[_\s]*b$',
        r'^artifact[_\s]*(\d+)[_\s]*transcript$',
        r'^artifact[_\s]*b[_\s]*transcript$',
        r'^(\d+)artifact[-_]*b$',
        # Number.artifact-b patterns (like 10.artifact-b.md)
        r'^(\d+)\.artifact[-_]*b$',
        # Video transcript with numbers
        r'^video[_\s]*transcript[_\s]*(\d+)$',
        # Generic artifact patterns with clear numbers
        r'^artifact[_\s]*(\d+)[_\s]*transcript$',
        # Artifact b with lecture patterns (like artifact_b_lecture75.md)
        r'^artifact[_\s]*b[_\s]*lecture[_\s]*(\d+)$',
        r'^artifact[_\s]*b[_\s]*lecture(\d+)$',
        # Artifact b transcript with number (like artifact_b_transcript_61.md)
        r'^artifact[_\s]*b[_\s]*transcript[_\s]*(\d+)$'
    ]
    
    for pattern in transcript_patterns:
        match = re.search(pattern, base_name.lower())
        if match:
            # Find the first group that contains digits
            lecture_num = None
            for group in match.groups():
                if group and group.isdigit():
                    lecture_num = group
                    break
            
            if lecture_num:
                std_lecture = standardize_lecture_number(lecture_num)
                expected_name = f"Lecture {std_lecture}{ext}"
                if filename != expected_name:
                    result["corrected"] = expected_name
                    result["needs_renaming"] = True
                result["type"] = "transcript"
                return result
    
    # Check for slide patterns - COMPREHENSIVE LIST
    slide_patterns = [
        # Basic slide patterns
        r'^(\d+)[-_]*slides?$',
        r'^(\d+)[-_]*slide[_\s]*content$',
        r'^slide[_\s]*content[_\s]*(\d+)$',
        r'^(\d+)[-_]*s$',
        r'^(\d+)[-_]*c$',
        # Lecture slides patterns - ALL VARIATIONS
        r'^lecture(\d+)[-_]*slides?$',               # lectureXX-slides, lectureXX_slides
        r'^lecture[_\s]*(\d+)[-_]*slides?$',         # lecture_XX-slides, lecture XX-slides
        r'^lecture[_\s]*(\d+)[_\s]*slides?$',        # lecture_XX_slides, lecture XX slides
        r'^lecture(\d+)[_\s]*slides?$',              # lectureXX_slides, lectureXX slides
        # Handle typos like "slideas" instead of "slides" - ALL VARIATIONS
        r'^lecture[_\s]*(\d+)[_\s]*slideas$',        # lecture_XX_slideas
        r'^lecture(\d+)[_\s]*slideas$',              # lectureXX_slideas
        r'^(\d+)[_\s]*slideas$',                     # XX_slideas
        r'^(\d+)[-_]*slideas$',                      # XX-slideas, XX_slideas
        # Artifact patterns
        r'^(\d+)[-_]*artifact[-_]*c$',
        r'^lecture[_\s]*(\d+)[_\s]*artifact[_\s]*c$',
        r'^lecture(\d+)[_\s]*slide[_\s]*content$',
        r'^lecture[_\s]*(\d+)[_\s]*slide[_\s]*content$',
        # Single letter with number at start
        r'^(\d+)[-_]*c$',
        # Artifact c with lecture patterns (like artifact_c_lecture62.md)
        r'^artifact[_\s]*c[_\s]*lecture[_\s]*(\d+)$',
        r'^artifact[_\s]*c[_\s]*lecture(\d+)$',
        # Artifact c slides pattern (like artifact_c_slides_61.md)
        r'^artifact[_\s]*c[_\s]*slides?[_\s]*(\d+)$'
    ]
    
    for pattern in slide_patterns:
        match = re.search(pattern, base_name.lower())
        if match:
            # Find the first group that contains digits
            lecture_num = None
            for group in match.groups():
                if group and group.isdigit():
                    lecture_num = group
                    break
            
            if lecture_num:
                std_lecture = standardize_lecture_number(lecture_num)
                expected_name = f"{std_lecture}-slides{ext}"
                if filename != expected_name:
                    result["corrected"] = expected_name
                    result["needs_renaming"] = True
                result["type"] = "slide"
                return result
    
    # Check for summary patterns - COMPREHENSIVE LIST
    summary_patterns = [
        # Basic summary patterns
        r'^(\d+)[-_]*summary$',
        r'^(\d+)[-_]*d$',
        r'^(\d+)[-_]*artifact[-_]*d$',
        r'^lecture[_\s]*(\d+)[_\s]*artifact[_\s]*d$',
        # Lecture summary patterns - ALL VARIATIONS
        r'^lecture[_\s]*(\d+)[_\s]*summary$',         # lecture_XX_summary, lecture XX summary
        r'^lecture(\d+)[_\s]*summary$',               # lectureXX_summary, lectureXX summary
        r'^lecture(\d+)[-_]*summary$',                # lectureXX-summary, lectureXX_summary
        r'^lecture[_\s]*(\d+)[-_]*summary$',          # lecture_XX-summary, lecture XX-summary
        r'^lecture(\d+)[_\s]*video[_\s]*summary$',
        r'^lecture[_\s]*(\d+)[_\s]*video[_\s]*summary$',
        # Lecture summary with duplicate indicators (like lecture11_summary (1).md)
        r'^lecture(\d+)[_\s]*summary[_\s]*\(\d+\)$',
        r'^lecture[_\s]*(\d+)[_\s]*summary[_\s]*\(\d+\)$',
        # Video summary patterns (like video_summary_56.md)
        r'^video[_\s]*summary[_\s]*(\d+)$',
        # Artifact patterns
        r'^artifact[_\s]*(\d+)[_\s]*summary$',
        r'^(\d+)[-_]*artifact[_\s]*d[_\s]*summary$',
        r'^(\d+)[-_]*artifact[_\s]*d$',
        # Artifact d summary with number (like artifact_d_summary_61.md)
        r'^artifact[_\s]*d[_\s]*summary[_\s]*(\d+)$',
        # Video summary with numbers
        r'^video[_\s]*transcript[_\s]*summary[_\s]*(\d+)$',
        # Artifact d with lecture patterns (like artifact_d_lecture76.md)
        r'^artifact[_\s]*d[_\s]*lecture[_\s]*(\d+)$',
        r'^artifact[_\s]*d[_\s]*lecture(\d+)$'
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, base_name.lower())
        if match:
            # Find the first group that contains digits
            lecture_num = None
            for group in match.groups():
                if group and group.isdigit():
                    lecture_num = group
                    break
            
            if lecture_num:
                std_lecture = standardize_lecture_number(lecture_num)
                expected_name = f"{std_lecture}-summary{ext}"
                if filename != expected_name:
                    result["corrected"] = expected_name
                    result["needs_renaming"] = True
                result["type"] = "summary"
                return result
    
    # Check for presentation patterns (PPTX files)
    if ext.lower() == '.pptx':
        # Simple pattern to match just numbers (like "01", "1", "02", etc.)
        number_match = re.search(r'^(\d+)$', base_name)
        if number_match:
            lecture_num = number_match.group(1)
            std_lecture = standardize_lecture_number(lecture_num)
            expected_name = f"Lecture {std_lecture}{ext}"
            if filename != expected_name:
                result["corrected"] = expected_name
                result["needs_renaming"] = True
            result["type"] = "presentation"
            return result
        
        # Pattern for files already starting with "lecture" but needing standardization
        lecture_match = re.search(r'^lecture[_\s]*(\d+)$', base_name.lower())
        if lecture_match:
            lecture_num = lecture_match.group(1)
            std_lecture = standardize_lecture_number(lecture_num)
            expected_name = f"Lecture {std_lecture}{ext}"
            if filename != expected_name:
                result["corrected"] = expected_name
                result["needs_renaming"] = True
            result["type"] = "presentation"
            return result
    
    return result

def detect_duplicates_by_target_name(all_files: List[Tuple[str, str]]) -> Dict[str, List[Tuple[str, str, float]]]:
    """
    Detect files that would have the same target name after renaming
    Returns a dictionary where keys are target names and values are lists of (file_type, file_path, mod_time)
    """
    target_groups = {}
    
    for file_type, file_path in all_files:
        filename = os.path.basename(file_path)
        rename_info = analyze_filename_for_renaming(filename)
        
        # Skip files that should be deleted
        if rename_info.get("should_delete", False):
            continue
            
        # Get the target name (what it would be renamed to)
        target_name = rename_info["corrected"]
        
        # Get file modification time
        try:
            mod_time = os.path.getmtime(file_path)
        except OSError:
            mod_time = 0
        
        # Group by directory + target name to handle duplicates within same directory
        dir_path = os.path.dirname(file_path)
        full_target_key = os.path.join(dir_path, target_name)
        
        if full_target_key not in target_groups:
            target_groups[full_target_key] = []
        
        target_groups[full_target_key].append((file_type, file_path, mod_time))
    
    # Only return groups that have duplicates
    return {k: v for k, v in target_groups.items() if len(v) > 1}

def analyze_files_for_renaming() -> Tuple[Dict, Dict, Dict]:
    """
    Analyze all files in the input directory for renaming and deletion
    
    Returns:
        Tuple of (course_data, file_mapping, delete_mapping)
    """
    input_dir = get_input_directory()
    
    # Get all files by type
    transcripts = find_transcript_files(input_dir)
    slides = find_slide_files(input_dir)
    summaries = find_summary_files(input_dir)
    presentations = find_presentation_files(input_dir)
    
    # Also find ALL markdown and text files for deletion analysis
    all_md_txt_files = find_files(input_dir, "*.md") + find_files(input_dir, "*.txt")
    
    # Group data by course
    course_data = {}
    file_mapping = {}
    delete_mapping = {}
    
    # Process all files for renaming and detect duplicates
    all_files = []
    all_files.extend([("transcript", f) for f in transcripts])
    all_files.extend([("slide", f) for f in slides])
    all_files.extend([("summary", f) for f in summaries])
    all_files.extend([("presentation", f) for f in presentations])
    
    # Detect and handle duplicates based on what they would be renamed to
    duplicate_groups = detect_duplicates_by_target_name(all_files)
    
    # Process duplicates - mark older files for deletion
    files_to_delete_as_duplicates = set()
    for target_key, duplicate_files in duplicate_groups.items():
        if len(duplicate_files) > 1:
            # Sort by modification time, keep the latest
            sorted_files = sorted(duplicate_files, key=lambda x: x[2], reverse=True)
            latest_file = sorted_files[0]
            
            # Mark older files for deletion
            for file_type, file_path, mod_time in sorted_files[1:]:
                files_to_delete_as_duplicates.add(file_path)
                filename = os.path.basename(file_path)
                latest_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_file[2]))
                delete_mapping[file_path] = {
                    "filename": filename,
                    "reason": f"Duplicate file (keeping latest version from {latest_time})",
                    "type": "duplicate",
                    "course": "Multiple"
                }

    for file_type, file_path in all_files:
        # Skip files marked for deletion as duplicates
        if file_path in files_to_delete_as_duplicates:
            continue
        
        # Get filename for processing
        filename = os.path.basename(file_path)
            
        # Extract course information
        course, lecture, _ = extract_course_lecture_section(file_path)
        
        # Get the directory path to extract full course name if possible
        dir_path = os.path.dirname(file_path)
        dir_parts = dir_path.split(os.sep)
        
        # Better course detection from directory structure
        if not course:
            # Look for course directories in the path
            for part in dir_parts:
                if re.search(r'course\s*\d+', part.lower()) or re.search(r'^c\d+', part.lower()):
                    course = part
                    break
                elif re.search(r'\d+', part) and len(part) <= 10:  # Likely a course number/name
                    course = part
                    break
        
        # If we found a course, use it; otherwise try to extract from path
        if course:
            # Check if it's just a number, then format it nicely
            if re.match(r'^\d+$', course):
                course = f"Course {course}"
            # Keep the original directory name if it already contains "Course"
        else:
            # Look at the relative path structure
            relative_path = os.path.relpath(file_path, get_input_directory())
            path_parts = relative_path.split(os.sep)
            
            # Use the first directory as course if it exists
            filename = os.path.basename(file_path)
            if len(path_parts) > 1 and path_parts[0] != filename:
                course = path_parts[0]
            else:
                course = "Uncategorized"
        
        if not lecture:
            # Try to extract lecture number from filename
            filename = os.path.basename(file_path)
            match = re.search(r'(\d+)', filename)
            lecture = match.group(1) if match else "unknown"
        
        # Standardize lecture number
        std_lecture = standardize_lecture_number(lecture)
        
        # Analyze file for renaming
        filename = os.path.basename(file_path)
        rename_info = analyze_filename_for_renaming(filename)
        
        # If file should be deleted, add to delete mapping instead
        if rename_info.get("should_delete", False):
            delete_mapping[file_path] = {
                "filename": filename,
                "reason": rename_info.get("reason", "Unknown reason"),
                "type": rename_info.get("type", "delete"),
                "course": course
            }
            continue
        
        # Create course entry if it doesn't exist
        if course not in course_data:
            course_data[course] = {}
        
        # Create lecture entry if it doesn't exist
        lecture_key = f"Lecture {std_lecture}"
        if lecture_key not in course_data[course]:
            course_data[course][lecture_key] = {
                "transcript": {"current": None, "corrected": None, "needs_renaming": False},
                "slide": {"current": None, "corrected": None, "needs_renaming": False},
                "summary": {"current": None, "corrected": None, "needs_renaming": False},
                "presentation": {"current": None, "corrected": None, "needs_renaming": False}
            }
        
        # Add file info
        course_data[course][lecture_key][file_type]["current"] = filename
        course_data[course][lecture_key][file_type]["corrected"] = rename_info["corrected"]
        course_data[course][lecture_key][file_type]["needs_renaming"] = rename_info.get("needs_renaming", filename != rename_info["corrected"])
        
        # Add to file mapping
        file_mapping[file_path] = {
            "type": file_type,
            "course": course,
            "lecture": lecture_key,
            "current": filename,
            "corrected": rename_info["corrected"],
            "needs_renaming": rename_info.get("needs_renaming", filename != rename_info["corrected"]),
            "should_delete": False,
            "full_path": file_path
        }
    
    # Process remaining files for deletion (files not captured by the main patterns)
    processed_files = set(f[1] for f in all_files)
    for file_path in all_md_txt_files:
        if file_path not in processed_files:
            filename = os.path.basename(file_path)
            rename_info = analyze_filename_for_renaming(filename)
            
            if rename_info.get("should_delete", False):
                # Extract course information for organization
                course, _, _ = extract_course_lecture_section(file_path)
                dir_path = os.path.dirname(file_path)
                dir_parts = dir_path.split(os.sep)
                
                if course:
                    for part in dir_parts:
                        if re.search(rf'{course}\b', part) or re.search(rf'course\s*{course}', part.lower()):
                            course = part
                            break
                    if not course:
                        course = f"Course {course}"
                else:
                    course = "Uncategorized"
                
                delete_mapping[file_path] = {
                    "filename": filename,
                    "reason": rename_info.get("reason", "Unknown reason"),
                    "type": rename_info.get("type", "delete"),
                    "course": course
                }
    
    return course_data, file_mapping, delete_mapping

def rename_files(file_mapping: Dict) -> List[Dict]:
    """
    Rename files according to the mapping
    
    Args:
        file_mapping: Dictionary mapping file paths to renaming information
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for original_path, info in file_mapping.items():
        try:
            # Check if the file actually needs renaming (either from the mapping or by comparing names)
            needs_renaming = info.get("needs_renaming", True)
            if info["current"] == info["corrected"] or not needs_renaming:
                results.append({
                    "file": info["current"],
                    "status": "unchanged",
                    "message": "No renaming needed"
                })
                continue
            
            # Get the directory path and create new path with corrected filename
            original_dir = os.path.dirname(original_path)
            new_path = os.path.join(original_dir, info["corrected"])
            
            # Check if the destination file already exists to avoid conflicts
            if os.path.exists(new_path) and original_path != new_path:
                results.append({
                    "file": info["current"],
                    "status": "error",
                    "message": f"Cannot rename: Destination file {info['corrected']} already exists"
                })
                continue
            
            # Simply rename the file (move operation) instead of copying
            os.rename(original_path, new_path)
            
            results.append({
                "file": info["current"],
                "new_file": info["corrected"],
                "status": "renamed",
                "message": f"Renamed to {info['corrected']}"
            })
        except Exception as e:
            results.append({
                "file": info["current"],
                "status": "error",
                "message": f"Error: {str(e)}"
            })
    
    return results

def delete_files(delete_mapping: Dict) -> List[Dict]:
    """
    Delete files according to the mapping
    
    Args:
        delete_mapping: Dictionary mapping file paths to deletion information
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for file_path, info in delete_mapping.items():
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                results.append({
                    "file": info["filename"],
                    "status": "deleted",
                    "message": f"Deleted: {info['reason']}"
                })
            else:
                results.append({
                    "file": info["filename"],
                    "status": "not_found",
                    "message": "File not found (already deleted?)"
                })
        except Exception as e:
            results.append({
                "file": info["filename"],
                "status": "error",
                "message": f"Error deleting: {str(e)}"
            })
    
    return results

# ===== CLI IMPLEMENTATION =====

def run_rename_files(ctx_obj: Dict[str, Any], force: bool = False, delete_problematic: bool = False) -> Dict[str, Any]:
    """
    Main function to run the rename files operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Create status manager
    status_manager = StatusManager(verbose=ctx_obj.get('verbose', False))
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_files": 0, "renamed_count": 0, "deleted_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Analyzing files in: {input_dir}")
    
    # Analyze files for renaming and deletion
    with DreamletProgress(description="Analyzing files for renaming", total=100) as progress:
        progress.update(completed=20, description="Finding files...")
        
        course_data, file_mapping, delete_mapping = analyze_files_for_renaming()
        
        progress.update(completed=100, description="Analysis complete")
    
    # Calculate statistics
    total_files = len(file_mapping)
    files_to_rename = sum(1 for info in file_mapping.values() if info.get("needs_renaming", False))
    files_to_delete = len(delete_mapping)
    
    status_manager.info(f"Analysis complete: {total_files} files found, {files_to_rename} need renaming, {files_to_delete} marked for deletion")
    
    # Show analysis results
    if not ctx_obj.get('quiet', False):
        show_analysis_results(course_data, file_mapping, delete_mapping, status_manager)
    
    results = {
        "rename_results": [],
        "delete_results": [],
        "statistics": {
            "total_files": total_files,
            "files_to_rename": files_to_rename,
            "files_to_delete": files_to_delete,
            "renamed_count": 0,
            "deleted_count": 0,
            "error_count": 0
        }
    }
    
    # Handle file deletion if requested
    if delete_problematic and files_to_delete > 0:
        status_manager.info(f"Deleting {files_to_delete} problematic files...")
        
        with DreamletProgress(description="Deleting problematic files", total=files_to_delete) as progress:
            delete_results = delete_files(delete_mapping)
            progress.update(completed=files_to_delete)
        
        results["delete_results"] = delete_results
        deleted_count = sum(1 for r in delete_results if r["status"] == "deleted")
        delete_errors = sum(1 for r in delete_results if r["status"] == "error")
        
        results["statistics"]["deleted_count"] = deleted_count
        results["statistics"]["error_count"] += delete_errors
        
        status_manager.success(f"Deleted {deleted_count} files") if deleted_count > 0 else None
        status_manager.error(f"Failed to delete {delete_errors} files") if delete_errors > 0 else None
    
    # Handle file renaming
    if files_to_rename > 0:
        status_manager.info(f"Renaming {files_to_rename} files...")
        
        with DreamletProgress(description="Renaming files", total=files_to_rename) as progress:
            rename_results = rename_files(file_mapping)
            progress.update(completed=files_to_rename)
        
        results["rename_results"] = rename_results
        renamed_count = sum(1 for r in rename_results if r["status"] == "renamed")
        rename_errors = sum(1 for r in rename_results if r["status"] == "error")
        
        results["statistics"]["renamed_count"] = renamed_count
        results["statistics"]["error_count"] += rename_errors
        
        status_manager.success(f"Renamed {renamed_count} files") if renamed_count > 0 else None
        status_manager.error(f"Failed to rename {rename_errors} files") if rename_errors > 0 else None
    
    # Determine final status
    if results["statistics"]["error_count"] > 0:
        final_status = "error"
        status_message = f"Completed with {results['statistics']['error_count']} errors"
    elif results["statistics"]["renamed_count"] == 0 and results["statistics"]["deleted_count"] == 0:
        final_status = "warning"
        status_message = "No files were renamed or deleted"
    else:
        final_status = "success"
        status_message = f"Successfully processed files: {results['statistics']['renamed_count']} renamed, {results['statistics']['deleted_count']} deleted"
    
    # Show summary
    status_manager.success(status_message) if final_status == "success" else \
    status_manager.warning(status_message) if final_status == "warning" else \
    status_manager.error(status_message)
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "total_files_analyzed": total_files,
            "files_needing_rename": files_to_rename,
            "files_marked_for_deletion": files_to_delete
        },
        "processing_results": results["rename_results"] + results["delete_results"],
        "statistics": results["statistics"],
        "errors": [r["message"] for r in results["rename_results"] + results["delete_results"] if r["status"] == "error"],
        "warnings": [],
        "output_files": []
    }
    
    # Generate report
    report_path = generate_report("02", "Rename Files", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

def show_analysis_results(course_data: Dict, file_mapping: Dict, delete_mapping: Dict, status_manager: StatusManager):
    """Show analysis results in terminal format"""
    
    # Summary statistics
    total_files = len(file_mapping)
    files_to_rename = sum(1 for info in file_mapping.values() if info.get("needs_renaming", False))
    files_to_delete = len(delete_mapping)
    
    # Create summary table
    summary_table = Table(title="File Analysis Summary")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Count", style="yellow")
    
    summary_table.add_row("Files to Rename", str(files_to_rename))
    summary_table.add_row("Files to Delete", str(files_to_delete))
    summary_table.add_row("Valid Files", str(total_files))
    
    console.print(summary_table)
    
    # Show files marked for deletion if any
    if files_to_delete > 0:
        console.print("\n[bold red]Files Recommended for Deletion:[/bold red]")
        
        delete_table = Table()
        delete_table.add_column("Course", style="cyan")
        delete_table.add_column("Filename", style="white")
        delete_table.add_column("Reason", style="yellow")
        
        for file_path, info in delete_mapping.items():
            delete_table.add_row(
                info.get("course", "Unknown"),
                info["filename"],
                info["reason"]
            )
        
        console.print(delete_table)
    
    # Show renaming details by course
    if files_to_rename > 0:
        console.print("\n[bold green]Files to be Renamed by Course:[/bold green]")
        
        for course, lectures in course_data.items():
            course_has_renames = False
            course_renames = []
            
            for lecture, lecture_data in lectures.items():
                for file_type in ["transcript", "slide", "summary", "presentation"]:
                    if lecture_data[file_type]["needs_renaming"]:
                        course_has_renames = True
                        current = lecture_data[file_type]["current"]
                        corrected = lecture_data[file_type]["corrected"]
                        course_renames.append(f"  {file_type.title()}: {current} → {corrected}")
            
            if course_has_renames:
                console.print(f"\n[bold cyan]{course}:[/bold cyan]")
                for rename in course_renames:
                    console.print(rename)

@click.command()
@click.pass_context
def rename_files_cmd(ctx):
    """
    Fix incorrectly named files according to standard naming conventions
    
    This command analyzes files in the input directory and renames them to follow
    standard conventions. It can also identify and delete problematic files that
    don't fit the expected patterns.
    
    All settings are configured in config.json under "page_02_rename":
    - patterns: Renaming patterns and rules
    - remove_prefixes: Prefixes to remove from filenames
    - standardize_extensions: Whether to standardize file extensions
    - fix_spacing: Whether to fix spacing in filenames
    
    Examples:
        dreamlet run 02                    # Rename files with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_02_rename')
    
    # Extract settings from config (with defaults)
    force = not config.skip_existing  # Inverse of skip_existing
    delete_problematic = page_config.get('delete_problematic', True)
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be renamed or deleted[/yellow]")
        console.print(f"Would rename with settings: force={force}, delete_problematic={delete_problematic}")
        return
    
    # Run the rename files operation
    try:
        results = run_rename_files(ctx.obj, force, delete_problematic)
        
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
    rename_files_cmd()