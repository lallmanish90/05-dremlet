"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: BACKUP
PURPOSE: Backup copy of the rename page retained for rollback and reference.
MAIN INPUTS:
- lecture folders and source files under `input/`
MAIN OUTPUTS:
- renamed files and optional cleanup actions applied in place
REQUIRED CONFIG / ASSETS:
- `input/` directory
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none
REPLACED BY:
- `pages/02_Rename.py`
"""

from dreamlet_cli.compat import st
import os
import re
import time
import pandas as pd
import fnmatch
from typing import Dict, List, Tuple, Optional

# Local utility functions (moved from utils.file_operations)
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

def get_all_courses_from_input() -> List[str]:
    """Get a list of all courses from the input directory"""
    input_dir = get_input_directory()
    courses = {}
    
    for root, dirs, files in os.walk(input_dir):
        dir_parts = root.split(os.sep)
        
        for part in dir_parts:
            course_num = None
            full_name = part
            
            course_match = re.search(r'course\s*(\d+)', part.lower())
            if course_match:
                course_num = int(course_match.group(1))
            elif re.match(r'^\d+\s+', part):
                match = re.match(r'^(\d+)\s+', part)
                if match:
                    course_num = int(match.group(1))
            elif re.search(r'[(\[]\s*(\d+)\s*[)\]]', part):
                match = re.search(r'[(\[]\s*(\d+)\s*[)\]]', part)
                if match:
                    course_num = int(match.group(1))
            
            if course_num is not None and course_num not in courses:
                courses[course_num] = full_name
    
    return [courses[num] for num in sorted(courses.keys())]

def copy_file_to_output(input_path: str, output_path: str) -> bool:
    """Copy file from input to output location"""
    try:
        import shutil
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(input_path, output_path)
        return True
    except Exception:
        return False

st.set_page_config(page_title="01 Rename - Dreamlet", page_icon="✏️")

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

def main():
    st.title("Rename")
    st.write("Fix incorrectly named files according to standard naming conventions.")
    
    # Display examples of renaming rules
    with st.expander("Examples of Renaming Rules"):
        st.write("""
        The following examples show how files will be renamed:
        
        **Transcript Files (to be renamed as "Lecture XX"):**
        - `lec1-transcript.md` → `Lecture 01.md`
        - `lecture32_transcript.md` → `Lecture 32.md`
        - `artifact_25_transcript.md` → `Lecture 25.md`
        - `52artifact-b.md` → `Lecture 52.md`
        - `video_transcript 40.txt` → `Lecture 40.txt`
        
        **Slide Files (to be renamed as "XX-slides"):**
        - `slide_content_28.md` → `28-slides.md`
        - `3-c.md` → `03-slides.md`
        - `lecture01_slide_content.md` → `01-slides.md`
        
        **Summary Files (to be renamed as "XX-summary"):**
        - `artifact_25_summary.md` → `25-summary.md`
        - `17-artifact_d_summary.md` → `17-summary.md`
        - `lecture32_summary.md` → `32-summary.md`
        - `video_transcript_summary 40.txt` → `40-summary.txt`
        
        **Files to be DELETED:**
        - `lecture_06_outline.md` → DELETE (outline files not supported)
        - `lecture_42_video_transcript_summary.md` → DELETE (hybrid files not supported)
        - `video_transcript (1).md` → DELETE (duplicate indicators)
        - `artifact_b_transcript.md` → DELETE (no clear lecture number)
        - `video_transcript.md` → DELETE (generic name without lecture number)
        
        **Files already correctly named:**
        - `08-slides.md` → No change needed
        - `Lecture 07.md` → No change needed
        
        Files will be standardized to have a two-digit lecture number and a consistent naming format.
        """)
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Analyze files for renaming
    if st.button("Analyze Files for Renaming and Deletion"):
        with st.spinner("Analyzing files..."):
            # Display progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize progress steps
            status_text.text("Finding files...")
            progress_bar.progress(0.2)
            time.sleep(0.5)
            
            status_text.text("Analyzing file names...")
            progress_bar.progress(0.5)
            
            # Analyze files
            course_data, file_mapping, delete_mapping = analyze_files_for_renaming()
            
            status_text.text("Generating renaming and deletion tables...")
            progress_bar.progress(0.8)
            time.sleep(0.5)
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("Analysis complete")
            
            # Store results in session state
            st.session_state.course_data = course_data
            st.session_state.file_mapping = file_mapping
            st.session_state.delete_mapping = delete_mapping
    
    # Display results if available
    if hasattr(st.session_state, 'course_data') and hasattr(st.session_state, 'file_mapping'):
        course_data = st.session_state.course_data
        file_mapping = st.session_state.file_mapping
        delete_mapping = getattr(st.session_state, 'delete_mapping', {})
        
        # Summary statistics
        total_files = len(file_mapping)
        files_to_rename = sum(1 for info in file_mapping.values() if info.get("needs_renaming", False))
        files_to_delete = len(delete_mapping)
        
        st.header("File Analysis Results")
        
        # Display statistics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Files to Rename", files_to_rename)
        with col2:
            st.metric("Files to Delete", files_to_delete)
        with col3:
            st.metric("Valid Files", total_files)
        
        # Show files marked for deletion first if any exist
        if files_to_delete > 0:
            st.subheader("Files Recommended for Deletion")
            st.warning("The following files have issues and should be deleted:")
            
            # Group deletion files by course
            delete_by_course = {}
            for file_path, info in delete_mapping.items():
                course = info.get("course", "Uncategorized")
                if course not in delete_by_course:
                    delete_by_course[course] = []
                delete_by_course[course].append({
                    "filename": info["filename"],
                    "reason": info["reason"],
                    "path": file_path
                })
            
            # Display deletion table
            delete_table_data = []
            for course, files in delete_by_course.items():
                for file_info in files:
                    delete_table_data.append({
                        "Course": course,
                        "Filename": file_info["filename"],
                        "Reason for Deletion": file_info["reason"]
                    })
            
            if delete_table_data:
                delete_df = pd.DataFrame(delete_table_data)
                st.dataframe(delete_df, use_container_width=True)
            
            # Option to apply deletion
            if st.button("Delete Problematic Files", type="secondary"):
                with st.spinner("Deleting files..."):
                    delete_results = delete_files(delete_mapping)
                    
                    deleted_count = sum(1 for r in delete_results if r["status"] == "deleted")
                    error_count = sum(1 for r in delete_results if r["status"] == "error")
                    
                    st.subheader("Deletion Results")
                    if deleted_count > 0:
                        st.success(f"Successfully deleted {deleted_count} files")
                    if error_count > 0:
                        st.error(f"Errors occurred while deleting {error_count} files")
                        with st.expander("Deletion Errors"):
                            for result in delete_results:
                                if result["status"] == "error":
                                    st.write(f"❌ {result['file']}: {result['message']}")
        
        # Display renaming details by course
        if files_to_rename > 0:
            st.subheader("Files to be Renamed by Course")
        
        # Sort courses in ascending order based on course number
        def extract_course_number(course_name):
            # Extract number from course name for sorting
            match = re.search(r'(\d+)', course_name)
            if match:
                return int(match.group(1))
            else:
                return 999  # Default for items without numbers
                
        sorted_courses = sorted(course_data.keys(), key=extract_course_number)
        
        # Create accordion for course results
        for course in sorted_courses:
            with st.expander(f"{course}"):
                # Create a DataFrame for this course's files
                course_lectures = course_data[course]
                
                # Sort lectures by number
                def extract_lecture_number(lecture_name):
                    # Extract number from lecture name for sorting
                    match = re.search(r'(\d+)', lecture_name)
                    if match:
                        return int(match.group(1))
                    else:
                        return 999  # Default for items without numbers
                        
                sorted_lectures = sorted(course_lectures.keys(), key=extract_lecture_number)
                
                # Create data for the table
                table_data = []
                
                for lecture in sorted_lectures:
                    lecture_data = course_lectures[lecture]
                    
                    # Add row for this lecture
                    row = {
                        "Transcript Current": lecture_data["transcript"]["current"] or "",
                        "Transcript Corrected": lecture_data["transcript"]["corrected"] or "",
                        "Slide Current": lecture_data["slide"]["current"] or "",
                        "Slide Corrected": lecture_data["slide"]["corrected"] or "",
                        "Summary Current": lecture_data["summary"]["current"] or "",
                        "Summary Corrected": lecture_data["summary"]["corrected"] or "",
                        "Presentation Current": lecture_data["presentation"]["current"] or "",
                        "Presentation Corrected": lecture_data["presentation"]["corrected"] or ""
                    }
                    
                    table_data.append(row)
                
                # Convert to DataFrame and display
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.table(df)
                else:
                    st.write("No files found for this course.")
        
        # Option to apply renaming
        st.header("Apply Renaming")
        st.write("Click the button below to apply the proposed renaming to files.")
        
        if st.button("Rename Files", disabled=files_to_rename == 0):
            with st.spinner("Renaming files..."):
                # Display progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process renaming
                status_text.text("Renaming files...")
                
                # Rename files and get results
                rename_results = rename_files(file_mapping)
                
                # Complete
                progress_bar.progress(1.0)
                status_text.text("Renaming complete")
                
                # Display results
                renamed_count = sum(1 for r in rename_results if r["status"] == "renamed")
                unchanged_count = sum(1 for r in rename_results if r["status"] == "unchanged")
                error_count = sum(1 for r in rename_results if r["status"] == "error")
                
                st.subheader("Renaming Results")
                st.write(f"✅ Successfully renamed: {renamed_count}")
                st.write(f"⏭️ Unchanged: {unchanged_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Detailed results in an expander (errors only)
                if error_count > 0:
                    with st.expander("Detailed Error Results"):
                        for result in rename_results:
                            if result["status"] == "error":
                                st.write(f"❌ {result['file']}: {result['message']}")
                else:
                    st.success("No errors occurred during renaming.")

if __name__ == "__main__":
    main()
