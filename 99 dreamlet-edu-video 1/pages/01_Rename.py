import streamlit as st
import os
import re
import time
import pandas as pd
from typing import Dict, List, Tuple

# Import utility functions
from utils.file_operations import (
    get_input_directory,
    get_output_directory,
    find_transcript_files,
    find_slide_files,
    find_summary_files,
    find_presentation_files,
    standardize_lecture_number,
    analyze_filename_for_renaming,
    copy_file_to_output,
    get_all_courses_from_input,
    extract_course_lecture_section
)

st.set_page_config(page_title="01 Rename - Dreamlet", page_icon="✏️")

def analyze_files_for_renaming() -> Tuple[Dict, Dict]:
    """
    Analyze all files in the input directory for renaming
    
    Returns:
        Tuple of (course_data, file_mapping)
    """
    input_dir = get_input_directory()
    
    # Get all files by type
    transcripts = find_transcript_files(input_dir)
    slides = find_slide_files(input_dir)
    summaries = find_summary_files(input_dir)
    presentations = find_presentation_files(input_dir)
    
    # Debug information (hidden)
    # st.write(f"Found transcripts: {len(transcripts)}")
    # st.write(f"Found slides: {len(slides)}")
    # st.write(f"Found summaries: {len(summaries)}")
    # st.write(f"Found presentations: {len(presentations)}")
    
    # Group data by course
    course_data = {}
    file_mapping = {}
    
    # Process all files
    all_files = []
    all_files.extend([("transcript", f) for f in transcripts])
    all_files.extend([("slide", f) for f in slides])
    all_files.extend([("summary", f) for f in summaries])
    all_files.extend([("presentation", f) for f in presentations])
    
    for file_type, file_path in all_files:
        # Extract course information
        course, lecture, _ = extract_course_lecture_section(file_path)
        
        # Get the directory path to extract full course name if possible
        dir_path = os.path.dirname(file_path)
        dir_parts = dir_path.split(os.sep)
        
        if course:
            # Search for the full directory name that contains this course number
            found_full_name = False
            for part in dir_parts:
                if re.search(rf'{course}\b', part) or re.search(rf'course\s*{course}', part.lower()):
                    course = part  # Use the full directory name
                    found_full_name = True
                    break
            
            # If no full name was found, use the standard "Course X" format
            if not found_full_name:
                course = f"Course {course}"
        else:
            course = "Uncategorized"
        
        if not lecture:
            # Try to extract lecture number from filename
            filename = os.path.basename(file_path)
            match = re.search(r'(\d+)', filename)
            lecture = match.group(1) if match else "unknown"
        
        # Standardize lecture number
        std_lecture = standardize_lecture_number(lecture)
        
        # Analyze file for renaming
        filename = os.path.basename(file_path)
        rename_info = analyze_filename_for_renaming(filename)
        
        # Create course entry if it doesn't exist
        if course not in course_data:
            course_data[course] = {}
        
        # Create lecture entry if it doesn't exist
        lecture_key = f"Lecture {std_lecture}"
        if lecture_key not in course_data[course]:
            course_data[course][lecture_key] = {
                "transcript": {"current": None, "corrected": None, "needs_renaming": False},
                "slide": {"current": None, "corrected": None, "needs_renaming": False},
                "summary": {"current": None, "corrected": None, "needs_renaming": False},
                "presentation": {"current": None, "corrected": None, "needs_renaming": False}
            }
        
        # Add file info
        course_data[course][lecture_key][file_type]["current"] = filename
        course_data[course][lecture_key][file_type]["corrected"] = rename_info["corrected"]
        course_data[course][lecture_key][file_type]["needs_renaming"] = rename_info.get("needs_renaming", filename != rename_info["corrected"])
        
        # Add to file mapping
        file_mapping[file_path] = {
            "type": file_type,
            "course": course,
            "lecture": lecture_key,
            "current": filename,
            "corrected": rename_info["corrected"],
            "needs_renaming": rename_info.get("needs_renaming", filename != rename_info["corrected"]),
            "full_path": file_path
        }
    
    return course_data, file_mapping

def rename_files(file_mapping: Dict) -> List[Dict]:
    """
    Rename files according to the mapping
    
    Args:
        file_mapping: Dictionary mapping file paths to renaming information
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for original_path, info in file_mapping.items():
        try:
            # Check if the file actually needs renaming (either from the mapping or by comparing names)
            needs_renaming = info.get("needs_renaming", True)
            if info["current"] == info["corrected"] or not needs_renaming:
                results.append({
                    "file": info["current"],
                    "status": "unchanged",
                    "message": "No renaming needed"
                })
                continue
            
            # Get the directory path and create new path with corrected filename
            original_dir = os.path.dirname(original_path)
            new_path = os.path.join(original_dir, info["corrected"])
            
            # Check if the destination file already exists to avoid conflicts
            if os.path.exists(new_path) and original_path != new_path:
                results.append({
                    "file": info["current"],
                    "status": "error",
                    "message": f"Cannot rename: Destination file {info['corrected']} already exists"
                })
                continue
            
            # Simply rename the file (move operation) instead of copying
            os.rename(original_path, new_path)
            
            results.append({
                "file": info["current"],
                "new_file": info["corrected"],
                "status": "renamed",
                "message": f"Renamed to {info['corrected']}"
            })
        except Exception as e:
            results.append({
                "file": info["current"],
                "status": "error",
                "message": f"Error: {str(e)}"
            })
    
    return results

def main():
    st.title("Rename")
    st.write("Fix incorrectly named files according to standard naming conventions.")
    
    # Display examples of renaming rules
    with st.expander("Examples of Renaming Rules"):
        st.write("""
        The following examples show how files will be renamed:
        
        **Transcript Files (to be renamed as "Lecture XX"):**
        - `lec1-transcript.md` → `Lecture 01.md`
        - `lec21-transcript.md` → `Lecture 21.md`
        - `lecture7-transcriptB.md` → `Lecture 07.md`
        - `lecture8-script.md` → `Lecture 08.md`
        - `01-b.md` → `Lecture 01.md`
        - `27-artifact-b.txt` → `Lecture 27.txt`
        
        **Slide Files (to be renamed as "XX-slides"):**
        - `01-slide.md` → `01-slides.md`
        - `27-s.txt` → `27-slides.txt`
        - `01-c.md` → `01-slides.md`
        - `27-artifact-c.txt` → `27-slides.txt`
        
        **Summary Files (to be renamed as "XX-summary"):**
        - `01-d.md` → `01-summary.md`
        - `27-artifact-d.txt` → `27-summary.txt`
        
        Files will be standardized to have a two-digit lecture number and a consistent naming format.
        """)
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Analyze files for renaming
    if st.button("Analyze Files for Renaming"):
        with st.spinner("Analyzing files..."):
            # Display progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize progress steps
            status_text.text("Finding files...")
            progress_bar.progress(0.2)
            time.sleep(0.5)
            
            status_text.text("Analyzing file names...")
            progress_bar.progress(0.5)
            
            # Analyze files
            course_data, file_mapping = analyze_files_for_renaming()
            
            status_text.text("Generating renaming table...")
            progress_bar.progress(0.8)
            time.sleep(0.5)
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("Analysis complete")
            
            # Store results in session state
            st.session_state.course_data = course_data
            st.session_state.file_mapping = file_mapping
    
    # Display results if available
    if hasattr(st.session_state, 'course_data') and hasattr(st.session_state, 'file_mapping'):
        course_data = st.session_state.course_data
        file_mapping = st.session_state.file_mapping
        
        # Summary statistics
        total_files = len(file_mapping)
        files_to_rename = sum(1 for info in file_mapping.values() if info.get("needs_renaming", False))
        
        st.header("Renaming Analysis")
        st.write(f"Total files found: {total_files}")
        st.write(f"Files requiring renaming: {files_to_rename}")
        
        # Display results by course in collapsible sections
        st.subheader("Renaming Details by Course")
        
        # Sort courses in ascending order based on course number
        def extract_course_number(course_name):
            # Extract number from course name for sorting
            match = re.search(r'(\d+)', course_name)
            if match:
                return int(match.group(1))
            else:
                return 999  # Default for items without numbers
                
        sorted_courses = sorted(course_data.keys(), key=extract_course_number)
        
        # Create accordion for course results
        for course in sorted_courses:
            with st.expander(f"{course}"):
                # Create a DataFrame for this course's files
                course_lectures = course_data[course]
                
                # Sort lectures by number
                def extract_lecture_number(lecture_name):
                    # Extract number from lecture name for sorting
                    match = re.search(r'(\d+)', lecture_name)
                    if match:
                        return int(match.group(1))
                    else:
                        return 999  # Default for items without numbers
                        
                sorted_lectures = sorted(course_lectures.keys(), key=extract_lecture_number)
                
                # Create data for the table
                table_data = []
                
                for lecture in sorted_lectures:
                    lecture_data = course_lectures[lecture]
                    
                    # Add row for this lecture
                    row = {
                        "Transcript Current": lecture_data["transcript"]["current"] or "",
                        "Transcript Corrected": lecture_data["transcript"]["corrected"] or "",
                        "Slide Current": lecture_data["slide"]["current"] or "",
                        "Slide Corrected": lecture_data["slide"]["corrected"] or "",
                        "Summary Current": lecture_data["summary"]["current"] or "",
                        "Summary Corrected": lecture_data["summary"]["corrected"] or "",
                        "Presentation Current": lecture_data["presentation"]["current"] or "",
                        "Presentation Corrected": lecture_data["presentation"]["corrected"] or ""
                    }
                    
                    table_data.append(row)
                
                # Convert to DataFrame and display
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.table(df)
                else:
                    st.write("No files found for this course.")
        
        # Option to apply renaming
        st.header("Apply Renaming")
        st.write("Click the button below to apply the proposed renaming to files.")
        
        if st.button("Rename Files", disabled=files_to_rename == 0):
            with st.spinner("Renaming files..."):
                # Display progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process renaming
                status_text.text("Renaming files...")
                
                # Rename files and get results
                rename_results = rename_files(file_mapping)
                
                # Complete
                progress_bar.progress(1.0)
                status_text.text("Renaming complete")
                
                # Display results
                renamed_count = sum(1 for r in rename_results if r["status"] == "renamed")
                unchanged_count = sum(1 for r in rename_results if r["status"] == "unchanged")
                error_count = sum(1 for r in rename_results if r["status"] == "error")
                
                st.subheader("Renaming Results")
                st.write(f"✅ Successfully renamed: {renamed_count}")
                st.write(f"⏭️ Unchanged: {unchanged_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Detailed results in an expander (errors only)
                if error_count > 0:
                    with st.expander("Detailed Error Results"):
                        for result in rename_results:
                            if result["status"] == "error":
                                st.write(f"❌ {result['file']}: {result['message']}")
                else:
                    st.success("No errors occurred during renaming.")

if __name__ == "__main__":
    main()
