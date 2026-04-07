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
import pandas as pd
from typing import Dict, List, Tuple
import pptx

# Import utility functions

    get_input_directory,
    find_transcript_files,
    find_slide_files,
    find_presentation_files,
    group_files_by_lecture,
    extract_course_lecture_section
)

    count_slides_in_transcript,
    count_slides_in_slide_file
)


st.set_page_config(page_title="05 Count - Dreamlet", page_icon="🔢", layout="wide")

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

def count_slides_in_all_files() -> Dict:
    """
    Count slides in all files and identify discrepancies
    
    Returns:
        Dictionary with counting results including:
        - total_discrepancies: Count discrepancies across all three file types
        - total_transcript_pres_discrepancies: Count discrepancies only between transcript and presentation files
    """
    input_dir = get_input_directory()
    
    # Get all files by type
    transcripts = find_transcript_files(input_dir)
    slides = find_slide_files(input_dir)
    presentations = find_presentation_files(input_dir)
    
    # Group files by lecture
    grouped_files = group_files_by_lecture(transcripts, slides, presentations)
    
    # Group data by course
    course_data = {}
    
    # Count discrepancies
    total_discrepancies = 0
    total_transcript_pres_discrepancies = 0
    discrepancies_data = []
    transcript_pres_discrepancies_data = []
    
    # Process all lecture sets
    for lecture_key, files in grouped_files.items():
        transcript_path = files["transcript"]
        slide_path = files["slide"]
        presentation_path = files["presentation"]
        
        # Extract course information using the full directory name
        full_course_name = None
        if transcript_path:
            full_course_name = get_full_course_name(transcript_path)
        elif slide_path:
            full_course_name = get_full_course_name(slide_path)
        elif presentation_path:
            full_course_name = get_full_course_name(presentation_path)
        
        if not full_course_name:
            full_course_name = "Uncategorized"
            
        # Also extract the numeric course id for sorting
        course_num = re.search(r'\d+', full_course_name)
        course = course_num.group() if course_num else "999"
        
        # Count slides in each file
        transcript_count = 0
        slide_count = 0
        presentation_count = 0
        
        if transcript_path:
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                transcript_count = count_slides_in_transcript(transcript_content)
            except Exception:
                transcript_count = -1  # Error indicator
        
        if slide_path:
            try:
                with open(slide_path, 'r', encoding='utf-8') as f:
                    slide_content = f.read()
                slide_count = count_slides_in_slide_file(slide_content)
            except Exception:
                slide_count = -1  # Error indicator
        
        if presentation_path:
            try:
                success, presentation_count = count_slides_in_pptx(presentation_path)
                if not success:
                    # Fallback: try using python-pptx library
                    try:
                        prs = pptx.Presentation(presentation_path)
                        presentation_count = len(prs.slides)
                    except Exception:
                        presentation_count = -1  # Error indicator
            except Exception:
                presentation_count = -1  # Error indicator
        
        # Check for discrepancies across all file types
        counts = [c for c in [transcript_count, slide_count, presentation_count] if c > 0]
        has_discrepancy = len(set(counts)) > 1 if counts else False
        
        # Check for discrepancies specifically between transcript and presentation (ignoring slide count)
        transcript_pres_counts = [c for c in [transcript_count, presentation_count] if c > 0]
        has_transcript_pres_discrepancy = len(set(transcript_pres_counts)) > 1 if len(transcript_pres_counts) > 1 else False
        
        if has_discrepancy:
            total_discrepancies += 1
            
        if has_transcript_pres_discrepancy:
            total_transcript_pres_discrepancies += 1
            transcript_pres_discrepancies_data.append({
                "lecture_key": lecture_key,
                "full_course_name": full_course_name,
                "course_num": course,
                "transcript_path": os.path.basename(transcript_path) if transcript_path else None,
                "transcript_count": transcript_count,
                "presentation_path": os.path.basename(presentation_path) if presentation_path else None,
                "presentation_count": presentation_count
            })
        
        # Create course entry if it doesn't exist
        if course not in course_data:
            course_data[course] = []
        
        # Create lecture data
        lecture_data = {
            "lecture_key": lecture_key,
            "full_course_name": full_course_name,
            "course_num": course,
            "transcript_path": os.path.basename(transcript_path) if transcript_path else None,
            "transcript_count": transcript_count,
            "slide_path": os.path.basename(slide_path) if slide_path else None,
            "slide_count": slide_count,
            "presentation_path": os.path.basename(presentation_path) if presentation_path else None,
            "presentation_count": presentation_count,
            "has_discrepancy": has_discrepancy
        }
        
        # Add to course data
        course_data[course].append(lecture_data)
        
        # If it has a discrepancy, add to discrepancies list
        if has_discrepancy:
            discrepancies_data.append(lecture_data)
    
    return {
        "course_data": course_data,
        "total_checked": len(grouped_files),
        "total_discrepancies": total_discrepancies,
        "discrepancies": discrepancies_data,
        "total_transcript_pres_discrepancies": total_transcript_pres_discrepancies,
        "transcript_pres_discrepancies": transcript_pres_discrepancies_data
    }

def main():
    st.title("Count - old")
    st.write("Verify alignment between transcript sections, slide descriptions, and presentation slides for each lecture.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Count Button
    if st.button("Count Slides"):
        with st.spinner("Counting slides in all files..."):
            # Display progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize progress steps
            status_text.text("Finding files...")
            progress_bar.progress(0.2)
            time.sleep(0.5)
            
            status_text.text("Counting slides...")
            progress_bar.progress(0.5)
            time.sleep(0.5)
            
            # Count slides
            results = count_slides_in_all_files()
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("Counting complete")
            
            # Store results in session state
            st.session_state.count_results = results
    
    # Display results if available
    if hasattr(st.session_state, 'count_results'):
        results = st.session_state.count_results
        course_data = results["course_data"]
        
        # Summary dashboard
        st.header("Status Dashboard")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Lecture Sets Checked", results["total_checked"])
        
        with col2:
            # Make this a clickable button that will show discrepancies
            discrepancy_text = f"Discrepancies Found: {results['total_discrepancies']}"
            if st.button(discrepancy_text, key="discrepancies_button"):
                st.session_state.show_discrepancies = True
            
        with col3:
            # Button for transcript-presentation discrepancies (ignoring slide count)
            transcript_discrepancy_text = f"Discrepancies (Ignoring Slide Count): {results['total_transcript_pres_discrepancies']}"
            if st.button(transcript_discrepancy_text, key="transcript_pres_discrepancies_button"):
                st.session_state.show_transcript_pres_discrepancies = True
                
        # Extract lecture number for proper sorting
        def extract_lecture_number(lecture_data):
            # Try to extract lecture number from transcript path first
            if lecture_data["transcript_path"]:
                match = re.search(r'lecture[_\s-]*(\d+)|lec[_\s-]*(\d+)|l(\d+)', lecture_data["transcript_path"], re.IGNORECASE)
                if match:
                    # Get the first non-None group
                    for group in match.groups():
                        if group:
                            return int(group)
            
            # Try from lecture_key if available
            if "lecture_key" in lecture_data:
                match = re.search(r'lecture[_\s-]*(\d+)|lec[_\s-]*(\d+)|(\d+)', lecture_data["lecture_key"], re.IGNORECASE)
                if match:
                    for group in match.groups():
                        if group:
                            return int(group)
            
            # Default to a high number if no lecture number found
            return 999
                
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
                    extract_lecture_number(x)
                )
            )
            
            for lecture_data in sorted_discrepancies:
                # Add row for this lecture with discrepancy
                row = {
                    "Course Name": lecture_data["full_course_name"],
                    "Transcript Name": lecture_data["transcript_path"] or "",
                    "Transcript Count": lecture_data["transcript_count"] if lecture_data["transcript_count"] >= 0 else "Error",
                    "Slide Name": lecture_data["slide_path"] or "",
                    "Slide Count": lecture_data["slide_count"] if lecture_data["slide_count"] >= 0 else "Error",
                    "Presentation Name": lecture_data["presentation_path"] or "",
                    "Presentation Count": lecture_data["presentation_count"] if lecture_data["presentation_count"] >= 0 else "Error"
                }
                
                discrepancy_data.append(row)
            
            # Convert to DataFrame and display
            if discrepancy_data:
                df = pd.DataFrame(discrepancy_data)
                
                # Sort the DataFrame by Course Name and Transcript Name in ascending order
                df = df.sort_values(by=["Course Name", "Transcript Name"])
                
                # Apply highlighting and display
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No discrepancies found.")
                
            # Button to hide discrepancies
            if st.button("Hide Discrepancies"):
                st.session_state.show_discrepancies = False
                st.rerun()
                
        # Show transcript-presentation discrepancies table if requested (ignoring slide count)
        if hasattr(st.session_state, 'show_transcript_pres_discrepancies') and st.session_state.show_transcript_pres_discrepancies:
            st.subheader("Discrepancies (Ignoring Slide Count)")
            st.write("This section shows discrepancies between transcript and presentation counts only, ignoring slide file counts.")
            
            # Create data for the discrepancies table
            discrepancy_data = []
            
            # Sort discrepancies by course number then lecture number
            sorted_discrepancies = sorted(
                results["transcript_pres_discrepancies"],
                key=lambda x: (
                    int(re.search(r'\d+', x["course_num"]).group()) if re.search(r'\d+', x["course_num"]) else 999,
                    extract_lecture_number(x)
                )
            )
            
            for lecture_data in sorted_discrepancies:
                # Add row for this lecture with discrepancy
                row = {
                    "Course Name": lecture_data["full_course_name"],
                    "Transcript Name": lecture_data["transcript_path"] or "",
                    "Transcript Count": lecture_data["transcript_count"] if lecture_data["transcript_count"] >= 0 else "Error",
                    "Presentation Name": lecture_data["presentation_path"] or "",
                    "Presentation Count": lecture_data["presentation_count"] if lecture_data["presentation_count"] >= 0 else "Error"
                }
                
                discrepancy_data.append(row)
            
            # Convert to DataFrame and display
            if discrepancy_data:
                df = pd.DataFrame(discrepancy_data)
                
                # Sort the DataFrame by Course Name and Transcript Name in ascending order
                df = df.sort_values(by=["Course Name", "Transcript Name"])
                
                # Display without highlighting as per user request
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No transcript-presentation discrepancies found.")
                
            # Button to hide discrepancies
            if st.button("Hide Transcript-Presentation Discrepancies"):
                st.session_state.show_transcript_pres_discrepancies = False
                st.rerun()
        
        # The "Count Details by Course" section has been removed per user request

if __name__ == "__main__":
    main()
