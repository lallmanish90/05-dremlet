import streamlit as st
import os
import re
import time
import json
from pathlib import Path
import glob
from typing import Dict, List, Tuple

# Import utility functions
from utils.file_operations import (
    get_input_directory,
    get_output_directory,
    ensure_directory_exists
)
from utils.text_processing import (
    clean_text_for_tts,
    calculate_word_count,
    estimate_audio_duration
)
from utils.openai_integration import (
    get_available_voices,
    tts_cost_estimation,
    convert_text_to_speech
)

st.set_page_config(page_title="07 TTS - Dreamlet", page_icon="🔊")

def find_section_files(summary_mode: bool = False) -> Dict[str, Dict[str, Dict]]:
    """
    Find all section files created by the previous step
    
    Args:
        summary_mode: If True, look for files in "English Summary text" folders instead of "English text"
    
    Returns:
        Nested dictionary of course -> lecture -> section files
    """
    input_dir = get_input_directory()
    
    organized_files = {}
    
    # Determine folder names based on mode
    text_folder_name = "English Summary text" if summary_mode else "English text"
    audio_folder_name = "English Summary audio" if summary_mode else "English audio"
    
    # Find all course directories
    for item in os.listdir(input_dir):
        course_path = os.path.join(input_dir, item)
        
        # Skip if not a directory or doesn't look like a course
        if not os.path.isdir(course_path):
            continue
        
        # Extract course information from directory name
        course_match = re.search(r'(\d+)', item)
        course = course_match.group(1) if course_match else "uncategorized"
        course_key = f"Course {course}" if course else "Uncategorized"
        
        # Find all lecture directories
        lecture_dirs = []
        
        # Search for Section directories first
        section_dirs = [d for d in os.listdir(course_path) if os.path.isdir(os.path.join(course_path, d)) and "Section" in d]
        
        # For each section, find lectures
        for section_dir in section_dirs:
            section_path = os.path.join(course_path, section_dir)
            lecture_dirs.extend([os.path.join(section_path, d) for d in os.listdir(section_path) 
                               if os.path.isdir(os.path.join(section_path, d)) and "Lecture" in d])
        
        # If no sections found, look for lectures directly in course
        if not section_dirs:
            lecture_dirs = [os.path.join(course_path, d) for d in os.listdir(course_path) 
                           if os.path.isdir(os.path.join(course_path, d)) and "Lecture" in d]
        
        # Process each lecture directory
        for lecture_dir in lecture_dirs:
            # Extract lecture number from directory name
            lecture_match = re.search(r'Lecture\s+(\d+)', os.path.basename(lecture_dir))
            if not lecture_match:
                continue
                
            lecture = lecture_match.group(1)
            lecture_key = f"Lecture {lecture}"
            
            # Check for the text folder based on mode
            text_dir = os.path.join(lecture_dir, text_folder_name)
            
            # Find all text files in the text directory if it exists
            section_files = []
            # Create text directory if it doesn't exist
            if not os.path.exists(text_dir):
                os.makedirs(text_dir, exist_ok=True)
                
            # Only look in the appropriate text directory
            section_files = glob.glob(os.path.join(text_dir, "*.txt"))
            
            if not section_files:
                continue
            
            # Add to organized files
            if course_key not in organized_files:
                organized_files[course_key] = {}
            
            # Store section files and text/audio directories
            audio_dir = os.path.join(lecture_dir, audio_folder_name)
            # Create audio directory if it doesn't exist
            if not os.path.exists(audio_dir):
                os.makedirs(audio_dir, exist_ok=True)
                
            organized_files[course_key][lecture_key] = {
                "base_dir": lecture_dir,
                "section_files": sorted(section_files),
                "text_dir": text_dir if os.path.exists(text_dir) else None,
                "audio_dir": audio_dir
            }
    
    return organized_files

def generate_tts_for_sections(
    section_files: List[str],
    voice: str,
    model: str,
    response_format: str = "mp3",
    instructions: str = None,
    audio_dir: str = None
) -> List[Dict]:
    """
    Generate TTS for a list of section files
    
    Args:
        section_files: List of section file paths
        voice: Voice to use for TTS
        model: Model to use for TTS (tts-1, tts-1-hd, or gpt-4o-mini-tts)
        response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
        instructions: Optional instructions for speech style
        audio_dir: Directory to save audio files (can be "English audio" or "English Summary audio")
        
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
            
            # Create output filename with proper extension
            file_name = os.path.basename(section_file)
            extension = response_format if response_format not in ["pcm"] else "wav"  # PCM uses WAV extension
            audio_name = os.path.splitext(file_name)[0] + f".{extension}"
            
            # Determine where to save the audio file
            if not audio_dir:
                # Extract the lecture directory from the section file path
                section_dir = os.path.dirname(section_file)
                lecture_dir = os.path.dirname(section_dir)
                
                # Determine audio directory name based on section directory name
                if "English Summary text" in section_dir:
                    audio_dir = os.path.join(lecture_dir, "English Summary audio")
                else:
                    audio_dir = os.path.join(lecture_dir, "English audio")
                
            # Ensure the audio directory exists
            if not os.path.exists(audio_dir):
                os.makedirs(audio_dir, exist_ok=True)
                
            # Save to the appropriate audio directory
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
            
            # Convert text to speech with the enhanced API
            success, message = convert_text_to_speech(
                cleaned_text, 
                audio_path, 
                voice, 
                model,
                response_format,
                instructions if instructions and instructions.strip() else None
            )
            
            if success:
                results.append({
                    "file_path": section_file,
                    "status": "success",
                    "message": message,
                    "audio_path": audio_path,
                    "word_count": calculate_word_count(cleaned_text),
                    "estimated_duration": estimate_audio_duration(cleaned_text),
                    "format": response_format
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

def display_tts_interface(summary_mode=False):
    """
    Display the TTS interface for either regular or summary files
    
    Args:
        summary_mode: If True, work with "English Summary text" folders instead of "English text"
    """
    # Find section files based on mode
    organized_files = find_section_files(summary_mode)
    
    if not organized_files:
        folder_type = "English Summary text" if summary_mode else "English text"
        st.warning(f"No section files found in {folder_type} folders.")
        st.info(f"Please run the previous step (06 Save Text) first to create proper {folder_type} files.")
        return
    
    # TTS Settings
    st.header("TTS Settings")
    
    # Model selection
    col1, col2 = st.columns(2)
    
    with col1:
        selected_model = st.radio(
            "Select Model",
            options=["tts-1", "tts-1-hd", "gpt-4o-mini-tts"],
            index=0,
            key=f"model_{summary_mode}",
            help="tts-1-hd offers higher audio quality but costs twice as much. gpt-4o-mini-tts is the newest model with enhanced capabilities."
        )
    
    # Filter available voices based on selected model
    model_type = "legacy" if selected_model in ["tts-1", "tts-1-hd"] else "new"
    available_voices = get_available_voices(model_type)
    voice_options = {v["id"]: f"{v['name']} ({v['gender']} - {v['description']})" for v in available_voices}
    
    with col2:
        selected_voice = st.selectbox(
            "Select Voice",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
            index=min(4, len(voice_options) - 1),  # Default to 'nova' or first available
            key=f"voice_{summary_mode}"
        )
    
    # Additional options for the new model
    if selected_model == "gpt-4o-mini-tts":
        with st.expander("Advanced Options", expanded=False):
            response_format = st.selectbox(
                "Audio Format",
                options=["mp3", "opus", "aac", "flac", "wav", "pcm"],
                index=0,
                key=f"format_{summary_mode}",
                help="MP3 is the default format. For faster response, choose WAV or PCM."
            )
            
            speech_instructions = st.text_area(
                "Speech Instructions",
                placeholder="E.g., 'Speak in a cheerful tone' or 'Speak slowly and clearly'",
                key=f"instructions_{summary_mode}",
                help="Provide instructions to control aspects of speech like tone, speed, or emotional range."
            )
    else:
        response_format = "mp3"
        speech_instructions = None
    
    # Section Selection
    st.header("Select Sections for TTS")
    
    # Create organized selection interface with expandable sections
    selected_lectures = {}
    
    # Sort courses numerically
    sorted_courses = sorted(
        organized_files.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}", expanded=True):
            # Option to select all lectures in this course
            all_in_course = st.checkbox(f"Select all lectures in {course}", key=f"all_{course}_{summary_mode}")
            
            # Sort lectures numerically
            sorted_lectures = sorted(
                organized_files[course].keys(),
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
            )
            
            for lecture in sorted_lectures:
                lecture_data = organized_files[course][lecture]
                section_files = lecture_data["section_files"]
                
                # Calculate total words and estimated cost
                total_words = 0
                total_chars = 0
                
                for section_file in section_files:
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
                
                # Display lecture info
                st.write(f"**{lecture}:** {len(section_files)} sections, ~{total_words} words")
                st.write(f"Estimated cost: ${estimated_cost:.4f}")
                
                # Select this lecture
                if all_in_course:
                    selected = True
                    st.write("✅ Selected (from 'Select all')")
                else:
                    selected = st.checkbox(f"Process {lecture}", key=f"{course}_{lecture}_{summary_mode}")
                
                if selected:
                    selected_lectures[(course, lecture)] = lecture_data
    
    # TTS Processing
    st.header("Process TTS")
    
    # Calculate total for selected lectures
    if selected_lectures:
        total_sections = sum(len(data["section_files"]) for data in selected_lectures.values())
        
        # Calculate total words and cost
        total_words = 0
        total_chars = 0
        
        for lecture_data in selected_lectures.values():
            for section_file in lecture_data["section_files"]:
                try:
                    with open(section_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    cleaned_text = clean_text_for_tts(content)
                    total_words += calculate_word_count(cleaned_text)
                    total_chars += len(cleaned_text)
                except Exception:
                    continue
        
        total_cost = tts_cost_estimation(
            "X" * total_chars,  # Dummy text for estimation
            model=selected_model
        )
        
        st.write(f"**Total selected:** {len(selected_lectures)} lectures, {total_sections} sections")
        st.write(f"**Total words:** ~{total_words}")
        st.write(f"**Estimated cost:** ${total_cost:.4f}")
        
        # Confirmation checkbox
        confirm = st.checkbox("I confirm the cost and want to proceed with TTS conversion", key=f"confirm_{summary_mode}")
        
        if st.button("Generate TTS", key=f"generate_{summary_mode}", disabled=not confirm or len(selected_lectures) == 0):
            if not confirm:
                st.warning("Please confirm the cost first.")
                return
            
            # Main progress section
            st.header("Processing Progress")
            
            # Setup UI containers - these will be updated during processing
            main_progress_container = st.container()
            with main_progress_container:
                main_progress_bar = st.progress(0)
                main_stats = st.empty()  # For overall progress stats
                eta_display = st.empty()  # For time remaining
                
            # Current task status
            current_task_container = st.container()
            with current_task_container:
                current_task_status = st.empty()
            
            # Latest results section
            latest_results_container = st.container()
            with latest_results_container:
                latest_result_header = st.empty()
                latest_result_status = st.empty()
            
            # Final results container (filled at the end)
            results_container = st.container()
            
            # Process tracking variables
            all_results = []
            processed_count = 0
            total_lectures = len(selected_lectures)
            total_sections = sum(len(data["section_files"]) for data in selected_lectures.values())
            processed_sections = 0
            total_sections_count = sum(len(lecture_data["section_files"]) for lecture_data in selected_lectures.values())
            
            # Time tracking for ETA calculation
            start_time = time.time()
            
            for (course, lecture), lecture_data in selected_lectures.items():
                # Update current task status
                current_task_status.info(f"Currently processing: {course} - {lecture} ({len(lecture_data['section_files'])} sections)")
                
                # Generate TTS for this lecture
                results = generate_tts_for_sections(
                    lecture_data["section_files"],
                    selected_voice,
                    selected_model,
                    response_format,
                    speech_instructions,
                    lecture_data.get("audio_dir")  # Use the audio_dir field
                )
                
                all_results.extend(results)
                processed_sections += len(lecture_data["section_files"])
                
                # Update main progress
                processed_count += 1
                progress_percentage = processed_count / total_lectures
                main_progress_bar.progress(progress_percentage)
                
                # Calculate and display overall stats
                percent_complete = int(processed_count / total_lectures * 100)
                main_stats.write(f"Processing {processed_count}/{total_lectures} lectures ({percent_complete}% complete)")
                
                # Calculate and display ETA
                elapsed_time = time.time() - start_time
                if processed_count > 0:
                    estimated_total_time = elapsed_time / processed_count * total_lectures
                    remaining_time = estimated_total_time - elapsed_time
                    minutes, seconds = divmod(int(remaining_time), 60)
                    eta_display.write(f"Estimated time remaining: {minutes} minutes, {seconds} seconds")
                
                # Display latest result
                latest_result_header.subheader(f"Latest Completed: {course} - {lecture}")
                
                # Count results by status for the current lecture
                success_count = len([r for r in results if r["status"] == "success"])
                skipped_count = len([r for r in results if r["status"] == "skipped"])
                error_count = len([r for r in results if r["status"] == "error"])
                
                # Create a nice summary for the current lecture
                result_summary = (
                    f"✅ Successfully processed {success_count} sections<br>"
                    f"⏭️ Skipped {skipped_count} sections (already exist)<br>"
                )
                
                if error_count > 0:
                    result_summary += f"❌ Encountered {error_count} errors<br>"
                else:
                    result_summary += "✨ No errors encountered<br>"
                
                latest_result_status.markdown(result_summary, unsafe_allow_html=True)
                
                # Small delay for UI updates
                time.sleep(0.1)
            
            # Complete the progress
            main_progress_bar.progress(1.0)
            current_task_status.success("Processing complete!")
            eta_display.empty()  # Clear the ETA display
            
            # Display final results
            with results_container:
                st.header("Final Processing Results")
                
                # Group results by status
                success_results = [r for r in all_results if r["status"] == "success"]
                skipped_results = [r for r in all_results if r["status"] == "skipped"]
                error_results = [r for r in all_results if r["status"] == "error"]
                
                # Calculate statistics
                total_processed = len(all_results)
                total_words_processed = sum(r.get("word_count", 0) for r in success_results)
                total_duration = sum(r.get("estimated_duration", 0) for r in success_results)
                
                # Display summary
                st.write(f"**Total processed:** {total_processed} sections")
                st.write(f"**Successfully converted:** {len(success_results)} sections")
                st.write(f"**Skipped (already exists):** {len(skipped_results)} sections")
                st.write(f"**Errors:** {len(error_results)} sections")
                st.write(f"**Total words processed:** ~{total_words_processed}")
                st.write(f"**Total estimated audio duration:** ~{total_duration:.2f} seconds (~{total_duration/60:.2f} minutes)")
                
                # Detailed Results
                if error_results:
                    with st.expander(f"Show Error Details ({len(error_results)})", expanded=True):
                        for result in error_results:
                            st.error(f"**Error:** {result['file_path']}\n{result['message']}")
                
                # Show successful conversions
                if success_results:
                    with st.expander(f"Show Successful Conversions ({len(success_results)})", expanded=False):
                        for result in success_results:
                            with st.container():
                                st.write(f"**File:** {os.path.basename(result['file_path'])}")
                                st.write(f"**Audio:** {os.path.basename(result['audio_path'])}")
                                
                                # Additional details
                                cols = st.columns(3)
                                with cols[0]:
                                    st.write(f"Format: {result.get('format', 'mp3')}")
                                with cols[1]:
                                    word_count = result.get("word_count", 0)
                                    st.write(f"Words: ~{word_count}")
                                with cols[2]:
                                    duration = result.get("estimated_duration", 0)
                                    st.write(f"Duration: ~{duration:.1f}s")
    else:
        st.info("Please select at least one lecture to process.")

def main():
    st.title("TTS - Open AI")
    st.write("Convert transcript sections to audio files using OpenAI's Text-to-Speech API.")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Create tabs for transcript and summary files
    tabs = st.tabs(["Transcript Files", "Summary Files"])
    
    # Tab 1: Transcript Files
    with tabs[0]:
        st.header("Transcript Files")
        st.write("Generate audio files from transcript sections in 'English text' folders.")
        display_tts_interface(summary_mode=False)
    
    # Tab 2: Summary Files
    with tabs[1]:
        st.header("Summary Files")
        st.write("Generate audio files from summary sections in 'English Summary text' folders.")
        display_tts_interface(summary_mode=True)

if __name__ == "__main__":
    main()