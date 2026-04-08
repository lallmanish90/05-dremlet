"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Translate lecture content using an LM Studio-compatible local OpenAI API endpoint.
MAIN INPUTS:
- lecture text content under `input/`
- selected target languages
MAIN OUTPUTS:
- translated text written back into lecture workflow folders
REQUIRED CONFIG / ASSETS:
- `config/prompt.txt`
EXTERNAL SERVICES:
- local LM Studio OpenAI-compatible API
HARDWARE ASSUMPTIONS:
- depends on the machine hosting the LM Studio model
"""

import streamlit as st
import os
import re
import json
import time
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from openai import OpenAI

st.set_page_config(page_title="08 Translator (LM Studio) - Dreamlet", page_icon="🌍")

# Define supported languages (this will be updated with LM Studio specific languages)
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

# LM Studio API constants
LM_STUDIO_API_KEY = "lm-studio"  # LM Studio typically uses this as a placeholder key
LM_STUDIO_API_URL = "http://127.0.0.1:1234/v1"  # Base URL for LM Studio local server
LM_STUDIO_MODEL = "gemma-3-12b-it-qat"  # Default model name - user can change in advanced settings

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

# Function to check LM Studio API connection
def check_lm_studio_api_key() -> Tuple[bool, str]:
    """
    Check if the LM Studio API server is running and accessible
    
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Initialize the OpenAI client with the LM Studio local server
        client = OpenAI(
            base_url=LM_STUDIO_API_URL,
            api_key=LM_STUDIO_API_KEY
        )
        
        # Build a minimal request to test connectivity
        from openai.types.chat import ChatCompletionUserMessageParam
        test_message = ChatCompletionUserMessageParam(role="user", content="Hello")
        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL,  # Use the model name shown in LM Studio
            messages=[test_message],
            max_tokens=5,
            timeout=3  # Add timeout to prevent long waits
        )
        
        # If we got a response, the connection is valid
        if response:
            return True, "Successfully connected to LM Studio API server"
        else:
            return False, "Unexpected empty response from LM Studio API"
            
    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg:
            return False, f"Could not connect to LM Studio API at {LM_STUDIO_API_URL}. Please make sure LM Studio is running with its API server enabled."
        elif "Timeout" in error_msg:
            return False, "Connection timed out. Is LM Studio running with its API server enabled?"
        else:
            return False, f"Error checking LM Studio API: {error_msg}"

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

# Function for translation with LM Studio API using LLM
def translate_with_lm_studio(text: str, target_lang_code: str, debug_mode: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Translate text from English to the specified language using the LM Studio LLM API
    
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
    
    # Prepare the messages for the LLM
    from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
    system_message = ChatCompletionSystemMessageParam(role="system", content="You are a professional translator.")
    user_message = ChatCompletionUserMessageParam(role="user", content=prompt)
    messages = [system_message, user_message]
    
    if debug_mode:
        st.write(f"Translating to language: {target_language} (code: {target_lang_code})")
        st.write("Prompt template:")
        st.code(prompt_template)
        st.write("Final prompt:")
        st.code(prompt)
        st.write("Messages:")
        st.write(messages)
    
    try:
        # Initialize the OpenAI client with the LM Studio local server
        client = OpenAI(
            base_url=LM_STUDIO_API_URL,
            api_key=LM_STUDIO_API_KEY
        )
        
        # Get the temperature from the session state (default to 0.3 if not set)
        temperature = st.session_state.get('temperature', 0.3)
        
        # Make the request to the LM Studio API using the OpenAI client
        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL,  # Use the model name shown in LM Studio
            messages=messages,
            temperature=temperature,  # Use the temperature from the UI
            max_tokens=4000  # Adjust based on expected response length
        )
        
        if debug_mode:
            st.write("API response:")
            st.write(response)
        
        # Extract the translated text from the response
        if response and response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if choice.message and choice.message.content:
                translated_text = choice.message.content.strip()
                return True, "Translation successful", translated_text
            else:
                return False, "Unexpected API response format: missing message content", None
        else:
            return False, "Unexpected API response format: missing choices", None
    
    except Exception as e:
        error_msg = f"Error in translation: {str(e)}"
        if debug_mode:
            st.exception(e)
            
        # Try to provide more helpful error messages for common issues
        if "Connection" in str(e):
            error_msg = f"Could not connect to LM Studio API. Please make sure LM Studio is running with the API server enabled at {LM_STUDIO_API_URL}"
        elif "Timeout" in str(e):
            error_msg = "LM Studio API request timed out. The model might be processing a large request or not loaded correctly."
        elif "404" in str(e):
            error_msg = f"Model '{LM_STUDIO_MODEL}' not found. Please check that you have the correct model loaded in LM Studio."
            
        return False, error_msg, None
    
    # This code should never be reached since we're handling all exceptions above
    # But it's kept as a fallback just in case
    if debug_mode:
        st.warning("Using simulated response because the API call failed or is not configured")
    
    return True, "Translation successful (simulated)", f"[LM Studio Translation to {target_language}] {text}"

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

            # Get all text files in this directory
            text_files = []
            for file in files:
                if file.endswith(('.txt', '.md')):
                    text_files.append(os.path.join(root, file))

            # Skip if no text files found
            if not text_files:
                continue

            # Add to organized files dictionary
            if course_name not in organized_files:
                organized_files[course_name] = {}

            # Create or update lecture entry
            if lecture_name not in organized_files[course_name]:
                organized_files[course_name][lecture_name] = {
                    # Use the lecture directory as base - important for creating language-specific text folders
                    "base_dir": lecture_dir,
                    "files": [],
                    "count": 0
                }
                
            # Store files with their type
            for file_path in text_files:
                organized_files[course_name][lecture_name]["files"].append({
                    "path": file_path,
                    "type": folder_type,
                    "source_folder": os.path.basename(root)
                })
            
            # Update count
            organized_files[course_name][lecture_name]["count"] += len(text_files)

    return organized_files

# Placeholder function for translation - will be implemented when API details are provided
def translate_files(selected_lectures: Dict, debug_mode: bool = False) -> List[Dict]:
    """
    Translate all selected files from English to multiple languages
    
    Args:
        selected_lectures: Dictionary of selected lectures to translate
        debug_mode: Whether to show detailed API responses
        
    Returns:
        List of result dictionaries with information about each translation
    """
    # Get target languages from session state
    target_languages = st.session_state.get('selected_languages', ['es'])
    if not target_languages:
        st.error("No target languages selected. Please select at least one language.")
        return []
    
    # Get skip existing setting from session state
    skip_existing = st.session_state.get('skip_existing', True)
    
    # Set up UI for progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    current_action_text = st.empty()
    results_container = st.container()
    status_manager = StatusManager(progress_bar, status_text, current_action_text)
    
    all_files = []
    lecture_file_map = {}
    
    # Collect all files and create a flat list for progress tracking
    for (course, lecture), lecture_data in selected_lectures.items():
        for file_info in lecture_data["files"]:
            all_files.append(file_info)
            lecture_file_map[file_info["path"]] = (course, lecture)
    
    # Total number of translations = files × languages
    total_operations = len(all_files) * len(target_languages)
    status_manager.set_total(total_operations)
    
    results = []
    processed_count = 0
    total_chars_translated = 0
    
    # Process each file for each selected language
    for file_info in all_files:
        file_path = file_info["path"]
        file_type = file_info["type"]  # "regular" or "summary"
        source_folder = file_info["source_folder"]
        
        # Get the associated course and lecture
        course, lecture = lecture_file_map[file_path]
        file_name = os.path.basename(file_path)
        
        # Read the file content once for all languages
        try:
            status_manager.update_action(f"Reading file: {file_name}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content or content.strip() == "":
                results.append({
                    "file_path": file_path,
                    "course": course,
                    "lecture": lecture,
                    "status": "error",
                    "message": "File is empty",
                    "file_type": file_type,
                    "language": "All"
                })
                continue
                
            # Process each target language for this file
            for lang_index, target_lang_code in enumerate(target_languages):
                # Get language name for display
                target_lang_name = SUPPORTED_LANGUAGES.get(target_lang_code, "Unknown Language")
                
                # Update progress counter and status
                processed_count += 1
                status_manager.update_progress(
                    processed_count, 
                    f"({processed_count}/{total_operations}) {course} - {lecture} - {file_name} → {target_lang_name}"
                )
                
                # Determine output directory and path based on file type and language
                lecture_dir = selected_lectures[(course, lecture)]["base_dir"]
                
                # Follow the exact folder naming convention: "[Language] text" and "[Language] Summary text"
                if file_type == "regular":
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                elif file_type == "summary":
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} Summary text")
                else:
                    # Shouldn't happen, but fall back to regular if unknown
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                
                # Add debug information about the folder creation
                if debug_mode:
                    st.write(f"**Creating {target_lang_name} text folder**: {target_dir}")
                    
                # Create the language-specific folder if it doesn't exist
                ensure_directory_exists(target_dir)
                
                # Output file has the same name but in language-specific folder
                target_path = os.path.join(target_dir, file_name)
                
                # Check if the file already exists
                if os.path.exists(target_path) and skip_existing:
                    status_manager.update_action(f"File already exists in {target_lang_name}: {file_name} - Skipping")
                    results.append({
                        "file_path": file_path,
                        "output_path": target_path,
                        "course": course,
                        "lecture": lecture,
                        "status": "skipped",
                        "message": f"File already exists in {target_lang_name} (skipped)",
                        "original_length": len(content),
                        "translated_length": 0,
                        "language": target_lang_name,
                        "language_code": target_lang_code
                    })
                    continue
                
                # Translate content to the target language
                status_manager.update_action(f"Translating to {target_lang_name}")
                
                # For UI mockup, we'll just simulate a translation
                # This will be replaced with actual API calls when details are provided
                success, message, translated_text = translate_with_lm_studio(
                    content, target_lang_code, debug_mode
                )
                
                if success and translated_text:
                    # Log the file saving attempt
                    status_manager.update_action(f"Writing translated {target_lang_name} file")
                    if debug_mode:
                        st.write(f"**Saving {target_lang_name} translation to**: {target_path}")
                        
                    try:
                        # Save translated text
                        with open(target_path, 'w', encoding='utf-8') as f:
                            f.write(translated_text)
                        
                        # Verify file was saved
                        if os.path.exists(target_path):
                            if debug_mode:
                                st.success(f"File successfully saved: {target_path}")
                                st.write(f"File size: {os.path.getsize(target_path)} bytes")
                        else:
                            if debug_mode:
                                st.error(f"File was not saved successfully: {target_path}")
                        
                        # Count characters for reporting
                        total_chars_translated += len(content)
                        
                        results.append({
                            "file_path": file_path,
                            "output_path": target_path,
                            "course": course,
                            "lecture": lecture,
                            "status": "success",
                            "message": f"Translation to {target_lang_name} successful",
                            "original_length": len(content),
                            "translated_length": len(translated_text),
                            "language": target_lang_name,
                            "language_code": target_lang_code
                        })
                    except Exception as e:
                        # Log any file saving errors
                        if debug_mode:
                            st.exception(e)
                        results.append({
                            "file_path": file_path,
                            "course": course,
                            "lecture": lecture,
                            "status": "error",
                            "message": f"Error saving {target_lang_name} translation: {str(e)}",
                            "language": target_lang_name,
                            "language_code": target_lang_code
                        })
                else:
                    # Record error
                    results.append({
                        "file_path": file_path,
                        "course": course,
                        "lecture": lecture,
                        "status": "error",
                        "message": f"Error translating to {target_lang_name}: {message}",
                        "original_length": len(content),
                        "translated_length": 0,
                        "language": target_lang_name,
                        "language_code": target_lang_code
                    })
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)
        
        except Exception as e:
            # Handle file reading or processing errors
            status_manager.error(f"Error processing file {file_name}: {str(e)}")
            results.append({
                "file_path": file_path,
                "course": course,
                "lecture": lecture,
                "status": "error",
                "message": f"Error: {str(e)}",
                "language": "All"
            })
    
    # Complete the progress
    status_manager.success(f"Completed {processed_count} translation operations with {total_chars_translated:,} characters processed")
    
    return results

def main():
    st.title("Translator - LM Studio")

    # Add API information expander
    with st.expander("About LM Studio API", expanded=False):
        st.write("""
        ### LM Studio API Information
        
        This tool uses LM Studio's local LLM inference server with OpenAI-compatible API to translate content 
        from English to multiple languages.
        
        #### Setup Instructions:
        1. **Install LM Studio**: Download and install from [lmstudio.ai](https://lmstudio.ai/)
        2. **Load a Model**: Choose a model with multilingual capabilities (like Gemma, Mistral, or LLaMA)
        3. **Enable the API Server**:
           - In LM Studio, go to Settings > API
           - Activate "OpenAI Compatible Server" 
           - Make sure port is 1234 (default)
        4. **Start Inference**:
           - Click "Local Inference" in LM Studio
           - Keep LM Studio running while using this page
        
        #### Configuration:
        - **API Endpoint**: {LM_STUDIO_API_URL} (local LM Studio server)
        - **Model Name**: Enter the exact name shown in LM Studio in Advanced Options
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
        """.format(LM_STUDIO_API_URL=LM_STUDIO_API_URL))
        
    # Check API key validity quietly in the background
    with st.spinner("Checking API key validity..."):
        key_valid, key_message = check_lm_studio_api_key()
        
    if not key_valid:
        st.error(f"API Key Error: {key_message}")
        st.warning("Please check the API key configuration. This will prevent successful translations until resolved.")

    # Check if we've hit rate limits and show persistent warning if needed
    if 'rate_limit_hit' in st.session_state and st.session_state.rate_limit_hit:
        st.error("""
        ### API Rate Limit Exceeded
        
        The quota for LM Studio API has been exceeded. To continue translating:
        
        1. Upgrade to a paid plan (if available)
        2. Contact your administrator for a new API key
        3. Try again later when the quota resets
        
        Note: Some translations may have succeeded before the limit was reached.
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
            st.session_state[
                f"all_{safe_course_key}"] = st.session_state.select_all_lectures

        with st.expander(f"Course: {course}", expanded=True):
            # Option to select all lectures in this course
            # Create a safer key by replacing spaces with underscores to avoid key conflicts
            safe_course_key = course.replace(" ", "_").replace("-", "_")
            all_in_course = st.checkbox(f"Select all lectures in {course}",
                                      key=f"all_{safe_course_key}",
                                      value=st.session_state.get(
                                          f"all_{safe_course_key}", False))

            # Sort lectures numerically
            def get_lecture_number(lecture_name):
                match = re.search(r'\d+', lecture_name)
                if match and match.group():
                    try:
                        return int(match.group())
                    except ValueError:
                        pass
                return 999
                
            try:
                sorted_lectures = sorted(organized_files[course].keys(), key=get_lecture_number)
            except (AttributeError, ValueError):
                # Fallback to string sorting if numeric sorting fails
                sorted_lectures = sorted(organized_files[course].keys())

            for lecture in sorted_lectures:
                lecture_data = organized_files[course][lecture]

                # Display lecture info
                st.write(
                    f"**{lecture}:** {lecture_data.get('count', 0)} text files"
                )

                # Select this lecture
                if all_in_course:
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
    languages_per_col = (len(filtered_languages) + num_cols - 1) // num_cols
    
    # Create columns
    cols = st.columns(num_cols)
    
    # Track newly selected languages
    selected_lang_codes = st.session_state.selected_languages.copy()
    
    # Display languages in a grid with checkboxes
    for i, (code, name) in enumerate(filtered_languages):
        col_idx = i // languages_per_col
        with cols[col_idx % num_cols]:
            # Check if language is currently selected
            is_selected = code in st.session_state.selected_languages
            
            # Create a unique key for each checkbox to avoid interference
            checkbox_key = f"lang_checkbox_{code}"
            
            # Create checkbox for each language
            if st.checkbox(name, value=is_selected, key=checkbox_key):
                if code not in selected_lang_codes:
                    selected_lang_codes.append(code)
            else:
                if code in selected_lang_codes:
                    selected_lang_codes.remove(code)
    
    # Update session state with selected languages
    st.session_state.selected_languages = selected_lang_codes
    
    # Show the selected languages summary
    if st.session_state.selected_languages:
        st.write("### Selected languages:")
        selected_lang_names = [SUPPORTED_LANGUAGES[code] for code in st.session_state.selected_languages if code in SUPPORTED_LANGUAGES]
        
        # Create a horizontal display of selected languages with badges
        lang_summary_cols = st.columns(min(4, len(selected_lang_names)))
        for i, lang_name in enumerate(selected_lang_names):
            with lang_summary_cols[i % len(lang_summary_cols)]:
                st.info(lang_name)
    else:
        st.warning("Please select at least one language for translation")
    
    # Translation calculation and execution
    if selected_lectures and st.session_state.selected_languages:
        total_files = sum(data["count"] for data in selected_lectures.values())
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
            if 'skip_existing' not in st.session_state:
                st.session_state.skip_existing = True
                
            st.session_state.skip_existing = st.checkbox(
                "Skip existing translations", 
                value=st.session_state.skip_existing,
                help="Skip files that already have translations"
            )
            
            # Declare global before using it
            global LM_STUDIO_MODEL
            
            # Model selection (set the default to the constant value initially)
            if 'lm_studio_model' not in st.session_state:
                st.session_state.lm_studio_model = LM_STUDIO_MODEL
                
            st.session_state.lm_studio_model = st.text_input(
                "LM Studio Model Name",
                value=st.session_state.lm_studio_model,
                help="The model name exactly as it appears in LM Studio"
            )
            
            # Update the global model name when changed
            LM_STUDIO_MODEL = st.session_state.lm_studio_model
            
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
            st.write("Current API Endpoint: ", LM_STUDIO_API_URL)
            st.write("Current Model: ", LM_STUDIO_MODEL)
            st.write("API Key: ", LM_STUDIO_API_KEY, " (default for LM Studio)")
            
            # Show actual API request format for LM Studio's OpenAI-compatible API
            st.write("### LM Studio API Request Format")
            st.code('''
from openai import OpenAI

# Initialize client pointing to LM Studio local server
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1", 
    api_key="lm-studio"  # LM Studio typically uses this as a placeholder key
)

# The prompt template is loaded from config/prompt.txt
prompt_template = """Please translate the following English text into {TARGET_LANGUAGE}, maintaining the original tone, paragraph structure, and terminology. Do not include commentary, notes, or explanations—just provide a clean, accurate translation that preserves the meaning, especially for technical, legal, regulatory, or industry-specific terms. This is for a video transcript, so clarity and natural flow are important.

{TEXT_CONTENT}
"""

# Replace placeholders in the prompt
prompt = prompt_template.replace(
    "{TARGET_LANGUAGE}", "Spanish"
).replace(
    "{TEXT_CONTENT}", "Hello world."
)

# Prepare messages for the chat completions API
messages = [
    {"role": "system", "content": "You are a professional translator."},
    {"role": "user", "content": prompt}
]

# Call the API with user-defined temperature
response = client.chat.completions.create(
    model="gemma-3-12b-it-qat", # Use the model name shown in your LM Studio
    messages=messages,
    temperature=0.3,            # Can be adjusted in Advanced Options (0.0-1.0)
    max_tokens=4000             # Adjust based on expected response length
)

# Extract translated content from response
translated_text = response.choices[0].message.content
            ''', language="python")
        
        # File analysis before translation
        st.subheader("Analyze Files")
        st.write("Scan the selected files to estimate translation workload.")
        st.info("Since LM Studio runs locally, there are no API costs - translation is free!")
        
        # Initialize session state variables for file analysis
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        if 'total_chars_to_translate' not in st.session_state:
            st.session_state.total_chars_to_translate = 0
        if 'files_to_translate' not in st.session_state:
            st.session_state.files_to_translate = 0
        if 'files_to_skip' not in st.session_state:
            st.session_state.files_to_skip = 0
        if 'estimated_time' not in st.session_state:
            st.session_state.estimated_time = 0
        
        # Analyze files button
        if st.button("Analyze Files", type="secondary"):
            with st.spinner("Scanning files and calculating workload..."):
                total_chars = 0
                files_to_translate = 0
                files_to_skip = 0
                
                # Actually count the files and characters
                for (course, lecture), lecture_data in selected_lectures.items():
                    # Get the base lecture directory
                    base_dir = lecture_data.get("base_dir", "")
                    
                    # Go through each file
                    for file_info in lecture_data.get("files", []):
                        file_path = file_info.get("path", "")
                        if not file_path or not os.path.exists(file_path):
                            continue
                            
                        # Check all target languages
                        skip_all_langs = True
                        for lang_code in st.session_state.selected_languages:
                            # Get language name
                            lang_name = SUPPORTED_LANGUAGES.get(lang_code, "Unknown")
                            
                            # Calculate where the translated file would go
                            lang_folder_name = f"{lang_name} text"
                            if file_info.get("type", "") == "summary":
                                lang_folder_name = f"{lang_name} Summary text"
                                
                            # Create full path for target file
                            lang_folder = os.path.join(base_dir, lang_folder_name)
                            target_file = os.path.join(lang_folder, os.path.basename(file_path))
                            
                            # Check if target file exists and we're set to skip existing
                            if st.session_state.skip_existing and os.path.exists(target_file):
                                # This file in this language can be skipped
                                pass
                            else:
                                # Need to translate this file for at least one language
                                skip_all_langs = False
                                break
                        
                        # Process this file
                        if skip_all_langs:
                            files_to_skip += 1
                        else:
                            files_to_translate += 1
                            # Count characters for non-skipped files
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    total_chars += len(content)
                            except Exception:
                                # If we can't read the file, just skip counting chars
                                pass
                
                # Calculate estimated time - very rough estimate
                # Assume average LLM processing speed of ~10 chars per second
                processing_speed = 10  # chars/second
                est_seconds_per_file = total_chars / processing_speed if total_chars > 0 else 0
                
                # Multiple by number of languages
                num_languages = len(st.session_state.selected_languages)
                total_est_seconds = est_seconds_per_file * num_languages
                
                # Store results in session state for display
                st.session_state.analysis_complete = True
                st.session_state.total_chars_to_translate = total_chars
                st.session_state.files_to_translate = files_to_translate
                st.session_state.files_to_skip = files_to_skip
                st.session_state.estimated_time = total_est_seconds
                st.session_state.num_languages = num_languages
                
                # Display analysis results
                st.success(f"✓ File analysis complete")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Files to Translate", f"{files_to_translate}")
                with col2:
                    st.metric("Files to Skip", f"{files_to_skip}")
                with col3:
                    st.metric("Total Characters", f"{total_chars:,}")
                
                # Show time estimate
                st.write("### Time Estimate")
                est_minutes = int(total_est_seconds / 60)
                est_hours = int(est_minutes / 60)
                est_minutes = est_minutes % 60
                
                if est_hours > 0:
                    time_msg = f"{est_hours} hour{'s' if est_hours > 1 else ''}"
                    if est_minutes > 0:
                        time_msg += f" {est_minutes} minute{'s' if est_minutes > 1 else ''}"
                else:
                    time_msg = f"{est_minutes} minute{'s' if est_minutes > 1 else ''}"
                    if est_minutes < 1:
                        time_msg = "less than 1 minute"
                
                st.write(f"- **Estimated processing time**: {time_msg}")
                st.write(f"- Processing {total_chars:,} characters in {files_to_translate} files")
                
                if num_languages > 1:
                    st.write(f"- Translating to {num_languages} languages")
                    
                st.info("Note: Actual processing time will depend on your computer's performance and the LLM model you're using in LM Studio.")
        
        # Only show confirmation button after analysis
        if st.session_state.analysis_complete:
            st.write("### Ready to Translate")
            st.write(f"Translation will process {st.session_state.files_to_translate} files" + 
                    (f" and skip {st.session_state.files_to_skip} existing files" if st.session_state.skip_existing else "") + 
                    f", with an estimated processing time of {int(st.session_state.estimated_time / 60)} minutes.")
            st.write("Click the button below to confirm and start the translation.")
            
            # Start translation button - only show if analysis is complete
            if st.button("Confirm and Start Translation", type="primary"):
                # Get the debug mode flag from the UI if it exists, default to True for troubleshooting
                debug_mode = st.session_state.get('debug_enabled', True)
                
                with st.container():
                    st.subheader("Translation Progress")
                
                # Process translations (placeholder function for now)
                results = translate_files(selected_lectures, debug_mode)
                
                # Display results
                st.subheader("Translation Results")
                
                # Calculate statistics from results
                success_count = sum(1 for r in results if r.get("status") == "success")
                error_count = sum(1 for r in results if r.get("status") == "error")
                skipped_count = sum(1 for r in results if r.get("status") == "skipped")
                
                # Display summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Successfully Translated", f"{success_count}/{len(results)}")
                with col2:
                    st.metric("Skipped Files", f"{skipped_count}")
                with col3:
                    st.metric("Failed Files", f"{error_count}")
                
                # Add note about LM Studio requirements
                st.info("To use this translation feature, make sure you have LM Studio running with a capable translation model loaded. The API server must be enabled in LM Studio's settings.")

if __name__ == "__main__":
    main()
