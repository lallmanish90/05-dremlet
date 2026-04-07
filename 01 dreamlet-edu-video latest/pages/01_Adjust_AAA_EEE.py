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
import glob
import time
import shutil
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Set page configuration
st.set_page_config(page_title="01 Adjust AAA EEE - Dreamlet", page_icon="📄")

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_processed_directory(course_path: str = None) -> str:
    """
    Get the path to the processed AAA/EEE directory.
    If course_path is provided, returns processed folder inside that course.
    Otherwise, returns the top-level all_ (for finding existing files).
    """
    if course_path:
        return os.path.join(course_path, "all_")
    return os.path.join(get_input_directory(), "all_")

def extract_lecture_number(filename: str) -> Optional[str]:
    """Extract lecture number from filename (e.g., '01-AAA.md' -> '01')"""
    match = re.match(r'^(\d+)-(?:AAA|EEE)\.(md|txt)$', filename)
    return match.group(1) if match else None

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    match = re.match(r'^(\d+)-(?:AAA|EEE)\.(md|txt)$', filename)
    return match.group(2) if match else 'md'

def find_aaa_eee_files(directory: str) -> Tuple[List[str], List[str]]:
    """Find all AAA and EEE files in the directory structure"""
    aaa_files = []
    eee_files = []
    
    for root, _, files in os.walk(directory):
        # Skip processed directory
        if "all_" in root:
            continue
            
        for file in files:
            if re.match(r'^\d+-AAA\.(md|txt)$', file):
                aaa_files.append(os.path.join(root, file))
            elif re.match(r'^\d+-EEE\.(md|txt)$', file):
                eee_files.append(os.path.join(root, file))
    
    return sorted(aaa_files), sorted(eee_files)

def find_processed_files() -> Tuple[List[str], List[str]]:
    """Find all processed AAA and EEE files"""
    processed_dir = get_processed_directory()
    if not os.path.exists(processed_dir):
        return [], []
    
    aaa_files = []
    eee_files = []
    
    for root, _, files in os.walk(processed_dir):
        for file in files:
            if re.match(r'^\d+-AAA\.(md|txt)$', file):
                aaa_files.append(os.path.join(root, file))
            elif re.match(r'^\d+-EEE\.(md|txt)$', file):
                eee_files.append(os.path.join(root, file))
    
    return sorted(aaa_files), sorted(eee_files)

def analyze_file_discrepancies(aaa_files: List[str], eee_files: List[str]) -> Dict:
    """Analyze discrepancies between AAA and EEE files"""
    discrepancies = {
        'missing_pairs': [],
        'sequence_gaps': [],
        'orphaned_files': []
    }
    
    # Group files by course and lecture number
    aaa_by_course = {}
    eee_by_course = {}
    
    for file_path in aaa_files:
        course_dir = os.path.basename(os.path.dirname(file_path))
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if lecture_num:
            if course_dir not in aaa_by_course:
                aaa_by_course[course_dir] = {}
            aaa_by_course[course_dir][lecture_num] = file_path
    
    for file_path in eee_files:
        course_dir = os.path.basename(os.path.dirname(file_path))
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if lecture_num:
            if course_dir not in eee_by_course:
                eee_by_course[course_dir] = {}
            eee_by_course[course_dir][lecture_num] = file_path
    
    # Check for missing pairs and sequence gaps
    all_courses = set(aaa_by_course.keys()) | set(eee_by_course.keys())
    
    for course in all_courses:
        aaa_lectures = set(aaa_by_course.get(course, {}).keys())
        eee_lectures = set(eee_by_course.get(course, {}).keys())
        
        # Find missing pairs
        aaa_only = aaa_lectures - eee_lectures
        eee_only = eee_lectures - aaa_lectures
        
        for lecture_num in aaa_only:
            discrepancies['missing_pairs'].append({
                'course': course,
                'lecture': lecture_num,
                'missing': 'EEE',
                'available': 'AAA'
            })
        
        for lecture_num in eee_only:
            discrepancies['missing_pairs'].append({
                'course': course,
                'lecture': lecture_num,
                'missing': 'AAA',
                'available': 'EEE'
            })
        
        # Check for sequence gaps (missing numbers in sequence)
        all_lectures = aaa_lectures | eee_lectures
        if all_lectures:
            lecture_numbers = sorted([int(num) for num in all_lectures])
            min_num, max_num = min(lecture_numbers), max(lecture_numbers)
            
            expected_range = set(range(min_num, max_num + 1))
            actual_numbers = set(lecture_numbers)
            missing_numbers = expected_range - actual_numbers
            
            for missing_num in missing_numbers:
                discrepancies['sequence_gaps'].append({
                    'course': course,
                    'missing_lecture': f"{missing_num:02d}",
                    'range': f"{min_num:02d}-{max_num:02d}"
                })
    
    return discrepancies

def validate_end_markers(file_path: str, file_type: str) -> Tuple[bool, str]:
    """Validate that the file has the correct end marker or add one if missing"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract lecture number from filename
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if not lecture_num:
            return False, "Could not extract lecture number from filename"
        
        # Check for multiple possible end marker patterns
        possible_markers = [
            f"===END OF LECTURE {lecture_num}-{file_type} GENERATION===",
            f"===END OF LECTURE [{lecture_num}]-{file_type} GENERATION===",
            f"===END OF LECTURE {lecture_num} {file_type} GENERATION===",
            f"===END OF LECTURE [{lecture_num}] {file_type} GENERATION==="
        ]
        
        # Check if any valid end marker exists
        for marker in possible_markers:
            if marker in content:
                return True, f"Valid end marker found: {marker}"
        
        # If no end marker found, add one automatically based on content structure
        # Look for patterns that indicate the file should end (like glossary section)
        if file_type == "AAA":
            # Look for slide end pattern or glossary pattern before adding marker
            if "[SUMMARY TRANSCRIPT]" in content or "Slide" in content:
                # Add the standard end marker
                standard_marker = f"===END OF LECTURE {lecture_num}-{file_type} GENERATION==="
                updated_content = content.rstrip() + "\n\n" + standard_marker
                
                # Write the updated content back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                return True, f"Added missing end marker: {standard_marker}"
        
        elif file_type == "EEE":
            # Look for glossary section or other EEE patterns
            if "[GLOSSARY]" in content or "[COMPREHENSIVE NOTES]" in content:
                # Add the standard end marker
                standard_marker = f"===END OF LECTURE {lecture_num}-{file_type} GENERATION==="
                updated_content = content.rstrip() + "\n\n" + standard_marker
                
                # Write the updated content back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                return True, f"Added missing end marker: {standard_marker}"
        
        # If we can't determine the structure, still allow processing
        return True, f"No end marker found, but allowing processing to continue"
            
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def extract_content_sections(content: str, section_markers: List[str]) -> Dict[str, str]:
    """Extract content between section markers"""
    sections = {}
    
    for i, marker in enumerate(section_markers):
        # Find the start of this section
        start_pattern = f"\\[{re.escape(marker)}\\]"
        start_match = re.search(start_pattern, content)
        
        if not start_match:
            sections[marker] = ""
            continue
        
        start_pos = start_match.end()
        
        # Find the start of the next section or end marker
        if i + 1 < len(section_markers):
            next_pattern = f"\\[{re.escape(section_markers[i + 1])}\\]"
            next_match = re.search(next_pattern, content[start_pos:])
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                # Look for end marker
                end_match = re.search(r"===END OF LECTURE.*?===", content[start_pos:])
                end_pos = start_pos + end_match.start() if end_match else len(content)
        else:
            # This is the last section, find end marker
            end_match = re.search(r"===END OF LECTURE.*?===", content[start_pos:])
            end_pos = start_pos + end_match.start() if end_match else len(content)
        
        # Extract and clean the content
        section_content = content[start_pos:end_pos].strip()
        sections[marker] = section_content
    
    return sections

def split_aaa_file(file_path: str) -> Dict[str, str]:
    """Split AAA file into component sections"""
    aaa_markers = [
        "VIDEO TRANSCRIPT OUTLINE",
        "VIDEO TRANSCRIPT", 
        "SLIDE CONTENT",
        "SUMMARY TRANSCRIPT"
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = extract_content_sections(content, aaa_markers)
        
        # Map to output files - always return something, even if empty
        result = {
            'a': sections.get("VIDEO TRANSCRIPT OUTLINE", ""),
            'b': sections.get("VIDEO TRANSCRIPT", ""),
            'c': sections.get("SLIDE CONTENT", ""),
            'd': sections.get("SUMMARY TRANSCRIPT", "")
        }
        
        return result
        
    except Exception as e:
        st.error(f"Error processing AAA file {file_path}: {str(e)}")
        # Return empty sections instead of empty dict to ensure processing continues
        return {'a': '', 'b': '', 'c': '', 'd': ''}

def split_eee_file(file_path: str) -> Dict[str, str]:
    """Split EEE file into component sections"""
    eee_markers = [
        "COMPREHENSIVE NOTES",
        "LINKEDIN POST",
        "SOCRATIC DIALOGUE", 
        "TWEET",
        "FLASHCARDS",
        "GLOSSARY"
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = extract_content_sections(content, eee_markers)
        
        # Map to output files - always return something, even if empty
        result = {
            'e': sections.get("COMPREHENSIVE NOTES", ""),
            'f': sections.get("LINKEDIN POST", ""),
            'g': sections.get("SOCRATIC DIALOGUE", ""),
            'h': sections.get("TWEET", ""),
            'i': sections.get("FLASHCARDS", ""),
            'j': sections.get("GLOSSARY", "")
        }
        
        return result
        
    except Exception as e:
        st.error(f"Error processing EEE file {file_path}: {str(e)}")
        # Return empty sections instead of empty dict to ensure processing continues
        return {'e': '', 'f': '', 'g': '', 'h': '', 'i': '', 'j': ''}

def save_split_files(base_file_path: str, sections: Dict[str, str], lecture_num: str) -> List[Dict]:
    """Save the split sections to individual files in organized folder structure"""
    results = []
    base_dir = os.path.dirname(base_file_path)
    
    # Create the "all_" directory structure
    all_dir = os.path.join(base_dir, "all_")
    ensure_directory_exists(all_dir)
    
    # Get the original file extension
    original_filename = os.path.basename(base_file_path)
    file_extension = get_file_extension(original_filename)
    
    # Clean up any old files at the root level (from previous runs)
    for suffix in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']:
        old_file = os.path.join(base_dir, f"{lecture_num}-{suffix}.{file_extension}")
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
            except Exception as e:
                pass  # Silently ignore if we can't delete
    
    for suffix, content in sections.items():
        # Create subdirectory for each suffix (a, b, c, d, e, f, g, h, i, j)
        suffix_dir = os.path.join(all_dir, suffix)
        ensure_directory_exists(suffix_dir)
        
        output_filename = f"{lecture_num}-{suffix}.{file_extension}"
        output_path = os.path.join(suffix_dir, output_filename)
        
        # Create files even with minimal content to ensure splitting works
        if content and len(content.strip()) > 0:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                results.append({
                    'status': 'success',
                    'file': output_filename,
                    'path': output_path,
                    'size': len(content)
                })
                
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file': output_filename,
                    'error': str(e)
                })
        else:
            # Still log that we attempted to process this section
            results.append({
                'status': 'skipped',
                'file': output_filename,
                'reason': f'No content found for section [{suffix.upper()}]'
            })
    
    return results

def move_file_to_processed(file_path: str) -> bool:
    """
    Move a file to the processed directory within its respective course folder.
    E.g., input/CourseName/Lecture01/01-AAA.md -> input/CourseName/Lecture01/all_/aaa eee/01-AAA.md
    """
    try:
        input_dir = get_input_directory()
        
        # Determine the target processed directory based on the file's course path
        # The file_path is already within its course/lecture structure
        current_dir = os.path.dirname(file_path)
        processed_lecture_dir = get_processed_directory(current_dir) # Use the current lecture directory as the course_path for processed folder
        
        # Create "aaa eee" subdirectory inside "all_"
        aaa_eee_dir = os.path.join(processed_lecture_dir, "aaa eee")
        ensure_directory_exists(aaa_eee_dir)
        
        # Construct the destination path
        dest_path = os.path.join(aaa_eee_dir, os.path.basename(file_path))
        
        # Move the file
        shutil.move(file_path, dest_path)
        return True
        
    except Exception as e:
        st.error(f"Error moving file {file_path}: {str(e)}")
        return False

def restore_file_from_processed(processed_file_path: str) -> bool:
    """Restore a file from processed directory back to input"""
    try:
        input_dir = get_input_directory()
        processed_dir = get_processed_directory()
        
        # Get relative path from processed directory
        rel_path = os.path.relpath(processed_file_path, processed_dir)
        
        # Create destination path in input
        dest_path = os.path.join(input_dir, rel_path)
        dest_dir = os.path.dirname(dest_path)
        
        # Ensure destination directory exists
        ensure_directory_exists(dest_dir)
        
        # Move the file back
        shutil.move(processed_file_path, dest_path)
        return True
        
    except Exception as e:
        st.error(f"Error restoring file {processed_file_path}: {str(e)}")
        return False

def create_artifact_c_structure(input_directory: str, results: Dict, create_folder: bool) -> Optional[Dict]:
    """
    Create artifact-c folder structure with all XX-c files organized by course
    Only creates the folder and copies files if create_folder is True.
    """
    if not create_folder:
        return None  # Skip creation if checkbox is unchecked

    artifact_results = {
        'created_folders': [],
        'copied_files': [],
        'errors': []
    }
    
    # Get the parent directory of input (project root)
    parent_dir = os.path.dirname(input_directory)
    artifact_dir = os.path.join(parent_dir, "artifact-c")
    
    try:
        # Create main artifact-c directory
        ensure_directory_exists(artifact_dir)
        artifact_results['created_folders'].append("artifact-c")
        
        # Process AAA results to find all XX-c files
        for aaa_result in results.get('aaa_results', []):
            # Get course name from the source file path
            source_path = None
            for split in aaa_result['splits']:
                if split['status'] == 'success' and (split['file'].endswith('-c.md') or split['file'].endswith('-c.txt')):
                    source_path = split['path']
                    break
            
            if source_path:
                # Extract course name from the directory structure
                # This needs to be relative to input_directory to get the course folder
                relative_path_from_input = os.path.relpath(source_path, input_directory)
                
                # The course directory is the first component of the relative path
                course_dir = relative_path_from_input.split(os.sep)[0]
                
                # Create course folder in artifact-c
                course_artifact_dir = os.path.join(artifact_dir, course_dir)
                ensure_directory_exists(course_artifact_dir)
                
                if course_dir not in artifact_results['created_folders']:
                    artifact_results['created_folders'].append(course_dir)
                
                # Copy the XX-c file to artifact-c structure
                filename = os.path.basename(source_path)
                destination_path = os.path.join(course_artifact_dir, filename)
                
                try:
                    # Read content from source and write to destination
                    with open(source_path, 'r', encoding='utf-8') as source_file:
                        content = source_file.read()
                    
                    with open(destination_path, 'w', encoding='utf-8') as dest_file:
                        dest_file.write(content)
                    
                    artifact_results['copied_files'].append({
                        'course': course_dir,
                        'filename': filename,
                        'source': source_path,
                        'destination': destination_path
                    })
                    
                except Exception as e:
                    artifact_results['errors'].append(f"Error copying {filename}: {str(e)}")
        
    except Exception as e:
        artifact_results['errors'].append(f"Error creating artifact-c structure: {str(e)}")
    
    return artifact_results

def process_files(aaa_files: List[str], eee_files: List[str], create_artifact_c: bool) -> Dict:
    """Process all AAA and EEE files"""
    results = {
        'aaa_results': [],
        'eee_results': [],
        'validation_errors': [],
        'discrepancies': analyze_file_discrepancies(aaa_files, eee_files),
        'total_processed': 0,
        'total_created': 0,
        'moved_files': [],
        'move_errors': [],
        'artifact_c_results': None
    }
    
    # Process AAA files
    for file_path in aaa_files:
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if not lecture_num:
            results['validation_errors'].append(f"Could not extract lecture number from {filename}")
            continue
        
        # Validate end marker (but don't skip processing if validation fails)
        is_valid, validation_msg = validate_end_markers(file_path, "AAA")
        if not is_valid:
            results['validation_errors'].append(f"{filename}: {validation_msg}")
            # Continue processing anyway - don't skip the file
        
        # Split the file - always attempt processing
        sections = split_aaa_file(file_path)
        split_results = save_split_files(file_path, sections, lecture_num)
        results['aaa_results'].append({
            'source_file': filename,
            'lecture_num': lecture_num,
            'splits': split_results,
            'original_path': file_path
        })
        results['total_processed'] += 1
        results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
        
        # Move original file to processed directory if splitting was successful
        if any(r['status'] == 'success' for r in split_results):
            if move_file_to_processed(file_path):
                results['moved_files'].append(filename)
            else:
                results['move_errors'].append(f"Failed to move {filename}")
    
    # Process EEE files
    for file_path in eee_files:
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if not lecture_num:
            results['validation_errors'].append(f"Could not extract lecture number from {filename}")
            continue
        
        # Validate end marker (but don't skip processing if validation fails)
        is_valid, validation_msg = validate_end_markers(file_path, "EEE")
        if not is_valid:
            results['validation_errors'].append(f"{filename}: {validation_msg}")
            # Continue processing anyway - don't skip the file
        
        # Split the file - always attempt processing
        sections = split_eee_file(file_path)
        split_results = save_split_files(file_path, sections, lecture_num)
        results['eee_results'].append({
            'source_file': filename,
            'lecture_num': lecture_num,
            'splits': split_results,
            'original_path': file_path
        })
        results['total_processed'] += 1
        results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
        
        # Move original file to processed directory if splitting was successful
        if any(r['status'] == 'success' for r in split_results):
            if move_file_to_processed(file_path):
                results['moved_files'].append(filename)
            else:
                results['move_errors'].append(f"Failed to move {filename}")
    
    # Create artifact-c structure after processing is complete, if enabled
    if results['aaa_results'] and create_artifact_c:  # Only if we have AAA files with XX-c content and checkbox is checked
        input_dir = get_input_directory()
        artifact_results = create_artifact_c_structure(input_dir, results, create_artifact_c)
        results['artifact_c_results'] = artifact_results
    
    return results

def display_compact_results(results: Dict):
    """Display processing results in a compact, user-friendly format"""
    
    # Calculate totals
    total_aaa_files = len(results.get('aaa_results', []))
    total_eee_files = len(results.get('eee_results', []))
    total_files_processed = total_aaa_files + total_eee_files
    total_moved = len(results.get('moved_files', []))
    validation_errors = len(results.get('validation_errors', []))
    
    # Main success message
    if total_files_processed > 0:
        st.success(f"✅ Processing complete! Processed {total_files_processed} files ({total_aaa_files} AAA + {total_eee_files} EEE) and created {results['total_created']} split files.")
        
        if total_moved > 0:
            st.info(f"📁 Moved {total_moved} original files to processed folder to prevent re-processing.")
    
    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Files Processed", total_files_processed)
    with col2:
        st.metric("Split Files Created", results.get('total_created', 0))
    with col3:
        st.metric("Files Moved", total_moved)
    with col4:
        st.metric("Validation Issues", validation_errors)
    
    # Show discrepancies in compact format
    discrepancies = results.get('discrepancies', {})
    missing_pairs = discrepancies.get('missing_pairs', [])
    sequence_gaps = discrepancies.get('sequence_gaps', [])
    
    if missing_pairs or sequence_gaps:
        with st.expander("⚠️ File Discrepancies Detected (Click to expand)"):
            if missing_pairs:
                st.error("Missing AAA/EEE Pairs:")
                discrepancy_data = []
                for issue in missing_pairs:
                    discrepancy_data.append({
                        "Course": issue['course'],
                        "Lecture": issue['lecture'],
                        "Issue": f"Missing {issue['missing']} (has {issue['available']})"
                    })
                if discrepancy_data:
                    df = pd.DataFrame(discrepancy_data)
                    st.dataframe(df, use_container_width=True)
            
            if sequence_gaps:
                st.info("Sequence Gaps (informational only):")
                gap_data = []
                for gap in sequence_gaps:
                    gap_data.append({
                        "Course": gap['course'],
                        "Missing Lecture": gap['missing_lecture'],
                        "Range": gap['range']
                    })
                if gap_data:
                    df = pd.DataFrame(gap_data)
                    st.dataframe(df, use_container_width=True)
    
    # Show validation errors if any
    if validation_errors > 0:
        with st.expander("⚠️ Validation Issues (Click to expand)"):
            for error in results['validation_errors']:
                st.write(f"• {error}")
    
    # Show move errors if any
    move_errors = results.get('move_errors', [])
    if move_errors:
        with st.expander("❌ File Movement Errors (Click to expand)"):
            for error in move_errors:
                st.write(f"• {error}")
    
    # Show artifact-c results if available
    artifact_results = results.get('artifact_c_results')
    if artifact_results:
        copied_files = len(artifact_results.get('copied_files', []))
        if copied_files > 0:
            st.success(f"📁 Created artifact-c folder with {copied_files} slide content files organized by course!")
            
            with st.expander("📋 Artifact-C Collection Details (Click to expand)"):
                for file_info in artifact_results['copied_files']:
                    st.write(f"• **{file_info['course']}** → {file_info['filename']}")
        
        artifact_errors = artifact_results.get('errors', [])
        if artifact_errors:
            with st.expander("❌ Artifact-C Collection Errors (Click to expand)"):
                for error in artifact_errors:
                    st.write(f"• {error}")
    
    # Detailed results in collapsible sections
    if results['aaa_results'] or results['eee_results']:
        with st.expander("📄 Detailed Processing Results (Click to expand)"):
            
            # AAA results in compact table
            if results['aaa_results']:
                st.subheader("AAA Files")
                aaa_summary = []
                for result in results['aaa_results']:
                    success_count = len([s for s in result['splits'] if s['status'] == 'success'])
                    error_count = len([s for s in result['splits'] if s['status'] == 'error'])
                    skipped_count = len([s for s in result['splits'] if s['status'] == 'skipped'])
                    
                    aaa_summary.append({
                        "Lecture": result['lecture_num'],
                        "Source File": result['source_file'],
                        "Success": success_count,
                        "Errors": error_count,
                        "Skipped": skipped_count
                    })
                
                if aaa_summary:
                    df = pd.DataFrame(aaa_summary)
                    st.dataframe(df, use_container_width=True)
            
            # EEE results in compact table
            if results['eee_results']:
                st.subheader("EEE Files")
                eee_summary = []
                for result in results['eee_results']:
                    success_count = len([s for s in result['splits'] if s['status'] == 'success'])
                    error_count = len([s for s in result['splits'] if s['status'] == 'error'])
                    skipped_count = len([s for s in result['splits'] if s['status'] == 'skipped'])
                    
                    eee_summary.append({
                        "Lecture": result['lecture_num'],
                        "Source File": result['source_file'],
                        "Success": success_count,
                        "Errors": error_count,
                        "Skipped": skipped_count
                    })
                
                if eee_summary:
                    df = pd.DataFrame(eee_summary)
                    st.dataframe(df, use_container_width=True)

def main():
    st.title("AAA & EEE Content Splitter")
    st.write("Analyze and split AAA and EEE files into individual content sections.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Check for processed files
    processed_aaa, processed_eee = find_processed_files()
    if processed_aaa or processed_eee:
        st.info(f"📁 Found {len(processed_aaa + processed_eee)} previously processed files in processed folder.")
        
        with st.expander("🔄 Restore Processed Files (Click to expand)"):
            st.write("You can restore previously processed files back to the input directory:")
            
            if st.button("Restore All Processed Files"):
                restored_count = 0
                error_count = 0
                
                for file_path in processed_aaa + processed_eee:
                    if restore_file_from_processed(file_path):
                        restored_count += 1
                    else:
                        error_count += 1
                
                if restored_count > 0:
                    st.success(f"✅ Restored {restored_count} files back to input directory.")
                if error_count > 0:
                    st.error(f"❌ Failed to restore {error_count} files.")
                
                # Refresh the page to show updated file counts
                st.experimental_rerun()
    
    # Add checkbox for Artifact-C creation (disabled by default)
    create_artifact_c = st.checkbox("✅ Create 'artifact-c' folder with 'XX-c' files?", value=False, help="If checked, a folder named 'artifact-c' will be created at the project root, containing copies of all 'XX-c' (Slide Content) files, organized by course.")

    # Analysis button (matching Rename page style)
    if st.button("Analyze AAA & EEE Files"):
        with st.spinner("Analyzing files and preparing for split..."):
            # Display progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize progress steps
            status_text.text("Finding AAA and EEE files...")
            progress_bar.progress(0.2)
            time.sleep(0.1)
            
            # Find AAA and EEE files
            aaa_files, eee_files = find_aaa_eee_files(input_dir)
            
            status_text.text("Analyzing file discrepancies...")
            progress_bar.progress(0.5)
            time.sleep(0.1)
            
            # Analyze discrepancies
            discrepancies = analyze_file_discrepancies(aaa_files, eee_files)
            
            status_text.text("Preparing analysis results...")
            progress_bar.progress(0.8)
            time.sleep(0.1)
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("Analysis complete")
            
            # Store results in session state, including the checkbox state
            st.session_state.aaa_files = aaa_files
            st.session_state.eee_files = eee_files
            st.session_state.discrepancies = discrepancies
            st.session_state.create_artifact_c = create_artifact_c # Store the checkbox state
    
    # Display results if available
    if hasattr(st.session_state, 'aaa_files') and hasattr(st.session_state, 'eee_files'):
        aaa_files = st.session_state.aaa_files
        eee_files = st.session_state.eee_files
        discrepancies = st.session_state.discrepancies
        
        if not aaa_files and not eee_files:
            st.warning("No AAA or EEE files found in the input directory.")
            st.info("Looking for files matching patterns: XX-AAA.md/.txt and XX-EEE.md/.txt")
            return
        
        # Summary statistics
        total_aaa = len(aaa_files)
        total_eee = len(eee_files)
        missing_pairs = len(discrepancies.get('missing_pairs', []))
        sequence_gaps = len(discrepancies.get('sequence_gaps', []))
        
        st.header("File Analysis Results")
        
        # Display statistics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("AAA Files Found", total_aaa)
        with col2:
            st.metric("EEE Files Found", total_eee)
        with col3:
            st.metric("Valid Pairs", total_aaa + total_eee - missing_pairs)
        
        # Show files by course in compact format
        if total_aaa > 0 or total_eee > 0:
            with st.expander("📋 Files to be Split by Course (Click to expand)"):
                # Group files by course for display
                aaa_by_course = {}
                eee_by_course = {}
                
                for file_path in aaa_files:
                    course_dir = os.path.basename(os.path.dirname(file_path))
                    filename = os.path.basename(file_path)
                    if course_dir not in aaa_by_course:
                        aaa_by_course[course_dir] = []
                    aaa_by_course[course_dir].append(filename)
                
                for file_path in eee_files:
                    course_dir = os.path.basename(os.path.dirname(file_path))
                    filename = os.path.basename(file_path)
                    if course_dir not in eee_by_course:
                        eee_by_course[course_dir] = []
                    eee_by_course[course_dir].append(filename)
                
                all_courses = set(aaa_by_course.keys()) | set(eee_by_course.keys())
                sorted_courses = sorted(all_courses)
                
                # Create summary table
                course_summary = []
                for course in sorted_courses:
                    aaa_count = len(aaa_by_course.get(course, []))
                    eee_count = len(eee_by_course.get(course, []))
                    course_summary.append({
                        "Course": course,
                        "AAA Files": aaa_count,
                        "EEE Files": eee_count,
                        "Total": aaa_count + eee_count
                    })
                
                if course_summary:
                    df = pd.DataFrame(course_summary)
                    st.dataframe(df, use_container_width=True)
        
        # Show discrepancy table if any issues exist
        if discrepancies['missing_pairs'] or discrepancies['sequence_gaps']:
            with st.expander("⚠️ Discrepancy Analysis (Click to expand)"):
                st.warning("Issues found with file pairs and sequences:")
                
                # Create discrepancy table
                discrepancy_data = []
                
                # Add missing pairs
                for issue in discrepancies.get('missing_pairs', []):
                    discrepancy_data.append({
                        "Course": issue['course'],
                        "Lecture": issue['lecture'],
                        "Issue Type": "Missing Pair",
                        "Description": f"Has {issue['available']} but missing {issue['missing']}"
                    })
                
                # Add sequence gaps
                for gap in discrepancies.get('sequence_gaps', []):
                    discrepancy_data.append({
                        "Course": gap['course'],
                        "Lecture": gap['missing_lecture'],
                        "Issue Type": "Sequence Gap",
                        "Description": f"Missing lecture in range {gap['range']}"
                    })
                
                if discrepancy_data:
                    discrepancy_df = pd.DataFrame(discrepancy_data)
                    st.dataframe(discrepancy_df, use_container_width=True)
        else:
            st.success("✅ All AAA and EEE files are properly paired with no sequence gaps detected.")
        
        # Processing section
        st.header("Apply Content Splitting")
        st.write("Split each file into individual sections based on content markers.")
        
        if st.button("Split Files", disabled=total_aaa == 0 and total_eee == 0):
            with st.spinner("Processing files..."):
                # Display progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Splitting content sections...")
                progress_bar.progress(0.3)
                
                # Process files, passing the checkbox state
                results = process_files(aaa_files, eee_files, st.session_state.create_artifact_c)
                
                progress_bar.progress(0.8)
                status_text.text("Generating results...")
                time.sleep(0.1)
                
                # Complete
                progress_bar.progress(1.0)
                status_text.text("Processing complete")
                
                # Store and display results
                st.session_state.split_results = results
                display_compact_results(results)
        
        # Show previous results if available
        if 'split_results' in st.session_state:
            display_compact_results(st.session_state.split_results)
    
    # Show description of what this tool does
    with st.expander("ℹ️ What does this tool do? (Click to expand)"):
        st.markdown("""
        ### AAA & EEE Content Splitter
        
        This tool processes generated AAA and EEE files to split them into individual content sections:
        
        **Supported File Formats:** .md and .txt (output preserves original format)
        
        **AAA Files (4 sections):**
        - `XX-a`: Video Transcript Outline
        - `XX-b`: Video Transcript
        - `XX-c`: Slide Content
        - `XX-d`: Summary Transcript
        
        **EEE Files (6 sections):**
        - `XX-e`: Comprehensive Notes
        - `XX-f`: LinkedIn Post
        - `XX-g`: Socratic Dialogue
        - `XX-h`: Tweet
        - `XX-i`: Flashcards
        - `XX-j`: Glossary
        
        **Key Features:**
        - **File Movement**: Original AAA/EEE files are moved to `all_/aaa eee/` folder after splitting to prevent re-processing
        - **Discrepancy Detection**: Identifies missing AAA/EEE file pairs and sequence gaps
        - **Artifact-C Collection**: Automatically creates an "artifact-c" folder containing all XX-c (slide content) files organized by course
        - **Validation**: Checks for proper end markers and reports any missing sections
        - **Restore Capability**: Option to restore processed files back to input directory if needed
        
        **Output:**
        - Split files are saved in the same directory as source files
        - Maintains original file extension (.md or .txt)
        - Preserves course folder structure
        - Provides detailed processing and discrepancy reports
        """)

if __name__ == "__main__":
    main()