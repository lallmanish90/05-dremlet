import streamlit as st
import os
import time
import re
from typing import Dict, List
from datetime import datetime, timedelta

# Import utility functions
from utils.file_operations import (
    get_input_directory,
    find_slide_files,
    ensure_directory_exists
)

st.set_page_config(page_title="05 Move Slides - Dreamlet", page_icon="📄")

def find_all_slide_files() -> List[str]:
    """
    Find all slide files in the input directory
    
    Returns:
        List of slide file paths
    """
    input_dir = get_input_directory()
    all_slides = find_slide_files(input_dir)
    
    # Filter out slides that are already in an all_slides directory
    filtered_slides = []
    for slide_path in all_slides:
        # Check if this is inside an all_slides directory - avoid moving already moved files
        parent_dir = os.path.basename(os.path.dirname(slide_path))
        if parent_dir != 'all_slides':
            filtered_slides.append(slide_path)
    
    return filtered_slides

def move_slide_files(progress_bar, status_text) -> List[Dict]:
    """
    Move slide files to all_slides folders
    
    Args:
        progress_bar: Streamlit progress bar object
        status_text: Streamlit text element for status updates
        
    Returns:
        List of results dictionaries
    """
    results = []
    
    # Find all slide files
    all_slides = find_all_slide_files()
    total_slides = len(all_slides)
    
    # Start time for estimating remaining time
    start_time = datetime.now()
    processed_count = 0
    
    # Process each slide file
    for i, slide_path in enumerate(all_slides):
        # Update progress
        processed_count = i + 1
        progress = processed_count / total_slides
        progress_bar.progress(progress)
        
        # Calculate estimated time remaining
        if processed_count > 0:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            time_per_file = elapsed_time / processed_count
            remaining_files = total_slides - processed_count
            remaining_seconds = remaining_files * time_per_file
            remaining_time = str(timedelta(seconds=int(remaining_seconds)))
            
            file_name = os.path.basename(slide_path)
            status_text.info(f"Processing {processed_count}/{total_slides}: {file_name} (Est. time remaining: {remaining_time})")
        else:
            file_name = os.path.basename(slide_path)
            status_text.info(f"Processing {processed_count}/{total_slides}: {file_name}")
        
        result = {
            "file_path": slide_path,
            "status": "error",
            "message": ""
        }
        
        try:
            # Get the directory containing the slide file
            slide_dir = os.path.dirname(slide_path)
            
            # Create 'all_slides' directory in the same folder as the slide file
            all_slides_folder = os.path.join(slide_dir, 'all_slides')
            ensure_directory_exists(all_slides_folder)
            
            # Check if destination file already exists
            new_slide_path = os.path.join(all_slides_folder, os.path.basename(slide_path))
            if os.path.exists(new_slide_path):
                result["status"] = "skipped"
                result["message"] = "Slide file already exists in all_slides directory"
            else:
                # Move the slide file to all_slides folder
                os.rename(slide_path, new_slide_path)
                
                result["status"] = "success"
                result["message"] = "Moved to all_slides directory"
        
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
        
        results.append(result)
        
        # Small delay for UI updates
        time.sleep(0.05)
    
    # Ensure progress bar reaches 100% at the end
    progress_bar.progress(1.0)
    
    return results

def main():
    st.title("Move Slides")
    st.write("Move slide files to 'all_slides' folders throughout the directory structure.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find slides
    all_slides = find_all_slide_files()
    
    if not all_slides:
        st.warning("No slide files found in the input directory or all slide files are already in 'all_slides' directories.")
        return
    
    # Display number of slides found
    total_slides = len(all_slides)
    st.info(f"Found {total_slides} slide files that need to be moved to 'all_slides' directories.")
    
    # Process slides
    st.header("Move Slides")
    
    if st.button("Move Slide Files", disabled=total_slides == 0):
        if total_slides == 0:
            st.warning("No slide files found for moving.")
            return
        
        # Process slides with progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        # Move the slide files with progress tracking
        results = move_slide_files(progress_bar, status_text)
        
        # Complete
        status_text.success(f"Processed {total_slides} slide files")
        
        # Display results
        with results_container:
            st.subheader("Processing Results")
            
            # Statistics
            success_count = sum(1 for r in results if r["status"] == "success")
            skipped_count = sum(1 for r in results if r["status"] == "skipped")
            error_count = sum(1 for r in results if r["status"] == "error")
            
            st.write(f"✅ Successfully moved: {success_count}")
            st.write(f"⏭️ Skipped (already moved): {skipped_count}")
            st.write(f"❌ Errors: {error_count}")
            
            # Detailed results
            for result in results:
                if result["status"] == "success":
                    status_icon = "✅"
                elif result["status"] == "skipped":
                    status_icon = "⏭️"
                else:
                    status_icon = "❌"
                
                file_name = os.path.basename(result["file_path"])
                
                with st.expander(f"{status_icon} {file_name}"):
                    st.write(f"**Status:** {result['status']}")
                    st.write(f"**Message:** {result['message']}")
                    st.write(f"**Original path:** {result['file_path']}")

if __name__ == "__main__":
    main()