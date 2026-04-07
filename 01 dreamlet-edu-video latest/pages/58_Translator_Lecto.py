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
import json
import time
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Define supported languages
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

# Import utility functions (add a custom directory creation function)
# This is a custom implementation in case the imported function has issues
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

# Lecto API constants - using the key provided in the documentation
LECTO_API_KEY = "P66PARQ-MH44AC6-HNA9BE2-25YRH37"
LECTO_API_URL = "https://api.lecto.ai/v1/translate/text"

# Add a function to check API key validity
def check_lecto_api_key() -> Tuple[bool, str]:
    """
    Check if the Lecto API key is valid by making a small test request
    
    Returns:
        Tuple of (is_valid, message)
    """
    headers = {
        "X-API-Key": LECTO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Make a small test request to check the API key - following exact format in example
    test_data = json.dumps({
        "texts": ["Hello"],
        "to": ["es"],
        "from": "en"
    })
    
    try:
        # Use data parameter (as string) instead of json parameter
        response = requests.post(LECTO_API_URL, data=test_data, headers=headers)
        
        if response.status_code == 200:
            try:
                # Parse the response to verify it has the expected structure
                data = response.json()
                if "translations" in data:
                    # Check if the translated field exists
                    if "translated" in data["translations"][0]:
                        return True, "API key is valid"
                    else:
                        return False, "API response structure is unexpected"
                else:
                    return False, "API response is missing translations data"
            except json.JSONDecodeError:
                return False, "Invalid JSON response from API"
        elif response.status_code == 401:
            return False, "Invalid API key. Please check your credentials."
        elif response.status_code == 429:
            return False, "Rate limit exceeded. Please try again later."
        else:
            return False, f"API error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

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
            self.current_action_text.empty(
            )  # Clear the current action text when we're done


def translate_with_lecto(text: str, target_lang_code: str, debug_mode: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Translate text from English to the specified language using the Lecto API
    
    Args:
        text: Text to translate
        target_lang_code: The language code to translate to (e.g., 'es', 'fr', 'de')
        debug_mode: Whether to show detailed API responses
        
    Returns:
        Tuple of (success, message, translated_text)
    """
    if not text or text.strip() == "":
        return False, "Empty text provided", None
    
    # Using exactly the working code format from the example
    headers = {
        "X-API-Key": LECTO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Create the data payload as a JSON string
    data_json = json.dumps({
        "texts": [text],
        "to": [target_lang_code],
        "from": "en"
    })
    
    if debug_mode:
        st.write(f"Translating to language code: {target_lang_code}")
        st.write(f"API request data: {data_json}")
    
    try:
        # Send the request using data parameter (string) instead of json parameter
        response = requests.post(LECTO_API_URL, headers=headers, data=data_json)
        
        # Check for rate limits
        if response.status_code == 429:
            # Mark rate limit as hit in session state
            st.session_state.rate_limit_hit = True
            return False, "Rate limit exceeded. Please upgrade your plan or try again later.", None
        
        # Check for other errors
        if response.status_code != 200:
            return False, f"API Error: {response.status_code} - {response.text}", None
        
        # Parse the response
        try:
            response_data = response.json()
            
            if debug_mode:
                st.write("API response:", response_data)
            
            # Access the translations array using the exact response format
            if "translations" in response_data:
                for lang_obj in response_data["translations"]:
                    if lang_obj["to"] == target_lang_code and "translated" in lang_obj and len(lang_obj["translated"]) > 0:
                        translated_text = lang_obj["translated"][0]
                        return True, "Translation successful", translated_text
            
            return False, f"Translation failed: No {target_lang_code} translation found in response", None
            
        except json.JSONDecodeError:
            return False, "Error parsing API response", None
    
    except Exception as e:
        return False, f"Error in translation: {str(e)}", None

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
                status_manager.update_action(f"Translating to {target_lang_name}: {file_name}")
                success, message, translated_text = translate_with_lecto(content, target_lang_code, debug_mode)
                
                if success and translated_text:
                    # Log the file saving attempt
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
                    results.append({
                        "file_path": file_path,
                        "course": course,
                        "lecture": lecture,
                        "status": "error",
                        "message": f"Error translating to {target_lang_name}: {message}",
                        "language": target_lang_name,
                        "language_code": target_lang_code
                    })
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)
        
        except Exception as e:
            # Error reading the source file - add an error for all languages
            for target_lang_code in target_languages:
                target_lang_name = SUPPORTED_LANGUAGES.get(target_lang_code, "Unknown Language")
                results.append({
                    "file_path": file_path,
                    "course": course,
                    "lecture": lecture,
                    "status": "error",
                    "message": f"Error reading source file: {str(e)}",
                    "language": target_lang_name,
                    "language_code": target_lang_code
                })
                processed_count += 1
    
    # Complete processing
    status_manager.success("Translation complete")
    
    # Return results for further processing
    return results

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
                    # Use the lecture directory as base - important for creating Spanish text folder
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


def main():
    st.title("Translator - Lecto")

    # Add API Key information
    with st.expander("About Lecto API", expanded=False):
        st.write("""
        ### Lecto API Information
        
        This tool uses the Lecto Translation API to translate content from English to multiple languages.
        
        - **Current API Key**: P66PARQ-MH44AC6-HNA9BE2-25YRH37
        - **Subscription Plan**: Sandbox plan (valid from 05/06/2025 to 06/06/2025)
        - **Plan Usage**: 92,556/14,000,000 characters (0.66%)
        - **Rate Limits**: The API may have translation limits based on the current plan
        - **Upgrade**: If you encounter rate limit errors, you may need to upgrade your Lecto plan at [https://dashboard.lecto.ai/pricing](https://dashboard.lecto.ai/pricing)
        - **Languages Supported**: Over 90 languages including Spanish, French, German, Japanese, and more
        
        If you need to use a different API key, contact your administrator.
        
        For API documentation, see [Lecto's GitHub repository](https://github.com/lecto-ai/docs/tree/main/examples).
        """)
        
    # Check API key validity quietly in the background
    with st.spinner("Checking API key validity..."):
        key_valid, key_message = check_lecto_api_key()
        
    if not key_valid:
        st.error(f"API Key Error: {key_message}")
        st.warning("Please check the API key configuration. This will prevent successful translations until resolved.")
    # Removed success message for a cleaner UI

    # Check if we've hit rate limits and show persistent warning if needed
    if 'rate_limit_hit' in st.session_state and st.session_state.rate_limit_hit:
        st.error("""
        ### API Rate Limit Exceeded
        
        The free trial quota for Lecto API has been exceeded. To continue translating:
        
        1. Upgrade to a paid plan at [https://dashboard.lecto.ai/pricing](https://dashboard.lecto.ai/pricing)
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
    sorted_courses = sorted(organized_files.keys(),
                            key=lambda x: int(re.search(r'\d+', x).group())
                            if re.search(r'\d+', x) else 999)

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
            try:
                sorted_lectures = sorted(organized_files[course].keys(),
                                         key=lambda x: int(
                                             re.search(r'\d+', x).group()
                                             if re.search(r'\d+', x) else 999))
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
    
    # Get the list of supported languages for the multiselect
    language_options = sorted([(code, name) for code, name in SUPPORTED_LANGUAGES.items()], key=lambda x: x[1])
    
    # Initialize language selections in session state
    if 'selected_languages' not in st.session_state:
        st.session_state.selected_languages = ['es']  # Default to Spanish
        
    # Language selection UI with multiselect
    selected_lang_tuples = st.multiselect(
        "Select target languages for translation",
        options=language_options,
        format_func=lambda x: x[1],  # Display the language name
        default=[lang_tuple for lang_tuple in language_options if lang_tuple[0] in st.session_state.selected_languages],
        help="Select one or more languages to translate the content into"
    )
    
    # Update session state with selected languages
    st.session_state.selected_languages = [lang_code for lang_code, lang_name in selected_lang_tuples]
    
    # Show the selected languages summary
    if st.session_state.selected_languages:
        selected_lang_names = [SUPPORTED_LANGUAGES[code] for code in st.session_state.selected_languages if code in SUPPORTED_LANGUAGES]
        st.write("Selected languages:")
        cols = st.columns(min(4, len(selected_lang_names)))
        for i, lang_name in enumerate(selected_lang_names):
            with cols[i % len(cols)]:
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
                help="Skip files that already have translations to save API costs"
            )
            
            st.info("Debug mode will show detailed information about API requests and responses for troubleshooting.")
            st.write("Current API Endpoint: ", LECTO_API_URL)
            st.write("API Key: ", LECTO_API_KEY[:5] + "..." + LECTO_API_KEY[-5:])
            
            # Show example API request and response
            st.write("### Example API Request Format")
            st.code('''
headers = {
    "X-API-Key": "API_KEY",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

data = '{"texts": ["Hello world."], "to": ["es"], "from": "en"}'

response = requests.post('https://api.lecto.ai/v1/translate/text', headers=headers, data=data)
            ''', language="python")
        
        # Cost calculation step before translation
        st.subheader("Calculate Translation Cost")
        st.write("Calculate the cost before proceeding with translation.")
        st.write("Current pricing: $9.99/month + $0.00001 per character")
        
        # Initialize session state variables for cost calculation
        if 'cost_calculated' not in st.session_state:
            st.session_state.cost_calculated = False
        if 'total_chars_to_translate' not in st.session_state:
            st.session_state.total_chars_to_translate = 0
        if 'files_to_translate' not in st.session_state:
            st.session_state.files_to_translate = 0
        if 'files_to_skip' not in st.session_state:
            st.session_state.files_to_skip = 0
        if 'estimated_cost' not in st.session_state:
            st.session_state.estimated_cost = 0
        
        # Calculate cost button
        if st.button("Calculate Cost", type="secondary"):
            total_chars_to_translate = 0
            files_to_skip = 0
            files_to_translate = 0
            
            with st.spinner("Scanning files and calculating cost..."):
                # Get the current settings
                debug_mode = st.session_state.debug_enabled
                skip_existing = st.session_state.skip_existing
                
                # Analyze files first to count characters
                for (course, lecture), lecture_data in selected_lectures.items():
                    for file_info in lecture_data["files"]:
                        file_path = file_info["path"]
                        file_type = file_info["type"]  # "regular" or "summary"
                        source_folder = file_info["source_folder"]
                        file_name = os.path.basename(file_path)
                        
                        # Check all target languages if file exists in any of them
                        lecture_dir = lecture_data["base_dir"]
                        
                        # Count as skipped only if it exists in ALL selected languages
                        existing_in_all_languages = True
                        
                        for target_lang_code in st.session_state.selected_languages:
                            target_lang_name = SUPPORTED_LANGUAGES.get(target_lang_code, "Unknown Language")
                            
                            # Determine path for each language
                            if file_type == "regular":
                                target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                            elif file_type == "summary":
                                target_dir = os.path.join(lecture_dir, f"{target_lang_name} Summary text")
                            else:
                                # Shouldn't happen, but fall back to regular if unknown
                                target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                            
                            target_path = os.path.join(target_dir, file_name)
                            
                            # If any language doesn't have the translation yet, we need to translate
                            if not os.path.exists(target_path):
                                existing_in_all_languages = False
                        
                        if existing_in_all_languages and skip_existing:
                            files_to_skip += 1
                            if debug_mode:
                                st.info(f"Will skip existing file: {file_name} (type: {file_type}) - exists in all selected languages")
                            continue
                        
                        try:
                            # Read file content to count characters
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content and content.strip():
                                    total_chars_to_translate += len(content)
                                    files_to_translate += 1
                        except Exception as e:
                            st.error(f"Error reading file {file_path}: {str(e)}")
            
            # Calculate cost using Lecto pricing
            # $9.99/month + $0.00001 per extra character
            # Cost is per character PER language
            base_cost = 9.99  # Base plan cost, already paid
            char_cost = 0.00001  # Cost per character
            num_languages = len(st.session_state.selected_languages)
            
            # Total cost = characters × cost per character × number of languages
            estimated_cost = (total_chars_to_translate * char_cost * num_languages)
            
            # Save to session state
            st.session_state.cost_calculated = True
            st.session_state.total_chars_to_translate = total_chars_to_translate
            st.session_state.files_to_translate = files_to_translate
            st.session_state.files_to_skip = files_to_skip
            st.session_state.estimated_cost = estimated_cost
            st.session_state.num_languages = num_languages
            
            # Display cost information
            st.success(f"✓ File analysis complete")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Files to Translate", f"{files_to_translate}")
            with col2:
                st.metric("Files to Skip", f"{files_to_skip}")
            with col3:
                st.metric("Total Characters", f"{total_chars_to_translate:,}")
            
            # Show cost breakdown
            st.write("### Cost Breakdown")
            st.write(f"- Base Plan Cost: ${base_cost:.2f}/month (already paid)")
            st.write(f"- Character Cost: {total_chars_to_translate:,} characters × ${char_cost:.8f} = ${total_chars_to_translate * char_cost:.4f}")
            if num_languages > 1:
                st.write(f"- Languages: {num_languages} languages selected")
                st.write(f"- Multiple Language Cost: {total_chars_to_translate:,} characters × ${char_cost:.8f} × {num_languages} languages = ${estimated_cost:.4f}")
            st.write(f"- **Total estimated cost**: ${estimated_cost:.4f}")
        
        # Only show confirmation button after cost calculation
        if st.session_state.cost_calculated:
            st.write("### Ready to Translate")
            st.write(f"Translation will process {st.session_state.files_to_translate} files" + 
                    (f" and skip {st.session_state.files_to_skip} existing files" if st.session_state.skip_existing else "") + 
                    f", with an estimated cost of ${st.session_state.estimated_cost:.4f}.")
            st.write("Click the button below to confirm and start the translation.")
            
            # Start translation button - only show if cost has been calculated
            if st.button("Confirm and Start Translation", type="primary"):
                # Get the debug mode flag from the UI if it exists, default to True for troubleshooting
                debug_mode = st.session_state.get('debug_enabled', True)
                
                with st.container():
                    st.subheader("Translation Progress")
                
                # Process translations
                results = translate_files(selected_lectures, debug_mode)
                
                # Display results
                st.subheader("Translation Results")
                
                # Calculate statistics
                success_count = sum(1 for r in results if r["status"] == "success")
                error_count = sum(1 for r in results if r["status"] == "error")
                skipped_count = sum(1 for r in results if r["status"] == "skipped")
                total_original_chars = sum(r.get("original_length", 0) for r in results if r["status"] == "success")
                total_translated_chars = sum(r.get("translated_length", 0) for r in results if r["status"] == "success")
                
                # Display summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Successfully Translated", f"{success_count}/{len(results)}")
                with col2:
                    st.metric("Skipped Files", f"{skipped_count}")
                with col3:
                    st.metric("Failed Files", f"{error_count}")
                
                # Display character counts
                st.write(f"**Total Characters:** Original: {total_original_chars:,} → Translated: {total_translated_chars:,}")
                
                # Display cost calculation
                if total_original_chars > 0:
                    # Calculate actual cost based on characters that were successfully translated
                    char_cost = 0.00001  # Cost per character
                    actual_cost = total_original_chars * char_cost
                    st.write(f"**Cost:** {total_original_chars:,} characters × ${char_cost:.8f} = ${actual_cost:.4f}")
                
                # Group results by course and lecture
                by_lecture = {}
                for result in results:
                    key = (result["course"], result["lecture"])
                    if key not in by_lecture:
                        by_lecture[key] = []
                    by_lecture[key].append(result)
                
                # Display results by lecture
                for (course, lecture), lecture_results in by_lecture.items():
                    with st.expander(f"{course} - {lecture}", expanded=True):
                        # Count successes, errors and skipped for this lecture
                        lecture_success = sum(1 for r in lecture_results if r["status"] == "success")
                        lecture_error = sum(1 for r in lecture_results if r["status"] == "error")
                        lecture_skipped = sum(1 for r in lecture_results if r["status"] == "skipped")
                        
                        st.write(f"**Summary:** {lecture_success} successful, {lecture_error} failed, {lecture_skipped} skipped")
                        
                        # Success results
                        if lecture_success > 0:
                            st.write("**Successful Translations:**")
                            for result in lecture_results:
                                if result["status"] == "success":
                                    file_name = os.path.basename(result["file_path"])
                                    output_file = os.path.basename(result["output_path"])
                                    expansion_ratio = result["translated_length"] / result["original_length"] if result["original_length"] > 0 else 0
                                    st.write(f"- **{file_name}** → **{output_file}** ({result['original_length']:,} → {result['translated_length']:,} chars, ratio: {expansion_ratio:.2f})")
                        
                        # Skipped results
                        if lecture_skipped > 0:
                            st.write("**Skipped Files:**")
                            for result in lecture_results:
                                if result["status"] == "skipped":
                                    file_name = os.path.basename(result["file_path"])
                                    st.write(f"- **{file_name}**: {result['message']}")
                        
                        # Error results
                        if lecture_error > 0:
                            st.write("**Errors:**")
                            for result in lecture_results:
                                if result["status"] == "error":
                                    file_name = os.path.basename(result["file_path"])
                                    st.write(f"- **{file_name}**: {result['message']}")
                
                # Summarize by language
                by_language = {}
                for result in results:
                    if "language" in result and "language_code" in result:
                        lang = result["language"]
                        if lang not in by_language:
                            by_language[lang] = {
                                "success": 0,
                                "error": 0,
                                "skipped": 0
                            }
                        by_language[lang][result["status"]] += 1
                
                # Language-specific metrics
                if len(by_language) > 0:
                    st.write("### Results by Language")
                    cols = st.columns(min(3, len(by_language)))
                    for i, (lang, stats) in enumerate(by_language.items()):
                        with cols[i % len(cols)]:
                            st.metric(
                                f"{lang}", 
                                f"{stats['success']} successful",
                                f"{stats['skipped']} skipped, {stats['error']} failed"
                            )
                
                # Show completion message
                if success_count > 0 or skipped_count > 0:
                    message = []
                    # Count languages with at least one successful translation
                    successful_langs = sum(1 for lang, stats in by_language.items() if stats['success'] > 0)
                    
                    if success_count > 0:
                        selected_langs = st.session_state.get('selected_languages', ['es'])
                        if len(selected_langs) > 1:
                            message.append(f"Successfully translated {success_count} files to {successful_langs} languages")
                        else:
                            lang_name = SUPPORTED_LANGUAGES.get(selected_langs[0], "the target language")
                            message.append(f"Successfully translated {success_count} files to {lang_name}")
                    
                    if skipped_count > 0:
                        message.append(f"Skipped {skipped_count} already translated files")
                        
                    st.success(f"{', '.join(message)}. Files are saved in appropriate language folders.")
                
                # Show error message if all files failed
                if error_count == len(results):
                    st.error("All translations failed. Please check the API key and try again.")
                # Show warning if some translations failed
                elif error_count > 0:
                    st.warning(f"{error_count} translations failed. See details above.")
            
    else:
        st.warning("Please select at least one lecture to translate.")


if __name__ == "__main__":
    main()