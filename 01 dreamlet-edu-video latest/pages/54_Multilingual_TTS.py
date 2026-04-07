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
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import utility functions

    get_input_directory,
    ensure_directory_exists
)

    clean_text_for_tts,
    calculate_word_count,
    estimate_audio_duration
)

    get_available_voices,
    tts_cost_estimation,
    convert_text_to_speech
)

st.set_page_config(page_title="14 Multilingual TTS - Dreamlet", page_icon="🔊")

def find_translated_section_files() -> Dict[str, Dict[str, Dict]]:
    """
    Find all translated text files created by the Multilingual Text step
    
    Returns:
        Nested dictionary of course -> lecture -> language -> data
    """
    input_dir = get_input_directory()
    
    # Find all translated metadata files (metadata_spanish.json, etc.)
    metadata_files = glob.glob(os.path.join(input_dir, "**", "metadata_*.json"), recursive=True)
    
    organized_files = {}
    
    for metadata_path in metadata_files:
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            course = metadata.get("course", "uncategorized")
            lecture = metadata.get("lecture", "unknown")
            language = metadata.get("language", "Unknown")
            
            # Skip English (source language) as it's handled by regular TTS
            if language.lower() == "english":
                continue
            
            course_key = f"Course {course}" if course else "Uncategorized"
            lecture_key = f"Lecture {lecture}" if lecture else "Unknown"
            
            # Get the directory containing the metadata file
            base_dir = os.path.dirname(metadata_path)
            
            # Get the language-specific text directory
            if "text_dir" in metadata:
                text_dir = metadata["text_dir"]
            else:
                # Try to infer from metadata filename
                lang_match = re.search(r'metadata_([a-z]+)\.json', os.path.basename(metadata_path))
                if lang_match:
                    lang_code = lang_match.group(1)
                    text_dir = os.path.join(base_dir, f"{language}_text")
                else:
                    continue
            
            if not os.path.exists(text_dir):
                continue
            
            # Find all text files in the text directory
            section_files = glob.glob(os.path.join(text_dir, "*.txt"))
            
            if not section_files:
                continue
            
            # Add to organized files
            if course_key not in organized_files:
                organized_files[course_key] = {}
            
            if lecture_key not in organized_files[course_key]:
                organized_files[course_key][lecture_key] = {}
            
            # Add language data
            organized_files[course_key][lecture_key][language] = {
                "metadata_path": metadata_path,
                "base_dir": base_dir,
                "text_dir": text_dir,
                "section_files": sorted(section_files),
                "count": len(section_files)
            }
        except Exception:
            # Skip problematic metadata files
            continue
    
    return organized_files

def generate_tts_for_translated_sections(
    section_files: List[str],
    voice: str,
    model: str,
    base_dir: str
) -> List[Dict]:
    """
    Generate TTS for translated section files
    
    Args:
        section_files: List of section file paths
        voice: Voice to use for TTS
        model: Model to use for TTS (tts-1 or tts-1-hd)
        base_dir: Base directory for the lecture
        
    Returns:
        List of processing results
    """
    results = []
    
    for section_file in section_files:
        try:
            # Read the section file
            with open(section_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Clean the text for TTS
            cleaned_text = clean_text_for_tts(content)
            
            # Skip empty sections
            if not cleaned_text:
                results.append({
                    "file_path": section_file,
                    "status": "skipped",
                    "message": "Empty section"
                })
                continue
            
            # Prepare output path for audio file
            # Get language from text directory name
            text_dir = os.path.dirname(section_file)
            language = os.path.basename(text_dir).replace("_text", "")
            
            # Create language-specific audio directory 
            audio_dir = os.path.join(base_dir, f"{language}_audio")
            ensure_directory_exists(audio_dir)
            
            # Create output filename (replacing .txt with .mp3)
            file_name = os.path.basename(section_file)
            audio_name = os.path.splitext(file_name)[0] + ".mp3"
            audio_path = os.path.join(audio_dir, audio_name)
            
            # Check if file already exists
            if os.path.exists(audio_path):
                results.append({
                    "file_path": section_file,
                    "status": "skipped",
                    "message": "Audio file already exists",
                    "audio_path": audio_path
                })
                continue
            
            # Convert text to speech
            success, message = convert_text_to_speech(
                cleaned_text, audio_path, voice, model
            )
            
            if success:
                results.append({
                    "file_path": section_file,
                    "status": "success",
                    "message": message,
                    "audio_path": audio_path,
                    "word_count": calculate_word_count(cleaned_text),
                    "estimated_duration": estimate_audio_duration(cleaned_text)
                })
            else:
                results.append({
                    "file_path": section_file,
                    "status": "error",
                    "message": message
                })
        
        except Exception as e:
            results.append({
                "file_path": section_file,
                "status": "error",
                "message": f"Error: {str(e)}"
            })
    
    return results

def main():
    st.title("14 Multilingual TTS")
    st.write("Convert translated text to speech in multiple languages.")
    
    # Check for input directory and translated files
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an input directory and add content.")
        return
    
    # Find translated section files
    organized_files = find_translated_section_files()
    
    if not organized_files:
        st.warning("No translated section files found in the input directory.")
        st.info("Please run the Prepare for Multilingual (12) and Convert Text to multiple languages (13) steps first.")
        # Show the interface anyway, just empty
        organized_files = {}
    
    # TTS Settings
    st.header("TTS Settings")
    
    # Voice selection
    available_voices = get_available_voices()
    voice_options = {v["id"]: f"{v['name']} ({v['gender']} - {v['description']})" for v in available_voices}
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_voice = st.selectbox(
            "Select Voice",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
            index=4  # Default to 'nova'
        )
    
    with col2:
        selected_model = st.radio(
            "Select Model",
            options=["tts-1", "tts-1-hd"],
            index=0,
            help="tts-1-hd offers higher audio quality but costs twice as much"
        )
    
    # Language and Section Selection
    st.header("Select Languages and Sections for TTS")
    
    # Create organized selection interface with expandable sections
    selected_items = []
    
    # Sort courses numerically
    sorted_courses = sorted(
        organized_files.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}"):
            # Sort lectures numerically
            sorted_lectures = sorted(
                organized_files[course].keys(),
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
            )
            
            for lecture in sorted_lectures:
                lecture_data = organized_files[course][lecture]
                
                # Display lecture header
                st.write(f"**{lecture}**")
                
                # Display languages for this lecture
                for language, language_data in lecture_data.items():
                    section_count = language_data["count"]
                    
                    # Calculate total words and estimated cost
                    total_words = 0
                    total_chars = 0
                    
                    for section_file in language_data["section_files"]:
                        try:
                            with open(section_file, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                            
                            cleaned_text = clean_text_for_tts(content)
                            total_words += calculate_word_count(cleaned_text)
                            total_chars += len(cleaned_text)
                        except Exception:
                            continue
                    
                    estimated_cost = tts_cost_estimation(
                        "X" * total_chars,  # Dummy text for estimation
                        model=selected_model
                    )
                    
                    # Display language info
                    st.write(f"**Language: {language}** - {section_count} sections, ~{total_words} words")
                    st.write(f"Estimated cost: ${estimated_cost:.4f}")
                    
                    # Checkbox to select this language for this lecture
                    if st.checkbox(f"Process {lecture} in {language}", key=f"{course}_{lecture}_{language}"):
                        selected_items.append((
                            course, lecture, language, language_data, total_words, estimated_cost
                        ))
    
    # TTS Processing
    st.header("Process TTS")
    
    # Calculate total for selected items
    if selected_items:
        total_sections = sum(data[3]["count"] for data in selected_items)
        total_words = sum(data[4] for data in selected_items)
        total_cost = sum(data[5] for data in selected_items)
        
        st.write(f"**Total selected:** {len(selected_items)} language-lecture combinations, {total_sections} sections")
        st.write(f"**Total words:** ~{total_words}")
        st.write(f"**Estimated cost:** ${total_cost:.4f}")
        
        # Confirmation checkbox
        confirm = st.checkbox("I confirm the cost and want to proceed with TTS conversion")
        
        if st.button("Generate Multilingual TTS", disabled=not confirm or len(selected_items) == 0):
            if not confirm:
                st.warning("Please confirm the cost first.")
                return
            
            # Process TTS for all selected items
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            all_results = []
            processed_count = 0
            
            for course, lecture, language, language_data, _, _ in selected_items:
                # Update status
                status_text.info(f"Processing {course} - {lecture} in {language}")
                
                # Get the base directory
                base_dir = language_data["base_dir"]
                
                # Generate TTS for this language-lecture combination
                results = generate_tts_for_translated_sections(
                    language_data["section_files"],
                    selected_voice,
                    selected_model,
                    base_dir
                )
                
                # Add metadata to results for display
                for result in results:
                    result["course"] = course
                    result["lecture"] = lecture
                    result["language"] = language
                
                all_results.extend(results)
                
                # Update progress
                processed_count += 1
                progress = processed_count / len(selected_items)
                progress_bar.progress(progress)
                
                # Small delay for UI updates
                time.sleep(0.1)
            
            # Complete
            status_text.success("Multilingual TTS generation complete")
            
            # Display results
            with results_container:
                st.subheader("Processing Results")
                
                # Statistics
                success_count = sum(1 for r in all_results if r["status"] == "success")
                skipped_count = sum(1 for r in all_results if r["status"] == "skipped")
                error_count = sum(1 for r in all_results if r["status"] == "error")
                
                st.write(f"✅ Successfully processed: {success_count}")
                st.write(f"⏭️ Skipped: {skipped_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Group results by course, lecture, and language for display
                results_by_group = {}
                
                for result in all_results:
                    group_key = (result["course"], result["lecture"], result["language"])
                    if group_key not in results_by_group:
                        results_by_group[group_key] = []
                    results_by_group[group_key].append(result)
                
                # Display grouped results
                for (course, lecture, language), group_results in results_by_group.items():
                    with st.expander(f"{course} - {lecture} - {language}"):
                        # Count results by status
                        group_success = sum(1 for r in group_results if r["status"] == "success")
                        group_skipped = sum(1 for r in group_results if r["status"] == "skipped")
                        group_error = sum(1 for r in group_results if r["status"] == "error")
                        
                        st.write(f"**Results:** {group_success} generated, {group_skipped} skipped, {group_error} errors")
                        
                        # Success results
                        if group_success > 0:
                            st.write("**Generated audio files:**")
                            for result in group_results:
                                if result["status"] == "success":
                                    audio_path = result["audio_path"]
                                    audio_name = os.path.basename(audio_path)
                                    word_count = result.get("word_count", 0)
                                    duration = result.get("estimated_duration", 0)
                                    
                                    st.write(f"- {audio_name}: {word_count} words, ~{duration:.1f} seconds")
                        
                        # Error results
                        if group_error > 0:
                            st.write("**Errors:**")
                            for result in group_results:
                                if result["status"] == "error":
                                    file_name = os.path.basename(result["file_path"])
                                    st.write(f"- {file_name}: {result['message']}")
    else:
        st.info("No languages selected for TTS processing.")

if __name__ == "__main__":
    main()
