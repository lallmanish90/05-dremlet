"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent
"""

import streamlit as st
import os
import re
import time
import shutil
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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

# Page configuration is set in Home.py

def get_transcript_files(input_dir):
    """Get all files that are transcript files (MD and TXT files with 'Lecture' in the name)"""
    result = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Only include markdown and text files
            if file_ext not in ['.md', '.txt']:
                continue
                
            # Skip files in all_transcripts or all_summary folders
            if 'all_transcripts' in file_path or 'all_summary' in file_path:
                continue
            
            # Skip files in "English text" or "English Summary text" folders
            if 'English text' in file_path or 'English Summary text' in file_path:
                continue
            
            # Include files that have "Lecture" in the filename and don't have summary indicators
            if 'lecture' in file_name.lower() and not any(marker in file_name.lower() for marker in ['-summary', '-d.', '-artifact-d.']):
                # Check if file is not inside a Lecture folder
                is_in_lecture_folder = any('lecture' in part.lower() for part in Path(root).parts)
                if not is_in_lecture_folder:
                    result.append(file_path)
    
    return result

def get_summary_files(input_dir):
    """Get all files that are summary files (MD and TXT files with summary indicators)"""
    result = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Only include markdown and text files
            if file_ext not in ['.md', '.txt']:
                continue
                
            # Skip files in all_transcripts or all_summary folders
            if 'all_transcripts' in file_path or 'all_summary' in file_path:
                continue
            
            # Skip files in "English text" or "English Summary text" folders
            if 'English text' in file_path or 'English Summary text' in file_path:
                continue
            
            # Include files that have summary indicators
            if any(marker in file_name.lower() for marker in ['-summary', '-d.', '-artifact-d.']):
                # Check if file is not inside a Lecture folder
                is_in_lecture_folder = any('lecture' in part.lower() for part in Path(root).parts)
                if not is_in_lecture_folder:
                    result.append(file_path)
    
    return result

def process_transcript_file(file_path):
    """Process a single transcript file"""
    try:
        # Get file info
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # Extract lecture number from filename
        match = re.search(r'lecture\s*(\d+)', file_name.lower())
        lecture_num = match.group(1) if match else "Unknown"
        
        # Create lecture folder name
        lecture_folder_name = f"Lecture {lecture_num.zfill(2)}"
        
        # Create directories
        all_transcripts_folder = os.path.join(dir_path, 'all_transcripts')
        os.makedirs(all_transcripts_folder, exist_ok=True)
        
        lecture_folder = os.path.join(dir_path, lecture_folder_name)
        os.makedirs(lecture_folder, exist_ok=True)
        
        english_text_folder = os.path.join(lecture_folder, "English text")
        os.makedirs(english_text_folder, exist_ok=True)
        
        # Read the file and extract slide blocks
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        slide_blocks = extract_slide_blocks(content)
        
        # Process each slide block
        for slide_number, slide_content, _ in slide_blocks:
            output_filename = f"{slide_number.zfill(2)}.txt"
            output_path = os.path.join(english_text_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(slide_content.strip())
        
        # Move the original file to all_transcripts folder
        new_transcript_path = os.path.join(all_transcripts_folder, file_name)
        if not os.path.exists(new_transcript_path):
            shutil.copy2(file_path, new_transcript_path)
            os.remove(file_path)
        
        return {
            "status": "success", 
            "file": file_name, 
            "slides": len(slide_blocks),
            "message": f"Processed {len(slide_blocks)} slides"
        }
    except Exception as e:
        # Just use basename of the file_path directly
        return {
            "status": "error", 
            "file": os.path.basename(file_path), 
            "slides": 0,
            "message": str(e)
        }

def process_summary_file(file_path):
    """Process a single summary file"""
    try:
        # Get file info
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # Extract lecture number from filename
        match = re.search(r'(\d+)', file_name)
        lecture_num = match.group(1) if match else "Unknown"
        
        # Create lecture folder name
        lecture_folder_name = f"Lecture {lecture_num.zfill(2)}"
        
        # Create directories
        all_summary_folder = os.path.join(dir_path, 'all_summary')
        os.makedirs(all_summary_folder, exist_ok=True)
        
        lecture_folder = os.path.join(dir_path, lecture_folder_name)
        os.makedirs(lecture_folder, exist_ok=True)
        
        english_summary_folder = os.path.join(lecture_folder, "English Summary text")
        os.makedirs(english_summary_folder, exist_ok=True)
        
        # Read the file and extract slide blocks
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        slide_blocks = extract_slide_blocks(content)
        
        # Process each slide block
        for slide_number, slide_content, _ in slide_blocks:
            output_filename = f"{slide_number.zfill(2)}.txt"
            output_path = os.path.join(english_summary_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(slide_content.strip())
        
        # Move the original file to all_summary folder
        new_summary_path = os.path.join(all_summary_folder, file_name)
        if not os.path.exists(new_summary_path):
            shutil.copy2(file_path, new_summary_path)
            os.remove(file_path)
        
        return {
            "status": "success", 
            "file": file_name, 
            "slides": len(slide_blocks),
            "message": f"Processed {len(slide_blocks)} slides"
        }
    except Exception as e:
        # Make sure file_name is defined even in case of error
        try:
            # If file_name was already defined earlier in the function
            file_name
        except NameError:
            # If not, define it now
            file_name = os.path.basename(file_path)
            
        return {
            "status": "error", 
            "file": file_name, 
            "slides": 0,
            "message": str(e)
        }

def display_compact_results(results: List[Dict], file_type: str):
    """Display processing results in a compact format"""
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    total_slides = sum(r.get("slides", 0) for r in results if r["status"] == "success")
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files Processed", success_count)
    with col2:
        st.metric("Slides Created", total_slides)
    with col3:
        st.metric("Errors", error_count)
    
    if success_count > 0:
        st.success(f"✅ Successfully processed {success_count} {file_type} files and created {total_slides} slide sections.")
    
    if error_count > 0:
        st.error(f"❌ {error_count} files had errors during processing.")
    
    # Show detailed results in expandable section
    if results:
        with st.expander(f"📋 Detailed {file_type.title()} Processing Results (Click to expand)"):
            # Create summary table
            table_data = []
            for result in results:
                table_data.append({
                    "File": result["file"],
                    "Status": "✅ Success" if result["status"] == "success" else "❌ Error",
                    "Slides": result.get("slides", 0),
                    "Message": result["message"]
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)

def main():
    st.title("Save Text")
    st.write("Break transcript and summary files into sections for TTS processing.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find transcript and summary files
    transcript_files = get_transcript_files(input_dir)
    summary_files = get_summary_files(input_dir)
    
    # Show what this tool does
    with st.expander("ℹ️ What does this tool do? (Click to expand)"):
        st.markdown("""
        ### Save Text - File Processing Tool
        
        This tool processes transcript and summary files to break them into individual slide sections for TTS (Text-to-Speech) processing:
        
        **Input Files:**
        - **Transcript Files**: Files with "Lecture" in the name (e.g., `Lecture 01.md`, `Lecture 32.txt`)
        - **Summary Files**: Files with summary indicators (e.g., `01-summary.md`, `25-d.txt`)
        
        **Processing:**
        - Extracts slide blocks from transcript/summary content
        - Creates individual `.txt` files for each slide (e.g., `01.txt`, `02.txt`, etc.)
        - Organizes files into proper folder structure
        
        **Output Structure:**
        ```
        Course Folder/
        ├── Lecture XX/
        │   ├── English text/          # From transcript files
        │   │   ├── 01.txt
        │   │   ├── 02.txt
        │   │   └── ...
        │   └── English Summary text/  # From summary files
        │       ├── 01.txt
        │       ├── 02.txt
        │       └── ...
        ├── all_transcripts/           # Original transcript files moved here
        └── all_summary/               # Original summary files moved here
        ```
        
        **File Movement:**
        - Original files are moved to `all_transcripts/` or `all_summary/` folders after processing
        - This prevents re-processing and keeps the workspace organized
        """)
    
    # Create tabs for transcript and summary files
    tabs = st.tabs(["📄 Transcript Files", "📋 Summary Files"])
    
    # Tab 1: Transcript Files
    with tabs[0]:
        st.header("Transcript Files")
        
        if not transcript_files:
            st.warning("No transcript files found in the input directory.")
            st.info("Looking for files with 'Lecture' in the filename that are not in processed folders.")
        else:
            # Display file count and process button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"Found {len(transcript_files)} transcript files ready for processing.")
            with col2:
                save_transcript = st.button("Process Transcript Files", key="save_transcript", use_container_width=True)
            
            # Show files to be processed
            with st.expander("📋 Files to be Processed (Click to expand)"):
                file_list = []
                for file_path in transcript_files:
                    file_name = os.path.basename(file_path)
                    course_dir = os.path.basename(os.path.dirname(file_path))
                    file_list.append({
                        "Course": course_dir,
                        "Filename": file_name
                    })
                
                if file_list:
                    df = pd.DataFrame(file_list)
                    st.dataframe(df, use_container_width=True)
            
            if save_transcript:
                with st.spinner("Processing transcript files..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results = []
                    
                    for i, file_path in enumerate(transcript_files):
                        # Update progress
                        progress = (i + 1) / len(transcript_files)
                        progress_bar.progress(progress)
                        
                        # Update status
                        file_name = os.path.basename(file_path)
                        status_text.info(f"Processing {i+1}/{len(transcript_files)}: {file_name}")
                        
                        # Process the file
                        result = process_transcript_file(file_path)
                        results.append(result)
                        
                        # Small delay for UI updates
                        time.sleep(0.1)
                    
                    # Complete
                    status_text.success(f"Processed {len(transcript_files)} files")
                    
                    # Store and display results
                    st.session_state.transcript_results = results
                    display_compact_results(results, "transcript")
        
        # Show previous results if available
        if 'transcript_results' in st.session_state:
            display_compact_results(st.session_state.transcript_results, "transcript")
    
    # Tab 2: Summary Files
    with tabs[1]:
        st.header("Summary Files")
        
        if not summary_files:
            st.warning("No summary files found in the input directory.")
            st.info("Looking for files with summary indicators (-summary, -d, -artifact-d) that are not in processed folders.")
        else:
            # Display file count and process button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"Found {len(summary_files)} summary files ready for processing.")
            with col2:
                save_summary = st.button("Process Summary Files", key="save_summary", use_container_width=True)
            
            # Show files to be processed
            with st.expander("📋 Files to be Processed (Click to expand)"):
                file_list = []
                for file_path in summary_files:
                    file_name = os.path.basename(file_path)
                    course_dir = os.path.basename(os.path.dirname(file_path))
                    file_list.append({
                        "Course": course_dir,
                        "Filename": file_name
                    })
                
                if file_list:
                    df = pd.DataFrame(file_list)
                    st.dataframe(df, use_container_width=True)
            
            if save_summary:
                with st.spinner("Processing summary files..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results = []
                    
                    for i, file_path in enumerate(summary_files):
                        # Update progress
                        progress = (i + 1) / len(summary_files)
                        progress_bar.progress(progress)
                        
                        # Update status
                        file_name = os.path.basename(file_path)
                        status_text.info(f"Processing {i+1}/{len(summary_files)}: {file_name}")
                        
                        # Process the file
                        result = process_summary_file(file_path)
                        results.append(result)
                        
                        # Small delay for UI updates
                        time.sleep(0.1)
                    
                    # Complete
                    status_text.success(f"Processed {len(summary_files)} files")
                    
                    # Store and display results
                    st.session_state.summary_results = results
                    display_compact_results(results, "summary")
        
        # Show previous results if available
        if 'summary_results' in st.session_state:
            display_compact_results(st.session_state.summary_results, "summary")

if __name__ == "__main__":
    main()