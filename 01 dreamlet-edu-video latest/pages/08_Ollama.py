"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Translate lecture content using a local Ollama model backend.
MAIN INPUTS:
- lecture text content under `input/`
- selected target languages
MAIN OUTPUTS:
- translated text written back into lecture workflow folders
REQUIRED CONFIG / ASSETS:
- `config/prompt.txt`
EXTERNAL SERVICES:
- Ollama API at `http://127.0.0.1:11434/api`
HARDWARE ASSUMPTIONS:
- depends on the local machine running the Ollama model
"""

import streamlit as st
import os
import re
import json
import time
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

st.set_page_config(page_title="08 Translator (Ollama) - Dreamlet", page_icon="🌍")

# Define supported languages (same as LM Studio version)
SUPPORTED_LANGUAGES = {
    "af": "Afrikaans",
    "sq": "Albanian",
    "am": "Amharic",
    "ar": "Arabic",
    "hy": "Armenian",
    "az": "Azerbaijani",
    "be": "Belarusian",
    "bel": "Belarusian",  # ISO-639-2
    "bn": "Bengali",
    "bs": "Bosnian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "ceb": "Cebuano",  # ISO-639-2
    "zh-CN": "Chinese (Simplified)",  # BCP-47
    "zh-TW": "Chinese (Traditional)",  # BCP-47
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "tl": "Filipino",
    "fi": "Finnish",
    "fr": "French",
    "fy": "Frisian",
    "gl": "Galician",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "gu": "Gujarati",
    "ht": "Haitian Creole",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "ig": "Igbo",
    "id": "Indonesian",
    "ga": "Irish",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "kk": "Kazakh",
    "km": "Khmer",
    "ko": "Korean",
    "lo": "Lao",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "lb": "Luxembourgish",
    "mk": "Macedonian",
    "mg": "Malagasy",
    "ms": "Malay",
    "ml": "Malayalam",
    "mr": "Marathi",
    "mn": "Mongolian",
    "my": "Myanmar (Burmese)",
    "ne": "Nepali",
    "nb": "Norwegian (Bokmål)",
    "no": "Norwegian",
    "or": "Odia (Oriya)",
    "ps": "Pashto",
    "fa": "Persian",
    "pl": "Polish",
    "pt": "Portuguese",
    "pt-BR": "Portuguese (Brazil)",  # BCP-47
    "pt-PT": "Portuguese (Portugal)",  # BCP-47
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "gd": "Scots Gaelic",
    "sr": "Serbian",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es": "Spanish",
    "su": "Sundanese",
    "sw": "Swahili",
    "sv": "Swedish",
    "ta": "Tamil",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "cy": "Welsh",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "zu": "Zulu"
}

# Utility function to ensure directory exists
def ensure_directory_exists(directory_path):
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory_path: Path to the directory to create
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        st.error(f"Error creating directory '{directory_path}': {str(e)}")
        return False

# Ollama API constants
OLLAMA_API_URL = "http://127.0.0.1:11434/api"  # Default Ollama API address
OLLAMA_MODEL = "gemma3:27b-it-qat"  # Default model as requested

# Path to the prompt template file
PROMPT_TEMPLATE_PATH = os.path.join("config", "prompt.txt")

# Function to load the prompt template
def load_prompt_template() -> str:
    """
    Load the prompt template from the config file
    
    Returns:
        The prompt template as a string
    """
    try:
        if os.path.exists(PROMPT_TEMPLATE_PATH):
            with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Default prompt template in case the file doesn't exist
            return """You are a professional translator with expertise in translating educational content. 

Your task is to translate the following text from English to {TARGET_LANGUAGE}.

Ensure that the translation:
1. Maintains the original meaning and educational value
2. Uses academic but clear language appropriate for the target language
3. Preserves any specialized terminology with appropriate translations
4. Keeps formatting and paragraph structure intact
5. Maintains any markdown formatting in the text
6. Does not add or remove information from the original text

Here is the text to translate:
{TEXT_CONTENT}

Provide only the translated text without any other explanations or notes."""
    except Exception as e:
        st.error(f"Error loading prompt template: {str(e)}")
        return "Translate the following text from English to {TARGET_LANGUAGE}: {TEXT_CONTENT}"

# Function to check Ollama API connection
def check_ollama_api() -> Tuple[bool, str]:
    """
    Check if the Ollama API server is running and accessible
    
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Make a simple request to the Ollama API to list models
        response = requests.get(f"{OLLAMA_API_URL}/tags")
        
        if response.status_code == 200:
            # Check if our model is in the list
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            
            if OLLAMA_MODEL in model_names:
                return True, f"Successfully connected to Ollama API. Model '{OLLAMA_MODEL}' is available."
            else:
                available_models = ", ".join(model_names) if model_names else "No models found"
                # Still return True if Ollama is running but model isn't pulled yet
                return False, f"Model '{OLLAMA_MODEL}' not found in Ollama. Available models: {available_models}"
        else:
            return False, f"Ollama API responded with status code {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, f"Could not connect to Ollama API at {OLLAMA_API_URL}. Please make sure Ollama is running."
    except Exception as e:
        return False, f"Error checking Ollama API: {str(e)}"

# Create a status manager for UI feedback
class StatusManager:
    """A class to manage and simplify status messages during translation processing"""

    def __init__(self, progress_bar, status_text, current_action_text=None):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.current_action_text = current_action_text
        self.current_file = ""
        self.current_action = ""
        self.processed_count = 0
        self.total_count = 0
        self.start_time = datetime.now()

    def set_total(self, total):
        """Set the total number of presentations to process"""
        self.total_count = total

    def update_progress(self, current_index, filename):
        """Update the progress bar and main status message"""
        self.processed_count = current_index
        self.current_file = filename
        progress = self.processed_count / self.total_count if self.total_count > 0 else 0
        self.progress_bar.progress(progress)

        # Calculate and display estimated time remaining
        if self.processed_count > 1:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            time_per_file = elapsed_time / (
                self.processed_count - 1
            )  # Exclude current file that just started
            remaining_files = self.total_count - self.processed_count
            remaining_seconds = remaining_files * time_per_file
            remaining_time = str(timedelta(seconds=int(remaining_seconds)))

            self.status_text.info(
                f"Processing {self.processed_count}/{self.total_count}: {filename} (Est. time remaining: {remaining_time})"
            )
        else:
            self.status_text.info(
                f"Processing {self.processed_count}/{self.total_count}: {filename}"
            )

    def update_action(self, message):
        """Update only the current action, not the main status display"""
        self.current_action = message
        if self.current_action_text:
            self.current_action_text.info(message)

    def info(self, message):
        """For compatibility with status_text.info but only updates the current action"""
        self.update_action(message)

    def warning(self, message):
        """For compatibility with status_text.warning"""
        st.warning(message)

    def error(self, message):
        """For compatibility with status_text.error"""
        st.error(message)

    def success(self, message):
        """For compatibility with status_text.success"""
        self.status_text.success(message)
        if self.current_action_text:
            self.current_action_text.empty()  # Clear the current action text when we're done

# Function for translation with Ollama API
def translate_with_ollama(text: str, target_lang_code: str, debug_mode: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Translate text from English to the specified language using the Ollama API
    
    Args:
        text: Text to translate
        target_lang_code: The language code to translate to (e.g., 'es', 'fr', 'de')
        debug_mode: Whether to show detailed API responses
        
    Returns:
        Tuple of (success, message, translated_text)
    """
    if not text or text.strip() == "":
        return False, "Empty text provided", None
    
    # Get the full language name for the prompt
    target_language = SUPPORTED_LANGUAGES.get(target_lang_code, "Unknown")
    
    # Load the prompt template
    prompt_template = load_prompt_template()
    
    # Replace placeholders in the prompt with the full language name, not the code
    prompt = prompt_template.replace("{TARGET_LANGUAGE}", target_language).replace("{TEXT_CONTENT}", text)
    
    # Prepare the system message and prompt
    system_message = "You are a professional translator."
    
    if debug_mode:
        st.write(f"Translating to language: {target_language} (code: {target_lang_code})")
        st.write("Prompt template:")
        st.code(prompt_template)
        st.write("Final prompt:")
        st.code(prompt)
        st.write("System message:")
        st.write(system_message)
    
    try:
        # Get the temperature from the session state (default to 0.3 if not set)
        temperature = st.session_state.get('temperature', 0.3)
        
        # Make the request to the Ollama API using the requests library
        response = requests.post(
            f"{OLLAMA_API_URL}/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "options": {
                    "temperature": temperature
                }
            }
        )
        
        if debug_mode:
            st.write("API response:")
            st.write(response.json())
        
        # Check if the response was successful
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract the translated text from the response
            if 'message' in response_data and 'content' in response_data['message']:
                translated_text = response_data['message']['content'].strip()
                return True, "Translation successful", translated_text
            else:
                return False, "Unexpected API response format: missing message content", None
        else:
            return False, f"API request failed with status code {response.status_code}: {response.text}", None
    
    except Exception as e:
        error_msg = f"Error in translation: {str(e)}"
        if debug_mode:
            st.exception(e)
            
        # Try to provide more helpful error messages for common issues
        if "ConnectionError" in str(e) or "Connection" in str(e):
            error_msg = f"Could not connect to Ollama API. Please make sure Ollama is running at {OLLAMA_API_URL}"
        elif "Timeout" in str(e):
            error_msg = "Ollama API request timed out. The model might be processing a large request or not loaded correctly."
            
        return False, error_msg, None

def find_english_text_files() -> Dict[str, Dict[str, Dict]]:
    """
    Find all English text files in all Lecture folders
    
    Returns:
        Nested dictionary of course -> lecture -> files
    """
    organized_files = {}

    # Get the base input directory (current working directory)
    input_dir = os.getcwd()

    # Find all files that might contain English text
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        # Check if this is an "English text" folder (regular or summary)
        is_english_folder = False
        folder_type = None
        
        if "English text" in root and "Summary" not in root:
            is_english_folder = True
            folder_type = "regular"
        elif "English Summary text" in root:
            is_english_folder = True
            folder_type = "summary"
        
        if is_english_folder:
            # Get the parent directory (which should be the lecture directory)
            lecture_dir = os.path.dirname(root)
            lecture_dir_name = os.path.basename(lecture_dir)

            # Get the course directory (parent of lecture directory)
            course_dir = os.path.dirname(lecture_dir)
            course_dir_name = os.path.basename(course_dir)

            # Use actual folder names first
            course_name = course_dir_name
            lecture_name = lecture_dir_name

            # Extract numbers if needed
            if "course" in course_dir_name.lower():
                course_num_match = re.search(r'\d+', course_dir_name)
                if course_num_match:
                    course_number = course_num_match.group()
                    # Preserve original case but standardize format
                    if "Course" in course_dir_name:
                        course_name = f"Course {course_number}"
                    elif "COURSE" in course_dir_name:
                        course_name = f"COURSE {course_number}"
                    else:
                        course_name = f"Course {course_number}"
            elif "history" in course_dir_name.lower():
                course_name = course_dir_name

            # Process lecture name
            if "lecture" in lecture_dir_name.lower():
                lecture_num_match = re.search(r'\d+', lecture_dir_name)
                if lecture_num_match:
                    lecture_number = lecture_num_match.group()
                    # Preserve original case but standardize format
                    if "Lecture" in lecture_dir_name:
                        lecture_name = f"Lecture {lecture_number}"
                    elif "LECTURE" in lecture_dir_name:
                        lecture_name = f"LECTURE {lecture_number}"
                    else:
                        lecture_name = f"Lecture {lecture_number}"

            # Initialize the course entry if it doesn't exist
            if course_name not in organized_files:
                organized_files[course_name] = {}

            # Initialize the lecture entry if it doesn't exist
            if lecture_name not in organized_files[course_name]:
                organized_files[course_name][lecture_name] = {
                    "regular": {},
                    "summary": {}
                }

            # Add all the files in this folder
            for file in files:
                if file.lower().endswith((".txt", ".md")):
                    file_path = os.path.join(root, file)
                    organized_files[course_name][lecture_name][folder_type][file_path] = {
                        "filename": file,
                        "folder_type": folder_type,
                        "path": file_path
                    }

    return organized_files

def translate_selected_files(selected_lectures, target_languages, status_manager, debug_mode=False):
    """
    Translate selected files to selected target languages
    
    Args:
        selected_lectures: Dictionary mapping (course, lecture) tuples to lecture data
        target_languages: List of target language codes
        status_manager: StatusManager instance for UI updates
        debug_mode: Whether to show detailed debug information
        
    Returns:
        Dictionary of results
    """
    results = {
        "processed_files": 0,
        "successful_translations": 0,
        "failed_translations": 0,
        "skipped_files": 0,
        "details": []
    }
    
    # Count all files for progress tracking
    total_files = 0
    for _, lecture_data in selected_lectures.items():
        for folder_type in ["regular", "summary"]:
            total_files += len(lecture_data[folder_type])
    
    # Multiply by the number of target languages
    total_operations = total_files * len(target_languages)
    status_manager.set_total(total_operations)
    
    # Track current progress
    current_progress = 0
    
    # Process each lecture
    for (course, lecture), lecture_data in selected_lectures.items():
        # Create a standardized directory structure based on course and lecture
        for folder_type in ["regular", "summary"]:
            # Skip if no files in this category
            if not lecture_data[folder_type]:
                continue
                
            for file_path, file_info in lecture_data[folder_type].items():
                file_name = file_info["filename"]
                
                # Track total files for statistics
                results["processed_files"] += 1
                
                # Read the file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_content = f.read()
                    
                    for target_lang_code in target_languages:
                        current_progress += 1
                        status_manager.update_progress(
                            current_progress, 
                            f"{file_name} → {SUPPORTED_LANGUAGES[target_lang_code]}"
                        )
                        status_manager.update_action(f"Translating to {SUPPORTED_LANGUAGES[target_lang_code]}")
                        
                        # Skip translation if the content is too small
                        if len(source_content.strip()) < 10:
                            status_manager.update_action(f"Skipping (content too small): {file_name}")
                            results["skipped_files"] += 1
                            results["details"].append({
                                "file": file_name,
                                "course": course,
                                "lecture": lecture,
                                "language": target_lang_code,
                                "status": "skipped",
                                "reason": "Content too small"
                            })
                            continue
                            
                        # Determine target path - recreate the directory structure with language code
                        dir_path = os.path.dirname(file_path)
                        parent_dir = os.path.dirname(dir_path)  # this is the lecture folder
                        
                        # Determine the language subfolder name
                        if "summary" in folder_type.lower():
                            target_dir = os.path.join(parent_dir, f"{SUPPORTED_LANGUAGES[target_lang_code]} Summary text")
                        else:
                            target_dir = os.path.join(parent_dir, f"{SUPPORTED_LANGUAGES[target_lang_code]} text")
                            
                        target_file = os.path.join(target_dir, file_name)
                        
                        # Ensure target directory exists
                        ensure_directory_exists(target_dir)
                        
                        # Check if file already exists and skip setting is enabled
                        skip_existing = st.session_state.get('skip_existing_translations', True)
                        if skip_existing and os.path.exists(target_file):
                            status_manager.update_action(f"Skipping (already exists): {target_file}")
                            results["skipped_files"] += 1
                            results["details"].append({
                                "file": file_name,
                                "course": course,
                                "lecture": lecture,
                                "language": target_lang_code,
                                "status": "skipped",
                                "reason": "File already exists"
                            })
                            continue
                        
                        # Perform the translation
                        status_manager.update_action(f"Translating {file_name} to {SUPPORTED_LANGUAGES[target_lang_code]}")
                        
                        success, message, translated_text = translate_with_ollama(
                            source_content, 
                            target_lang_code,
                            debug_mode
                        )
                        
                        if success and translated_text:
                            # Save the translated file
                            try:
                                with open(target_file, 'w', encoding='utf-8') as f:
                                    f.write(translated_text)
                                    
                                results["successful_translations"] += 1
                                results["details"].append({
                                    "file": file_name,
                                    "course": course,
                                    "lecture": lecture,
                                    "language": target_lang_code,
                                    "status": "success",
                                    "target_file": target_file
                                })
                                
                                status_manager.update_action(f"Successfully translated: {target_file}")
                                
                            except Exception as e:
                                error_msg = f"Error saving translation: {str(e)}"
                                status_manager.error(error_msg)
                                
                                results["failed_translations"] += 1
                                results["details"].append({
                                    "file": file_name,
                                    "course": course,
                                    "lecture": lecture,
                                    "language": target_lang_code,
                                    "status": "error",
                                    "error": error_msg
                                })
                                
                        else:
                            # Translation failed
                            results["failed_translations"] += 1
                            results["details"].append({
                                "file": file_name,
                                "course": course,
                                "lecture": lecture,
                                "language": target_lang_code,
                                "status": "error",
                                "error": message
                            })
                            
                            status_manager.error(f"Translation failed: {message}")
                            
                except Exception as e:
                    status_manager.error(f"Error processing file {file_path}: {str(e)}")
                    
                    results["failed_translations"] += 1
                    results["details"].append({
                        "file": file_name,
                        "course": course, 
                        "lecture": lecture,
                        "status": "error",
                        "error": str(e)
                    })
    
    return results

def main():
    st.title("Translator - Ollama")

    # Add API information expander
    with st.expander("About Ollama API", expanded=False):
        st.write("""
        ### Ollama API Information
        
        This tool uses Ollama's local LLM inference server to translate content 
        from English to multiple languages.
        
        #### Setup Instructions:
        1. **Install Ollama**: Download and install from [ollama.ai](https://ollama.ai/)
        2. **Pull the Model**: Run command `ollama pull gemma3:27b-it-qat` in your terminal
        3. **Start Ollama Server**:
           - Run `ollama serve` in your terminal
           - Default port is 11434
        4. **Keep Running**: Leave Ollama running while using this page
        
        #### Configuration:
        - **API Endpoint**: {OLLAMA_API_URL}
        - **Model Name**: gemma3:27b-it-qat (can be changed in Advanced Options)
        - **Prompt Template**: Stored in config/prompt.txt (can be customized)
        
        #### How it works:
        1. Each text file is sent to the local LLM with a translation prompt
        2. The prompt template includes instructions for academic translation quality
        3. The language model processes locally on your computer (no data sent to the cloud)
        4. The results are saved in the appropriate language folder structure
        
        #### Advantages:
        - Free to use (no API costs)
        - Private processing (all data stays on your computer)
        - Works offline
        - Translation quality depends on the model you choose
        """.format(OLLAMA_API_URL=OLLAMA_API_URL))
        
    # Check API connectivity quietly in the background
    with st.spinner("Checking Ollama API connectivity..."):
        api_valid, api_message = check_ollama_api()
        
    if not api_valid:
        st.error(f"Ollama API Error: {api_message}")
        
        # Create a more helpful message with instructions
        st.warning("""
        ### Ollama Model Installation Required
        
        To use this translator, you need to:
        
        1. Install Ollama from [ollama.ai](https://ollama.ai/) if not already installed
        2. Open a terminal and run:
           ```
           ollama pull gemma3:27b-it-qat
           ```
        3. Make sure Ollama is running with:
           ```
           ollama serve
           ```
           
        This will download and install the necessary model (about 8-14GB download depending on quantization).
        You can still use this page to select files and languages while waiting for model installation.
        """)

    # Find all English text files
    with st.spinner("Finding English text files..."):
        organized_files = find_english_text_files()

    if not organized_files:
        st.warning(
            "No English text files found in any Lecture folders. Please make sure you have processed the files with the 'Prepare Multilingual' step first."
        )
        return

    # Initialize session state for selections if not already done
    if 'select_all_lectures' not in st.session_state:
        st.session_state.select_all_lectures = False

    st.success(
        f"Found {sum(len(course_data) for course_data in organized_files.values())} lectures with English text files"
    )

    # Course and lecture selection
    st.header("Select Lectures to Translate")

    # Add Select All / Unselect All buttons at the top level
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Select All Lectures"):
            st.session_state.select_all_lectures = True
            # Set all individual course select_all flags
            for course in organized_files.keys():
                safe_course_key = course.replace(" ", "_").replace("-", "_")
                st.session_state[f"all_{safe_course_key}"] = True

    with col2:
        if st.button("Unselect All Lectures"):
            st.session_state.select_all_lectures = False
            # Clear all individual course select_all flags
            for course in organized_files.keys():
                safe_course_key = course.replace(" ", "_").replace("-", "_")
                st.session_state[f"all_{safe_course_key}"] = False

    # Organize selection with expandable sections
    selected_lectures = {}

    # Sort courses numerically (with fallback to 999 if parsing fails)
    def get_course_number(course_name):
        match = re.search(r'\d+', course_name)
        if match and match.group():
            try:
                return int(match.group())
            except ValueError:
                pass
        return 999
        
    sorted_courses = sorted(organized_files.keys(), key=get_course_number)

    for course in sorted_courses:
        # Create a safer key by replacing spaces with underscores to avoid key conflicts
        safe_course_key = course.replace(" ", "_").replace("-", "_")

        # Initialize course selection state if not already done
        if f"all_{safe_course_key}" not in st.session_state:
            st.session_state[f"all_{safe_course_key}"] = False

        # Sort lectures numerically
        def get_lecture_number(lecture_name):
            match = re.search(r'\d+', lecture_name)
            if match and match.group():
                try:
                    return int(match.group())
                except ValueError:
                    pass
            return 999
            
        sorted_lectures = sorted(organized_files[course].keys(), key=get_lecture_number)

        # Create an expander for each course
        with st.expander(f"{course} ({len(sorted_lectures)} lectures)", expanded=False):
            # Add Select All / None buttons for this course
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"Select All {course}", key=f"btn_all_{safe_course_key}"):
                    st.session_state[f"all_{safe_course_key}"] = True
                    
            with col2:
                if st.button(f"Select None {course}", key=f"btn_none_{safe_course_key}"):
                    st.session_state[f"all_{safe_course_key}"] = False

            # Show a checkbox for each lecture
            for lecture in sorted_lectures:
                lecture_data = organized_files[course][lecture]
                
                # Count files for this lecture
                total_files = 0
                for folder_type in ["regular", "summary"]:
                    total_files += len(lecture_data[folder_type])
                
                if st.session_state[f"all_{safe_course_key}"] or st.session_state.select_all_lectures:
                    selected = True
                    st.write("✅ Selected (from 'Select all')")
                else:
                    # Create safer key by replacing spaces and dashes
                    safe_course_key = course.replace(" ",
                                                   "_").replace("-", "_")
                    safe_lecture_key = lecture.replace(" ",
                                                     "_").replace("-", "_")
                    checkbox_key = f"{safe_course_key}_{safe_lecture_key}"

                    # Initialize checkbox state
                    if checkbox_key not in st.session_state:
                        st.session_state[checkbox_key] = False

                    selected = st.checkbox(f"Translate {lecture}",
                                         key=checkbox_key)

                if selected:
                    selected_lectures[(course, lecture)] = lecture_data

    # Translation Processing
    st.header("Select Target Languages")
    
    # Get the list of supported languages
    language_options = sorted([(code, name) for code, name in SUPPORTED_LANGUAGES.items()], key=lambda x: x[1])
    
    # Initialize language selections in session state
    if 'selected_languages' not in st.session_state:
        st.session_state.selected_languages = ['es']  # Default to Spanish
    
    # Create a more user-friendly language selection interface with search
    st.write("### Select target languages for translation")
    
    # Add search filter
    if 'lang_search' not in st.session_state:
        st.session_state.lang_search = ""
        
    lang_search = st.text_input("Search languages", value=st.session_state.lang_search, key="lang_search_input")
    st.session_state.lang_search = lang_search
    
    # Filter languages based on search
    filtered_languages = []
    if lang_search:
        filtered_languages = [(code, name) for code, name in language_options 
                             if lang_search.lower() in name.lower()]
    else:
        filtered_languages = language_options
    
    # Group languages into columns for a more compact display
    # Show languages in a grid with checkboxes
    num_cols = 4  # Number of columns in the grid
    cols = st.columns(num_cols)
    
    # Initialize selected languages if not already done
    if 'selected_languages' not in st.session_state:
        st.session_state.selected_languages = []
        
    selected_languages = []
    
    # Display languages in a grid with checkboxes
    for i, (code, name) in enumerate(filtered_languages):
        col_index = i % num_cols
        
        with cols[col_index]:
            lang_key = f"lang_{code}"
            
            # Initialize the checkbox state from session state if needed
            if lang_key not in st.session_state:
                # Default Spanish to selected
                st.session_state[lang_key] = code == 'es'
                
            # Use the key parameter with Streamlit's checkbox
            # but don't try to update session_state afterwards
            selected = st.checkbox(name, value=st.session_state[lang_key], key=lang_key)
            
            # Check if selected and add to our list
            if selected:
                selected_languages.append(code)
    
    # Check if any languages were selected
    if not selected_languages:
        st.warning("Please select at least one target language")
        
    # Count total files to be processed
    total_files = 0
    for _, lecture_data in selected_lectures.items():
        for folder_type in ["regular", "summary"]:
            total_files += len(lecture_data[folder_type])
            
    st.write(
        f"Selected {len(selected_lectures)} lectures with {total_files} text files to translate"
    )
    
    # Advanced options - expanded by default to show debug settings
    with st.expander("Advanced Options", expanded=True):
        # Store debug mode in session state so it persists - default to True for troubleshooting
        if 'debug_enabled' not in st.session_state:
            st.session_state.debug_enabled = True
            
        st.session_state.debug_enabled = st.checkbox(
            "Enable debug mode (shows detailed API responses)", 
            value=st.session_state.debug_enabled
        )
        
        # Add option to skip existing translated files
        if 'skip_existing_translations' not in st.session_state:
            st.session_state.skip_existing_translations = True
            
        st.session_state.skip_existing_translations = st.checkbox(
            "Skip already translated files", 
            value=st.session_state.skip_existing_translations,
            help="If checked, will not overwrite existing translated files"
        )
        
        # Declare global before using it
        global OLLAMA_MODEL
        
        # Model selection (set the default to the constant value initially)
        if 'ollama_model' not in st.session_state:
            st.session_state.ollama_model = OLLAMA_MODEL
            
        st.session_state.ollama_model = st.text_input(
            "Ollama Model Name",
            value=st.session_state.ollama_model,
            help="The model name exactly as it appears in Ollama CLI (example: gemma3:27b-it-qat)"
        )
        
        # Update the global model name when changed
        OLLAMA_MODEL = st.session_state.ollama_model
        
        # Temperature setting for translation
        if 'temperature' not in st.session_state:
            st.session_state.temperature = 0.3
            
        st.session_state.temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="Lower values (0.0-0.3) give more consistent translations, higher values (0.7-1.0) may be more creative"
        )
        
        st.info("Debug mode will show detailed information about API requests and responses for troubleshooting.")
        st.write("Current API Endpoint: ", OLLAMA_API_URL)
        st.write("Current Model: ", OLLAMA_MODEL)
        
        # Show example API request for documentation purposes
        st.write("### Ollama API Request Format")
        st.code('''
import requests

response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "gemma3:27b-it-qat",
        "messages": [
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": "Translate this text to Spanish: Hello world!"}
        ],
        "options": {
            "temperature": 0.3
        }
    }
)

# Extract translated content from response
translated_text = response.json()["message"]["content"]
        ''', language="python")
        
    # File analysis before translation
    st.subheader("Analyze Files")
    st.write("Scan the selected files to estimate translation workload.")
    
    if st.button("Analyze Selected Files"):
        with st.spinner("Analyzing files..."):
            # Count words in all selected files
            total_files = 0
            total_words = 0
            file_statistics = []
            
            for (course, lecture), lecture_data in selected_lectures.items():
                for folder_type in ["regular", "summary"]:
                    for file_path, file_info in lecture_data[folder_type].items():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                word_count = len(content.split())
                                
                                total_files += 1
                                total_words += word_count
                                
                                file_statistics.append({
                                    "course": course,
                                    "lecture": lecture,
                                    "file": file_info["filename"],
                                    "type": folder_type,
                                    "words": word_count
                                })
                                
                        except Exception as e:
                            st.error(f"Error analyzing file {file_path}: {str(e)}")
            
            # Display stats
            st.write(f"Total files: {total_files}")
            st.write(f"Total words: {total_words:,}")
            
            # Estimate time based on model and word count
            # Gemma models are approximately 20-30 words per second for translation tasks
            # Using a conservative estimate of 15 words/sec
            words_per_second = 15
            estimated_seconds = total_words / words_per_second
            estimated_minutes = estimated_seconds / 60
            
            if estimated_minutes < 1:
                st.write(f"Estimated processing time: Less than 1 minute")
            else:
                st.write(f"Estimated processing time: ~{estimated_minutes:.1f} minutes")
            
            # Show files with most words
            if file_statistics:
                st.write("### Largest files:")
                sorted_stats = sorted(file_statistics, key=lambda x: x["words"], reverse=True)
                
                # Display top 5 largest files
                for i, stat in enumerate(sorted_stats[:5]):
                    st.write(f"{i+1}. {stat['course']} - {stat['lecture']} - {stat['file']}: {stat['words']:,} words")
            
    # Translation button
    st.header("Translate Files")
    st.write("Start the translation process for all selected files and languages.")
    
    # Only enable translation if API is valid and files are selected
    translation_disabled = not api_valid or not selected_lectures or not selected_languages
    
    if translation_disabled:
        st.warning("Please select at least one lecture and one language, and ensure Ollama API is working")
    
    if st.button("Start Translation", disabled=translation_disabled, type="primary"):
        # Setup progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        current_action_text = st.empty()
        
        # Create a status manager to update the UI
        status_manager = StatusManager(
            progress_bar=progress_bar,
            status_text=status_text,
            current_action_text=current_action_text
        )
        
        # Start translation process
        with st.spinner("Translating files..."):
            results = translate_selected_files(
                selected_lectures=selected_lectures,
                target_languages=selected_languages,
                status_manager=status_manager,
                debug_mode=st.session_state.debug_enabled
            )
            
        # Display results
        if results:
            st.success(f"Translation completed!")
            
            # Create a result summary
            st.subheader("Translation Results")
            st.write(f"Processed files: {results['processed_files']}")
            st.write(f"Successful translations: {results['successful_translations']}")
            st.write(f"Failed translations: {results['failed_translations']}")
            st.write(f"Skipped files: {results['skipped_files']}")
            
            # Show details of failures if any
            if results['failed_translations'] > 0:
                with st.expander("Failed Translations", expanded=True):
                    for detail in results['details']:
                        if detail.get('status') == 'error':
                            st.error(f"{detail.get('course', '')} - {detail.get('lecture', '')} - {detail.get('file', '')}: {detail.get('error', 'Unknown error')}")
        else:
            st.error("Translation process failed or was cancelled.")

if __name__ == "__main__":
    main()
