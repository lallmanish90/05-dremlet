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
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Set page configuration
st.set_page_config(page_title="02 Adjust AAA EEE - Dreamlet", page_icon="📄")

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

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
    """Save the split sections to individual files"""
    results = []
    base_dir = os.path.dirname(base_file_path)
    
    # Get the original file extension
    original_filename = os.path.basename(base_file_path)
    file_extension = get_file_extension(original_filename)
    
    for suffix, content in sections.items():
        output_filename = f"{lecture_num}-{suffix}.{file_extension}"
        output_path = os.path.join(base_dir, output_filename)
        
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

def create_artifact_c_structure(input_directory: str, results: Dict) -> Dict:
    """Create artifact-c folder structure with all XX-c files organized by course"""
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
                if split['status'] == 'success' and split['file'].endswith('-c.md') or split['file'].endswith('-c.txt'):
                    source_path = split['path']
                    break
            
            if source_path:
                # Extract course name from the directory structure
                course_dir = os.path.basename(os.path.dirname(source_path))
                
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

def process_files(aaa_files: List[str], eee_files: List[str]) -> Dict:
    """Process all AAA and EEE files"""
    results = {
        'aaa_results': [],
        'eee_results': [],
        'validation_errors': [],
        'discrepancies': analyze_file_discrepancies(aaa_files, eee_files),
        'total_processed': 0,
        'total_created': 0,
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
            'splits': split_results
        })
        results['total_processed'] += 1
        results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
    
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
            'splits': split_results
        })
        results['total_processed'] += 1
        results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
    
    # Create artifact-c structure after processing is complete
    if results['aaa_results']:  # Only if we have AAA files with XX-c content
        input_dir = get_input_directory()
        artifact_results = create_artifact_c_structure(input_dir, results)
        results['artifact_c_results'] = artifact_results
    
    return results

def display_results(results: Dict):
    """Display processing results in a user-friendly format"""
    
    # Calculate totals
    total_aaa_files = len(results.get('aaa_results', []))
    total_eee_files = len(results.get('eee_results', []))
    total_files_processed = total_aaa_files + total_eee_files
    
    st.success(f"Processing complete! Found and processed {total_files_processed} files ({total_aaa_files} AAA + {total_eee_files} EEE) and created {results['total_created']} split files.")
    
    # Show discrepancies first (most important)
    discrepancies = results.get('discrepancies', {})
    
    # Missing AAA/EEE pairs
    if discrepancies.get('missing_pairs'):
        st.error("Missing AAA/EEE Pairs Found:")
        for issue in discrepancies['missing_pairs']:
            st.write(f"🔴 **{issue['course']}** - Lecture {issue['lecture']}: Has {issue['available']} but missing {issue['missing']}")
    
    # Sequence gaps (informational only - not errors)
    if discrepancies.get('sequence_gaps'):
        with st.expander("📊 Lecture Sequence Information (Click to expand)"):
            st.info("This shows lecture numbers that exist vs. complete sequential numbering. Missing numbers are normal and not errors.")
            for gap in discrepancies['sequence_gaps']:
                st.write(f"ℹ️ **{gap['course']}** - Lecture {gap['missing_lecture']} not found in range {gap['range']}")
                
    # Show file processing summary
    total_files_found = len(results.get('aaa_results', [])) + len(results.get('eee_results', []))
    if total_files_found > 0:
        st.success(f"✅ Successfully processed {total_files_found} files and created split sections.")
    
    # Show validation errors if any
    if results['validation_errors']:
        st.warning("Validation Issues Found:")
        for error in results['validation_errors']:
            st.write(f"⚠️ {error}")
    
    # Show AAA results
    if results['aaa_results']:
        st.subheader("AAA Files Processed")
        for result in results['aaa_results']:
            with st.expander(f"Lecture {result['lecture_num']} AAA - {result['source_file']}"):
                for split in result['splits']:
                    if split['status'] == 'success':
                        st.write(f"✅ {split['file']} ({split['size']} characters)")
                    elif split['status'] == 'error':
                        st.write(f"❌ {split['file']}: {split['error']}")
                    else:
                        st.write(f"⏭️ {split['file']}: {split['reason']}")
    
    # Show EEE results
    if results['eee_results']:
        st.subheader("EEE Files Processed")
        for result in results['eee_results']:
            with st.expander(f"Lecture {result['lecture_num']} EEE - {result['source_file']}"):
                for split in result['splits']:
                    if split['status'] == 'success':
                        st.write(f"✅ {split['file']} ({split['size']} characters)")
                    elif split['status'] == 'error':
                        st.write(f"❌ {split['file']}: {split['error']}")
                    else:
                        st.write(f"⏭️ {split['file']}: {split['reason']}")

def display_simple_results(results: Dict):
    """Display simplified processing results summary"""
    st.subheader("Content Splitting Results")
    
    # Simple summary
    total_processed = results.get('total_processed', 0)
    total_created = results.get('total_created', 0)
    validation_errors = len(results.get('validation_errors', []))
    
    # Display basic metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files Processed", total_processed)
    with col2:
        st.metric("Split Files Created", total_created)
    with col3:
        st.metric("Validation Errors", validation_errors)
    
    # Display artifact-c results if available
    artifact_results = results.get('artifact_c_results')
    if artifact_results:
        st.subheader("Artifact-C Collection Results")
        
        copied_files = len(artifact_results.get('copied_files', []))
        created_folders = len(artifact_results.get('created_folders', []))
        artifact_errors = len(artifact_results.get('errors', []))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Slide Content Files", copied_files)
        with col2:
            st.metric("Course Folders Created", created_folders)
        with col3:
            st.metric("Collection Errors", artifact_errors)
        
        if copied_files > 0:
            st.success(f"✅ Created artifact-c folder with {copied_files} slide content files organized by course!")
            
            # Show details in expander
            with st.expander("View Artifact-C Details"):
                for file_info in artifact_results['copied_files']:
                    st.write(f"📁 **{file_info['course']}** → {file_info['filename']}")
        
        if artifact_errors > 0:
            st.warning("Artifact-C Collection Issues:")
            for error in artifact_results['errors']:
                st.write(f"⚠️ {error}")
    
    # Show validation errors if any
    if validation_errors > 0:
        st.warning("Validation Issues:")
        for error in results['validation_errors']:
            st.write(f"⚠️ {error}")
    
    # Show discrepancies if detected during processing
    discrepancies = results.get('discrepancies', {})
    if discrepancies.get('missing_pairs') or discrepancies.get('sequence_gaps'):
        st.warning("File Discrepancies Detected:")
        
        discrepancy_data = []
        
        # Add missing pairs
        for issue in discrepancies.get('missing_pairs', []):
            discrepancy_data.append({
                "Course": issue['course'],
                "Lecture": issue['lecture'],
                "Issue": f"Missing {issue['missing']} (has {issue['available']})"
            })
        
        # Add sequence gaps
        for gap in discrepancies.get('sequence_gaps', []):
            discrepancy_data.append({
                "Course": gap['course'],
                "Lecture": gap['missing_lecture'],
                "Issue": f"Sequence gap in range {gap['range']}"
            })
        
        if discrepancy_data:
            discrepancy_df = pd.DataFrame(discrepancy_data)
            st.dataframe(discrepancy_df, use_container_width=True)
    
    if total_created > 0:
        st.success(f"Successfully created {total_created} split files from {total_processed} source files.")
    elif total_processed > 0:
        st.info("Files were processed but no split files were created. Check validation errors above.")
    else:
        st.warning("No files were processed.")

def main():
    st.title("AAA & EEE Content Splitter")
    st.write("Analyze and split AAA and EEE files into individual content sections.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Analysis button (matching Rename page style)
    if st.button("Analyze AAA & EEE Files"):
        with st.spinner("Analyzing files..."):
            # Display progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize progress steps
            status_text.text("Finding AAA and EEE files...")
            progress_bar.progress(0.2)
            time.sleep(0.5)
            
            # Find AAA and EEE files
            aaa_files, eee_files = find_aaa_eee_files(input_dir)
            
            status_text.text("Analyzing file discrepancies...")
            progress_bar.progress(0.5)
            
            # Analyze discrepancies
            discrepancies = analyze_file_discrepancies(aaa_files, eee_files)
            
            status_text.text("Generating analysis results...")
            progress_bar.progress(0.8)
            time.sleep(0.5)
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("Analysis complete")
            
            # Store results in session state
            st.session_state.aaa_files = aaa_files
            st.session_state.eee_files = eee_files
            st.session_state.discrepancies = discrepancies
    
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
        
        # Show files by course in expandable sections
        st.subheader("Files to be Split by Course")
        
        all_courses = set(aaa_by_course.keys()) | set(eee_by_course.keys())
        sorted_courses = sorted(all_courses)
        
        for course in sorted_courses:
            with st.expander(f"{course}"):
                aaa_files_course = aaa_by_course.get(course, [])
                eee_files_course = eee_by_course.get(course, [])
                
                if aaa_files_course:
                    st.write(f"**AAA Files**: {', '.join(aaa_files_course)}")
                if eee_files_course:
                    st.write(f"**EEE Files**: {', '.join(eee_files_course)}")
        
        # Show discrepancy table if any issues exist
        if discrepancies['missing_pairs'] or discrepancies['sequence_gaps']:
            st.subheader("Discrepancy Analysis")
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
                import pandas as pd
                discrepancy_df = pd.DataFrame(discrepancy_data)
                st.dataframe(discrepancy_df, use_container_width=True)
        else:
            st.success("All AAA and EEE files are properly paired with no sequence gaps detected.")
        
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
                
                # Process files
                results = process_files(aaa_files, eee_files)
                
                progress_bar.progress(0.8)
                status_text.text("Generating results...")
                time.sleep(0.5)
                
                # Complete
                progress_bar.progress(1.0)
                status_text.text("Processing complete")
                
                # Store and display results
                st.session_state.split_results = results
                display_simple_results(results)
        
        # Show previous results if available
        if 'split_results' in st.session_state:
            display_simple_results(st.session_state.split_results)
    
    # Show description of what this tool does
    with st.expander("What does this tool do?"):
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
        
        **Discrepancy Detection:**
        - Identifies missing AAA/EEE file pairs
        - Detects gaps in lecture number sequences
        - Reports orphaned files and inconsistencies
        
        **Validation:**
        - Checks for proper end markers: `===END OF LECTURE [XX]-AAA GENERATION===`
        - Reports any missing sections or validation errors
        - Only creates files with actual content
        
        **Output:**
        - Split files are saved in the same directory as source files
        - Maintains original file extension (.md or .txt)
        - Preserves course folder structure
        - **Artifact-C Collection**: Automatically creates an "artifact-c" folder containing all XX-c (slide content) files organized by course
        - Provides detailed processing and discrepancy reports
        """)

if __name__ == "__main__":
    main()