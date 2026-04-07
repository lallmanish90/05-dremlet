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
import json
import glob
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

# Import utility functions

    get_input_directory,
    ensure_directory_exists,
    find_files
)

st.set_page_config(page_title="12 Prepare Folders for Multilingual - Dreamlet", page_icon="🌍")

def find_processed_lectures() -> Dict[str, Dict[str, Dict]]:
    """
    Find all lectures with text, audio, and image files
    
    Returns:
        Nested dictionary of course -> lecture -> data
    """
    input_dir = get_input_directory()
    
    # Search for content directly in lecture folders without relying on metadata
    organized_data = {}
    
    # Walk through all directories looking for lectures with content
    for root, dirs, files in os.walk(input_dir):
        # Skip very deep nested directories for performance
        if root.count(os.sep) > 10:
            continue
            
        # Analyze the directory name to identify lectures
        dir_name = os.path.basename(root)
        
        # Check if this looks like a lecture directory
        lecture_match = re.search(r'lecture[-_\s]*(\d+)', dir_name.lower())
        if not lecture_match:
            continue
            
        lecture_number = lecture_match.group(1)
        
        # Extract course information from parent directories
        parent_dir = os.path.dirname(root)
        course_number = "1"  # Default course number
        
        # Try to extract course number from parent directory names
        for part in parent_dir.split(os.sep):
            course_match = re.search(r'course[-_\s]*(\d+)', part.lower())
            if course_match:
                course_number = course_match.group(1)
                break
                
        # Look for various file types in this lecture directory
        text_files = []
        audio_files = []
        image_files = []
        
        # Scan for files in the current directory and its immediate subdirectories
        for dirpath, subdirs, dirfiles in os.walk(root):
            # Don't recurse too deep
            rel_path = os.path.relpath(dirpath, root)
            if rel_path != '.' and rel_path.count(os.sep) > 1:
                continue
                
            # Look for text files
            for file in dirfiles:
                file_path = os.path.join(dirpath, file)
                if file.endswith('.txt') or file.endswith('.md'):
                    text_files.append(file_path)
                elif file.endswith('.mp3') or file.endswith('.wav') or file.endswith('.m4a'):
                    audio_files.append(file_path)
                elif file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg'):
                    image_files.append(file_path)
            
        # Need at least some of each type to consider it a valid lecture for our purposes
        if text_files and (audio_files or image_files):
            course_key = f"Course {course_number}"
            lecture_key = f"Lecture {lecture_number}"
            
            if course_key not in organized_data:
                organized_data[course_key] = {}
                
            # Calculate directory paths
            sections_dir = None
            audio_dir = None
            images_dir = None
            
            # Check for standard folder structure
            for subdir in dirs:
                subdir_path = os.path.join(root, subdir)
                if subdir.lower() == 'sections':
                    sections_dir = subdir_path
                elif subdir.lower() == 'audio':
                    audio_dir = subdir_path
                elif subdir.lower() == 'images':
                    images_dir = subdir_path
            
            # Add lecture data
            organized_data[course_key][lecture_key] = {
                "base_dir": root,
                "sections_dir": sections_dir,
                "audio_dir": audio_dir,
                "images_dir": images_dir,
                "section_files": sorted(text_files),
                "audio_files": sorted(audio_files),
                "image_files": sorted(image_files),
                "text_count": len(text_files),
                "audio_count": len(audio_files),
                "image_count": len(image_files)
            }
    
    return organized_data

def organize_files_for_multilingual(
    lecture_data: Dict,
    target_languages: List[str]
) -> Dict:
    """
    Organize files into language-specific folders
    
    Args:
        lecture_data: Dictionary with lecture file data
        target_languages: List of target languages to prepare folders for
        
    Returns:
        Dictionary with processing results
    """
    results = {
        "text": {"success": 0, "skipped": 0, "error": 0, "moved": 0},
        "audio": {"success": 0, "skipped": 0, "error": 0, "moved": 0},
        "image": {"success": 0, "skipped": 0, "error": 0, "moved": 0}
    }
    
    base_dir = lecture_data["base_dir"]
    
    # Extract course and lecture numbers from the base_dir path
    base_path = base_dir
    course_number = "1"  # Default
    lecture_number = "1"  # Default
    
    # Parse the directory path to find course and lecture numbers
    dir_parts = base_path.split(os.sep)
    for part in dir_parts:
        course_match = re.search(r'course[-_\s]*(\d+)', part.lower())
        if course_match:
            course_number = course_match.group(1)
        
        lecture_match = re.search(r'lecture[-_\s]*(\d+)', part.lower())
        if lecture_match:
            lecture_number = lecture_match.group(1)
    
    # Delete any existing metadata files
    try:
        metadata_files = glob.glob(os.path.join(base_dir, "metadata_*.json"))
        for file_path in metadata_files:
            try:
                os.remove(file_path)
            except:
                pass  # Continue if deletion fails
    except:
        pass  # Continue if glob fails
    
    # Create a language-specific folder for each target language
    lang_folders = {}
    for language in target_languages:
        lang_folders[language] = {
            "text_dir": os.path.join(base_dir, f"{language} text"),
            "audio_dir": os.path.join(base_dir, f"{language} audio"),
            "image_dir": os.path.join(base_dir, f"{language} image")
        }
        
        # Ensure directories exist
        ensure_directory_exists(lang_folders[language]["text_dir"])
        ensure_directory_exists(lang_folders[language]["audio_dir"])
        ensure_directory_exists(lang_folders[language]["image_dir"])
    
    # Move all original files to English folders, ONLY if English is selected
    # First, process English files by moving them
    if "English" in target_languages:
        # Process text files
        for text_file in lecture_data["section_files"]:
            try:
                # Get filename
                file_name = os.path.basename(text_file)
                
                # Create destination path
                eng_dest_path = os.path.join(lang_folders["English"]["text_dir"], file_name)
                if os.path.exists(eng_dest_path):
                    results["text"]["skipped"] += 1
                else:
                    # Move the file
                    shutil.move(text_file, eng_dest_path)
                    results["text"]["moved"] += 1
            except Exception as e:
                results["text"]["error"] += 1
        
        # Process audio files
        for audio_file in lecture_data["audio_files"]:
            try:
                # Get filename
                file_name = os.path.basename(audio_file)
                
                # Create destination path
                eng_dest_path = os.path.join(lang_folders["English"]["audio_dir"], file_name)
                if os.path.exists(eng_dest_path):
                    results["audio"]["skipped"] += 1
                else:
                    # Move the file
                    shutil.move(audio_file, eng_dest_path)
                    results["audio"]["moved"] += 1
            except Exception as e:
                results["audio"]["error"] += 1
        
        # Process image files
        for image_file in lecture_data["image_files"]:
            try:
                # Get filename
                file_name = os.path.basename(image_file)
                
                # Create destination path
                eng_dest_path = os.path.join(lang_folders["English"]["image_dir"], file_name)
                if os.path.exists(eng_dest_path):
                    results["image"]["skipped"] += 1
                else:
                    # Move the file
                    shutil.move(image_file, eng_dest_path)
                    results["image"]["moved"] += 1
            except Exception as e:
                results["image"]["error"] += 1
    
    # Just ensure other language folders exist (no README files)
    for language in target_languages:
        if language.lower() == "english":
            continue  # Skip English as we already processed it
        
        # The folders were already created earlier, no additional action needed here
    
    return results

def main():
    st.title("12 Prepare Folders for Multilingual")
    st.write("Organize files into language-specific folders to prepare for multilingual video production.")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an input directory and add content.")
        return
    
    # Find processed lectures
    organized_data = find_processed_lectures()
    
    if not organized_data:
        st.warning("No processed lectures found with text, audio, and image files.")
        st.info("Please run the previous steps (Save Text, TTS, and either 4K Image or MP4) first.")
        return
    
    # Language settings
    st.header("Language Settings")
    
    # List of common languages to select from
    available_languages = [
        "English", "French", "German", "Spanish", "Italian", "Polish", 
        "Turkish", "Indonesian", "Mandarin", "Arabic", "Hindi", 
        "Russian", "Korean", "Japanese", "Vietnamese"
    ]
    
    # Add "Select All" button for languages
    col1, col2 = st.columns([1, 3])
    with col1:
        select_all_languages = st.button("Select All Languages")
    
    # Store the selection state in session state to persist across reruns
    if "selected_languages" not in st.session_state:
        st.session_state.selected_languages = ["English"]
    
    # If Select All button is clicked, update session state
    if select_all_languages:
        st.session_state.selected_languages = available_languages
    
    # Multi-select for languages using session state for persistence
    selected_languages = st.multiselect(
        "Select languages to prepare folders for",
        options=available_languages,
        default=st.session_state.selected_languages,
        help="Select multiple languages to create language-specific folders"
    )
    
    # Update session state with current selection
    st.session_state.selected_languages = selected_languages
    
    # Ensure at least one language is selected
    if not selected_languages:
        st.warning("Please select at least one language.")
        selected_languages = ["English"]  # Default to English
    
    # Course and lecture selection
    st.header("Select Lectures to Prepare")
    
    # Organize selection with expandable sections
    selected_lectures = []
    
    # Sort courses numerically
    sorted_courses = sorted(
        organized_data.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}"):
            # Option to select all lectures in this course
            all_in_course = st.checkbox(f"Select all lectures in {course}", key=f"all_{course}")
            
            # Sort lectures numerically
            sorted_lectures = sorted(
                organized_data[course].keys(),
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
            )
            
            for lecture in sorted_lectures:
                lecture_data = organized_data[course][lecture]
                
                # Display lecture info
                st.write(f"**{lecture}:**")
                st.write(f"- Text sections: {lecture_data['text_count']}")
                st.write(f"- Audio files: {lecture_data['audio_count']}")
                st.write(f"- Image files: {lecture_data['image_count']}")
                
                # Select this lecture
                if all_in_course:
                    selected = True
                    st.write("✅ Selected (from 'Select all')")
                else:
                    selected = st.checkbox(f"Prepare {lecture}", key=f"{course}_{lecture}")
                
                if selected:
                    selected_lectures.append((course, lecture, lecture_data))
    
    # Processing
    st.header("Organize Files")
    
    if selected_lectures:
        total_lectures = len(selected_lectures)
        st.write(f"**Selected:** {total_lectures} lectures to prepare for multilingual processing")
        
        if st.button("Organize Files"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            all_results = []
            processed_count = 0
            
            for course, lecture, lecture_data in selected_lectures:
                # Update status
                status_text.info(f"Processing {course} - {lecture}")
                
                # Organize files
                results = organize_files_for_multilingual(
                    lecture_data,
                    selected_languages
                )
                
                # Add metadata
                result_with_metadata = {
                    "course": course,
                    "lecture": lecture,
                    "results": results
                }
                
                all_results.append(result_with_metadata)
                
                # Update progress
                processed_count += 1
                progress = processed_count / total_lectures
                progress_bar.progress(progress)
                
                # Small delay for UI updates
                time.sleep(0.1)
            
            # Complete
            status_text.success("Organization complete")
            
            # Display results
            with results_container:
                st.subheader("Processing Results")
                
                # Calculate overall statistics
                total_stats = {
                    "text": {"success": 0, "skipped": 0, "error": 0, "moved": 0},
                    "audio": {"success": 0, "skipped": 0, "error": 0, "moved": 0},
                    "image": {"success": 0, "skipped": 0, "error": 0, "moved": 0}
                }
                
                for result in all_results:
                    for file_type in ["text", "audio", "image"]:
                        for status in ["success", "skipped", "error", "moved"]:
                            total_stats[file_type][status] += result["results"][file_type].get(status, 0)
                
                # Display overall stats
                st.write("### Overall Statistics")
                st.write(f"✅ **Text files:** {total_stats['text']['moved']} moved, {total_stats['text']['success']} copied, {total_stats['text']['skipped']} skipped, {total_stats['text']['error']} errors")
                st.write(f"🔊 **Audio files:** {total_stats['audio']['moved']} moved, {total_stats['audio']['success']} copied, {total_stats['audio']['skipped']} skipped, {total_stats['audio']['error']} errors")
                st.write(f"🖼️ **Image files:** {total_stats['image']['moved']} moved, {total_stats['image']['success']} copied, {total_stats['image']['skipped']} skipped, {total_stats['image']['error']} errors")
                
                # Detailed results by course and lecture
                st.write("### Detailed Results")
                for result in all_results:
                    with st.expander(f"{result['course']} - {result['lecture']}"):
                        r = result["results"]
                        st.write(f"**Text files:** {r['text'].get('moved', 0)} moved, {r['text'].get('success', 0)} copied, {r['text'].get('skipped', 0)} skipped, {r['text'].get('error', 0)} errors")
                        st.write(f"**Audio files:** {r['audio'].get('moved', 0)} moved, {r['audio'].get('success', 0)} copied, {r['audio'].get('skipped', 0)} skipped, {r['audio'].get('error', 0)} errors")
                        st.write(f"**Image files:** {r['image'].get('moved', 0)} moved, {r['image'].get('success', 0)} copied, {r['image'].get('skipped', 0)} skipped, {r['image'].get('error', 0)} errors")
                        
                        # Show selected languages for this lecture
                        st.write(f"**Languages prepared:** {', '.join(selected_languages)}")
    else:
        st.info("No lectures selected. Please select lectures to prepare for multilingual processing.")

if __name__ == "__main__":
    main()