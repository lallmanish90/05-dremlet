import streamlit as st
import os
import re
from pathlib import Path
import time
from typing import List, Dict

# Import utility functions
from utils.file_operations import (
    get_input_directory, 
    get_output_directory,
    find_transcript_files,
    find_slide_files,
    find_non_supported_files,
    map_input_to_output_path,
    ensure_directory_exists,
    extract_course_lecture_section
)
from utils.text_processing import (
    extract_slide_blocks,
    extract_content_outside_slides,
    adjust_transcript_structure,
    standardize_slide_markers,
    remove_headers
)

st.set_page_config(page_title="04 Remove unwanted - Dreamlet", page_icon="🗑️")

def process_transcript_file(file_path: str) -> Dict:
    """
    Process a transcript file to adjust its structure
    
    Args:
        file_path: Path to the transcript file
        
    Returns:
        Dictionary with processing results
    """
    result = {
        "file_path": file_path, 
        "status": "skipped", 
        "message": "",
        "has_slide_markers": False,
        "slide_count": 0,
        "discrepancy": False,
        "discrepancy_type": None,
        "timestamp": time.time(),
        "slide_marker_modifications": [],
        "timestamp_markers_removed": 0,
        "headers_removed": 0
    }
    
    try:
        # Read the transcript file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if this is actually a slide file (not a transcript file)
        filename = os.path.basename(file_path).lower()
        is_slide_file = "slide" in filename or "-s." in filename
        
        if is_slide_file:
            # For slide files, we'll still process for header removal, but skip slide marker checks
            
            # Remove all header formatting from the slide content
            content_without_headers, headers_removed_count = remove_headers(content)
            result["headers_removed"] = headers_removed_count
            
            # Save the adjusted slide file to the output directory
            output_path = map_input_to_output_path(file_path)
            ensure_directory_exists(os.path.dirname(output_path))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content_without_headers)
            
            message = f"Processed slide file, removed {headers_removed_count} headers"
            result["status"] = "processed"
            result["message"] = message
            
            return result
        
        # For transcript files, continue with standard processing
        
        # First standardize the slide markers (remove timestamps)
        standardized_content, modifications = standardize_slide_markers(content)
        result["slide_marker_modifications"] = modifications
        result["timestamp_markers_removed"] = len(modifications)
        
        # Now check for slide markers in the standardized content
        slide_blocks = extract_slide_blocks(standardized_content)
        
        if not slide_blocks:
            result["status"] = "discrepancy"
            result["message"] = "No slide markers found, marking as discrepancy"
            result["discrepancy"] = True
            result["discrepancy_type"] = "Missing slide markers"
            return result
        
        result["has_slide_markers"] = True
        result["slide_count"] = len(slide_blocks)
        
        # Extract content outside slide markers
        pre_content, post_content, _ = extract_content_outside_slides(standardized_content)
        
        # Adjust the transcript structure
        adjusted_content = adjust_transcript_structure(standardized_content)
        
        # Remove all header formatting from the content
        content_without_headers, headers_removed_count = remove_headers(adjusted_content)
        result["headers_removed"] = headers_removed_count
        
        # Save the adjusted transcript to the output directory
        output_path = map_input_to_output_path(file_path)
        ensure_directory_exists(os.path.dirname(output_path))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content_without_headers)
        
        message = f"Processed {len(slide_blocks)} slides"
        if result["timestamp_markers_removed"] > 0:
            message += f", removed timestamps from {result['timestamp_markers_removed']} slide markers"
        if headers_removed_count > 0:
            message += f", removed {headers_removed_count} headers"
        
        result["status"] = "processed"
        result["message"] = message
        result["pre_content_size"] = len(pre_content)
        result["post_content_size"] = len(post_content)
        
        return result
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Error: {str(e)}"
        return result

def extract_lecture_number(file_path):
    """
    Extract lecture number from a file path
    
    Args:
        file_path: Path to extract lecture number from
        
    Returns:
        Integer lecture number or 999 if not found
    """
    match = re.search(r'lecture[_\s-]*(\d+)|lec[_\s-]*(\d+)|l(\d+)', file_path, re.IGNORECASE)
    if match:
        # Get the first non-None group
        for group in match.groups():
            if group:
                return int(group)
    
    # Default to a high number if no lecture number found
    return 999

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

def process_all_files(all_transcripts: List[str]) -> Dict:
    """
    Process all transcript files and track results
    
    Args:
        all_transcripts: List of transcript file paths
        
    Returns:
        Dictionary with processing results
    """
    # Group files by course for organizing the results
    files_by_course = {}
    discrepancies = []
    timestamp_markers_standardized = []
    
    # Process files with progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    
    results = []
    for i, file_path in enumerate(all_transcripts):
        # Update progress
        progress = (i + 1) / len(all_transcripts)
        progress_bar.progress(progress)
        
        # Update status message
        file_name = os.path.basename(file_path)
        status_container.info(f"Processing {i+1}/{len(all_transcripts)}: {file_name}")
        
        # Process the file
        result = process_transcript_file(file_path)
        
        # Extract course information
        course, lecture, _ = extract_course_lecture_section(file_path)
        course_num = course if course else "999"
        
        # Get full course name
        full_course_name = get_full_course_name(file_path)
        
        # Add to course data
        if course_num not in files_by_course:
            files_by_course[course_num] = []
        
        # Create file data with course information
        file_data = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "course_num": course_num,
            "full_course_name": full_course_name,
            "lecture": lecture,
            "status": result["status"],
            "message": result["message"],
            "has_slide_markers": result["has_slide_markers"],
            "slide_count": result["slide_count"],
            "timestamp": result["timestamp"],
            "timestamp_markers_removed": result.get("timestamp_markers_removed", 0),
            "headers_removed": result.get("headers_removed", 0)
        }
        
        # Track timestamp marker standardization
        if result.get("timestamp_markers_removed", 0) > 0:
            file_data["slide_marker_modifications"] = result.get("slide_marker_modifications", [])
            timestamp_markers_standardized.append(file_data)
        
        if result["status"] == "processed":
            file_data["pre_content_size"] = result.get("pre_content_size", 0)
            file_data["post_content_size"] = result.get("post_content_size", 0)
        
        if result["status"] == "discrepancy":
            file_data["discrepancy_type"] = result["discrepancy_type"]
            discrepancies.append(file_data)
        
        # Add to course data
        files_by_course[course_num].append(file_data)
        results.append(result)
        
        # Add a small delay to make the progress visible
        time.sleep(0.1)
    
    # Clear status message
    status_container.success(f"Processed {len(all_transcripts)} files")
    
    # Calculate statistics
    processed_count = sum(1 for r in results if r["status"] == "processed")
    discrepancy_count = sum(1 for r in results if r["status"] == "discrepancy")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    error_count = sum(1 for r in results if r["status"] == "error")
    timestamp_markers_count = sum(r.get("timestamp_markers_removed", 0) for r in results)
    headers_removed_count = sum(r.get("headers_removed", 0) for r in results)
    
    return {
        "course_data": files_by_course,
        "total_processed": len(all_transcripts),
        "processed_count": processed_count,
        "discrepancy_count": discrepancy_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "timestamp_markers_count": timestamp_markers_count,
        "headers_removed_count": headers_removed_count,
        "discrepancies": discrepancies,
        "timestamp_markers_standardized": timestamp_markers_standardized,
        "results": results
    }

def main():
    st.title("Remove unwanted")
    st.write("Delete non-supported files from the input directory.")
    
    input_dir = get_input_directory()
    output_dir = get_output_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find all transcript and slide files
    st.header("Available Files")
    all_transcripts = find_transcript_files(input_dir)
    all_slides = find_slide_files(input_dir)
    
    # Combine both lists
    all_files = all_transcripts + all_slides
    
    if not all_files:
        st.warning("No transcript or slide files found in the input directory.")
        return
    
    st.success(f"Found {len(all_transcripts)} transcript files and {len(all_slides)} slide files in the input directory.")
    
    # Find non-supported files
    non_supported_files = find_non_supported_files(input_dir)
    
    if non_supported_files:
        st.warning(f"Found {len(non_supported_files)} non-supported files in the input directory.")
        
        # Display non-supported files in a table
        with st.expander("View Non-Supported Files"):
            # Create data for the table
            table_data = []
            for file_path in non_supported_files:
                file_name = os.path.basename(file_path)
                dir_name = os.path.dirname(file_path)
                table_data.append({
                    "File Name": file_name,
                    "Directory": dir_name,
                    "Full Path": file_path
                })
            
            # Convert to DataFrame and display
            if table_data:
                import pandas as pd
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Add a button to delete all non-supported files
                if st.button("Delete All Non-Supported Files"):
                    deleted_count = 0
                    
                    # Show progress bar for deletion
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, file_path in enumerate(non_supported_files):
                        try:
                            # Update progress
                            progress = (i + 1) / len(non_supported_files)
                            progress_bar.progress(progress)
                            status_text.text(f"Deleting {i+1}/{len(non_supported_files)}: {os.path.basename(file_path)}")
                            
                            # Delete the file
                            os.remove(file_path)
                            deleted_count += 1
                        except Exception as e:
                            st.error(f"Error deleting {file_path}: {str(e)}")
                    
                    # Complete
                    progress_bar.progress(1.0)
                    status_text.text(f"Deleted {deleted_count} files")
                    
                    # Rerun the app to refresh the file list
                    st.rerun()
    
    # Group files by course for display purposes only
    files_by_course = {}
    for file_path in all_files:  # Use all_files instead of just all_transcripts
        # Extract course information
        course, _, _ = extract_course_lecture_section(file_path)
        course_name = f"Course {course}" if course else "Uncategorized"
        
        if course_name not in files_by_course:
            files_by_course[course_name] = []
        files_by_course[course_name].append(file_path)
    
    # Sort courses numerically
    sorted_courses = sorted(
        files_by_course.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    # Display file count by course
    for course_name in sorted_courses:
        file_paths = files_by_course[course_name]
        st.write(f"**{course_name}:** {len(file_paths)} files")
    
    # Display results if available
    if hasattr(st.session_state, 'adjust_results'):
        results = st.session_state.adjust_results
        course_data = results["course_data"]
        
        # Summary dashboard
        st.header("Status Dashboard")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Total Files Processed", results["total_processed"])
        
        with col2:
            st.metric("Successfully Processed", results["processed_count"])
            
        with col3:
            # Make this a clickable button that will show discrepancies
            if results["discrepancy_count"] > 0:
                if st.button(f"Discrepancies Found: {results['discrepancy_count']}", key="discrepancies_button"):
                    st.session_state.show_discrepancies = True
            else:
                st.metric("Discrepancies Found", 0)
        
        with col4:
            # Add a metric or button for timestamp markers standardized
            if results.get("timestamp_markers_count", 0) > 0:
                if st.button(f"Markers Standardized: {results['timestamp_markers_count']}", key="markers_button"):
                    st.session_state.show_standardized_markers = True
            else:
                st.metric("Markers Standardized", 0)
                
        with col5:
            # Add a metric for headers removed
            if results.get("headers_removed_count", 0) > 0:
                st.metric("Headers Removed", results["headers_removed_count"])
            else:
                st.metric("Headers Removed", 0)
        
        with col6:
            st.metric("Errors", results["error_count"])
        
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
                    extract_lecture_number(x["file_path"])
                )
            )
            
            for file_data in sorted_discrepancies:
                # Add row for this file with discrepancy
                row = {
                    "Course Name": file_data["full_course_name"],
                    "Lecture": file_data.get("lecture", "Unknown"),
                    "Transcript Name": file_data["file_name"],
                    "Discrepancy Type": file_data["discrepancy_type"]
                }
                
                discrepancy_data.append(row)
            
            # Convert to DataFrame and display
            if discrepancy_data:
                import pandas as pd
                df = pd.DataFrame(discrepancy_data)
                
                # Sort by Course Name and Transcript Name
                df = df.sort_values(by=["Course Name", "Lecture", "Transcript Name"])
                
                # Display table
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No discrepancies found.")
                
            # Button to hide discrepancies
            if st.button("Hide Discrepancies"):
                st.session_state.show_discrepancies = False
                st.rerun()
                
        # Show standardized markers table if requested
        if hasattr(st.session_state, 'show_standardized_markers') and st.session_state.show_standardized_markers:
            st.subheader("Standardized Slide Markers")
            
            # Create data for the standardized markers table
            markers_data = []
            
            # Sort by course number then lecture number
            sorted_markers = sorted(
                results["timestamp_markers_standardized"],
                key=lambda x: (
                    int(re.search(r'\d+', x["course_num"]).group()) if re.search(r'\d+', x["course_num"]) else 999,
                    extract_lecture_number(x["file_path"])
                )
            )
            
            for file_data in sorted_markers:
                # For each file with standardized markers
                filename = file_data["file_name"]
                course_name = file_data["full_course_name"]
                lecture = file_data.get("lecture", "Unknown")
                
                # Add a row for each marker that was standardized
                for mod in file_data.get("slide_marker_modifications", []):
                    row = {
                        "Course Name": course_name,
                        "Lecture": lecture,
                        "Transcript Name": filename,
                        "Slide Number": mod.get("slide", ""),
                        "Original Marker": mod.get("original", ""),
                        "Standardized Marker": mod.get("new", "")
                    }
                    markers_data.append(row)
            
            # Convert to DataFrame and display
            if markers_data:
                import pandas as pd
                df = pd.DataFrame(markers_data)
                
                # Sort by Course Name, Lecture, and Transcript Name
                df = df.sort_values(by=["Course Name", "Lecture", "Transcript Name", "Slide Number"])
                
                # Display table
                st.dataframe(df, use_container_width=True)
            else:
                st.write("No slide markers were standardized.")
                
            # Button to hide standardized markers
            if st.button("Hide Standardized Markers"):
                st.session_state.show_standardized_markers = False
                st.rerun()
        
        # Display results by course in collapsible sections
        st.subheader("Adjustment Details by Course")
        
        # Sort courses in ascending order
        sorted_courses = sorted(
            course_data.keys(),
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
        )
        
        # Create a mapping of course names to their IDs
        course_options = {}
        for course in sorted_courses:
            if course_data[course]:
                full_name = course_data[course][0]["full_course_name"]
                course_options[full_name] = course
        
        if course_options:
            # First check if we need to use a searchable dropdown (more than 10 courses)
            if len(course_options) > 10:
                # Use selectbox with search capability for many courses
                selected_course = st.selectbox(
                    "Select a course to view:",
                    options=list(course_options.keys()),
                    key="course_selector"
                )
            else:
                # For fewer courses, we'll use a cleaner radio button interface
                col1, col2 = st.columns([1, 3])  # Adjust column widths for better layout
                with col1:
                    selected_course = st.radio(
                        "Select a course:",
                        options=list(course_options.keys()),
                        key="course_selector"
                    )
            
            # Get the course ID from our mapping
            selected_course_id = course_options.get(selected_course)
            
            # Create expander for the selected course
            if selected_course_id:
                with st.expander(selected_course, expanded=True):
                    # Sort files by lecture number
                    sorted_files = sorted(
                        course_data[selected_course_id],
                        key=lambda x: extract_lecture_number(x["file_path"])
                    )
                    
                    # Create data for the table
                    table_data = []
                    
                    for file_data in sorted_files:
                        # Add row for this file
                        row = {
                            "Transcript Name": file_data["file_name"],
                            "Status": file_data["status"].capitalize(),
                            "Slide Count": file_data["slide_count"] if file_data["has_slide_markers"] else "N/A",
                            "Markers Standardized": file_data.get("timestamp_markers_removed", 0),
                            "Headers Removed": file_data.get("headers_removed", 0)
                        }
                        
                        # If it has a discrepancy, add the type
                        if file_data["status"] == "discrepancy":
                            row["Discrepancy"] = file_data["discrepancy_type"]
                        else:
                            row["Discrepancy"] = ""
                        
                        table_data.append(row)
                    
                    # Convert to DataFrame and display
                    if table_data:
                        import pandas as pd
                        df = pd.DataFrame(table_data)
                        
                        # Sort the DataFrame by Transcript Name in ascending order
                        df = df.sort_values(by=["Transcript Name"])
                        
                        # Display table with full width
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write("No files found for this course.")

if __name__ == "__main__":
    main()
