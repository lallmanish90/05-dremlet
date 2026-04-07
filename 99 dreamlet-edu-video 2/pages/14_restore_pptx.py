import streamlit as st
import os
import shutil
from typing import Dict, List, Tuple
from utils.file_operations import get_input_directory
import re

st.set_page_config(page_title="14 Restore PPTX - Dreamlet", page_icon="↩️")

st.title("14 Restore PPTX Files")
st.markdown("""
This page allows you to restore PPTX files from their `all_pptx` folders back to their original locations.
This reverses the file movement performed by the 06_4K_Image processing.
""")

def find_all_pptx_files() -> Dict[str, List[str]]:
    """
    Find all PPTX files in all_pptx folders, organized by course
    
    Returns:
        Dictionary mapping course names to lists of PPTX file paths in all_pptx folders
    """
    input_dir = get_input_directory()
    course_files = {}
    
    # Walk through all directories to find all_pptx folders
    for root, dirs, files in os.walk(input_dir):
        # Check if current directory is an all_pptx folder
        if os.path.basename(root) == 'all_pptx':
            # Find PPTX files in this all_pptx folder
            pptx_files = [f for f in files if f.lower().endswith('.pptx')]
            
            if pptx_files:
                # Determine the course name from the path structure
                # Remove input_dir from the path and split into parts
                relative_path = os.path.relpath(root, input_dir)
                path_parts = relative_path.split(os.sep)
                
                # The course name should be the first part of the path
                # Handle different possible structures:
                # 1. course/lecture/all_pptx
                # 2. course/section/lecture/all_pptx
                course_name = path_parts[0] if len(path_parts) >= 1 else "Unknown"
                
                # Skip if this doesn't look like a valid course structure
                if course_name in ['.', '..', 'all_pptx']:
                    continue
                
                if course_name not in course_files:
                    course_files[course_name] = []
                
                # Add full paths to the PPTX files
                for pptx_file in pptx_files:
                    full_path = os.path.join(root, pptx_file)
                    course_files[course_name].append(full_path)
    
    return course_files

def get_original_location(pptx_path: str) -> str:
    """
    Determine the original location of a PPTX file
    
    Args:
        pptx_path: Current path of PPTX file in all_pptx folder
        
    Returns:
        Original path where the file should be restored
    """
    # Current path structure: .../lecture/all_pptx/filename.pptx
    # Original path structure: .../lecture/filename.pptx
    
    all_pptx_dir = os.path.dirname(pptx_path)
    lecture_dir = os.path.dirname(all_pptx_dir)
    filename = os.path.basename(pptx_path)
    
    original_path = os.path.join(lecture_dir, filename)
    return original_path

def restore_pptx_files(selected_courses: List[str], course_files: Dict[str, List[str]]) -> List[Dict]:
    """
    Restore PPTX files from all_pptx folders to their original locations
    
    Args:
        selected_courses: List of course names to process
        course_files: Dictionary mapping course names to PPTX file paths
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        pptx_files = course_files[course_name]
        
        for pptx_path in pptx_files:
            result = {
                "course": course_name,
                "file": os.path.basename(pptx_path),
                "status": "error",
                "message": "",
                "original_path": "",
                "restored_path": ""
            }
            
            try:
                original_path = get_original_location(pptx_path)
                result["original_path"] = pptx_path
                result["restored_path"] = original_path
                
                # Check if source file exists
                if not os.path.exists(pptx_path):
                    result["message"] = "Source file no longer exists in all_pptx folder"
                    results.append(result)
                    continue
                
                # Check if destination already exists
                if os.path.exists(original_path):
                    result["message"] = "Destination file already exists - skipping to avoid overwrite"
                    result["status"] = "skipped"
                    results.append(result)
                    continue
                
                # Move the file back to original location
                shutil.move(pptx_path, original_path)
                
                result["status"] = "success"
                result["message"] = "Successfully restored to original location"
                results.append(result)
                
            except Exception as e:
                result["message"] = f"Error restoring file: {str(e)}"
                results.append(result)
    
    return results

def cleanup_empty_all_pptx_folders(selected_courses: List[str], course_files: Dict[str, List[str]]):
    """
    Remove empty all_pptx folders after restoration
    
    Args:
        selected_courses: List of course names that were processed
        course_files: Dictionary mapping course names to PPTX file paths
    """
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        pptx_files = course_files[course_name]
        
        # Get all unique all_pptx folders from the processed files
        all_pptx_folders = set()
        for pptx_path in pptx_files:
            all_pptx_dir = os.path.dirname(pptx_path)
            all_pptx_folders.add(all_pptx_dir)
        
        # Check each folder and remove if empty
        for folder in all_pptx_folders:
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    st.info(f"Removed empty folder: {folder}")
            except Exception as e:
                st.warning(f"Could not remove empty folder {folder}: {str(e)}")

def main():
    # Find all PPTX files in all_pptx folders
    with st.spinner("Scanning for PPTX files in all_pptx folders..."):
        course_files = find_all_pptx_files()
    
    if not course_files:
        st.info("No PPTX files found in any all_pptx folders. Nothing to restore.")
        return
    
    # Display summary
    total_files = sum(len(files) for files in course_files.values())
    st.success(f"Found {total_files} PPTX files across {len(course_files)} courses that can be restored.")
    
    # Course selection
    st.header("Select Courses to Restore")
    
    # Select All button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Select All", type="secondary"):
            st.session_state.selected_courses = list(course_files.keys())
    
    with col2:
        if st.button("Deselect All", type="secondary"):
            st.session_state.selected_courses = []
    
    # Initialize session state for selected courses
    if 'selected_courses' not in st.session_state:
        st.session_state.selected_courses = []
    
    # Course checkboxes
    st.subheader("Available Courses")
    
    # Sort courses numerically
    def extract_course_number(course_name):
        match = re.search(r'(\d+)', course_name)
        return int(match.group(1)) if match else 999
    
    sorted_courses = sorted(course_files.keys(), key=extract_course_number)
    
    # Display courses with file counts and checkboxes
    for course_name in sorted_courses:
        file_count = len(course_files[course_name])
        
        # Create checkbox for each course
        is_selected = course_name in st.session_state.selected_courses
        checkbox_value = st.checkbox(
            f"{course_name} ({file_count} files)",
            value=is_selected,
            key=f"course_{course_name}"
        )
        
        # Update session state based on checkbox
        if checkbox_value and course_name not in st.session_state.selected_courses:
            st.session_state.selected_courses.append(course_name)
        elif not checkbox_value and course_name in st.session_state.selected_courses:
            st.session_state.selected_courses.remove(course_name)
        
        # Show file details in an expandable section
        with st.expander(f"Files in {course_name}"):
            for pptx_path in course_files[course_name]:
                filename = os.path.basename(pptx_path)
                original_location = get_original_location(pptx_path)
                st.write(f"**{filename}**")
                st.write(f"From: `{pptx_path}`")
                st.write(f"To: `{original_location}`")
                st.write("---")
    
    # Restore button
    if st.session_state.selected_courses:
        selected_count = len(st.session_state.selected_courses)
        selected_files = sum(len(course_files[course]) for course in st.session_state.selected_courses)
        
        st.header("Ready to Restore")
        st.write(f"Selected {selected_count} courses with {selected_files} total files.")
        
        if st.button("Restore PPTX Files", type="primary"):
            # Perform restoration
            with st.spinner("Restoring PPTX files..."):
                results = restore_pptx_files(st.session_state.selected_courses, course_files)
            
            # Display results
            st.header("Restoration Results")
            
            # Summary statistics
            success_count = len([r for r in results if r["status"] == "success"])
            skipped_count = len([r for r in results if r["status"] == "skipped"])
            error_count = len([r for r in results if r["status"] == "error"])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Successfully Restored", success_count)
            with col2:
                st.metric("Skipped", skipped_count)
            with col3:
                st.metric("Errors", error_count)
            
            # Detailed results by course
            for course_name in st.session_state.selected_courses:
                course_results = [r for r in results if r["course"] == course_name]
                if course_results:
                    with st.expander(f"Results for {course_name} ({len(course_results)} files)"):
                        for result in course_results:
                            if result["status"] == "success":
                                st.success(f"✅ {result['file']}: {result['message']}")
                            elif result["status"] == "skipped":
                                st.warning(f"⏭️ {result['file']}: {result['message']}")
                            else:
                                st.error(f"❌ {result['file']}: {result['message']}")
            
            # Clean up empty all_pptx folders
            if success_count > 0:
                with st.spinner("Cleaning up empty all_pptx folders..."):
                    cleanup_empty_all_pptx_folders(st.session_state.selected_courses, course_files)
                
                st.success("Restoration completed successfully!")
            
    else:
        st.info("Select one or more courses to restore their PPTX files.")

if __name__ == "__main__":
    main()