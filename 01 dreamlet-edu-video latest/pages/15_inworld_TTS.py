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
import requests
import base64
import fnmatch
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
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'__(.*?)__', r'\1', text)      # Underline
    text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # URLs
    text = re.sub(r'<.*?>', '', text)             # HTML tags
    text = re.sub(r'[#*_~`]', ' ', text)          # Special characters
    text = re.sub(r'\s+', ' ', text).strip()      # Normalize whitespace
    return text

def calculate_word_count(text: str) -> int:
    """Calculate the word count in a text"""
    cleaned_text = clean_text_for_tts(text)
    words = cleaned_text.split()
    return len(words)

def calculate_character_count(text: str) -> int:
    """Calculate the character count in a text"""
    cleaned_text = clean_text_for_tts(text)
    return len(cleaned_text)

def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate audio duration based on word count"""
    word_count = calculate_word_count(text)
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60

# Inworld API integration functions
INWORLD_API_URL = "https://api.inworld.ai/tts/v1/voice"

def get_api_key() -> Optional[str]:
    """Get Inworld API key - hardcoded for local internal project"""
    return "default-fs1qvbalzzasjvt87bghow"

def get_api_credentials() -> str:
    """Get Base64 encoded API credentials for authentication"""
    return "OWVPRldLYmMzemNxcGdHNmNLdGJkZ0toYUNLb3hEN2I6Y3FSWnp3OVAwd2E5bXBVbXRPVHh5YXpJYXp0aE9RZGo3ZlBRNlRmYktxaXNjSVdJV3V6RHFvYWNtWFcybjhFTw=="

def get_available_voices() -> List[Dict[str, str]]:
    """Get available voices for Inworld TTS"""
    # For now, return the default voice provided
    # This can be expanded later if Inworld provides a voices endpoint
    return [
        {
            "id": "default-fs1qvbalzzasjvt87bghow__manish_7",
            "name": "Manish 7",
            "gender": "Male",
            "language": "English",
            "description": "Default English voice"
        }
    ]

def tts_cost_estimation(character_count: int) -> float:
    """Estimate cost for TTS processing based on character count"""
    # Typical cloud TTS pricing is around $4-16 per 1M characters
    # Using conservative estimate of $10 per 1M characters
    cost_per_million_chars = 10.0
    estimated_cost = (character_count / 1_000_000) * cost_per_million_chars
    return estimated_cost

def convert_text_to_speech(
    text: str, 
    output_path: str, 
    voice_id: str = "default-fs1qvbalzzasjvt87bghow__manish_7",
    response_format: str = "mp3",
    speaking_rate: float = 0.85,
    temperature: float = 0.75,
    normalize_text: bool = True
) -> Tuple[bool, str, Optional[Dict]]:
    """Convert text to speech using Inworld's TTS API"""
    try:
        # Get API key
        api_key = get_api_key()
        if not api_key:
            return False, "API key not available", None
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Clean text if requested
        if normalize_text:
            text = clean_text_for_tts(text)
        
        # Prepare headers with Base64 encoded credentials
        headers = {
            "Authorization": f"Basic {get_api_credentials()}",
            "Content-Type": "application/json"
        }
        
        # Prepare payload
        audio_encoding = "MP3" if response_format.lower() == "mp3" else "WAV"
        payload = {
            "text": text,
            "voice_id": voice_id,
            "audio_config": {
                "audio_encoding": audio_encoding,
                "speaking_rate": speaking_rate
            },
            "temperature": temperature,
            "model_id": "inworld-tts-1-max"
        }
        
        # Make API request with timeout
        try:
            response = requests.post(INWORLD_API_URL, json=payload, headers=headers, timeout=30)
        except requests.exceptions.Timeout:
            return False, "API request timed out after 30 seconds", None
        except requests.exceptions.ConnectionError:
            return False, "Connection error to Inworld API", None
        
        if response.status_code != 200:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_detail = response.json()
                if "error" in error_detail:
                    error_msg += f": {error_detail['error']}"
                elif "message" in error_detail:
                    error_msg += f": {error_detail['message']}"
            except:
                error_msg += f": {response.text[:200]}"  # Limit error text
            return False, error_msg, None
        
        # Parse response
        try:
            result = response.json()
        except json.JSONDecodeError:
            return False, f"Invalid JSON response from API: {response.text[:200]}", None
            
        if "audioContent" not in result:
            return False, f"No audio content in API response. Response keys: {list(result.keys())}", None
        
        # Decode and save audio content
        try:
            audio_content = base64.b64decode(result['audioContent'])
            with open(output_path, "wb") as f:
                f.write(audio_content)
        except Exception as e:
            return False, f"Error saving audio file: {str(e)}", None
        
        return True, "Text-to-speech conversion successful", None
    
    except Exception as e:
        return False, f"Error in text-to-speech conversion: {str(e)}", None

def test_api_simple() -> Tuple[bool, str]:
    """Test API with a very simple request"""
    try:
        headers = {
            "Authorization": f"Basic {get_api_credentials()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": "Hello world",
            "voice_id": "default-fs1qvbalzzasjvt87bghow__manish_7",
            "audio_config": {
                "audio_encoding": "MP3",
                "speaking_rate": 0.85
            },
            "temperature": 0.75,
            "model_id": "inworld-tts-1-max"
        }
        
        response = requests.post(INWORLD_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if "audioContent" in result:
                return True, f"API test successful - received {len(result['audioContent'])} characters of audio data"
            else:
                return False, f"API responded but no audioContent. Keys: {list(result.keys())}"
        else:
            return False, f"API test failed: {response.status_code} - {response.text[:200]}"
            
    except Exception as e:
        return False, f"API test error: {str(e)}"

def check_connection() -> Tuple[bool, str]:
    """Check if the Inworld API is accessible"""
    try:
        api_key = get_api_key()
        if not api_key:
            return False, "API key not available"
        
        # Test with a minimal request
        headers = {
            "Authorization": f"Basic {get_api_credentials()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": "test",
            "voice_id": "default-fs1qvbalzzasjvt87bghow__manish_7",
            "audio_config": {
                "audio_encoding": "MP3",
                "speaking_rate": 0.85
            },
            "temperature": 0.75,
            "model_id": "inworld-tts-1-max"
        }
        
        response = requests.post(INWORLD_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "Connected to Inworld API"
        elif response.status_code == 401:
            return False, "Invalid API key"
        elif response.status_code == 403:
            return False, "API access forbidden - check your subscription"
        else:
            return False, f"API returned status code {response.status_code}"
    
    except requests.exceptions.ConnectionError:
        return False, "Connection error: Could not connect to Inworld API"
    except requests.exceptions.Timeout:
        return False, "Connection timeout: Inworld API did not respond in time"
    except Exception as e:
        return False, f"Error checking Inworld API connection: {str(e)}"

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
    voice_id: str,
    output_dir: str,
    response_format: str = "mp3",
    speaking_rate: float = 0.85,
    temperature: float = 0.75,
    normalize_text: bool = True
) -> List[Dict]:
    """
    Generate TTS for a list of section files
    
    Args:
        section_files: List of section file paths
        voice_id: Voice ID to use for TTS
        output_dir: Directory to save audio files
        response_format: Audio format (mp3, wav)
        speaking_rate: Speech rate (default: 0.9)
        normalize_text: Apply text normalization
        
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
                "word_count": 0,
                "character_count": 0
            })
            continue
        
        # Read the content of the section file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                results.append({
                    "success": True,
                    "file": file_path,
                    "output": output_path,
                    "status": "skipped",
                    "message": "Empty or whitespace-only file",
                    "processing_time": 0,
                    "word_count": 0,
                    "character_count": 0
                })
                continue
            
            # Count words and characters for statistics
            word_count = calculate_word_count(content)
            character_count = calculate_character_count(content)
            
            # Start timing
            start_time = time.time()
            
            # Show current file being processed
            st.write(f"Processing: {os.path.basename(file_path)}")
            
            # Generate speech from text
            success, message, _ = convert_text_to_speech(
                text=content,
                voice_id=voice_id,
                output_path=output_path,
                response_format=response_format,
                speaking_rate=speaking_rate,
                temperature=temperature,
                normalize_text=normalize_text
            )
            
            # Stop timing
            processing_time = time.time() - start_time
            
            # Create result dictionary
            result = {
                "success": success,
                "file": file_path,
                "output": output_path,
                "message": message,
                "processing_time": processing_time,
                "word_count": word_count,
                "character_count": character_count,
                "status": "processed" if success else "failed"
            }
            
            results.append(result)
        
        except Exception as e:
            # Handle any other exceptions
            results.append({
                "success": False,
                "file": file_path,
                "output": output_path,
                "status": "failed",
                "message": f"Error: {str(e)}",
                "processing_time": 0,
                "word_count": 0,
                "character_count": 0
            })
    
    return results

def main():
    st.title("TTS Inworld")
    st.write("Convert transcript and summary sections to audio files using Inworld Text-to-Speech API.")
    
    # Check for API key
    api_key = get_api_key()
    if not api_key:
        st.error("API key not available")
        st.info("Please check the API key configuration")
        return
    
    # Check for Inworld API connection
    connection_status, connection_message = check_connection()
    
    if not connection_status:
        st.error(f"Cannot connect to Inworld API: {connection_message}")
        
        # Try simple API test
        with st.expander("API Test Details"):
            test_status, test_message = test_api_simple()
            if test_status:
                st.success(test_message)
            else:
                st.error(test_message)
        return
    else:
        st.success(f"🌐 {connection_message}")
        
        # Show simple test result too
        test_status, test_message = test_api_simple()
        if test_status:
            st.info(f"✅ {test_message}")
        else:
            st.warning(f"⚠️ Simple test failed: {test_message}")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Get available voices
    available_voices = get_available_voices()
    voice_options = {v["id"]: f"{v['name']} ({v['gender']})" for v in available_voices}
    
    st.header("TTS Settings")
    st.info("Using Inworld Text-to-Speech API with cloud processing")
    
    # Settings
    col1, col2 = st.columns(2)
    
    with col1:
        # Voice selection
        voice_ids = list(voice_options.keys())
        selected_voice = st.selectbox(
            "Voice",
            options=voice_ids,
            format_func=lambda x: voice_options[x],
            index=0,
            help="Select the voice for text-to-speech conversion"
        )
        
        # Audio format
        audio_format = st.selectbox(
            "Audio Format",
            options=["mp3", "wav"],
            index=0,
            help="Select audio output format"
        )
    
    with col2:
        # Speaking rate (called "Talking speed" in playground)
        speaking_rate = st.slider(
            "Talking Speed",
            min_value=0.5,
            max_value=1.5,
            value=0.85,
            step=0.05,
            help="Adjust the speed of speech (0.85 is recommended)"
        )
        
        # Temperature control (matches playground range)
        temperature = st.slider(
            "Temperature",
            min_value=0.7,
            max_value=1.5,
            value=0.75,
            step=0.05,
            help="Controls randomness in speech generation (0.75 is recommended)"
        )
        
        # Text normalization
        normalize_text = st.checkbox(
            "Normalize Text", 
            value=True,
            help="Clean and normalize text for better TTS output"
        )
    
    # Language selection (simplified)
    st.subheader("Language Processing")
    language = st.selectbox(
        "Select Language",
        options=["English"],  # Can be expanded later
        index=0,
        help="Select the language to process"
    )
    
    # Find files for the selected language
    language_files = find_language_section_files(language=language)
    
    if not language_files:
        st.warning(f"No files found for {language}. Please ensure you have text files in the correct directory structure.")
        st.info("Expected structure: input/[course]/[lecture]/{language} text/ and {language} Summary text/")
        return
    
    # Display found files summary
    total_transcript_files = 0
    total_summary_files = 0
    total_characters = 0
    
    for course, lectures in language_files.items():
        for lecture, lecture_data in lectures.items():
            total_transcript_files += len(lecture_data["transcript"]["section_files"])
            total_summary_files += len(lecture_data["summary"]["section_files"])
            
            # Calculate total characters for cost estimation
            for file_path in lecture_data["transcript"]["section_files"] + lecture_data["summary"]["section_files"]:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if normalize_text:
                            content = clean_text_for_tts(content)
                        total_characters += len(content)
                except:
                    pass
    
    total_files = total_transcript_files + total_summary_files
    
    st.subheader("Processing Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Total Characters", f"{total_characters:,}")
    with col3:
        estimated_cost = tts_cost_estimation(total_characters)
        st.metric("Estimated Cost", f"${estimated_cost:.4f}")
    
    # Show detailed breakdown
    with st.expander("Detailed File Breakdown"):
        for course, lectures in language_files.items():
            st.write(f"**{course}**")
            for lecture, lecture_data in lectures.items():
                transcript_count = len(lecture_data["transcript"]["section_files"])
                summary_count = len(lecture_data["summary"]["section_files"])
                st.write(f"  - {lecture}: {transcript_count} transcript files, {summary_count} summary files")
    
    # Process button
    if st.button("Process Files", type="primary"):
        if total_files == 0:
            st.error("No files to process")
            return
        
        # Confirm if cost is high
        if estimated_cost > 1.0:
            if not st.checkbox(f"I understand the estimated cost is ${estimated_cost:.4f}"):
                st.warning("Please confirm you understand the estimated cost before proceeding")
                return
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            eta_display = st.empty()
        
        # Results accumulator
        all_results = []
        processed_files = 0
        
        # Overall start time
        start_time = time.time()
        
        st.info(f"Processing {total_files} files for {language}")
        
        # Process each course and lecture
        for course, lectures in language_files.items():
            for lecture, lecture_data in lectures.items():
                status_text.info(f"Processing {course} - {lecture}")
                
                # Create audio directories
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
                        voice_id=selected_voice,
                        output_dir=transcript_audio_dir,
                        response_format=audio_format,
                        speaking_rate=speaking_rate,
                        temperature=temperature,
                        normalize_text=normalize_text
                    )
                    all_results.extend(transcript_results)
                    processed_files += len(transcript_results)
                
                # Process summary files
                if lecture_data["summary"]["section_files"]:
                    summary_results = generate_tts_for_sections(
                        section_files=lecture_data["summary"]["section_files"],
                        voice_id=selected_voice,
                        output_dir=summary_audio_dir,
                        response_format=audio_format,
                        speaking_rate=speaking_rate,
                        temperature=temperature,
                        normalize_text=normalize_text
                    )
                    all_results.extend(summary_results)
                    processed_files += len(summary_results)
                
                # Update progress
                progress = processed_files / total_files
                progress_bar.progress(progress)
                
                # Calculate ETA
                elapsed_time = time.time() - start_time
                if processed_files > 0:
                    files_per_second = processed_files / elapsed_time
                    remaining_files = total_files - processed_files
                    eta_seconds = remaining_files / files_per_second if files_per_second > 0 else 0
                    minutes, seconds = divmod(int(eta_seconds), 60)
                    eta_display.text(f"Progress: {processed_files}/{total_files} files. ETA: {minutes}m {seconds}s")
        
        # Processing complete
        progress_bar.progress(1.0)
        status_text.success(f"Processing complete: {processed_files} files processed")
        
        # Display results summary
        st.header("Processing Results")
        
        # Count successes and failures
        success_count = sum(1 for r in all_results if r["success"])
        failure_count = sum(1 for r in all_results if not r["success"])
        skipped_count = sum(1 for r in all_results if r["status"] == "skipped")
        success_rate = (success_count / len(all_results)) * 100 if all_results else 0
        
        # Calculate totals
        total_words = sum(r["word_count"] for r in all_results if "word_count" in r)
        total_characters = sum(r["character_count"] for r in all_results if "character_count" in r)
        total_processing_time = sum(r["processing_time"] for r in all_results if "processing_time" in r)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Successful", success_count)
        with col2:
            st.metric("Failed", failure_count)
        with col3:
            st.metric("Skipped", skipped_count)
        with col4:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Additional statistics
        st.subheader("Processing Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Words", f"{total_words:,}")
        with col2:
            st.metric("Total Characters", f"{total_characters:,}")
        with col3:
            processing_speed = total_characters / total_processing_time if total_processing_time > 0 else 0
            st.metric("Processing Speed", f"{processing_speed:.0f} chars/sec")
        
        # Display failures if any
        if failure_count > 0:
            with st.expander("Failed Files"):
                for result in all_results:
                    if not result["success"] and result["status"] != "skipped":
                        st.error(f"{os.path.basename(result['file'])}: {result['message']}")
        
        # Final summary
        total_time = time.time() - start_time
        st.success(f"✅ Processing completed in {total_time:.2f} seconds")
        
        if success_count > 0:
            st.info(f"🎵 {success_count} audio files generated successfully")

if __name__ == "__main__":
    main()