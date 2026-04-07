import streamlit as st
import os
import re
import time
import json
from pathlib import Path
import glob
from typing import Dict, List, Tuple, Optional

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
from utils.kokoro_integration import (
    get_available_voices,
    tts_cost_estimation,
    convert_text_to_speech,
    generate_combined_voice,
    check_connection,
    check_gpu_availability
)

st.set_page_config(page_title="07 TTS Kokoro - Multi-Language", page_icon="📝")

# Language code mapping for voice IDs
LANGUAGE_MAP = {
    "af": "English",
    "am": "English",
    "bf": "British English",
    "bm": "British English",
    "ef": "European English",
    "em": "European English",
    "ff": "French",
    "fm": "French",
    "df": "German", 
    "dm": "German",
    "cf": "Chinese",
    "cm": "Chinese",
    "if": "Italian",
    "im": "Italian", 
    "pf": "Portuguese",
    "pm": "Portuguese",
    "sf": "Spanish",
    "sm": "Spanish",
    "rf": "Russian",
    "rm": "Russian",
    "jf": "Japanese",
    "jm": "Japanese",
    "kf": "Korean",
    "km": "Korean",
    "hf": "Hindi",
    "hm": "Hindi",
    "nf": "Dutch",
    "nm": "Dutch",
    "tf": "Turkish",
    "tm": "Turkish",
    "af": "English",
    "am": "English"
}

def get_language_from_voice_id(voice_id: str) -> str:
    """
    Extract the language name from a voice ID
    
    Args:
        voice_id: Voice ID (e.g., 'af_bella', 'pm_antonio')
        
    Returns:
        The language name (e.g., 'English', 'Portuguese')
    """
    prefix = voice_id.split('_')[0]
    return LANGUAGE_MAP.get(prefix, "Unknown")

def get_voices_by_language():
    """
    Group available voices by language to make selection easier
    
    Returns:
        Dict mapping language names to lists of voice dictionaries
    """
    all_voices = get_available_voices()
    languages = {}
    
    for voice in all_voices:
        language = get_language_from_voice_id(voice["id"])
        if language not in languages:
            languages[language] = []
        languages[language].append(voice)
    
    return languages

def find_language_section_files(language: str = "English") -> Dict[str, Dict[str, Dict]]:
    """
    Find all section files for a specific language created by the previous step
    
    Args:
        language: The language to find files for (default: "English")
        
    Returns:
        Nested dictionary of course -> lecture -> section files with type indicators
    """
    input_dir = get_input_directory()
    language_files = {}
    
    # Get all course directories (can be any name now, not just numeric)
    course_dirs = glob.glob(os.path.join(input_dir, "*"))
    course_dirs = [d for d in course_dirs if os.path.isdir(d)]
    
    for course_dir in course_dirs:
        course_name = os.path.basename(course_dir)
        
        # Get all lecture directories (any name containing 'Lecture')
        lecture_dirs = glob.glob(os.path.join(course_dir, "*Lecture*"))
        if not lecture_dirs:
            # If no 'Lecture' folders found, try all subdirectories
            lecture_dirs = glob.glob(os.path.join(course_dir, "*"))
            lecture_dirs = [d for d in lecture_dirs if os.path.isdir(d)]
        
        for lecture_dir in lecture_dirs:
            lecture_name = os.path.basename(lecture_dir)
            
            # Check for language-specific transcript folder
            transcript_folder = f"{language} text"
            transcript_dir = os.path.join(lecture_dir, transcript_folder)
            
            # Check for language-specific summary folder
            summary_folder = f"{language} Summary text"
            summary_dir = os.path.join(lecture_dir, summary_folder)
            
            transcript_files = []
            summary_files = []
            
            # Get transcript section files if folder exists
            if os.path.exists(transcript_dir):
                # Try numbered files first, then any .txt files
                transcript_files = glob.glob(os.path.join(transcript_dir, "[0-9]*.txt"))
                if not transcript_files:
                    transcript_files = glob.glob(os.path.join(transcript_dir, "*.txt"))
                transcript_files.sort()
            
            # Get summary section files if folder exists
            if os.path.exists(summary_dir):
                # Try numbered files first, then any .txt files
                summary_files = glob.glob(os.path.join(summary_dir, "[0-9]*.txt"))
                if not summary_files:
                    summary_files = glob.glob(os.path.join(summary_dir, "*.txt"))
                summary_files.sort()
            
            # Add to results if there are files for this lecture
            if transcript_files or summary_files:
                if course_name not in language_files:
                    language_files[course_name] = {}
                
                language_files[course_name][lecture_name] = {
                    "base_dir": lecture_dir,
                    "transcript": {
                        "dir": transcript_dir if os.path.exists(transcript_dir) else None,
                        "section_files": transcript_files
                    },
                    "summary": {
                        "dir": summary_dir if os.path.exists(summary_dir) else None,
                        "section_files": summary_files
                    }
                }
    
    return language_files

def generate_tts_for_sections(
    section_files: List[str],
    voice: str,
    model: str,
    output_dir: str,
    response_format: str = "mp3",
    speed: float = 1.0,
    normalize_text: bool = True,
    enable_timestamps: bool = False,
    save_timestamps: bool = False
) -> List[Dict]:
    """
    Generate TTS for a list of section files
    
    Args:
        section_files: List of section file paths
        voice: Voice to use for TTS
        model: Model to use for TTS (kokoro)
        output_dir: Directory to save audio files
        response_format: Audio format (mp3, wav)
        speed: Speech speed (default: 1.0)
        normalize_text: Apply text normalization
        enable_timestamps: Generate word-level timestamps
        save_timestamps: Save timestamps to a JSON file alongside the audio
        
    Returns:
        List of processing results
    """
    results = []
    
    for file_path in section_files:
        # Extract section number from filename
        section_file = os.path.basename(file_path)
        section_number = os.path.splitext(section_file)[0]
        
        # Determine output filename
        output_filename = f"{section_number}.{response_format}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Skip if output already exists and is not empty
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            results.append({
                "success": True,
                "file": file_path,
                "output": output_path,
                "status": "skipped",
                "message": "Output file already exists",
                "processing_time": 0,
                "word_count": 0
            })
            continue
        
        # Read the content of the section file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean the text
            if normalize_text:
                content = clean_text_for_tts(content)
            
            # Skip empty files
            if not content.strip():
                results.append({
                    "success": True,
                    "file": file_path,
                    "output": output_path,
                    "status": "skipped",
                    "message": "Empty or whitespace-only file",
                    "processing_time": 0,
                    "word_count": 0
                })
                continue
            
            # Count words for statistics
            word_count = calculate_word_count(content)
            
            # Start timing
            start_time = time.time()
            
            # Generate speech from text
            result = convert_text_to_speech(
                text=content,
                voice=voice,
                model=model,
                output_path=output_path,
                response_format=response_format,
                speed=speed,
                enable_timestamps=enable_timestamps
            )
            
            # Stop timing
            processing_time = time.time() - start_time
            
            if result["success"]:
                # Save timestamps if requested
                if enable_timestamps and save_timestamps and "timestamps" in result:
                    timestamps_path = f"{os.path.splitext(output_path)[0]}.json"
                    with open(timestamps_path, 'w', encoding='utf-8') as f:
                        json.dump(result["timestamps"], f, indent=2)
                
                # Add additional statistics
                result["processing_time"] = processing_time
                result["word_count"] = word_count
                result["output"] = output_path
                result["status"] = "processed"
                
                # Add to results list
                results.append(result)
            else:
                # Add failure information
                result["file"] = file_path
                result["processing_time"] = processing_time
                result["word_count"] = word_count
                result["status"] = "failed"
                results.append(result)
        
        except Exception as e:
            # Handle any other exceptions
            results.append({
                "success": False,
                "file": file_path,
                "status": "failed",
                "message": f"Error: {str(e)}",
                "processing_time": 0,
                "word_count": 0
            })
    
    return results

def main():
    st.title("TTS Kokoro")
    st.write("Convert transcript and summary sections to audio files using local Kokoro Text-to-Speech API.")
    
    # Check for Kokoro API connection
    connection_status, connection_message = check_connection()
    
    if not connection_status:
        st.error(f"Cannot connect to Kokoro API: {connection_message}")
        st.info("Please ensure the Kokoro TTS server is running at http://localhost:8880")
        return
    
    # Check GPU availability
    gpu_available, gpu_message = check_gpu_availability()
    if gpu_available:
        st.success(f"🚀 {gpu_message}")
    else:
        st.warning(f"💻 {gpu_message} - Processing may be slower")
        st.info("For better performance, ensure CUDA and PyTorch GPU support are properly configured")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Get available voices and organize by language
    voices_by_language = get_voices_by_language()
    all_voices = get_available_voices()
    
    # Create mapping of voice_id to voice display name
    voice_options = {v["id"]: f"{v['name']} ({v['gender']})" for v in all_voices}
    
    # List of supported languages (only those with available voices)
    supported_languages = [lang for lang in voices_by_language.keys() if voices_by_language[lang]]
    
    # Model and format settings
    selected_model = "kokoro"
    st.header("TTS Settings")
    st.info("Using Kokoro Text-to-Speech (Local) with GPU acceleration")
    
    # Initialize session state for language settings if not already present
    if "language_settings" not in st.session_state:
        # Start with an empty dictionary - user will select languages directly
        st.session_state.language_settings = {}
    
    # STEP 1: Language Selection
    st.subheader("1️⃣ Select Languages")
    st.write("Choose which languages you want to process. Only languages with available voices are shown.")
    
    # Create a grid of checkboxes for language selection
    language_cols = st.columns(3)
    selected_languages = []
    
    for i, lang in enumerate(supported_languages):
        with language_cols[i % 3]:
            is_selected = st.checkbox(
                lang, 
                value=lang in st.session_state.language_settings,
                key=f"lang_select_{lang}"
            )
            
            if is_selected:
                selected_languages.append(lang)
    
    # Sync language settings based on selected languages
    # Add new languages
    for lang in selected_languages:
        if lang not in st.session_state.language_settings:
            # Find a suitable default voice for this language
            lang_voices = voices_by_language.get(lang, [])
            default_voice = lang_voices[0]["id"] if lang_voices else list(voice_options.keys())[0]
            
            # Add the language with default settings
            st.session_state.language_settings[lang] = {
                "voice": default_voice,
                "speed": 1.0,
                "normalize": True
            }
    
    # Remove deselected languages
    for lang in list(st.session_state.language_settings.keys()):
        if lang not in selected_languages:
            del st.session_state.language_settings[lang]
    
    # STEP 2: Common Settings
    st.subheader("2️⃣ Common Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        audio_format = st.selectbox(
            "Audio Format",
            options=["mp3", "wav"],
            index=0,
            key="audio_format",
            help="Select audio output format for all languages"
        )
    
    with col2:
        generate_timestamps = st.checkbox(
            "Generate Word Timestamps",
            value=False,
            key="generate_timestamps",
            help="Generate timing information for all languages"
        )
        
        save_timestamps = False
        if generate_timestamps:
            save_timestamps = st.checkbox(
                "Save Timestamps to JSON",
                value=True,
                key="save_timestamps",
                help="Save word timing information for all languages"
            )
    
    # STEP 3: Language-Specific Settings
    if st.session_state.language_settings:
        st.subheader("3️⃣ Language-Specific Settings")
        
        # Display all configured languages
        for language, settings in list(st.session_state.language_settings.items()):
            with st.expander(f"{language} Settings", expanded=True):
                # Get available voices for this language
                language_voice_options = {}
                for voice in voices_by_language.get(language, []):
                    language_voice_options[voice["id"]] = f"{voice['name']} ({voice['gender']})"
                
                # If no voices available for this language, use all voices
                if not language_voice_options:
                    language_voice_options = voice_options
                
                # Find the index of the currently selected voice
                voice_options_list = list(language_voice_options.keys())
                selected_index = 0
                
                if settings["voice"] in voice_options_list:
                    selected_index = voice_options_list.index(settings["voice"])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    voice = st.selectbox(
                        f"Voice",
                        options=voice_options_list,
                        format_func=lambda x: language_voice_options[x],
                        index=selected_index,
                        key=f"voice_{language}"
                    )
                    st.session_state.language_settings[language]["voice"] = voice
                
                with col2:
                    speed = st.slider(
                        f"Speed",
                        min_value=0.5,
                        max_value=2.0,
                        value=settings["speed"],
                        step=0.1,
                        key=f"speed_{language}"
                    )
                    st.session_state.language_settings[language]["speed"] = speed
                
                normalize = st.checkbox(
                    "Normalize Text", 
                    value=settings["normalize"],
                    key=f"normalize_{language}",
                    help="Convert numbers, dates, etc. to spoken form"
                )
                st.session_state.language_settings[language]["normalize"] = normalize
    
    # STEP 4: Process Button
    st.subheader("4️⃣ Process Selected Languages")
    if st.button("Process Selected Languages", type="primary", key="process_languages"):
        # Get list of selected languages
        enabled_languages = list(st.session_state.language_settings.keys())
        
        if not enabled_languages:
            st.error("No languages selected. Please select at least one language.")
        else:
            # Progress tracking
            main_progress_container = st.container()
            with main_progress_container:
                main_progress_bar = st.progress(0)
                main_stats = st.empty()
                eta_display = st.empty()
            
            # Current language status
            language_status_container = st.container()
            
            # Results accumulator
            all_language_results = {}
            
            # Track overall progress across all languages
            total_languages = len(enabled_languages)
            processed_languages = 0
            
            # Overall start time
            overall_start_time = time.time()
            
            st.info(f"Processing {total_languages} languages: {', '.join(enabled_languages)}")
            
            # Process each selected language
            for language in enabled_languages:
                # Language settings
                lang_settings = st.session_state.language_settings[language]
                
                with language_status_container:
                    st.subheader(f"Processing {language}")
                    language_progress = st.progress(0)
                    language_status = st.empty()
                
                # Find files for this language
                language_files = find_language_section_files(language=language)
                
                if not language_files:
                    language_status.warning(f"No files found for {language}. Skipping.")
                    continue
                
                # Create results container for this language
                language_results = []
                
                # Count total sections for this language
                total_sections = 0
                for course, lectures in language_files.items():
                    for lecture, lecture_data in lectures.items():
                        total_sections += len(lecture_data["transcript"]["section_files"])
                        total_sections += len(lecture_data["summary"]["section_files"])
                
                # Track processed sections for this language
                processed_sections = 0
                
                # Language start time
                language_start_time = time.time()
                
                # Process each lecture for this language
                for course, lectures in language_files.items():
                    for lecture, lecture_data in lectures.items():
                        # Update status
                        language_status.info(f"Processing {course} - {lecture}")
                        
                        # Create audio directories for this language
                        lecture_base_dir = lecture_data["base_dir"]
                        
                        # For transcript files
                        transcript_audio_folder = f"{language} audio"
                        transcript_audio_dir = os.path.join(lecture_base_dir, transcript_audio_folder)
                        os.makedirs(transcript_audio_dir, exist_ok=True)
                        
                        # For summary files
                        summary_audio_folder = f"{language} Summary audio"
                        summary_audio_dir = os.path.join(lecture_base_dir, summary_audio_folder)
                        os.makedirs(summary_audio_dir, exist_ok=True)
                        
                        # Process transcript files
                        if lecture_data["transcript"]["section_files"]:
                            transcript_results = generate_tts_for_sections(
                                section_files=lecture_data["transcript"]["section_files"],
                                voice=lang_settings["voice"],
                                model=selected_model,
                                output_dir=transcript_audio_dir,
                                response_format=audio_format,
                                speed=lang_settings["speed"],
                                normalize_text=lang_settings["normalize"],
                                enable_timestamps=generate_timestamps,
                                save_timestamps=save_timestamps
                            )
                            language_results.extend(transcript_results)
                            processed_sections += len(transcript_results)
                        
                        # Process summary files
                        if lecture_data["summary"]["section_files"]:
                            summary_results = generate_tts_for_sections(
                                section_files=lecture_data["summary"]["section_files"],
                                voice=lang_settings["voice"],
                                model=selected_model,
                                output_dir=summary_audio_dir,
                                response_format=audio_format,
                                speed=lang_settings["speed"],
                                normalize_text=lang_settings["normalize"],
                                enable_timestamps=generate_timestamps,
                                save_timestamps=save_timestamps
                            )
                            language_results.extend(summary_results)
                            processed_sections += len(summary_results)
                        
                        # Update language progress
                        language_progress.progress(processed_sections / total_sections)
                        
                        # Calculate ETA for this language
                        elapsed_language_time = time.time() - language_start_time
                        if processed_sections > 0:
                            sections_per_second = processed_sections / elapsed_language_time
                            remaining_sections = total_sections - processed_sections
                            eta_seconds = remaining_sections / sections_per_second if sections_per_second > 0 else 0
                            minutes, seconds = divmod(int(eta_seconds), 60)
                            language_status.text(f"Progress: {processed_sections}/{total_sections} sections. ETA: {minutes}m {seconds}s")
                
                # Language complete
                language_progress.progress(1.0)
                language_status.success(f"{language} processing complete: {processed_sections} sections processed")
                
                # Store results for this language
                all_language_results[language] = language_results
                
                # Update overall progress
                processed_languages += 1
                main_progress_bar.progress(processed_languages / total_languages)
                
                # Calculate overall ETA
                elapsed_overall_time = time.time() - overall_start_time
                if processed_languages > 0:
                    languages_per_second = processed_languages / elapsed_overall_time
                    remaining_languages = total_languages - processed_languages
                    eta_overall_seconds = remaining_languages / languages_per_second if languages_per_second > 0 else 0
                    eta_minutes, eta_seconds = divmod(int(eta_overall_seconds), 60)
                    main_stats.text(f"Overall progress: {processed_languages}/{total_languages} languages. ETA: {eta_minutes}m {eta_seconds}s")
            
            # All languages processed
            main_progress_bar.progress(1.0)
            main_stats.success(f"All {total_languages} languages processed successfully!")
            
            # Display results summary
            st.header("Processing Results")
            
            for language, results in all_language_results.items():
                with st.expander(f"{language} Results"):
                    # Count successes and failures
                    success_count = sum(1 for r in results if r["success"])
                    failure_count = sum(1 for r in results if not r["success"])
                    total_count = len(results)
                    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
                    
                    # Calculate total words and processing time
                    total_words = sum(r["word_count"] for r in results if "word_count" in r)
                    total_processing_time = sum(r["processing_time"] for r in results if "processing_time" in r)
                    
                    # Average processing speed
                    words_per_second = total_words / total_processing_time if total_processing_time > 0 else 0
                    
                    # Display summary
                    st.write(f"**Summary for {language}:**")
                    st.write(f"- Processed: {success_count}/{total_count} files ({success_rate:.1f}% success rate)")
                    st.write(f"- Total words: {total_words:,}")
                    st.write(f"- Total processing time: {total_processing_time:.2f} seconds")
                    st.write(f"- Average speed: {words_per_second:.1f} words per second")
                    
                    # Display failures if any
                    if failure_count > 0:
                        st.write("**Failed files:**")
                        for result in results:
                            if not result["success"]:
                                st.error(f"{os.path.basename(result['file'])}: {result['message']}")
            
            # Overall summary
            st.subheader("Overall Summary")
            total_files = sum(len(results) for results in all_language_results.values())
            total_successes = sum(sum(1 for r in results if r["success"]) for results in all_language_results.values())
            overall_success_rate = (total_successes / total_files) * 100 if total_files > 0 else 0
            
            st.write(f"- Total languages processed: {total_languages}")
            st.write(f"- Total files processed: {total_files}")
            st.write(f"- Overall success rate: {overall_success_rate:.1f}%")
            st.write(f"- Total processing time: {(time.time() - overall_start_time):.2f} seconds")

if __name__ == "__main__":
    main()