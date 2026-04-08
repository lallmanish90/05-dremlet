"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Delete selected lecture files as a maintenance and recovery utility.
MAIN INPUTS:
- lecture folders under `input/`
MAIN OUTPUTS:
- files removed in place from the selected lecture folders
REQUIRED CONFIG / ASSETS:
- `input/` directory
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none
"""

import streamlit as st
import os
import re
import time
import shutil
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any

# Local utility functions (moved from utils.file_operations)
def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def extract_course_lecture_section(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract course, lecture, and section information from a file path"""
    dir_parts = os.path.normpath(file_path).split(os.sep)
    course, lecture, section = None, None, None
    
    for part in dir_parts:
        if not course:
            course_match = re.search(r'course\s*(\d+)', part.lower())
            if course_match:
                course = course_match.group(1)
    
    filename = os.path.basename(file_path)
    for pattern in [r'lecture\s*(\d+)', r'lec\s*(\d+)', r'^(\d+)[-\s]']:
        lecture_match = re.search(pattern, filename.lower())
        if lecture_match:
            lecture = lecture_match.group(1)
            break
    
    return course, lecture, section

st.set_page_config(page_title="12 Delete - Dreamlet", page_icon="🗑️")

def find_lecture_files(input_dir: str) -> Dict:
    """
    Find all lecture files across the file system and organize them by course and lecture
    
    Args:
        input_dir: Base input directory
        
    Returns:
        Dictionary organized by course and lecture
    """
    organized_data = {}
    
    # Find all lecture directories
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Check if this is a lecture directory (contains "lecture" in name)
        parts = Path(root).parts
        
        # Check if directory name contains "lecture"
        is_lecture_dir = any(
            "lecture" in part.lower() 
            for part in parts
        )
        
        if not is_lecture_dir:
            continue
            
        # Extract lecture info
        course_name = None
        lecture_name = None
        
        # Find lecture name (directory with "lecture" in it)
        for i, part in enumerate(parts):
            if "lecture" in part.lower():
                lecture_name = part
                # Course is typically the parent directory of lecture
                if i > 0:
                    course_name = parts[i-1]
                break
        
        # Skip if we couldn't determine both course and lecture
        if not course_name or not lecture_name:
            continue
            
        # Initialize data structures if needed
        if course_name not in organized_data:
            organized_data[course_name] = {}
            
        # Initialize lecture data with base directory
        if lecture_name not in organized_data[course_name]:
            organized_data[course_name][lecture_name] = {
                "base_dir": root,
                "files_to_delete": set(),
                "directories_to_delete": set(),
                "file_count": 0,
                "directory_count": 0
            }
            
        # First, add the lecture directory itself
        organized_data[course_name][lecture_name]["directories_to_delete"].add(root)
        
        # Find all files in this lecture directory
        lecture_files = []
        for r, d, f in os.walk(root):
            # Add all files
            for file in f:
                file_path = os.path.join(r, file)
                organized_data[course_name][lecture_name]["files_to_delete"].add(file_path)
                lecture_files.append(file_path)
            
            # Add all subdirectories
            for directory in d:
                dir_path = os.path.join(r, directory)
                organized_data[course_name][lecture_name]["directories_to_delete"].add(dir_path)
    
        # Find lecture number to use for matching files in all_* folders
        lecture_num = None
        lecture_num_match = re.search(r'lecture\s*(\d+)', lecture_name.lower())
        if lecture_num_match:
            lecture_num = lecture_num_match.group(1)
        
        if lecture_num:
            # Find files in all_transcripts, all_summary, all_pptx, and all_slides that match this lecture
            for folder_name in ['all_transcripts', 'all_summary', 'all_pptx', 'all_slides']:
                # Navigate from course directory
                course_dir = os.path.dirname(root)
                all_folder = os.path.join(course_dir, folder_name)
                
                if os.path.exists(all_folder) and os.path.isdir(all_folder):
                    # Find files with matching lecture number
                    for file in os.listdir(all_folder):
                        file_path = os.path.join(all_folder, file)
                        
                        # Check if file is related to this lecture
                        if re.search(rf'lecture\s*{lecture_num}\b', file.lower()) or re.search(rf'\b{lecture_num}\b', file):
                            organized_data[course_name][lecture_name]["files_to_delete"].add(file_path)
                            lecture_files.append(file_path)
        
        # Update counts
        organized_data[course_name][lecture_name]["file_count"] = len(organized_data[course_name][lecture_name]["files_to_delete"])
        organized_data[course_name][lecture_name]["directory_count"] = len(organized_data[course_name][lecture_name]["directories_to_delete"])
    
    return organized_data

def delete_lecture(lecture_data: Dict) -> Dict:
    """
    Delete all files and directories for a lecture
    
    Args:
        lecture_data: Dictionary with lecture data
        
    Returns:
        Dictionary with results
    """
    result = {
        "files_deleted": 0,
        "directories_deleted": 0,
        "errors": []
    }
    
    # First delete individual files to clean up directories
    for file_path in sorted(lecture_data["files_to_delete"]):
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                result["files_deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting file {file_path}: {str(e)}")
    
    # Delete directories in reverse order (deepest first)
    for dir_path in sorted(lecture_data["directories_to_delete"], reverse=True):
        try:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # Try to delete, but only if empty (safety check)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    result["directories_deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting directory {dir_path}: {str(e)}")
    
    return result

def main():
    st.title("Delete Lecture Files")
    st.write("Delete all files and directories related to specific lectures.")
    
    # Add warning about permanent deletion
    st.warning("""
    ## ⚠️ WARNING: PERMANENT DELETION ⚠️
    
    This tool will permanently delete all files related to the selected lectures!
    
    This includes:
    - All files in the lecture directory
    - All files in the English text folder
    - All files in the English Summary text folder
    - All files in the English image folder
    - Matching files in all_transcripts folder
    - Matching files in all_summary folder
    - Matching files in all_pptx folder
    - Matching files in all_slides folder
    
    This action cannot be undone!
    """)
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Button to refresh data
    if st.button("Refresh File Data", use_container_width=True):
        st.rerun()
    
    # Find and organize lecture files
    with st.spinner("Scanning for lecture files..."):
        organized_data = find_lecture_files(input_dir)
    
    # Check if we found any lectures
    if not organized_data:
        st.error("No lecture files found in the input directory.")
        return
    
    # Global controls
    st.header("Select Lectures to Delete")
    
    # Global select all button
    select_all = st.checkbox("Select ALL Lectures (use with caution)", key="select_all_global")
    
    if select_all:
        st.error("⚠️ You have selected ALL lectures for deletion! Please review carefully before proceeding.")
    
    # Create organized selection interface with expandable sections
    selected_lectures = {}
    total_files_to_delete = 0
    total_directories_to_delete = 0
    
    # Sort courses numerically
    def extract_number(course_name):
        match = re.search(r'\d+', course_name)
        if match:
            return int(match.group())
        return 999
    
    sorted_courses = sorted(organized_data.keys(), key=extract_number)
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}", expanded=True):
            # Add "Select All" checkbox for this course
            all_in_course = st.checkbox(f"Select All in {course}", key=f"all_{course}") or select_all
            
            if all_in_course:
                st.error(f"⚠️ You have selected ALL lectures in {course} for deletion!")
            
            # Sort lectures numerically using the same extract_number function
            sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
            
            for lecture in sorted_lectures:
                lecture_data = organized_data[course][lecture]
                file_count = lecture_data["file_count"]
                dir_count = lecture_data["directory_count"]
                
                # Display lecture info with file counts (simplified)
                st.write(f"**{lecture}:** {file_count} files, {dir_count} directories")
                
                # Select this lecture
                if all_in_course:
                    selected = True
                    st.write("🗑️ Selected for deletion (from 'Select all')")
                else:
                    selected = st.checkbox(f"Delete {lecture}", key=f"{course}_{lecture}")
                
                if selected:
                    selected_lectures[(course, lecture)] = lecture_data
                    total_files_to_delete += file_count
                    total_directories_to_delete += dir_count
    
    # Deletion section
    st.header("Delete Selected Lectures")
    
    # Show summary of what will be deleted
    if selected_lectures:
        st.info(f"Selected {len(selected_lectures)} lectures for deletion")
        st.info(f"This will delete approximately {total_files_to_delete} files and {total_directories_to_delete} directories")
        
        # Confirmation checkboxes
        st.write("### Confirmation Required")
        confirmation = st.checkbox("I understand that this action will permanently delete all selected files and cannot be undone", key="confirm")
        double_confirmation = st.checkbox("I have backed up any important data and am ready to proceed with deletion", key="double_confirm")
        
        if confirmation and double_confirmation:
            delete_button = st.button("DELETE SELECTED LECTURES", key="delete_button", type="primary", use_container_width=True)
            
            if delete_button:
                # Perform deletion
                progress_bar = st.progress(0)
                status_text = st.empty()
                results = []
                
                for i, ((course, lecture), lecture_data) in enumerate(selected_lectures.items()):
                    # Update progress
                    progress = (i + 1) / len(selected_lectures)
                    progress_bar.progress(progress)
                    
                    # Update status
                    status_text.info(f"Deleting {i+1}/{len(selected_lectures)}: {course} - {lecture}")
                    
                    # Delete files and directories
                    result = delete_lecture(lecture_data)
                    
                    # Add to results
                    results.append({
                        "course": course,
                        "lecture": lecture,
                        "files_deleted": result["files_deleted"],
                        "directories_deleted": result["directories_deleted"],
                        "errors": len(result["errors"]),
                        "error_details": result["errors"]
                    })
                    
                    # Small delay for UI updates
                    time.sleep(0.1)
                
                # Complete
                status_text.success(f"Deleted {len(selected_lectures)} lectures")
                
                # Display results
                total_files_deleted = sum(r["files_deleted"] for r in results)
                total_dirs_deleted = sum(r["directories_deleted"] for r in results)
                total_errors = sum(r["errors"] for r in results)
                
                st.write(f"✅ Successfully deleted: {total_files_deleted} files and {total_dirs_deleted} directories")
                if total_errors > 0:
                    st.write(f"❌ Errors: {total_errors}")
                
                # Add a refresh button to clear all selections
                if st.button("Refresh Page (Clear Selections)", key="refresh_after_delete", use_container_width=True):
                    # Using session state would be better, but for now we'll just rerun
                    st.rerun()
                
                # Show simplified results
                st.subheader("Deletion Results:")
                for result in results:
                    st.write(f"**{result['course']} - {result['lecture']}**: {result['files_deleted']} files, {result['directories_deleted']} directories")
                
                # Show errors if any
                if total_errors > 0:
                    with st.expander("View Error Details"):
                        for result in results:
                            if result["errors"] > 0:
                                st.write(f"### {result['course']} - {result['lecture']}")
                                for error in result["error_details"]:
                                    st.error(error)
        else:
            st.write("Please confirm both checkboxes to proceed with deletion.")
    else:
        st.warning("No lectures selected for deletion.")

if __name__ == "__main__":
    main()
