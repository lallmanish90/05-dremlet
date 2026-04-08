"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Restore PPTX files back into lecture folders after earlier reorganization or cleanup steps.
MAIN INPUTS:
- lecture folder trees under `input/`
MAIN OUTPUTS:
- restored PPTX files placed back into the expected lecture locations
REQUIRED CONFIG / ASSETS:
- `input/` directory
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none
"""

from dreamlet_cli.compat import st
import os
import shutil
from typing import Dict, List, Tuple

import re

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), 'input')

st.set_page_config(page_title="14 Restore PPTX - Dreamlet", page_icon="↩️")

st.title("14 Restore Files")
st.markdown("""
This page allows you to restore files from their processed folders back to their original locations.
This reverses the file movement performed by various processing steps.
""")

def find_files_by_type(folder_name: str, file_extensions: List[str]) -> Dict[str, List[str]]:
    """
    Find files of specific types in specified folders, organized by course
    
    Args:
        folder_name: Name of the folder to search for (e.g., 'all_pptx', 'all_slides')
        file_extensions: List of file extensions to search for (e.g., ['.pptx'], ['.txt', '.md'])
    
    Returns:
        Dictionary mapping course names to lists of file paths
    """
    input_dir = get_input_directory()
    course_files = {}
    
    # Walk through all directories to find specified folders
    for root, dirs, files in os.walk(input_dir):
        # Check if current directory matches the folder name
        if os.path.basename(root) == folder_name:
            # Find files with specified extensions
            matching_files = []
            for file in files:
                for ext in file_extensions:
                    if file.lower().endswith(ext.lower()):
                        matching_files.append(file)
                        break
            
            if matching_files:
                # Determine the course name from the path structure
                relative_path = os.path.relpath(root, input_dir)
                path_parts = relative_path.split(os.sep)
                
                # The course name should be the first part of the path
                course_name = path_parts[0] if len(path_parts) >= 1 else "Unknown"
                
                # Skip if this doesn't look like a valid course structure
                if course_name in ['.', '..', folder_name]:
                    continue
                
                if course_name not in course_files:
                    course_files[course_name] = []
                
                # Add full paths to the files
                for file in matching_files:
                    full_path = os.path.join(root, file)
                    course_files[course_name].append(full_path)
    
    return course_files

def get_original_location(file_path: str, folder_name: str) -> str:
    """
    Determine the original location of a file
    
    Args:
        file_path: Current path of file in the processed folder
        folder_name: Name of the processed folder (e.g., 'all_pptx', 'all_slides')
        
    Returns:
        Original path where the file should be restored
    """
    # Current path structure: .../lecture/folder_name/filename
    # Original path structure: .../lecture/filename
    
    processed_dir = os.path.dirname(file_path)
    parent_dir = os.path.dirname(processed_dir)
    filename = os.path.basename(file_path)
    
    original_path = os.path.join(parent_dir, filename)
    return original_path

def restore_files(selected_courses: List[str], course_files: Dict[str, List[str]], folder_name: str) -> List[Dict]:
    """
    Restore files from processed folders to their original locations
    
    Args:
        selected_courses: List of course names to process
        course_files: Dictionary mapping course names to file paths
        folder_name: Name of the processed folder (for context in messages)
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        files = course_files[course_name]
        
        for file_path in files:
            result = {
                "course": course_name,
                "file": os.path.basename(file_path),
                "status": "error",
                "message": "",
                "original_path": "",
                "restored_path": ""
            }
            
            try:
                original_path = get_original_location(file_path, folder_name)
                result["original_path"] = file_path
                result["restored_path"] = original_path
                
                # Check if source file exists
                if not os.path.exists(file_path):
                    result["message"] = f"Source file no longer exists in {folder_name} folder"
                    results.append(result)
                    continue
                
                # Check if destination already exists
                if os.path.exists(original_path):
                    result["message"] = "Destination file already exists - skipping to avoid overwrite"
                    result["status"] = "skipped"
                    results.append(result)
                    continue
                
                # Move the file back to original location
                shutil.move(file_path, original_path)
                
                result["status"] = "success"
                result["message"] = "Successfully restored to original location"
                results.append(result)
                
            except Exception as e:
                result["message"] = f"Error restoring file: {str(e)}"
                results.append(result)
    
    return results

def cleanup_empty_folders(selected_courses: List[str], course_files: Dict[str, List[str]], folder_name: str):
    """
    Remove empty processed folders after restoration
    
    Args:
        selected_courses: List of course names that were processed
        course_files: Dictionary mapping course names to file paths
        folder_name: Name of the processed folder to clean up
    """
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        files = course_files[course_name]
        
        # Get all unique processed folders from the processed files
        processed_folders = set()
        for file_path in files:
            processed_dir = os.path.dirname(file_path)
            processed_folders.add(processed_dir)
        
        # Check each folder and remove if empty
        for folder in processed_folders:
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    st.info(f"Removed empty folder: {folder}")
            except Exception as e:
                st.warning(f"Could not remove empty folder {folder}: {str(e)}")

def create_restore_tab(tab_name: str, folder_name: str, file_extensions: List[str], description: str):
    """
    Create a restore tab for a specific file type
    
    Args:
        tab_name: Display name for the tab
        folder_name: Name of the folder to search for files
        file_extensions: List of file extensions to look for
        description: Description of what this tab restores
    """
    st.markdown(f"**{description}**")
    
    # Find files
    with st.spinner(f"Scanning for {tab_name.lower()} files in {folder_name} folders..."):
        course_files = find_files_by_type(folder_name, file_extensions)
    
    if not course_files:
        st.info(f"No {tab_name.lower()} files found in any {folder_name} folders. Nothing to restore.")
        return
    
    # Display summary
    total_files = sum(len(files) for files in course_files.values())
    st.success(f"Found {total_files} {tab_name.lower()} files across {len(course_files)} courses that can be restored.")
    
    # Course selection
    st.header("Select Courses to Restore")
    
    # Create unique session state keys for this tab
    selected_key = f"selected_courses_{folder_name}"
    
    # Select All button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Select All", type="secondary", key=f"select_all_{folder_name}"):
            st.session_state[selected_key] = list(course_files.keys())
    
    with col2:
        if st.button("Deselect All", type="secondary", key=f"deselect_all_{folder_name}"):
            st.session_state[selected_key] = []
    
    # Initialize session state for selected courses
    if selected_key not in st.session_state:
        st.session_state[selected_key] = []
    
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
        is_selected = course_name in st.session_state[selected_key]
        checkbox_value = st.checkbox(
            f"{course_name} ({file_count} files)",
            value=is_selected,
            key=f"course_{course_name}_{folder_name}"
        )
        
        # Update session state based on checkbox
        if checkbox_value and course_name not in st.session_state[selected_key]:
            st.session_state[selected_key].append(course_name)
        elif not checkbox_value and course_name in st.session_state[selected_key]:
            st.session_state[selected_key].remove(course_name)
        
        # Show file details in an expandable section
        with st.expander(f"Files in {course_name}"):
            for file_path in course_files[course_name]:
                filename = os.path.basename(file_path)
                original_location = get_original_location(file_path, folder_name)
                st.write(f"**{filename}**")
                st.write(f"From: `{file_path}`")
                st.write(f"To: `{original_location}`")
                st.write("---")
    
    # Restore button
    if st.session_state[selected_key]:
        selected_count = len(st.session_state[selected_key])
        selected_files = sum(len(course_files[course]) for course in st.session_state[selected_key])
        
        st.header("Ready to Restore")
        st.write(f"Selected {selected_count} courses with {selected_files} total files.")
        
        if st.button(f"Restore {tab_name} Files", type="primary", key=f"restore_{folder_name}"):
            # Perform restoration
            with st.spinner(f"Restoring {tab_name.lower()} files..."):
                results = restore_files(st.session_state[selected_key], course_files, folder_name)
            
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
            for course_name in st.session_state[selected_key]:
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
            
            # Clean up empty folders
            if success_count > 0:
                with st.spinner(f"Cleaning up empty {folder_name} folders..."):
                    cleanup_empty_folders(st.session_state[selected_key], course_files, folder_name)
                
                st.success("Restoration completed successfully!")
            
    else:
        st.info(f"Select one or more courses to restore their {tab_name.lower()} files.")

def main():
    # Create tabs for different file types
    tab1, tab2, tab3, tab4 = st.tabs(["PPTX Files", "Summary Files", "Slides Files", "Transcripts Files"])
    
    with tab1:
        create_restore_tab(
            "PPTX", 
            "all_pptx", 
            [".pptx"],
            "Restore PPTX files from all_pptx folders back to their original locations. This reverses the file movement performed by the 06_4K_Image processing."
        )
    
    with tab2:
        create_restore_tab(
            "Summary", 
            "all_summary", 
            [".txt", ".md"],
            "Restore summary files from all_summary folders back to their original locations."
        )
    
    with tab3:
        create_restore_tab(
            "Slides", 
            "all_slides", 
            [".txt", ".md"],
            "Restore slide files from all_slides folders back to their original locations."
        )
    
    with tab4:
        create_restore_tab(
            "Transcripts", 
            "all_transcripts", 
            [".txt", ".md"],
            "Restore transcript files from all_transcripts folders back to their original locations."
        )

if __name__ == "__main__":
    main()
