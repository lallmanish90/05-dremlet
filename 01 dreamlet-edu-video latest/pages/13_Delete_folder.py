"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Delete selected folder types across lecture trees as a maintenance and recovery utility.
MAIN INPUTS:
- lecture folder trees under `input/`
MAIN OUTPUTS:
- matching subfolders removed in place
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
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any

# Local utility functions (moved from utils.file_operations)
def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

st.set_page_config(page_title="13 Delete Folders - Dreamlet", page_icon="🗂️")

def find_lecture_folders(input_dir: str) -> Dict:
    """
    Find all lecture folders across the file system and organize them by course and lecture
    
    Args:
        input_dir: Base input directory
        
    Returns:
        Dictionary organized by course, lecture, and folder types
    """
    organized_data = {}
    folder_types = set()  # To track all folder types across all lectures
    
    # Debug information
    st.sidebar.write("Scanning input directory:", input_dir)
    
    # First pass: find all courses by looking at top-level directories
    courses = {}
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Consider all top-level directories as potential courses
            courses[item] = item_path
    
    # Find all folders in lecture directories
    for course_name, course_path in courses.items():
        # Initialize course in data structure
        if course_name not in organized_data:
            organized_data[course_name] = {}
        
        # Look for lecture directories within this course
        for item in os.listdir(course_path):
            item_path = os.path.join(course_path, item)
            
            # Skip non-directories and hidden files
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
            
            # Check if this is a lecture directory
            is_lecture = "lecture" in item.lower()
            
            if is_lecture:
                lecture_name = item
                
                # Initialize lecture in data structure
                if lecture_name not in organized_data[course_name]:
                    organized_data[course_name][lecture_name] = {
                        "base_dir": item_path,
                        "folders": {}
                    }
                
                # Look for folders within this lecture
                lecture_folders = {}
                for folder in os.listdir(item_path):
                    folder_path = os.path.join(item_path, folder)
                    
                    # Skip non-directories and hidden files
                    if not os.path.isdir(folder_path) or folder.startswith('.'):
                        continue
                    
                    # Count files in this folder (for display)
                    file_count = sum(len(files) for _, _, files in os.walk(folder_path))
                    
                    # Store folder info
                    lecture_folders[folder] = {
                        "path": folder_path,
                        "file_count": file_count
                    }
                    
                    # Add to global set of folder types
                    folder_types.add(folder)
                
                # Store folders for this lecture
                organized_data[course_name][lecture_name]["folders"] = lecture_folders
    
    # If no lectures found directly, try a deeper search
    if not any(organized_data.values()):
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
            
            # If we couldn't determine the course, use a default name
            if not course_name:
                course_name = "Unknown Course"
            
            # Initialize data structures if needed
            if course_name not in organized_data:
                organized_data[course_name] = {}
                
            # Check for subdirectories (folder types) in this lecture directory
            folders_in_lecture = {}
            
            # Immediate subdirectories (folder types like "English text", "English audio", etc.)
            for folder in dirs:
                folder_path = os.path.join(root, folder)
                
                # Count files in this folder (for display)
                file_count = 0
                for _, _, f in os.walk(folder_path):
                    file_count += len(f)
                
                # Store folder info
                folders_in_lecture[folder] = {
                    "path": folder_path,
                    "file_count": file_count
                }
                
                # Add to global set of folder types
                folder_types.add(folder)
            
            # Store lecture info with its folders
            if lecture_name:
                organized_data[course_name][lecture_name] = {
                    "base_dir": root,
                    "folders": folders_in_lecture
                }
    
    # Add debug info to sidebar
    st.sidebar.write(f"Found {len(folder_types)} folder types")
    st.sidebar.write(f"Found {sum(len(lectures) for lectures in organized_data.values())} lectures")
    
    # Store all folder types in the organized data
    organized_data["__folder_types__"] = list(folder_types)
    
    return organized_data

def delete_folders(folders_to_delete: List[str]) -> Dict:
    """
    Delete selected folders
    
    Args:
        folders_to_delete: List of folder paths to delete
        
    Returns:
        Dictionary with results
    """
    result = {
        "deleted": 0,
        "errors": []
    }
    
    for folder_path in folders_to_delete:
        try:
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                result["deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting folder {folder_path}: {str(e)}")
    
    return result

def main():
    st.title("Delete Specific Folders")
    st.write("Delete specific folders within lectures without removing the entire lecture.")
    
    # Add warning about permanent deletion
    st.warning("""
    ## ⚠️ WARNING: PERMANENT DELETION ⚠️
    
    This tool will permanently delete selected folders!
    
    You can delete:
    - Specific folder types (e.g., "English text") from selected lectures
    - All instances of a specific folder type across multiple lectures
    
    This action cannot be undone!
    """)
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Button to refresh data
    if st.button("🔄 Refresh File Data", use_container_width=True):
        st.rerun()
    
    # Find and organize lecture folders
    with st.spinner("Scanning for folders..."):
        organized_data = find_lecture_folders(input_dir)
    
    # Extract folder types from the data
    all_folder_types = organized_data.pop("__folder_types__", [])
    all_folder_types.sort()  # Sort alphabetically
    
    # Check if we found any lectures
    if not organized_data:
        st.error("No lecture folders found in the input directory.")
        return
    
    # Create two tabs for different deletion modes
    tab1, tab2 = st.tabs(["Delete Specific Folders", "Delete Folder Type Across Lectures"])
    
    with tab1:
        st.header("Select Specific Folders to Delete")
        
        # Create organized selection interface with expandable sections
        selected_folders = []
        
        # Sort courses numerically
        def extract_number(course_name):
            match = re.search(r'\d+', course_name)
            if match:
                return int(match.group())
            return 999
        
        sorted_courses = sorted(organized_data.keys(), key=extract_number)
        
        # Course selection (as dropdown if many, radio if few)
        if len(sorted_courses) > 10:
            # Convert course names to readable format for selection
            course_options = {course: course for course in sorted_courses}
            selected_course = st.selectbox(
                "Select a course:",
                options=list(course_options.keys()),
                key="course_selector_specific"
            )
            courses_to_show = [selected_course]
        else:
            # For fewer courses, allow multi-select
            selected_courses = st.multiselect(
                "Select courses to view:",
                options=sorted_courses,
                default=[sorted_courses[0]] if sorted_courses else [],
                key="course_selector_multiselect"
            )
            courses_to_show = selected_courses if selected_courses else []
        
        # Display selected courses and their lectures
        for course in courses_to_show:
            with st.expander(f"Course: {course}", expanded=True):
                # Sort lectures numerically
                sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
                
                for lecture in sorted_lectures:
                    lecture_data = organized_data[course][lecture]
                    folders = lecture_data["folders"]
                    
                    if not folders:
                        continue
                    
                    st.write(f"**{lecture}**")
                    
                    # Create columns for better layout
                    cols = st.columns(2)
                    col_idx = 0
                    
                    # Display each folder with checkbox for selection
                    for folder_name, folder_info in sorted(folders.items()):
                        with cols[col_idx]:
                            # Display folder info
                            folder_label = f"{folder_name} ({folder_info['file_count']} files)"
                            if st.checkbox(folder_label, key=f"{course}_{lecture}_{folder_name}"):
                                selected_folders.append(folder_info["path"])
                        
                        # Alternate columns
                        col_idx = (col_idx + 1) % 2
        
        # Deletion section for specific folders
        st.subheader("Delete Selected Folders")
        
        # Show summary of what will be deleted
        if selected_folders:
            st.info(f"Selected {len(selected_folders)} folders for deletion")
            
            # Show selected folders (truncated if too many)
            max_display = 5
            with st.expander("View Selected Folders"):
                for i, folder in enumerate(selected_folders):
                    if i < max_display:
                        st.write(f"{i+1}. {folder}")
                    elif i == max_display:
                        st.write(f"...and {len(selected_folders) - max_display} more")
                        break
            
            # Confirmation checkboxes
            st.write("### Confirmation Required")
            confirmation = st.checkbox("I understand that this action will permanently delete all selected folders and cannot be undone", key="confirm_specific")
            
            if confirmation:
                delete_button = st.button("DELETE SELECTED FOLDERS", key="delete_specific_button", type="primary", use_container_width=True)
                
                if delete_button:
                    # Perform deletion
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Delete folders
                    status_text.info(f"Deleting {len(selected_folders)} folders...")
                    result = delete_folders(selected_folders)
                    
                    # Update progress
                    progress_bar.progress(1.0)
                    
                    # Show results
                    if result["errors"]:
                        status_text.warning(f"Deleted {result['deleted']} folders with {len(result['errors'])} errors")
                        with st.expander("View Errors"):
                            for error in result["errors"]:
                                st.error(error)
                    else:
                        status_text.success(f"Successfully deleted {result['deleted']} folders")
                    
                    # Add a refresh button
                    if st.button("Refresh Page", key="refresh_after_specific_delete", use_container_width=True):
                        st.rerun()
            else:
                st.write("Please confirm to proceed with deletion.")
        else:
            st.warning("No folders selected for deletion.")
    
    with tab2:
        st.header("Delete Folder Type Across Lectures")
        
        if not all_folder_types:
            st.warning("No common folder types found across lectures.")
            return
        
        # Select folder types to delete
        selected_types = st.multiselect(
            "Select folder types to delete across lectures:",
            options=all_folder_types,
            key="folder_type_selector"
        )
        
        if selected_types:
            # Course filter options
            st.subheader("Select Scope")
            scope = st.radio(
                "Where to delete these folder types:",
                options=["Selected courses only", "All courses"],
                key="scope_selector"
            )
            
            # If "Selected courses only", show course selection
            selected_courses_for_bulk = []
            if scope == "Selected courses only":
                # Default to the first course if available
                default_selection = [sorted_courses[0]] if sorted_courses else []
                
                selected_courses_for_bulk = st.multiselect(
                    "Select courses:",
                    options=sorted_courses,
                    default=default_selection,
                    key="course_selector_bulk"
                )
                
                if not selected_courses_for_bulk:
                    st.warning("Please select at least one course, or change the scope to 'All courses'.")
            else:
                # If "All courses", use all courses
                selected_courses_for_bulk = sorted_courses
                st.warning("⚠️ You have chosen to delete folders across ALL courses!")
            
            # Find all matching folders
            matching_folders = []
            for course in selected_courses_for_bulk:
                for lecture, lecture_data in organized_data[course].items():
                    for folder_name, folder_info in lecture_data["folders"].items():
                        if folder_name in selected_types:
                            matching_folders.append({
                                "course": course,
                                "lecture": lecture,
                                "folder": folder_name,
                                "path": folder_info["path"],
                                "file_count": folder_info["file_count"]
                            })
            
            # Show what will be deleted
            if matching_folders:
                st.info(f"Found {len(matching_folders)} folders matching selected types across {len(selected_courses_for_bulk)} courses")
                
                # Group by folder type for display
                folder_summary = {}
                for folder in matching_folders:
                    folder_type = folder["folder"]
                    if folder_type not in folder_summary:
                        folder_summary[folder_type] = {
                            "count": 0,
                            "file_count": 0
                        }
                    folder_summary[folder_type]["count"] += 1
                    folder_summary[folder_type]["file_count"] += folder["file_count"]
                
                # Display summary
                st.subheader("Summary of Folders to Delete")
                for folder_type, summary in folder_summary.items():
                    st.write(f"**{folder_type}**: {summary['count']} folders, {summary['file_count']} total files")
                
                # Show detailed list (expandable)
                with st.expander("View All Matching Folders"):
                    for folder in matching_folders:
                        st.write(f"{folder['course']} - {folder['lecture']} - {folder['folder']} ({folder['file_count']} files)")
                
                # Confirmation checkboxes
                st.write("### Confirmation Required")
                confirmation = st.checkbox("I understand that this action will permanently delete all matching folders and cannot be undone", key="confirm_bulk")
                double_confirmation = st.checkbox("I have backed up any important data and am ready to proceed with deletion", key="double_confirm_bulk")
                
                if confirmation and double_confirmation:
                    delete_button = st.button("DELETE SELECTED FOLDER TYPES", key="delete_bulk_button", type="primary", use_container_width=True)
                    
                    if delete_button:
                        # Perform deletion
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Collect all folder paths
                        folders_to_delete = [folder["path"] for folder in matching_folders]
                        
                        # Delete in batches for better progress updates
                        batch_size = max(1, len(folders_to_delete) // 10)
                        results = {
                            "deleted": 0,
                            "errors": []
                        }
                        
                        for i in range(0, len(folders_to_delete), batch_size):
                            batch = folders_to_delete[i:i+batch_size]
                            progress = (i + len(batch)) / len(folders_to_delete)
                            progress_bar.progress(progress)
                            
                            status_text.info(f"Deleting batch {i//batch_size + 1}/{(len(folders_to_delete) - 1)//batch_size + 1}...")
                            
                            # Delete batch
                            batch_result = delete_folders(batch)
                            results["deleted"] += batch_result["deleted"]
                            results["errors"].extend(batch_result["errors"])
                            
                            # Short delay for UI
                            time.sleep(0.1)
                        
                        # Complete progress
                        progress_bar.progress(1.0)
                        
                        # Show results
                        if results["errors"]:
                            status_text.warning(f"Deleted {results['deleted']} folders with {len(results['errors'])} errors")
                            with st.expander("View Errors"):
                                for error in results["errors"]:
                                    st.error(error)
                        else:
                            status_text.success(f"Successfully deleted {results['deleted']} folders")
                        
                        # Add a refresh button
                        if st.button("Refresh Page", key="refresh_after_bulk_delete", use_container_width=True):
                            st.rerun()
                else:
                    st.write("Please confirm both checkboxes to proceed with deletion.")
            else:
                st.warning(f"No folders of the selected types found in the chosen courses.")
        else:
            st.info("Please select at least one folder type to delete.")

if __name__ == "__main__":
    main()
