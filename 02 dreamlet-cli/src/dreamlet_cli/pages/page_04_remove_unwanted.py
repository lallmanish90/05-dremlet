"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Remove unwanted or low-value files from lecture folders before later processing steps.
MAIN INPUTS:
- lecture folders and source artifacts under `input/`
MAIN OUTPUTS:
- filtered folder contents with unwanted files removed in place
REQUIRED CONFIG / ASSETS:
- `input/` directory
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none
"""

from dreamlet_cli.compat import st
import os
import re
import fnmatch
from pathlib import Path
import time
from typing import List, Dict, Tuple, Optional, Union

# Local utility functions (moved from utils.file_operations and utils.text_processing)
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

def map_input_to_output_path(input_path: str) -> str:
    """Convert an input path to its corresponding output path"""
    return input_path

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

def find_non_supported_files(directory: str) -> List[str]:
    """Find all files that are not supported"""
    all_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            all_files.append(os.path.join(root, filename))
    
    supported_extensions = ['.txt', '.md', '.pptx', '.zip']
    media_extensions = [
        '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.svg', '.webp', '.img',
        '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
        '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm'
    ]
    
    accepted_extensions = supported_extensions + media_extensions
    
    non_supported = []
    for file_path in all_files:
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in accepted_extensions:
            non_supported.append(file_path)
    
    return non_supported

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

def extract_slide_blocks(text: str) -> List[Tuple[str, str, str]]:
    """Extract slide blocks from transcript text"""
    patterns = [
        (r'\[Slide\s+(\d+)\s*-\s*Start\](.*?)\[Slide\s+\1\s*-\s*End\]', '[Slide {} - Start]', '[Slide {} - End]'),
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+[\d:]+\](.*?)\[Slide\s+\1\s*-\s*End\s+[\d:]+\]', '[Slide {} - Start]', '[Slide {} - End]'),
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+\d+\](.*?)\[Slide\s+\1\s*-\s*End\s+\d+\]', '[Slide {} - Start]', '[Slide {} - End]'),
        (r'\[Slide\s+(\d+)\](.*?)\[End\s+Slide\s+\1\]', '[Slide {}]', '[End Slide {}]'),
        (r'##\s*Slide\s+(\d+)(.*?)##\s*End\s+Slide\s+\1', '## Slide {}', '## End Slide {}'),
        (r'\[Slide\s+#(\d+)\s*-\s*Start\](.*?)\[Slide\s+#\1\s*-\s*End\]', '[Slide #{} - Start]', '[Slide #{} - End]'),
        (r'\[Slide\s+(\d+)\](.*?)(?=\[Slide\s+\d+\]|\[End\]|$)', '[Slide {}]', '[Slide {} - End]'),
        (r'Slide\s+(\d+):(.*?)(?=Slide\s+\d+:|End|$)', 'Slide {}:', 'End'),
        (r'\[Slide-(\d+)\](.*?)\[Slide-\1-End\]', '[Slide-{}]', '[Slide-{}-End]'),
        (r'Slide\s+(\d+)\s+Start(.*?)Slide\s+\1\s+End', 'Slide {} Start', 'Slide {} End')
    ]
    
    all_matches = []
    for pattern, start_format, end_format in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            for match in matches:
                slide_number = match[0]
                content = match[1]
                all_matches.append((slide_number, content, (start_format, end_format)))
    
    if all_matches:
        return sorted(all_matches, key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    
    slide_indicators = re.findall(r'(?:Slide|SLIDE)\s+(\d+)', text)
    if slide_indicators:
        sections = []
        for i, slide_num in enumerate(slide_indicators):
            if i < len(slide_indicators) - 1:
                next_slide_pattern = f"(?:Slide|SLIDE)\\s+{slide_indicators[i+1]}"
                section_text = re.split(next_slide_pattern, text, 1)[0]
                text = text.replace(section_text, '', 1)
                sections.append((slide_num, section_text, ('[Slide {} - Start]', '[Slide {} - End]')))
            else:
                sections.append((slide_num, text, ('[Slide {} - Start]', '[Slide {} - End]')))
        
        if sections:
            return sections
    
    return []

def extract_content_outside_slides(text: str) -> Tuple[str, str, List[Tuple[str, str, str]]]:
    """Extract content outside slide markers"""
    slide_blocks = extract_slide_blocks(text)
    
    if not slide_blocks:
        return "", "", []
    
    first_slide_number, first_slide_content, (start_format, _) = slide_blocks[0]
    first_marker = start_format.format(first_slide_number)
    first_marker_pos = text.find(first_marker)
    
    last_slide_number, last_slide_content, (_, end_format) = slide_blocks[-1]
    last_marker = end_format.format(last_slide_number)
    last_marker_pos = text.rfind(last_marker) + len(last_marker)
    
    pre_content = text[:first_marker_pos].strip()
    post_content = text[last_marker_pos:].strip()
    
    return pre_content, post_content, slide_blocks

def standardize_slide_markers(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Standardize slide markers to the preferred format"""
    modifications = []
    standardized_text = text
    
    patterns = [
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+([\d:]+)\]', r'[Slide \1 - Start]'),
        (r'\[Slide\s+(\d+)\s*-\s*End\s+([\d:]+)\]', r'[Slide \1 - End]'),
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+(\d+)\]', r'[Slide \1 - Start]'),
        (r'\[Slide\s+(\d+)\s*-\s*End\s+(\d+)\]', r'[Slide \1 - End]'),
        (r'\[Slide\s+(\d+)\s*-\s*Title\s+Slide:\s*Start\]', r'[Slide \1 - Start]'),
        (r'\[Slide\s+(\d+)\s*-\s*Title\s+Slide:\s*End\]', r'[Slide \1 - End]')
    ]
    
    for pattern, replacement in patterns:
        matches = re.findall(pattern, standardized_text)
        
        for match in matches:
            slide_number = match[0] if isinstance(match, tuple) else match
            
            if "Title Slide" in pattern:
                if "Start" in pattern:
                    original = f"[Slide {slide_number} - Title Slide: Start]"
                else:
                    original = f"[Slide {slide_number} - Title Slide: End]"
                mod_type = "title_slide_format_standardized"
            else:
                timestamp = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                if "Start" in pattern:
                    original = f"[Slide {slide_number} - Start {timestamp}]".strip()
                else:
                    original = f"[Slide {slide_number} - End {timestamp}]".strip()
                mod_type = "timestamp_removed"
            
            new = replacement.replace(r'\1', slide_number)
            
            modifications.append({
                "type": mod_type,
                "slide": slide_number,
                "original": original,
                "new": new
            })
            
            standardized_text = standardized_text.replace(original, new)
    
    return standardized_text, modifications

def adjust_transcript_structure(text: str) -> str:
    """Adjust transcript structure to ensure consistency"""
    standardized_text, _ = standardize_slide_markers(text)
    pre_content, post_content, slide_blocks = extract_content_outside_slides(standardized_text)
    
    if not slide_blocks:
        return standardized_text
    
    adjusted_text = ""
    
    for i, (slide_number, content, (start_format, end_format)) in enumerate(slide_blocks):
        start_marker = start_format.format(slide_number)
        end_marker = end_format.format(slide_number)
        
        if i == 0 and pre_content:
            adjusted_text += start_marker + "\n" + pre_content + "\n" + content.strip() + "\n" + end_marker + "\n\n"
        elif i == len(slide_blocks) - 1 and post_content:
            adjusted_text += start_marker + "\n" + content.strip() + "\n" + post_content + "\n" + end_marker + "\n\n"
        else:
            adjusted_text += start_marker + "\n" + content.strip() + "\n" + end_marker + "\n\n"
    
    return adjusted_text

def remove_headers(text: str) -> Tuple[str, int]:
    """Remove Markdown and other header formatting from text content"""
    headers_removed = 0
    modified_text = text
    
    md_header_pattern = r'^(#{1,6})\s+(.*?)$'
    
    lines = modified_text.split('\n')
    for i, line in enumerate(lines):
        md_match = re.match(md_header_pattern, line)
        if md_match:
            header_content = md_match.group(2)
            lines[i] = header_content
            headers_removed += 1
    
    modified_text = '\n'.join(lines)
    
    return modified_text, headers_removed

st.set_page_config(page_title="04 Remove unwanted - Dreamlet", page_icon="🗑️")

def process_transcript_file(file_path: str) -> Dict:
    """
    Process a transcript file to adjust its structure
    
    Args:
        file_path: Path to the transcript file
        
    Returns:
        Dictionary with processing results
    """
    result = {
        "file_path": file_path, 
        "status": "skipped", 
        "message": "",
        "has_slide_markers": False,
        "slide_count": 0,
        "discrepancy": False,
        "discrepancy_type": None,
        "timestamp": time.time(),
        "slide_marker_modifications": [],
        "timestamp_markers_removed": 0,
        "headers_removed": 0
    }
    
    try:
        # Read the transcript file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if this is actually a slide file (not a transcript file)
        filename = os.path.basename(file_path).lower()
        is_slide_file = "slide" in filename or "-s." in filename
        
        if is_slide_file:
            # For slide files, we'll still process for header removal, but skip slide marker checks
            
            # Remove all header formatting from the slide content
            content_without_headers, headers_removed_count = remove_headers(content)
            result["headers_removed"] = headers_removed_count
            
            # Save the adjusted slide file to the output directory
            output_path = map_input_to_output_path(file_path)
            ensure_directory_exists(os.path.dirname(output_path))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content_without_headers)
            
            message = f"Processed slide file, removed {headers_removed_count} headers"
            result["status"] = "processed"
            result["message"] = message
            
            return result
        
        # For transcript files, continue with standard processing
        
        # First standardize the slide markers (remove timestamps)
        standardized_content, modifications = standardize_slide_markers(content)
        result["slide_marker_modifications"] = modifications
        result["timestamp_markers_removed"] = len(modifications)
        
        # Now check for slide markers in the standardized content
        slide_blocks = extract_slide_blocks(standardized_content)
        
        if not slide_blocks:
            result["status"] = "discrepancy"
            result["message"] = "No slide markers found, marking as discrepancy"
            result["discrepancy"] = True
            result["discrepancy_type"] = "Missing slide markers"
            return result
        
        result["has_slide_markers"] = True
        result["slide_count"] = len(slide_blocks)
        
        # Extract content outside slide markers
        pre_content, post_content, _ = extract_content_outside_slides(standardized_content)
        
        # Adjust the transcript structure
        adjusted_content = adjust_transcript_structure(standardized_content)
        
        # Remove all header formatting from the content
        content_without_headers, headers_removed_count = remove_headers(adjusted_content)
        result["headers_removed"] = headers_removed_count
        
        # Save the adjusted transcript to the output directory
        output_path = map_input_to_output_path(file_path)
        ensure_directory_exists(os.path.dirname(output_path))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content_without_headers)
        
        message = f"Processed {len(slide_blocks)} slides"
        if result["timestamp_markers_removed"] > 0:
            message += f", removed timestamps from {result['timestamp_markers_removed']} slide markers"
        if headers_removed_count > 0:
            message += f", removed {headers_removed_count} headers"
        
        result["status"] = "processed"
        result["message"] = message
        result["pre_content_size"] = len(pre_content)
        result["post_content_size"] = len(post_content)
        
        return result
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Error: {str(e)}"
        return result

def extract_lecture_number(file_path):
    """
    Extract lecture number from a file path
    
    Args:
        file_path: Path to extract lecture number from
        
    Returns:
        Integer lecture number or 999 if not found
    """
    match = re.search(r'lecture[_\s-]*(\d+)|lec[_\s-]*(\d+)|l(\d+)', file_path, re.IGNORECASE)
    if match:
        # Get the first non-None group
        for group in match.groups():
            if group:
                return int(group)
    
    # Default to a high number if no lecture number found
    return 999

def get_full_course_name(path: str) -> str:
    """
    Extract the full course name from the file path
    
    Args:
        path: File path
        
    Returns:
        Full course name
    """
    if not path:
        return "Uncategorized"
    
    # Extract directory containing the file
    dir_path = os.path.dirname(path)
    
    # Split the path and find the course directory
    parts = dir_path.split(os.sep)
    if len(parts) > 1:
        # The course name is typically the parent directory of the file
        # We try to find a directory that matches a course pattern
        for i in range(len(parts)):
            if re.search(r'course|module|section', parts[i], re.IGNORECASE) or re.search(r'\d+', parts[i]):
                return parts[i]
    
    # If we can't find a specific course directory, use the numeric match
    course, _, _ = extract_course_lecture_section(path)
    if course:
        # Try to get the full directory name that contains this course number
        for part in parts:
            if re.search(fr'\b{course}\b', part):
                return part
        return f"Course {course}"
    
    return "Uncategorized"

def process_all_files(all_transcripts: List[str]) -> Dict:
    """
    Process all transcript files and track results
    
    Args:
        all_transcripts: List of transcript file paths
        
    Returns:
        Dictionary with processing results
    """
    # Group files by course for organizing the results
    files_by_course = {}
    discrepancies = []
    timestamp_markers_standardized = []
    
    # Process files with progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    
    results = []
    for i, file_path in enumerate(all_transcripts):
        # Update progress
        progress = (i + 1) / len(all_transcripts)
        progress_bar.progress(progress)
        
        # Update status message
        file_name = os.path.basename(file_path)
        status_container.info(f"Processing {i+1}/{len(all_transcripts)}: {file_name}")
        
        # Process the file
        result = process_transcript_file(file_path)
        
        # Extract course information
        course, lecture, _ = extract_course_lecture_section(file_path)
        course_num = course if course else "999"
        
        # Get full course name
        full_course_name = get_full_course_name(file_path)
        
        # Add to course data
        if course_num not in files_by_course:
            files_by_course[course_num] = []
        
        # Create file data with course information
        file_data = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "course_num": course_num,
            "full_course_name": full_course_name,
            "lecture": lecture,
            "status": result["status"],
            "message": result["message"],
            "has_slide_markers": result["has_slide_markers"],
            "slide_count": result["slide_count"],
            "timestamp": result["timestamp"],
            "timestamp_markers_removed": result.get("timestamp_markers_removed", 0),
            "headers_removed": result.get("headers_removed", 0)
        }
        
        # Track timestamp marker standardization
        if result.get("timestamp_markers_removed", 0) > 0:
            file_data["slide_marker_modifications"] = result.get("slide_marker_modifications", [])
            timestamp_markers_standardized.append(file_data)
        
        if result["status"] == "processed":
            file_data["pre_content_size"] = result.get("pre_content_size", 0)
            file_data["post_content_size"] = result.get("post_content_size", 0)
        
        if result["status"] == "discrepancy":
            file_data["discrepancy_type"] = result["discrepancy_type"]
            discrepancies.append(file_data)
        
        # Add to course data
        files_by_course[course_num].append(file_data)
        results.append(result)
        
        # Add a small delay to make the progress visible
        time.sleep(0.1)
    
    # Clear status message
    status_container.success(f"Processed {len(all_transcripts)} files")
    
    # Calculate statistics
    processed_count = sum(1 for r in results if r["status"] == "processed")
    discrepancy_count = sum(1 for r in results if r["status"] == "discrepancy")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    error_count = sum(1 for r in results if r["status"] == "error")
    timestamp_markers_count = sum(r.get("timestamp_markers_removed", 0) for r in results)
    headers_removed_count = sum(r.get("headers_removed", 0) for r in results)
    
    return {
        "course_data": files_by_course,
        "total_processed": len(all_transcripts),
        "processed_count": processed_count,
        "discrepancy_count": discrepancy_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "timestamp_markers_count": timestamp_markers_count,
        "headers_removed_count": headers_removed_count,
        "discrepancies": discrepancies,
        "timestamp_markers_standardized": timestamp_markers_standardized,
        "results": results
    }

def main():
    st.title("Remove unwanted")
    st.write("Delete non-supported files from the input directory.")
    
    input_dir = get_input_directory()
    output_dir = get_output_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find all transcript and slide files
    st.header("Available Files")
    all_transcripts = find_transcript_files(input_dir)
    all_slides = find_slide_files(input_dir)
    
    # Combine both lists
    all_files = all_transcripts + all_slides
    
    if not all_files:
        st.warning("No transcript or slide files found in the input directory.")
        return
    
    st.success(f"Found {len(all_transcripts)} transcript files and {len(all_slides)} slide files in the input directory.")
    
    # Find non-supported files
    non_supported_files = find_non_supported_files(input_dir)
    
    if non_supported_files:
        st.warning(f"Found {len(non_supported_files)} non-supported files in the input directory.")
        
        # Display non-supported files in a table
        with st.expander("View Non-Supported Files"):
            # Create data for the table
            table_data = []
            for file_path in non_supported_files:
                file_name = os.path.basename(file_path)
                dir_name = os.path.dirname(file_path)
                table_data.append({
                    "File Name": file_name,
                    "Directory": dir_name,
                    "Full Path": file_path
                })
            
            # Convert to DataFrame and display
            if table_data:
                import pandas as pd
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Add a button to delete all non-supported files
                if st.button("Delete All Non-Supported Files"):
                    deleted_count = 0
                    
                    # Show progress bar for deletion
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, file_path in enumerate(non_supported_files):
                        try:
                            # Update progress
                            progress = (i + 1) / len(non_supported_files)
                            progress_bar.progress(progress)
                            status_text.text(f"Deleting {i+1}/{len(non_supported_files)}: {os.path.basename(file_path)}")
                            
                            # Delete the file
                            os.remove(file_path)
                            deleted_count += 1
                        except Exception as e:
                            st.error(f"Error deleting {file_path}: {str(e)}")
                    
                    # Complete
                    progress_bar.progress(1.0)
                    status_text.text(f"Deleted {deleted_count} files")
                    
                    # Rerun the app to refresh the file list
                    st.rerun()
    
    # Group files by course for display purposes only
    files_by_course = {}
    for file_path in all_files:  # Use all_files instead of just all_transcripts
        # Extract course information
        course, _, _ = extract_course_lecture_section(file_path)
        course_name = f"Course {course}" if course else "Uncategorized"
        
        if course_name not in files_by_course:
            files_by_course[course_name] = []
        files_by_course[course_name].append(file_path)
    
    # Sort courses numerically
    sorted_courses = sorted(
        files_by_course.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    # Display file count by course
    for course_name in sorted_courses:
        file_paths = files_by_course[course_name]
        st.write(f"**{course_name}:** {len(file_paths)} files")
    
    # Display results if available
    if hasattr(st.session_state, 'adjust_results'):
        results = st.session_state.adjust_results
        course_data = results["course_data"]
        
        # Summary dashboard
        st.header("Status Dashboard")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Total Files Processed", results["total_processed"])
        
        with col2:
            st.metric("Successfully Processed", results["processed_count"])
            
        with col3:
            # Make this a clickable button that will show discrepancies
            if results["discrepancy_count"] > 0:
                if st.button(f"Discrepancies Found: {results['discrepancy_count']}", key="discrepancies_button"):
                    st.session_state.show_discrepancies = True
            else:
                st.metric("Discrepancies Found", 0)
        
        with col4:
            # Add a metric or button for timestamp markers standardized
            if results.get("timestamp_markers_count", 0) > 0:
                if st.button(f"Markers Standardized: {results['timestamp_markers_count']}", key="markers_button"):
                    st.session_state.show_standardized_markers = True
            else:
                st.metric("Markers Standardized", 0)
                
        with col5:
            # Add a metric for headers removed
            if results.get("headers_removed_count", 0) > 0:
                st.metric("Headers Removed", results["headers_removed_count"])
            else:
                st.metric("Headers Removed", 0)
        
        with col6:
            st.metric("Errors", results["error_count"])
        
        # Show discrepancies table if requested
        if hasattr(st.session_state, 'show_discrepancies') and st.session_state.show_discrepancies:
            st.subheader("All Discrepancies")
            
            # Create data for the discrepancies table
            discrepancy_data = []
            
            # Sort discrepancies by course number then lecture number
            sorted_discrepancies = sorted(
                results["discrepancies"],
                key=lambda x: (
                    int(re.search(r'\d+', x["course_num"]).group()) if re.search(r'\d+', x["course_num"]) else 999,
                    extract_lecture_number(x["file_path"])
                )
            )
            
            for file_data in sorted_discrepancies:
                # Add row for this file with discrepancy
                row = {
                    "Course Name": file_data["full_course_name"],
                    "Lecture": file_data.get("lecture", "Unknown"),
                    "Transcript Name": file_data["file_name"],
                    "Discrepancy Type": file_data["discrepancy_type"]
                }
                
                discrepancy_data.append(row)
            
            # Convert to DataFrame and display
            if discrepancy_data:
                import pandas as pd
                df = pd.DataFrame(discrepancy_data)
                
                # Sort by Course Name and Transcript Name
                df = df.sort_values(by=["Course Name", "Lecture", "Transcript Name"])
                
                # Display table
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No discrepancies found.")
                
            # Button to hide discrepancies
            if st.button("Hide Discrepancies"):
                st.session_state.show_discrepancies = False
                st.rerun()
                
        # Show standardized markers table if requested
        if hasattr(st.session_state, 'show_standardized_markers') and st.session_state.show_standardized_markers:
            st.subheader("Standardized Slide Markers")
            
            # Create data for the standardized markers table
            markers_data = []
            
            # Sort by course number then lecture number
            sorted_markers = sorted(
                results["timestamp_markers_standardized"],
                key=lambda x: (
                    int(re.search(r'\d+', x["course_num"]).group()) if re.search(r'\d+', x["course_num"]) else 999,
                    extract_lecture_number(x["file_path"])
                )
            )
            
            for file_data in sorted_markers:
                # For each file with standardized markers
                filename = file_data["file_name"]
                course_name = file_data["full_course_name"]
                lecture = file_data.get("lecture", "Unknown")
                
                # Add a row for each marker that was standardized
                for mod in file_data.get("slide_marker_modifications", []):
                    row = {
                        "Course Name": course_name,
                        "Lecture": lecture,
                        "Transcript Name": filename,
                        "Slide Number": mod.get("slide", ""),
                        "Original Marker": mod.get("original", ""),
                        "Standardized Marker": mod.get("new", "")
                    }
                    markers_data.append(row)
            
            # Convert to DataFrame and display
            if markers_data:
                import pandas as pd
                df = pd.DataFrame(markers_data)
                
                # Sort by Course Name, Lecture, and Transcript Name
                df = df.sort_values(by=["Course Name", "Lecture", "Transcript Name", "Slide Number"])
                
                # Display table
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No slide markers were standardized.")
                
            # Button to hide standardized markers
            if st.button("Hide Standardized Markers"):
                st.session_state.show_standardized_markers = False
                st.rerun()
        
        # Display results by course in collapsible sections
        st.subheader("Adjustment Details by Course")
        
        # Sort courses in ascending order
        sorted_courses = sorted(
            course_data.keys(),
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
        )
        
        # Create a mapping of course names to their IDs
        course_options = {}
        for course in sorted_courses:
            if course_data[course]:
                full_name = course_data[course][0]["full_course_name"]
                course_options[full_name] = course
        
        if course_options:
            # First check if we need to use a searchable dropdown (more than 10 courses)
            if len(course_options) > 10:
                # Use selectbox with search capability for many courses
                selected_course = st.selectbox(
                    "Select a course to view:",
                    options=list(course_options.keys()),
                    key="course_selector"
                )
            else:
                # For fewer courses, we'll use a cleaner radio button interface
                col1, col2 = st.columns([1, 3])  # Adjust column widths for better layout
                with col1:
                    selected_course = st.radio(
                        "Select a course:",
                        options=list(course_options.keys()),
                        key="course_selector"
                    )
            
            # Get the course ID from our mapping
            selected_course_id = course_options.get(selected_course)
            
            # Create expander for the selected course
            if selected_course_id:
                with st.expander(selected_course, expanded=True):
                    # Sort files by lecture number
                    sorted_files = sorted(
                        course_data[selected_course_id],
                        key=lambda x: extract_lecture_number(x["file_path"])
                    )
                    
                    # Create data for the table
                    table_data = []
                    
                    for file_data in sorted_files:
                        # Add row for this file
                        row = {
                            "Transcript Name": file_data["file_name"],
                            "Status": file_data["status"].capitalize(),
                            "Slide Count": file_data["slide_count"] if file_data["has_slide_markers"] else "N/A",
                            "Markers Standardized": file_data.get("timestamp_markers_removed", 0),
                            "Headers Removed": file_data.get("headers_removed", 0)
                        }
                        
                        # If it has a discrepancy, add the type
                        if file_data["status"] == "discrepancy":
                            row["Discrepancy"] = file_data["discrepancy_type"]
                        else:
                            row["Discrepancy"] = ""
                        
                        table_data.append(row)
                    
                    # Convert to DataFrame and display
                    if table_data:
                        import pandas as pd
                        df = pd.DataFrame(table_data)
                        
                        # Sort the DataFrame by Transcript Name in ascending order
                        df = df.sort_values(by=["Transcript Name"])
                        
                        # Display table with full width
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write("No files found for this course.")

if __name__ == "__main__":
    main()
