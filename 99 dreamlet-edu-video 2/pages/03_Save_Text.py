import streamlit as st
import os
import re
import time
import shutil
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# Import utility functions
from utils.file_operations import (
    get_input_directory,
    get_output_directory,
    ensure_directory_exists,
    extract_course_lecture_section
)
from utils.text_processing import extract_slide_blocks

st.set_page_config(page_title="03 Save Text - Dreamlet", page_icon="💾")

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
    
    # List all files in input directory for debugging
    with st.expander("Debug: Show all files in input directory"):
        all_files = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        st.write(f"Total files found: {len(all_files)}")
        for file in all_files:
            st.write(file)
    
    tabs = st.tabs(["Transcript Files", "Summary Files"])
    
    # Tab 1: Transcript Files
    with tabs[0]:
        st.header("Transcript Files")
        
        if not transcript_files:
            st.warning("No transcript files found in the input directory.")
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"Found {len(transcript_files)} transcript files.")
            with col2:
                save_transcript = st.button("Save Transcript Files", key="save_transcript", use_container_width=True)
            
            if save_transcript:
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
                
                # Display results
                success_count = sum(1 for r in results if r["status"] == "success")
                error_count = len(results) - success_count
                
                st.write(f"✅ Successfully processed: {success_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Show results table
                df = pd.DataFrame(results)
                st.dataframe(df)
    
    # Tab 2: Summary Files
    with tabs[1]:
        st.header("Summary Files")
        
        if not summary_files:
            st.warning("No summary files found in the input directory.")
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"Found {len(summary_files)} summary files.")
            with col2:
                save_summary = st.button("Save Summary Files", key="save_summary", use_container_width=True)
            
            if save_summary:
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
                
                # Display results
                success_count = sum(1 for r in results if r["status"] == "success")
                error_count = len(results) - success_count
                
                st.write(f"✅ Successfully processed: {success_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Show results table
                df = pd.DataFrame(results)
                st.dataframe(df)

if __name__ == "__main__":
    main()