import os
import re
import shutil
import fnmatch
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Set
import glob

def get_all_files(directory: str, include_hidden: bool = False) -> List[str]:
    """
    Get all files in a directory recursively
    
    Args:
        directory: Directory to search in
        include_hidden: Whether to include hidden files
        
    Returns:
        List of file paths
    """
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            # Skip hidden files if not explicitly included
            if not include_hidden and file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files

def ensure_directory_exists(directory_path: str) -> None:
    """
    Create directory if it doesn't exist
    
    Args:
        directory_path: Path to the directory to create
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_input_directory() -> str:
    """
    Get the path to the input directory
    
    Returns:
        Path to the input directory
    """
    # Default input directory is in the current working directory
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def get_output_directory() -> str:
    """
    Get the path to the output directory
    Note: As per new requirements, this now returns the input directory path
    to ensure all operations happen within the input folder itself.
    
    Returns:
        Path to the input directory (no separate output directory)
    """
    # Return the input directory as the output directory
    return get_input_directory()

def map_input_to_output_path(input_path: str) -> str:
    """
    Convert an input path to its corresponding output path
    Note: As per new requirements, this now returns the input path itself
    since all operations should happen within the input directory.
    
    Args:
        input_path: Path in the input directory
        
    Returns:
        The same input path (no separate output path)
    """
    # Simply return the input path as is
    return input_path

def find_files(directory: str, pattern: str) -> List[str]:
    """
    Find all files matching a pattern in a directory (recursively)
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match files against
        
    Returns:
        List of file paths
    """
    result = []
    for root, _, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            result.append(os.path.join(root, filename))
    return result

def find_transcript_files(directory: str) -> List[str]:
    """
    Find all transcript files in a directory
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of transcript file paths
    """
    # Look for text files that might be transcripts
    transcripts = []
    
    # Pattern for transcript files - typically named like "Lecture X.txt" or similar
    transcript_patterns = [
        "Lecture*.txt", "Lecture*.md", 
        "*lecture*.txt", "*lecture*.md",
        "*transcript*.txt", "*transcript*.md",
        "*artifact_b*.txt", "*artifact_b*.md",  # New underscore artifact patterns
        "*artifact-b*.txt", "*artifact-b*.md",  # Hyphen artifact patterns
        "*.txt", "*.md"  # Include all text and markdown files for further filtering
    ]
    
    for pattern in transcript_patterns:
        transcripts.extend(find_files(directory, pattern))
    
    # Filter out files that are actually slide files (contain "slide" in filename)
    transcripts = [f for f in transcripts if "slide" not in os.path.basename(f).lower()]
    
    # Also filter out files that match the slide pattern "NN-s.md" or "NN-s.txt"
    transcripts = [f for f in transcripts if not re.search(r'^\d+-s\.(md|txt)$', os.path.basename(f).lower())]
    
    # Filter out summary files - explicitly exclude patterns that would identify summary files
    transcripts = [f for f in transcripts if not re.search(r'summary', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-d\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-artifact-d\.(md|txt)$', os.path.basename(f).lower())]
    
    # Remove duplicates that might have been added by the broader pattern
    transcripts = list(set(transcripts))
    
    return transcripts

def find_slide_files(directory: str) -> List[str]:
    """
    Find all slide description files in a directory
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of slide file paths
    """
    # Look for text files that might be slide descriptions
    slides = []
    
    # Pattern for slide files - typically named like "X-slides.txt" or similar
    slide_patterns = [
        "*-slides.txt", "*-slides.md",
        "*-slide.txt", "*-slide.md",
        "*slides*.txt", "*slides*.md",
        "*slide*.txt", "*slide*.md",
        "*-s.txt", "*-s.md",  # Add specific pattern for the "-s" suffix
        "*artifact_c*.txt", "*artifact_c*.md",  # New underscore artifact patterns
        "*artifact-c*.txt", "*artifact-c*.md",  # Hyphen artifact patterns
        "*slide_content*.txt", "*slide_content*.md"  # New slide content patterns
    ]
    
    for pattern in slide_patterns:
        slides.extend(find_files(directory, pattern))
    
    # Additionally find all text and markdown files to check for the "-s" pattern
    all_text_files = find_files(directory, "*.txt") + find_files(directory, "*.md")
    
    # Check each file for the pattern "NN-s.md" or "NN-s.txt"
    for file_path in all_text_files:
        filename = os.path.basename(file_path)
        if re.search(r'^\d+-s\.(md|txt)$', filename.lower()):
            if file_path not in slides:
                slides.append(file_path)
    
    # Remove duplicates that might have been added
    slides = list(set(slides))
    
    return slides

def find_summary_files(directory: str) -> List[str]:
    """
    Find all summary files in a directory
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of summary file paths
    """
    # Look for text files that might be summary files
    summaries = []
    
    # Pattern for summary files - typically named like "XX-summary.txt" or similar
    summary_patterns = [
        "*-summary.txt", "*-summary.md",
        "*-d.txt", "*-d.md",
        "*-artifact-d.txt", "*-artifact-d.md",
        "*artifact_d*.txt", "*artifact_d*.md",  # New underscore artifact patterns
        "*_summary*.txt", "*_summary*.md",  # New underscore summary patterns
        "*video_summary*.txt", "*video_summary*.md"  # New video summary patterns
    ]
    
    for pattern in summary_patterns:
        summaries.extend(find_files(directory, pattern))
    
    # Remove duplicates that might have been added
    summaries = list(set(summaries))
    
    return summaries

def find_presentation_files(directory: str) -> List[str]:
    """
    Find all presentation files in a directory
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of presentation file paths
    """
    # Look for PowerPoint files
    return find_files(directory, "*.pptx")

def find_non_supported_files(directory: str) -> List[str]:
    """
    Find all files that are not supported (not txt, md, pptx, or common media files)
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of non-supported file paths
    """
    # Get all files
    all_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            all_files.append(os.path.join(root, filename))
    
    # Define supported extensions
    # Text and document formats
    supported_extensions = ['.txt', '.md', '.pptx']
    
    # Common media formats that should not be reported as "unsupported"
    # as per requirements
    media_extensions = [
        # Image formats
        '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.svg', '.webp', '.img',
        # Audio formats
        '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
        # Video formats
        '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm'
    ]
    
    # Combine all accepted extensions
    accepted_extensions = supported_extensions + media_extensions
    
    # Filter to find non-supported files
    non_supported = []
    for file_path in all_files:
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in accepted_extensions:
            non_supported.append(file_path)
    
    return non_supported

def group_files_by_lecture(
    transcripts: List[str], 
    slides: List[str],
    summaries: List[str],
    presentations: List[str]
) -> Dict[str, Dict[str, str]]:
    """
    Group transcript, slide, summary, and presentation files by lecture
    
    Args:
        transcripts: List of transcript file paths
        slides: List of slide file paths
        summaries: List of summary file paths
        presentations: List of presentation file paths
        
    Returns:
        Dictionary mapping lecture identifiers to dictionaries with transcript, slide, summary, and presentation paths
    """
    grouped = {}
    
    # Extract course and lecture information from paths
    for file_path in transcripts + slides + summaries + presentations:
        course, lecture, _ = extract_course_lecture_section(file_path)
        
        if not course and not lecture:
            # If our extraction function didn't find anything, try a fallback approach
            dir_parts = os.path.dirname(file_path).split(os.sep)
            filename = os.path.basename(file_path)
            
            # Try to determine course and lecture from additional patterns
            for part in dir_parts:
                # Look for any numbers in directory names
                numbers = re.findall(r'\d+', part)
                if numbers and not course:
                    course = numbers[0]  # Take the first number as a course
                    break
            
            # Extract any numbers from filename if lecture is still None
            if not lecture:
                filename_numbers = re.findall(r'\d+', filename)
                if filename_numbers:
                    lecture = filename_numbers[0]  # Take the first number as a lecture
        
        # If we found either course or lecture, create a key and group
        if course or lecture:
            course_str = f"Course {course}" if course else "Unknown Course"
            lecture_str = f"Lecture {lecture}" if lecture else "Unknown Lecture"
            key = f"{course_str} - {lecture_str}"
            
            if key not in grouped:
                grouped[key] = {"transcript": None, "slide": None, "summary": None, "presentation": None}
            
            # Determine file type and add to group
            filename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            # Determine file type based on content and extension
            if ext == '.pptx':
                grouped[key]["presentation"] = file_path
            elif ext in ['.txt', '.md']:
                # First check for summary markers
                if "summary" in filename.lower() or "-d" in filename.lower() or "-artifact-d" in filename.lower():
                    grouped[key]["summary"] = file_path
                # Then check for slide markers
                elif "slide" in filename.lower() or "-s" in filename.lower() or "-c" in filename.lower() or "-artifact-c" in filename.lower():
                    grouped[key]["slide"] = file_path
                # Otherwise, treat as transcript
                else:
                    grouped[key]["transcript"] = file_path
    
    return grouped

def extract_course_lecture_section(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract course, lecture, and section information from a file path
    
    Args:
        file_path: Path to extract information from
        
    Returns:
        Tuple of (course, lecture, section) - any or all may be None if not found
    """
    # Extract directory parts from the path
    dir_parts = os.path.normpath(file_path).split(os.sep)
    
    # Initialize variables
    course = None
    lecture = None
    section = None
    
    # Try to extract course from directory names
    for part in dir_parts:
        # First try explicit "course X" patterns
        course_match = re.search(r'course\s*(\d+)', part.lower())
        if course_match:
            course = course_match.group(1)
            break
        # Then try directories that start with a number (like "2 Advanced GenAI Security")
        number_start_match = re.match(r'^(\d+)\s+', part)
        if number_start_match:
            course = number_start_match.group(1)
            break
        # Or try directories that contain a number in parentheses or brackets
        bracket_match = re.search(r'[(\[]\s*(\d+)\s*[)\]]', part)
        if bracket_match:
            course = bracket_match.group(1)
            break
    
    # Try to extract lecture/section from directory names or filename
    filename = os.path.basename(file_path)
    
    # Check for lecture in filename
    lecture_patterns = [
        r'lecture\s*(\d+)',    # Lecture 01, lecture01, etc.
        r'lec\s*(\d+)',        # Lec 01, lec01, etc.
        r'^(\d+)[-\s]',        # 01-slides, 01 - transcript, etc.
        r'^\w+\s*(\d+)'        # Lecture 01, Lec 01, etc.
    ]
    
    for pattern in lecture_patterns:
        lecture_match = re.search(pattern, filename.lower())
        if lecture_match:
            lecture = lecture_match.group(1)
            break
    
    # If not found in filename, check directories
    if not lecture:
        for part in dir_parts:
            for pattern in lecture_patterns:
                lecture_match = re.search(pattern, part.lower())
                if lecture_match:
                    lecture = lecture_match.group(1)
                    break
            if lecture:
                break
    
    # Check for section in directories
    section_patterns = [
        r'section\s*(\d+)',    # Section 01, section01, etc.
        r'sec\s*(\d+)'         # Sec 01, sec01, etc.
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

def get_all_courses_from_input() -> List[str]:
    """
    Get a list of all courses from the input directory
    
    Returns:
        List of course identifiers sorted in ascending order
    """
    input_dir = get_input_directory()
    courses = {}  # Dictionary to store course number and full name
    
    # Walk through all directories
    for root, dirs, files in os.walk(input_dir):
        dir_parts = root.split(os.sep)
        
        # Look for course directories using the same patterns as extract_course_lecture_section
        for part in dir_parts:
            course_num = None
            full_name = part
            
            # Try explicit "course X" patterns
            course_match = re.search(r'course\s*(\d+)', part.lower())
            if course_match:
                course_num = int(course_match.group(1))
            
            # Try directories that start with a number (like "2 Advanced GenAI Security")
            elif re.match(r'^\d+\s+', part):
                match = re.match(r'^(\d+)\s+', part)
                if match:
                    course_num = int(match.group(1))
            
            # Try directories that contain a number in parentheses or brackets
            elif re.search(r'[(\[]\s*(\d+)\s*[)\]]', part):
                match = re.search(r'[(\[]\s*(\d+)\s*[)\]]', part)
                if match:
                    course_num = int(match.group(1))
            
            if course_num is not None:
                # Store the full directory name as the course name
                courses[course_num] = full_name
    
    # Sort courses by number and use full names
    return [courses[num] for num in sorted(courses.keys())]

def standardize_lecture_number(lecture_num: str) -> str:
    """
    Standardize lecture number format
    
    Args:
        lecture_num: Lecture number as string
        
    Returns:
        Standardized lecture number (e.g., "01", "02", "100", etc.)
    """
    try:
        # Convert to integer
        num = int(lecture_num)
        
        # Use different formatting based on number size
        if num < 100:
            # For numbers 1-99, use leading zero (01, 02, ..., 99)
            return f"{num:02d}"
        else:
            # For numbers 100+, no special formatting needed (100, 101, ...)
            return str(num)
    except ValueError:
        # If not a valid number, return as is
        return lecture_num

def analyze_filename_for_renaming(filename: str) -> Dict[str, Union[str, bool]]:
    """
    Analyze a filename to determine the correct standardized name
    
    Args:
        filename: Original filename
        
    Returns:
        Dictionary with original and corrected names
    """
    base, ext = os.path.splitext(filename)
    corrected = base
    lecture_num = None
    file_type = None
    
    # === CATEGORY A: Slide Files (to be renamed to NN-slides.ext) ===
    
    # Pattern 1: (\d+)[-_]?(s|slide|slides)(-content)?\.(md|txt)
    # Examples: 1-slide.md, 27-s.txt, 18-slides.txt, 1-slide-content.md, 11-s.md
    pattern1 = re.search(r'^(\d+)[-_]?(s|slide|slides)(?:-content)?$', base.lower())
    
    # Handle special case for "-s" suffix which might not be caught by the regex
    if not pattern1 and "-s" in base.lower():
        s_pattern = re.search(r'^(\d+)-s$', base.lower())
        if s_pattern:
            pattern1 = s_pattern  # Use this match instead
    if pattern1:
        lecture_num = pattern1.group(1)
        file_type = "slide"
    
    # Pattern 2: lec(\d+)-slides\.(md|txt)
    # Examples: lec1-slides.txt, lec23-slides.md
    if not lecture_num:
        pattern2 = re.search(r'^lec(?:ture)?[-_]?(\d+)[-_]?slides$', base.lower())
        if pattern2:
            lecture_num = pattern2.group(1)
            file_type = "slide"
    
    # Pattern 3: lecture(\d+)[-_]?(slides?|slide-content)?\.(md|txt)
    # Examples: lecture10-slides.md, lecture16-slide-content.txt
    if not lecture_num:
        pattern3 = re.search(r'^lecture[-_]?(\d+)[-_]?(?:slides?|slide-content)$', base.lower())
        if pattern3:
            lecture_num = pattern3.group(1)
            file_type = "slide"
    
    # Pattern for xx-c or xx-artifact-c (new pattern for slide files)
    # Examples: 01-c.md, 27-c.txt, 01-artifact-c.md, 27-artifact-c.txt, 
    # Also handles: 15-ArtifactC.md, 6-artifactC.md, 11-artifact_c.md
    if not lecture_num:
        pattern_c = re.search(r'^(\d+)(?:[-_][aA]rtifact)?[-_]?[cC]$', base.lower())
        if pattern_c:
            lecture_num = pattern_c.group(1)
            file_type = "slide"
    
    # === CATEGORY B: Transcript/Lecture Files (to be renamed to Lecture NN.ext) ===
    
    # Pattern 4: lecture[-_]?(\d+)[-_]?transcript\.(md|txt)
    # Examples: lecture13-transcript.md, lecture-19-transcript.txt
    if not lecture_num:
        pattern4 = re.search(r'^lecture[-_]?(\d+)[-_]?transcript$', base.lower())
        if pattern4:
            lecture_num = pattern4.group(1)
            file_type = "transcript"
    
    # Pattern 5: lecture(\d+)[-_]?video[-_]?transcript\.(md|txt)
    # Examples: lecture16-video-transcript.md
    if not lecture_num:
        pattern5 = re.search(r'^lecture(\d+)[-_]?video[-_]?transcript$', base.lower())
        if pattern5:
            lecture_num = pattern5.group(1)
            file_type = "transcript"
    
    # Pattern 6: lec(\d+)[-_]?transcript\.(md|txt)
    # Examples: lec1-transcript.md, lec21-transcript.txt
    if not lecture_num:
        pattern6 = re.search(r'^lec(\d+)(?:[-_]transcript)?(?:[bB])?$', base.lower())
        if pattern6:
            lecture_num = pattern6.group(1)
            file_type = "transcript"
    
    # Pattern 7: lecture(\d+)[-_]?(?:transcript[bB]|script)\.(md|txt)
    # Examples: lecture7-transcriptB.md, lecture8-script.txt
    if not lecture_num:
        pattern7 = re.search(r'^lecture(\d+)[-_]?(?:transcript[bB]|script)$', base.lower())
        if pattern7:
            lecture_num = pattern7.group(1)
            file_type = "transcript"
    
    # Pattern for xx-b or xx-artifact-b (new pattern for transcript files)
    # Examples: 01-b.md, 27-b.txt, 01-artifact-b.md, 27-artifact-b.txt
    # Also handles: 6-artifactB.md, 11-artifact_b.md, 15-ArtifactB.md
    if not lecture_num:
        pattern_b = re.search(r'^(\d+)(?:[-_][aA]rtifact)?[-_]?[bB]$', base.lower())
        if pattern_b:
            lecture_num = pattern_b.group(1)
            file_type = "transcript"
    
    # Pattern 8: (\d+)\.(md|txt) - Plain numeric file names
    # Examples: 1.md, 27.txt, 01.md, 09.md, 09.txt, 100.md, 123.txt
    if not lecture_num:
        pattern8 = re.search(r'^(\d+)$', base)
        if pattern8:
            lecture_num = pattern8.group(1)
            file_type = "transcript"  # Default to transcript for pure numbers
    
    # Additional pattern for matching lecture in filename without any specific suffix
    if not lecture_num:
        lecture_match = re.search(r'^lecture[-_]?(\d+)$', base.lower())
        if lecture_match:
            lecture_num = lecture_match.group(1)
            file_type = "transcript"
            
    # Pattern for xx-d or xx-artifact-d (new pattern for summary files)
    # Examples: 01-d.md, 27-d.txt, 01-artifact-d.md, 27-artifact-d.txt
    # Also handles: 6-artifactD.md, 11-artifact_d.md, 15-ArtifactD.md
    if not lecture_num:
        pattern_d = re.search(r'^(\d+)(?:[-_][aA]rtifact)?[-_]?[dD]$', base.lower())
        if pattern_d:
            lecture_num = pattern_d.group(1)
            file_type = "summary"
    
    # === NEW PATTERNS FOR UNDERSCORE FORMAT ===
    
    # Pattern for lecture_XX_summary (underscore format summary files)
    # Examples: lecture_11_summary.md, lecture_27_summary.md, lecture01_summary.md
    if not lecture_num:
        pattern_underscore_summary = re.search(r'^lecture[-_]?(\d+)[-_]summary$', base.lower())
        if pattern_underscore_summary:
            lecture_num = pattern_underscore_summary.group(1)
            file_type = "summary"
    
    # Pattern for lecture_XX_artifact_b (underscore format transcript files)
    # Examples: lecture_06_artifact_b.md
    if not lecture_num:
        pattern_underscore_artifact_b = re.search(r'^lecture[-_](\d+)[-_]artifact[-_][bB]$', base.lower())
        if pattern_underscore_artifact_b:
            lecture_num = pattern_underscore_artifact_b.group(1)
            file_type = "transcript"
    
    # Pattern for lecture_XX_artifact_c (underscore format slide files)
    # Examples: lecture_06_artifact_c.md
    if not lecture_num:
        pattern_underscore_artifact_c = re.search(r'^lecture[-_](\d+)[-_]artifact[-_][cC]$', base.lower())
        if pattern_underscore_artifact_c:
            lecture_num = pattern_underscore_artifact_c.group(1)
            file_type = "slide"
    
    # Pattern for lecture_XX_artifact_d (underscore format summary files)
    # Examples: lecture_06_artifact_d.md
    if not lecture_num:
        pattern_underscore_artifact_d = re.search(r'^lecture[-_](\d+)[-_]artifact[-_][dD]$', base.lower())
        if pattern_underscore_artifact_d:
            lecture_num = pattern_underscore_artifact_d.group(1)
            file_type = "summary"
    
    # Pattern for lectureXX_slide_content (underscore format slide files)
    # Examples: lecture01_slide_content.md, lecture59_slide_content.md
    if not lecture_num:
        pattern_underscore_slide_content = re.search(r'^lecture[-_]?(\d+)[-_]slide[-_]content$', base.lower())
        if pattern_underscore_slide_content:
            lecture_num = pattern_underscore_slide_content.group(1)
            file_type = "slide"
    
    # Pattern for lectureXX_video_summary (underscore format summary files)
    # Examples: lecture01_video_summary.md, lecture60_video_summary.md
    if not lecture_num:
        pattern_underscore_video_summary = re.search(r'^lecture[-_]?(\d+)[-_]video[-_]summary$', base.lower())
        if pattern_underscore_video_summary:
            lecture_num = pattern_underscore_video_summary.group(1)
            file_type = "summary"
    
    # If we found a lecture number, standardize it
    if lecture_num:
        lecture_num = standardize_lecture_number(lecture_num)
        
        # Apply renaming rules based on file type
        if file_type == "slide":
            # Format for slide files: NN-slides.ext
            corrected = f"{lecture_num}-slides"
        elif file_type == "summary":
            # Format for summary files: NN-summary.ext
            corrected = f"{lecture_num}-summary"
        else:
            # Format for transcript files: Lecture NN.ext
            corrected = f"Lecture {lecture_num}"
    
    # Check if the corrected name would be different from the original
    corrected_filename = corrected + ext
    if corrected_filename == filename:
        # No change needed, avoid redundant renaming
        return {
            "original": filename,
            "corrected": filename,
            "needs_renaming": False
        }
    
    return {
        "original": filename,
        "corrected": corrected_filename,
        "needs_renaming": True
    }

def copy_file_to_output(input_path: str, output_path: str) -> bool:
    """
    Copy a file to a destination path within the input directory structure.
    Note: As per new requirements, this is rarely needed since we operate
    within the input directory structure directly. But kept for compatibility
    with existing code that may call it.
    
    Args:
        input_path: Source file path
        output_path: Destination file path (usually same as input_path now)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # If the paths are the same, no need to copy
        if os.path.abspath(input_path) == os.path.abspath(output_path):
            return True
            
        # Otherwise, ensure destination directory exists
        output_dir = os.path.dirname(output_path)
        ensure_directory_exists(output_dir)
        
        # Copy the file
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        print(f"Error copying file: {e}")
        return False
