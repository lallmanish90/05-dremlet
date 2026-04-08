"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: LEGACY
PURPOSE: Older Kokoro TTS page retained for reference and backward compatibility.
MAIN INPUTS:
- section text files under lecture folders in `input/`
MAIN OUTPUTS:
- generated audio files for lecture narration
REQUIRED CONFIG / ASSETS:
- running Kokoro TTS service
EXTERNAL SERVICES:
- Kokoro API
HARDWARE ASSUMPTIONS:
- local machine dependent
REPLACED BY:
- `pages/07 Generate Audio with Kokoro.py`
"""

from dreamlet_cli.compat import st
import os
import re
import time
import json
import requests
from pathlib import Path
import glob
from typing import Dict, List, Tuple, Optional

# Local utility functions (moved from multiple utils modules)
def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def get_output_directory() -> str:
    """Get the path to the output directory"""
    return get_input_directory()

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def clean_text_for_tts(text: str) -> str:
    """Clean text for TTS processing"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[#*_~`]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_word_count(text: str) -> int:
    """Calculate the word count in a text"""
    cleaned_text = clean_text_for_tts(text)
    words = cleaned_text.split()
    return len(words)

def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate audio duration based on word count"""
    word_count = calculate_word_count(text)
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60

# Kokoro API integration functions
KOKORO_API_URL = "http://localhost:8880/v1"

def get_available_voices() -> List[Dict[str, str]]:
    """Get available voices from the Kokoro API"""
    try:
        response = requests.get(f"{KOKORO_API_URL}/audio/voices")
        voices_data = response.json()

        voice_list = []
        for voice_id in voices_data.get("voices", []):
            parts = voice_id.split('_')

            if len(parts) >= 2:
                language_code = parts[0]
                voice_name = parts[1]

                language_name = "English"
                gender = "Female"

                if language_code in {"am", "bm", "em", "hm", "im", "jm", "pm", "zm"}:
                    gender = "Male"

                if language_code in {"bf", "bm"}:
                    language_name = "British English"
                elif language_code in {"ef", "em"}:
                    language_name = "European English"
                elif language_code == "ff":
                    language_name = "French"
                elif language_code in {"hf", "hm"}:
                    language_name = "Hindi"
                elif language_code in {"if", "im"}:
                    language_name = "Italian"
                elif language_code in {"jf", "jm"}:
                    language_name = "Japanese"
                elif language_code in {"pf", "pm"}:
                    language_name = "Portuguese"
                elif language_code in {"zf", "zm"}:
                    language_name = "Chinese"

                description = f"{language_name} voice"

                voice_list.append({
                    "id": voice_id,
                    "name": voice_name.capitalize(),
                    "gender": gender,
                    "language": language_name,
                    "description": description,
                })

        return sorted(voice_list, key=lambda x: (x["language"], x["name"]))

    except Exception as e:
        st.error(f"Error retrieving voices from Kokoro API: {str(e)}")
        return []

def tts_cost_estimation(word_count: int, model: str = "kokoro") -> float:
    """Estimate cost for TTS processing (always returns 0 for local Kokoro TTS)"""
    return 0.0

def generate_combined_voice(voice_weights: Dict[str, float]) -> Tuple[bool, str, Optional[str]]:
    """Generate a combined voice string for direct use in TTS API"""
    if not voice_weights:
        return False, "No voices specified for combination", None

    try:
        voice_combination = "+".join([f"{voice}({int(weight)})" for voice, weight in voice_weights.items()])
        return True, "Voice combination created successfully", voice_combination

    except Exception as e:
        return False, f"Error in voice combination: {str(e)}", None

def convert_text_to_speech(
    text: str,
    output_path: str,
    voice: str = "af_bella",
    model: str = "kokoro",
    response_format: str = "mp3",
    speed: float = 1.0,
    enable_timestamps: bool = False,
    normalize_text: bool = True,
    save_timestamps: bool = False,
) -> Tuple[bool, str, Optional[Dict]]:
    """Convert text to speech using Kokoro's TTS API"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        params = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": response_format,
            "speed": speed,
            "normalization_options": {
                "normalize": normalize_text,
            },
        }

        if enable_timestamps:
            params["timestamps"] = True

        response = requests.post(
            f"{KOKORO_API_URL}/audio/speech",
            json=params,
        )

        if response.status_code != 200:
            return False, f"API request failed with status {response.status_code}: {response.text}", None

        timestamps = None
        if enable_timestamps and 'x-timestamps' in response.headers:
            try:
                timestamps = json.loads(response.headers['x-timestamps'])

                if save_timestamps:
                    timestamps_path = os.path.splitext(output_path)[0] + '.json'
                    with open(timestamps_path, 'w', encoding='utf-8') as f:
                        json.dump(timestamps, f, indent=2)
            except Exception as e:
                st.warning(f"Generated audio successfully, but could not parse timestamps: {str(e)}")

        with open(output_path, "wb") as f:
            f.write(response.content)

        return True, "Text-to-speech conversion successful", timestamps

    except Exception as e:
        return False, f"Error in text-to-speech conversion: {str(e)}", None

def check_connection() -> Tuple[bool, str]:
    """Check if the Kokoro API is accessible"""
    try:
        response = requests.get(f"{KOKORO_API_URL}/audio/voices", timeout=5)
        if response.status_code == 200:
            return True, "Connected to Kokoro API"
        else:
            return False, f"API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection error: Could not connect to Kokoro API (http://localhost:8880)"
    except requests.exceptions.Timeout:
        return False, "Connection timeout: Kokoro API did not respond in time"
    except Exception as e:
        return False, f"Error checking Kokoro API connection: {str(e)}"

def check_gpu_availability() -> Tuple[bool, str]:
    """Check if the Kokoro API is using GPU"""
    try:
        response = requests.get(f"{KOKORO_API_URL}/debug/system", timeout=5)
        if response.status_code == 200:
            system_info = response.json()
            if "gpu" in system_info and system_info["gpu"]:
                gpu_info = system_info["gpu"]
                if "devices" in gpu_info and gpu_info["devices"]:
                    gpu_devices = gpu_info["devices"]
                    return True, f"Using GPU: {gpu_devices[0].get('name', 'Unknown')} with {gpu_devices[0].get('memory_total', 'Unknown')} memory"
                return True, "GPU is available"
            return False, "No GPU detected, using CPU for inference"
        else:
            return False, "Could not determine GPU status"
    except Exception as e:
        return False, f"Error checking GPU status: {str(e)}"

st.set_page_config(page_title="08 TTS (Local) - Dreamlet", page_icon="📝")

def get_language_from_voice_id(voice_id: str) -> str:
    """
    Extract the language name from a voice ID
    
    Args:
        voice_id: Voice ID (e.g., 'af_bella', 'pm_antonio')
        
    Returns:
        The language name (e.g., 'English', 'Portuguese')
    """
    # Extract language code from voice ID
    if not voice_id or "_" not in voice_id:
        return "English"  # Default to English for invalid IDs
        
    language_code = voice_id.split('_')[0].lower()
    
    # Map language codes to language names
    language_map = {
        "af": "English",
        "am": "English",
        "bf": "British English",
        "bm": "British English",
        "ef": "European English",
        "em": "European English",
        "ff": "French",
        "fm": "French",
        "gf": "German",
        "gm": "German",
        "hf": "Hindi",
        "hm": "Hindi",
        "if": "Italian",
        "im": "Italian",
        "jf": "Japanese",
        "jm": "Japanese",
        "pf": "Portuguese",
        "pm": "Portuguese",
        "sf": "Spanish",
        "sm": "Spanish",
        "zf": "Chinese",
        "zm": "Chinese"
    }
    
    return language_map.get(language_code, "English")

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
                "text_dir": text_dir,
                "audio_dir": audio_dir
            }
    
    return organized_files

def generate_tts_for_sections(
    section_files: List[str],
    voice: str,
    model: str,
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
        response_format: Audio format (mp3, wav)
        speed: Speech speed (default: 1.0)
        normalize_text: Apply text normalization
        enable_timestamps: Generate word-level timestamps
        save_timestamps: Save timestamps to a JSON file alongside the audio
        
    Returns:
        List of processing results
    """
    results = []
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, section_file in enumerate(section_files):
        # Update progress
        progress = (i / len(section_files))
        progress_bar.progress(progress)
        status_text.text(f"Processing file {i+1}/{len(section_files)}: {os.path.basename(section_file)}")
        
        result = {
            "file": section_file,
            "status": "processing",
            "output_path": None,
            "success": False,
            "message": "",
            "word_count": 0,
            "processing_time": 0,
            "has_timestamps": False
        }
        
        try:
            # Read the text file
            with open(section_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                result["status"] = "skipped"
                result["message"] = "Empty file"
                results.append(result)
                continue
            
            # Clean the text
            cleaned_text = clean_text_for_tts(content)
            
            if not cleaned_text:
                result["status"] = "skipped"
                result["message"] = "No content after cleaning"
                results.append(result)
                continue
            
            # Calculate word count
            word_count = calculate_word_count(cleaned_text)
            result["word_count"] = word_count
            
            # Create output path
            # Text file is in "English text" or "English Summary text" folder
            section_dir = os.path.dirname(section_file)  # Text folder
            lecture_dir = os.path.dirname(section_dir)   # Lecture folder
            
            # Determine language from voice
            voice_language = "English"  # Default language
            
            # First check if it's a combined voice
            is_combined = "+" in voice
            
            if is_combined:
                # For combined voices, use the primary voice's language (first voice in combination)
                primary_voice = voice.split("+")[0].split("(")[0]
                voice_language = get_language_from_voice_id(primary_voice)
            else:
                # For single voice, get the language directly
                voice_language = get_language_from_voice_id(voice)
                
            # Determine if it's summary or regular text
            is_summary = "English Summary text" in section_dir
            
            # Create language-specific folder name
            folder_suffix = "Summary audio" if is_summary else "audio"
            audio_folder_name = f"{voice_language} {folder_suffix}"
            
            # Create the full audio directory path
            audio_dir = os.path.join(lecture_dir, audio_folder_name)
            
            # Create the audio directory if it doesn't exist
            if not os.path.exists(audio_dir):
                os.makedirs(audio_dir, exist_ok=True)
                
            # Save to the appropriate audio directory
            base_name = os.path.basename(section_file).replace('.txt', f'.{response_format}')
            output_path = os.path.join(audio_dir, base_name)
            result["output_path"] = output_path
            
            # Generate TTS
            start_time = time.time()
            success, message, timestamps = convert_text_to_speech(
                text=cleaned_text, 
                output_path=output_path, 
                voice=voice, 
                model=model,
                response_format=response_format,
                speed=speed,
                normalize_text=normalize_text,
                enable_timestamps=enable_timestamps,
                save_timestamps=save_timestamps
            )
            end_time = time.time()
            
            # Record result
            result["processing_time"] = end_time - start_time
            result["success"] = success
            result["message"] = message
            result["status"] = "completed" if success else "failed"
            result["has_timestamps"] = timestamps is not None
            
        except Exception as e:
            result["status"] = "failed"
            result["message"] = f"Error: {str(e)}"
            result["success"] = False
        
        results.append(result)
    
    # Complete progress bar
    progress_bar.progress(1.0)
    status_text.text("Processing complete")
    
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
    
    # Model selection (Kokoro only for now)
    col1, col2 = st.columns(2)
    
    with col1:
        selected_model = "kokoro"
        st.text("Model: Kokoro (Local)")
        st.caption("Running on local GPU with CUDA acceleration")
    
    # Get available voices
    available_voices = get_available_voices()
    voice_options = {v["id"]: f"{v['name']} ({v['gender']} - {v['language']})" for v in available_voices}
    
    # Voice selection
    with col2:
        voice_mode = st.radio(
            "Voice Selection Mode",
            options=["Single Voice", "Advanced (Voice Combination)"],
            index=0,
            key=f"voice_mode_{summary_mode}",
            help="Choose a single voice or combine multiple voices with weights"
        )
    
    if voice_mode == "Single Voice":
        # Find the index of "af_heart" if it exists
        heart_index = 0
        if "af_heart" in voice_options:
            heart_index = list(voice_options.keys()).index("af_heart")
        
        selected_voice = st.selectbox(
            "Select Voice",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
            index=heart_index,
            key=f"voice_{summary_mode}"
        )
        combined_voice_name = None
    else:
        st.subheader("Voice Combination")
        st.write("Combine multiple voices with different weights. Total weights will be normalized to 100%.")
        
        # Create a container for voice combination
        voice_combination_container = st.container()
        
        voice_weights_key = f"voice_weights_{summary_mode}"
        
        with voice_combination_container:
            # Initialize voice weights in session state if needed
            if voice_weights_key not in st.session_state:
                # Initialize with "af_heart" (Heart) if available, or first voice as fallback
                if "af_heart" in voice_options:
                    st.session_state[voice_weights_key] = {"af_heart": 1}
                else:
                    first_voice = list(voice_options.keys())[0] if voice_options else "af_bella"
                    st.session_state[voice_weights_key] = {first_voice: 1}
            
            # Function to add a new voice
            def add_voice():
                # Find a voice that's not already in the list
                for voice_id in voice_options.keys():
                    if voice_id not in st.session_state[voice_weights_key]:
                        st.session_state[voice_weights_key][voice_id] = 1
                        break
            
            # Function to remove a voice
            def remove_voice(voice_id):
                if voice_id in st.session_state[voice_weights_key]:
                    del st.session_state[voice_weights_key][voice_id]
            
            # Display all selected voices with weights
            for i, (voice_id, weight) in enumerate(list(st.session_state[voice_weights_key].items())):
                cols = st.columns([3, 1, 0.5])
                with cols[0]:
                    new_voice = st.selectbox(
                        f"Voice {i+1}",
                        options=list(voice_options.keys()),
                        format_func=lambda x: voice_options[x],
                        key=f"voice_{i}_{summary_mode}",
                        index=list(voice_options.keys()).index(voice_id)
                    )
                
                with cols[1]:
                    new_weight = st.number_input(
                        f"Weight {i+1}",
                        min_value=1,
                        max_value=10,
                        value=weight,
                        key=f"weight_{i}_{summary_mode}"
                    )
                
                with cols[2]:
                    if len(st.session_state[voice_weights_key]) > 1:  # Only show remove button if there's more than one voice
                        st.button("❌", key=f"remove_{i}_{summary_mode}", on_click=remove_voice, args=(voice_id,))
                
                # Update the voice and weight in session state
                if voice_id in st.session_state[voice_weights_key]:
                    del st.session_state[voice_weights_key][voice_id]
                st.session_state[voice_weights_key][new_voice] = new_weight
            
            # Button to add more voices
            if len(st.session_state[voice_weights_key]) < len(voice_options):
                st.button("Add Voice", on_click=add_voice, key=f"add_voice_{summary_mode}")
        
        # Show the final voice combination
        total_weight = sum(st.session_state[voice_weights_key].values())
        st.write("Final Voice Combination:")
        
        for voice_id, weight in st.session_state[voice_weights_key].items():
            percentage = (weight / total_weight) * 100
            st.write(f"- {voice_options[voice_id]}: {percentage:.1f}%")
        
        # Button to create a combined voice
        if st.button("Use Combined Voice", key=f"use_combined_{summary_mode}"):
            with st.spinner("Creating voice combination..."):
                # Generate the combined voice string directly
                success, message, combined_voice = generate_combined_voice(st.session_state[voice_weights_key])
                
                if success:
                    selected_voice = combined_voice
                    
                    # Show a preview of the voice combination
                    weighted_voices = []
                    total_weight = sum(st.session_state[voice_weights_key].values())
                    
                    for voice_id, weight in st.session_state[voice_weights_key].items():
                        percentage = (weight / total_weight) * 100
                        voice_name = voice_options[voice_id].split(' (')[0] 
                        weighted_voices.append(f"{voice_name} ({percentage:.1f}%)")
                    
                    weighted_voice_str = ", ".join(weighted_voices)
                    st.success(f"Voice combination created: {weighted_voice_str}")
                else:
                    st.error(message)
                    # Fall back to the first voice
                    selected_voice = list(st.session_state[voice_weights_key].keys())[0]
        else:
            # Use the combined voice string directly
            success, _, combined_voice = generate_combined_voice(st.session_state[voice_weights_key])
            if success:
                selected_voice = combined_voice
            else:
                # Use the first voice as a fallback
                selected_voice = list(st.session_state[voice_weights_key].keys())[0]
    
    # Audio format and settings
    audio_col1, audio_col2 = st.columns(2)
    
    with audio_col1:
        response_format = st.selectbox(
            "Audio Format",
            options=["mp3", "wav", "opus", "flac"],
            index=0,
            key=f"format_{summary_mode}",
            help="Select output audio format"
        )
    
    with audio_col2:
        speed = st.slider(
            "Speech Speed",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key=f"speed_{summary_mode}",
            help="Adjust the speaking rate (1.0 is normal speed)"
        )
    
    # Advanced options
    with st.expander("Advanced Options", expanded=False):
        st.subheader("Text Processing")
        normalize_text = st.checkbox(
            "Enable Text Normalization", 
            value=True,
            key=f"normalize_{summary_mode}",
            help="Normalize input text before processing (recommended). Disable if you notice missing words or phrases."
        )
        
        st.subheader("Timestamp Generation")
        enable_timestamps = st.checkbox(
            "Generate Word Timestamps", 
            value=False,
            key=f"timestamps_{summary_mode}",
            help="Generate word-level timestamps for the audio"
        )
        
        save_timestamps = st.checkbox(
            "Save Timestamps to JSON", 
            value=False, 
            key=f"save_timestamps_{summary_mode}",
            disabled=not enable_timestamps,
            help="Save timestamp data to a JSON file alongside the audio"
        )
    
    # Section Selection
    st.header("Select Sections for TTS")
    
    # Create organized selection interface with expandable sections
    selected_lectures = {}
    
    # Sort courses numerically
    sorted_courses = sorted(
        organized_files.keys(),
        key=lambda x: int(re.search(r'\d+', x).group(0)) if re.search(r'\d+', x) else 999
    )
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}", expanded=True):
            # Add "Select All" checkbox for this course
            all_in_course = st.checkbox(f"Select All in {course}", key=f"all_{course}_{summary_mode}")
            
            # Sort lectures numerically
            sorted_lectures = sorted(
                organized_files[course].keys(),
                key=lambda x: int(re.search(r'\d+', x).group(0)) if re.search(r'\d+', x) else 999
            )
            
            for lecture in sorted_lectures:
                st.write(f"**{lecture}**")
                
                # Get lecture data
                lecture_data = organized_files[course][lecture]
                section_files = lecture_data["section_files"]
                
                # Calculate word count and cost estimate
                total_words = 0
                for section_file in section_files:
                    try:
                        with open(section_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        cleaned_text = clean_text_for_tts(content)
                        total_words += calculate_word_count(cleaned_text)
                    except Exception:
                        continue
                
                # For local TTS, cost is always 0
                estimated_cost = tts_cost_estimation(total_words, model=selected_model)
                
                st.write(f"**{lecture}:** {len(section_files)} sections, ~{total_words} words")
                st.caption("Cost: Free (Local Processing)")
                
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
        
        # Calculate total words
        total_words = 0
        for lecture_data in selected_lectures.values():
            for section_file in lecture_data["section_files"]:
                try:
                    with open(section_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    cleaned_text = clean_text_for_tts(content)
                    total_words += calculate_word_count(cleaned_text)
                except Exception:
                    continue
        
        # Estimate processing time (rough estimate: 5 words per second)
        estimated_processing_time = total_words / 5
        
        # Show processing details
        st.write(f"**Selected:** {len(selected_lectures)} lectures, {total_sections} sections, {total_words} words")
        st.write(f"**Estimated processing time:** ~{estimated_processing_time:.1f} seconds")
        
        # Process button
        if st.button("Process Selected Sections", key=f"process_{summary_mode}"):
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
                
                # Get section files
                section_files = lecture_data["section_files"]
                
                # Process this lecture
                # Ensure voice is a string (not None)
                voice_to_use = selected_voice if selected_voice is not None else "af_bella"
                
                results = generate_tts_for_sections(
                    section_files=section_files,
                    voice=voice_to_use,
                    model=selected_model,
                    response_format=response_format,
                    speed=speed,
                    normalize_text=normalize_text,
                    enable_timestamps=enable_timestamps,
                    save_timestamps=save_timestamps
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
                completed_count = len([r for r in results if r["status"] == "completed"])
                skipped_count = len([r for r in results if r["status"] == "skipped"])
                failed_count = len([r for r in results if r["status"] == "failed"])
                
                # Create a nice summary for the current lecture
                result_summary = (
                    f"✅ Successfully processed {completed_count} sections<br>"
                    f"⏭️ Skipped {skipped_count} sections (already exist)<br>"
                )
                
                if failed_count > 0:
                    result_summary += f"❌ Failed to process {failed_count} sections<br>"
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
                
                # Calculate statistics
                completed = [r for r in all_results if r["status"] == "completed"]
                skipped = [r for r in all_results if r["status"] == "skipped"]
                failed = [r for r in all_results if r["status"] == "failed"]
                
                # Display summary
                st.write(f"**Total processed:** {len(all_results)} sections")
                st.write(f"**Successfully completed:** {len(completed)} sections")
                st.write(f"**Skipped:** {len(skipped)} sections")
            st.write(f"**Failed:** {len(failed)} sections")
            
            # Show failed items
            if failed:
                with st.expander("Show Failed Items", expanded=True):
                    for result in failed:
                        st.error(f"**{os.path.basename(result['file'])}:** {result['message']}")
            
            # Show processing times
            if completed:
                total_processing_time = sum(r["processing_time"] for r in completed)
                average_processing_time = total_processing_time / len(completed)
                total_words_processed = sum(r["word_count"] for r in completed)
                
                st.write(f"**Total processing time:** {total_processing_time:.2f} seconds")
                st.write(f"**Average processing time per file:** {average_processing_time:.2f} seconds")
                st.write(f"**Total words processed:** {total_words_processed}")
                
                # Calculate words per second
                if total_processing_time > 0:
                    words_per_second = total_words_processed / total_processing_time
                    st.write(f"**Processing speed:** {words_per_second:.2f} words per second")
    else:
        st.info("Please select at least one lecture to process.")

def main():
    st.title("TTS Kokoro - old")
    st.write("Convert transcript sections to audio files using local Kokoro Text-to-Speech API.")
    
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
