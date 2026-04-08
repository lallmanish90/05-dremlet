"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: LEGACY
PURPOSE: Narrow transcript-only adjustment page retained as a legacy variant.
MAIN INPUTS:
- transcript files under `input/`
MAIN OUTPUTS:
- adjusted transcript files written in place
REQUIRED CONFIG / ASSETS:
- `input/` directory
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none
REPLACED BY:
- `pages/01_Adjust_AAA_EEE.py`
"""

from dreamlet_cli.compat import st
import os
import re
import glob
import time
import logging
import fnmatch
from pathlib import Path
from typing import List, Dict, Tuple

# Local utility functions (moved from utils.file_operations)
def get_input_directory() -> str:
    """
    Get the path to the input directory
    
    Returns:
        Path to the input directory
    """
    # Default input directory is in the current working directory
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def ensure_directory_exists(directory_path: str) -> None:
    """
    Create directory if it doesn't exist
    
    Args:
        directory_path: Path to the directory to create
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

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

st.set_page_config(page_title="02 Adjust Transcript Only - Dreamlet", page_icon="🔄")

def extract_slides_from_content(content):
    """
    Extract slides from content, handling multiple slide sequences.
    Handles both timestamped format [Slide N - Start: MM:SS] and 
    already-converted format [Slide N - Start].
    
    Args:
        content (str): The file content to extract slides from
        
    Returns:
        list: List of (slide_num, content) tuples
    """
    # Fix incomplete slide markers (missing closing brackets)
    content = re.sub(r'\[Slide (\d+) - End: (\d+:\d+)(?!\])', r'[Slide \1 - End: \2]', content)
    
    # Remove Word Count line that might appear after slide markers
    content = re.sub(r'(\[Slide \d+ - End.*?\])\s*\n\s*Word Count:\s*\d+\s*\n', r'\1\n', content)
    
    # Create a standardized version of the content with all timestamps removed
    # This helps when there are mixed formats for the same slide number
    standardized_content = re.sub(r'\[Slide (\d+) - Start: \d+:\d+\]', r'[Slide \1 - Start]', content)
    standardized_content = re.sub(r'\[Slide (\d+) - End: \d+:\d+\]', r'[Slide \1 - End]', standardized_content)
    
    # Find all slide start markers with their positions in the standardized content
    slide_markers = [(int(m.group(1)), m.start()) for m in re.finditer(r'\[Slide (\d+) - Start\]', standardized_content)]
    
    if not slide_markers:
        st.warning("No slide markers found in the standardized content. Trying original content.")
        # Fallback to original content if standardization didn't work
        slide_markers = [(int(m.group(1)), m.start()) for m in re.finditer(r'\[Slide (\d+) - Start(?::\s*\d+:\d+)?\]', content)]
        if not slide_markers:
            st.warning("No slide markers found in the content.")
            return []
    
    # Create a dictionary to collect slide content - one entry per slide number
    slide_content_map = {}
    
    # Try multiple patterns to extract slide content from both standardized and original content
    slide_patterns = [
        (standardized_content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End\]'),  # No timestamps
        (content, r'\[Slide (\d+) - Start: (\d+:\d+)\](.*?)\[Slide \1 - End: (\d+:\d+)\]'),  # Both timestamps
        (content, r'\[Slide (\d+) - Start: (\d+:\d+)\](.*?)\[Slide \1 - End\]'),  # Start timestamp only
        (content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End: (\d+:\d+)\]'),  # End timestamp only
        (content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End\]')  # No timestamps (original)
    ]
    
    # Try each pattern to extract slide content
    for content_to_use, pattern in slide_patterns:
        for match in re.finditer(pattern, content_to_use, re.DOTALL):
            slide_num = int(match.group(1))
            
            # Determine content group based on the pattern
            if "Start: " in pattern and "End: " in pattern:  # Both timestamps
                slide_content = match.group(3).strip()
            else:  # Either no timestamps or only one timestamp
                slide_content = match.group(2).strip()
            
            # Clean the slide content
            slide_content = clean_slide_content(slide_content)
            
            # Keep content for each slide number (first match only)
            if slide_num not in slide_content_map:
                slide_content_map[slide_num] = slide_content
    
    # If we didn't find any slides using patterns, try a last resort approach
    if not slide_content_map:
        st.warning("No slides extracted with regular patterns. Attempting manual extraction...")
        
        # Find all start markers in the original content
        start_markers = list(re.finditer(r'\[Slide (\d+) - Start(?::\s*\d+:\d+)?\]', content))
        end_markers = list(re.finditer(r'\[Slide (\d+) - End(?::\s*\d+:\d+)?\]', content))
        
        # Build dictionaries of positions
        start_positions = {}
        for match in start_markers:
            slide_num = int(match.group(1))
            if slide_num not in start_positions:  # Take first occurrence only
                start_positions[slide_num] = match.end()
        
        end_positions = {}
        for match in end_markers:
            slide_num = int(match.group(1))
            if slide_num not in end_positions:  # Take first occurrence only
                end_positions[slide_num] = match.start()
        
        # Extract content between markers
        for slide_num in sorted(set(start_positions.keys()) & set(end_positions.keys())):
            start_pos = start_positions[slide_num]
            end_pos = end_positions[slide_num]
            
            if start_pos < end_pos:
                slide_content = content[start_pos:end_pos].strip()
                slide_content = clean_slide_content(slide_content)
                slide_content_map[slide_num] = slide_content
    
    # Convert the map to a list of tuples and sort by slide number
    slides = [(str(num), content) for num, content in slide_content_map.items()]
    slides.sort(key=lambda x: int(x[0]))
    
    if not slides:
        st.error("Failed to extract any slides after trying all methods.")
    
    return slides

def clean_slide_content(content):
    """
    Clean the slide content by removing unwanted elements.
    
    Args:
        content (str): The slide content to clean
        
    Returns:
        str: The cleaned slide content
    """
    # Remove lines containing "transcript" or "duration" (often metadata)
    lines = content.split('\n')
    lines = [line for line in lines if 'transcript' not in line.lower() and 'duration' not in line.lower()]
    
    # Remove Markdown headers (e.g., # Header, ## Subheader)
    lines = [re.sub(r'^#+\s+', '', line) for line in lines]
    
    # Remove text inside brackets that mentions music or other stage directions
    # (e.g., [Mysterious music fades in], [Audience applause])
    lines = [re.sub(r'\[.*?music.*?\]', '', line) for line in lines]
    lines = [re.sub(r'\[.*?applause.*?\]', '', line) for line in lines]
    
    # Remove timestamp information in format [MM:SS - NN:SS]
    lines = [re.sub(r'\[\d+:\d+\s*-\s*\d+:\d+\]', '', line) for line in lines]
    
    # Remove "Word Count: NNN" lines
    lines = [line for line in lines if not re.match(r'^\s*Word Count:\s*\d+\s*$', line)]
    
    # Remove empty lines (that might be left after removing content)
    lines = [line for line in lines if line.strip()]
    
    # Remove bracketed placeholders like [Name]
    lines = [re.sub(r'\[Name\]', 'Professor', line) for line in lines]
    
    # Handle formatting: bold/italic - we keep the content but remove the markdown syntax
    lines = [re.sub(r'\*\*(.*?)\*\*', r'\1', line) for line in lines]  # Bold
    lines = [re.sub(r'\*(.*?)\*', r'\1', line) for line in lines]      # Italic
    
    # Remove any lines that are purely metadata (like "_Duration: 20 minutes (1200 words)_")
    lines = [line for line in lines if not re.match(r'^\s*_.*?_\s*$', line)]
    
    # Join the lines back together
    return '\n'.join(lines)

def format_slides(slides):
    """
    Apply standard formatting to slides.
    
    Args:
        slides (list): List of (slide_num, content) tuples
        
    Returns:
        str: Formatted content
    """
    formatted_lines = []
    for i, (slide_num, content) in enumerate(slides):
        formatted_lines.append(f"[Slide {slide_num} - Start]")
        
        # Add empty line after first slide start tag only
        if i == 0:
            formatted_lines.append("")
                
        formatted_lines.append(content)
        formatted_lines.append(f"[Slide {slide_num} - End]")
        
        # Add empty line after each slide
        formatted_lines.append("")
    
    return '\n'.join(formatted_lines)

def convert_file(file_path) -> Dict:
    """
    Convert a single file from timestamped format to clean format and overwrite it.
    
    Args:
        file_path (str): Path to the file to convert
        
    Returns:
        Dict: Result dictionary with processing information
    """
    result = {
        "file_path": file_path,
        "status": "skipped",
        "message": "",
        "slide_count": 0,
        "timestamp": time.time(),
    }
    
    try:
        # Read the input file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup of original file
        backup_file = f"{file_path}.bak"
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            result["status"] = "warning"
            result["message"] = f"Failed to create backup: {str(e)}"
        
        # Extract slides from content
        slides = extract_slides_from_content(content)
        
        if not slides:
            result["status"] = "error"
            result["message"] = f"No valid slides found in {file_path}"
            return result
        
        # Format slides
        formatted_content = format_slides(slides)
        
        # Verify the formatted content before writing to ensure no duplicate slide markers
        has_duplicates = False
        slide_counts = {}
        
        # Count occurrences of each slide marker in the formatted content
        for match in re.finditer(r'\[Slide (\d+) - Start\]', formatted_content):
            slide_num = match.group(1)
            slide_counts[slide_num] = slide_counts.get(slide_num, 0) + 1
        
        # Check for duplicates
        duplicate_slides = []
        for slide_num, count in slide_counts.items():
            if count > 1:
                duplicate_slides.append(f"Slide {slide_num} ({count} occurrences)")
                has_duplicates = True
        
        # If duplicates found, try another approach - last resort recovery
        if has_duplicates:
            result["duplicate_slides"] = duplicate_slides
            
            # Extract unique slide numbers and their content
            unique_slides = []
            seen_slide_nums = set()
            
            for slide_num, slide_content in slides:
                if slide_num not in seen_slide_nums:
                    unique_slides.append((slide_num, slide_content))
                    seen_slide_nums.add(slide_num)
            
            # Sort by slide number
            unique_slides.sort(key=lambda x: int(x[0]))
            
            # Format the unique slides
            formatted_content = format_slides(unique_slides)
        
        # Overwrite the original file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        result["status"] = "processed"
        result["slide_count"] = len(slides)
        result["message"] = f"Successfully converted {len(slides)} slides"
        if has_duplicates:
            result["message"] += f" (fixed {len(duplicate_slides)} duplicate slide markers)"
        
        return result
    
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Error converting {file_path}: {str(e)}"
        return result

def process_directory(all_files: List[str]) -> List[Dict]:
    """
    Process all selected files and track results
    
    Args:
        all_files: List of file paths to process
        
    Returns:
        List of dictionaries with processing results
    """
    if not all_files:
        st.warning("No files found for processing.")
        return []
    
    # Show progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    for i, file_path in enumerate(all_files):
        # Update progress
        progress = (i + 1) / len(all_files)
        progress_bar.progress(progress)
        
        # Update status message
        file_name = os.path.basename(file_path)
        status_text.info(f"Processing {i+1}/{len(all_files)}: {file_name}")
        
        # Process the file
        result = convert_file(file_path)
        results.append(result)
        
        # Add a small delay to make the progress visible
        time.sleep(0.1)
    
    # Clear status message
    status_text.success(f"Processed {len(all_files)} files")
    
    return results

def cleanup_backup_files(input_dir):
    """
    Clean up all backup files created during processing
    
    Args:
        input_dir: Input directory path
    
    Returns:
        Tuple of (cleaned_count, total_count)
    """
    # Find all backup files
    backup_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.bak') or file.endswith('.ba') or file.endswith('.md.ba'):
                backup_files.append(os.path.join(root, file))
    
    total_count = len(backup_files)
    if total_count == 0:
        return 0, 0
    
    # Show progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    cleaned_count = 0
    for i, backup_file in enumerate(backup_files):
        # Update progress
        progress = (i + 1) / total_count
        progress_bar.progress(progress)
        
        # Update status message
        file_name = os.path.basename(backup_file)
        status_text.info(f"Cleaning up {i+1}/{total_count}: {file_name}")
        
        # Remove the backup file
        try:
            os.remove(backup_file)
            cleaned_count += 1
        except Exception as e:
            st.warning(f"Failed to remove backup file {backup_file}: {str(e)}")
        
        # Add a small delay to make the progress visible
        time.sleep(0.05)
    
    # Clear status message
    status_text.success(f"Cleaned up {cleaned_count} backup files")
    
    return cleaned_count, total_count

def display_results(results: List[Dict]):
    """
    Display processing results in a user-friendly format
    
    Args:
        results: List of result dictionaries
    """
    if not results:
        return
    
    # Calculate statistics
    processed_count = sum(1 for r in results if r["status"] == "processed")
    error_count = sum(1 for r in results if r["status"] == "error")
    warning_count = sum(1 for r in results if r["status"] == "warning")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    total_slides = sum(r.get("slide_count", 0) for r in results if r["status"] == "processed")
    
    # Display summary statistics
    st.header("Processing Results")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Files Processed", f"{processed_count}/{len(results)}")
    col2.metric("Slides Processed", total_slides)
    col3.metric("Files with Errors", error_count)
    col4.metric("Files Skipped", skipped_count)
    
    # Show detailed results
    with st.expander("View Detailed Results"):
        # Create a table for displaying results
        table_data = []
        for result in results:
            file_name = os.path.basename(result["file_path"])
            dir_name = os.path.dirname(result["file_path"])
            
            row = {
                "File Name": file_name,
                "Directory": dir_name,
                "Status": result["status"].capitalize(),
                "Slides": result.get("slide_count", 0),
                "Message": result["message"]
            }
            table_data.append(row)
        
        # Convert to DataFrame and display
        if table_data:
            import pandas as pd
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
    
    # Show files with errors
    if error_count > 0:
        with st.expander(f"View Files with Errors ({error_count})"):
            error_files = [r for r in results if r["status"] == "error"]
            for result in error_files:
                st.error(f"{os.path.basename(result['file_path'])}: {result['message']}")
    
    # Show files with warnings
    if warning_count > 0:
        with st.expander(f"View Files with Warnings ({warning_count})"):
            warning_files = [r for r in results if r["status"] == "warning"]
            for result in warning_files:
                st.warning(f"{os.path.basename(result['file_path'])}: {result['message']}")

def main():
    st.title("Adjust Transcript - Only")
    st.write("This specialized tool corrects and standardizes transcript files by removing timestamps, cleaning unwanted content, and handling formatting issues.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find all transcript files (we focus only on transcripts for this specialized tool)
    st.header("Available Transcript Files")
    all_transcripts = find_transcript_files(input_dir)
    
    if not all_transcripts:
        st.warning("No transcript files found in the input directory.")
        return
    
    st.success(f"Found {len(all_transcripts)} transcript files in the input directory.")
    
    # Display counts with course grouping
    transcript_counts = {}
    for file_path in all_transcripts:
        dir_path = os.path.dirname(file_path)
        if dir_path not in transcript_counts:
            transcript_counts[dir_path] = 0
        transcript_counts[dir_path] += 1
    
    with st.expander("View Transcript Counts by Directory"):
        for dir_path, count in transcript_counts.items():
            st.write(f"**{dir_path}**: {count} files")
    
    # Simple process button for transcript files
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("Click the button to clean and standardize all transcript files, removing timestamps and formatting issues.")
    
    with col2:
        process_button = st.button("Process Transcripts", 
                               key="process_transcripts", 
                               disabled=len(all_transcripts) == 0,
                               use_container_width=True,
                               type="primary")
    
    if process_button:
        with st.spinner("Processing transcript files..."):
            results = process_directory(all_transcripts)
            st.session_state.adjust_transcript_results = results
            display_results(results)
            
            # Show backup cleanup button after processing
            if st.button("Clean Up Backup Files", key="clean_backups", type="secondary"):
                with st.spinner("Cleaning up backup files..."):
                    cleaned_count, total_count = cleanup_backup_files(input_dir)
                    if cleaned_count > 0:
                        st.success(f"Cleaned up {cleaned_count} of {total_count} backup files.")
                    else:
                        st.info("No backup files to clean up.")
    
    # Show description of what this tool does
    with st.expander("What does this specialized tool do?"):
        st.markdown("""
        ### Transcript File Adjustment (Specialized Version)
        
        This specialized tool processes transcript files to remove timestamps, clean unwanted content, and standardize slide markers. Unlike the regular Adjust page, this focuses exclusively on transcripts and uses a more advanced processing algorithm.
        
        #### Processing Features:
        
        1. **Timestamp Removal**: Converts `[Slide N - Start: MM:SS]` to `[Slide N - Start]`
        
        2. **Content Cleanup**:
           - Removes lines containing "transcript" or "duration"
           - Removes Markdown headers (e.g., `# Header`, `## Subheader`)
           - Removes music cue notations (e.g., `[Music fades in]`, `[Background music]`)
           - Removes empty lines and excessive whitespace
           - Removes Word Count lines
        
        3. **Formatting Cleanup**:
           - Removes Markdown formatting (bold `**text**` → `text`, italic `*text*` → `text`)
           - Removes lines that are purely metadata
           - Replaces placeholder text (`[Name]` → `Professor`)
        
        4. **Slide Content Formatting**:
           - Adds empty line after the first slide start tag
           - Adds empty line after each slide for better readability
        
        5. **Error Handling**:
           - Fixes incomplete slide markers (missing closing brackets)
           - Handles duplicate slide markers
           - Uses multiple extraction methods to handle difficult cases
           - Employs fallback mechanisms for malformed content
        
        The tool processes files in-place, overwriting the original content with the cleaned version, but creates backups before making changes.
        """)

if __name__ == "__main__":
    main()
