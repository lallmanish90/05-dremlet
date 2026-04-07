"""
CLI Command: Translator LM Studio (Page 08)

Converts the Streamlit page 08_Translator_LM_Studio.py to CLI interface
while maintaining 100% functional parity.

This command translates English text files to multiple languages using 
LM Studio API with local LLM models.
"""

import click
import os
import sys
import re
import json
import time
import requests
import glob
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from openai import OpenAI

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress
from cli.reports import generate_report
from cli.config import load_config
from rich.console import Console

console = Console()

class StatusManager:
    """CLI-compatible status manager for translation processing"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.console = Console()
        
    def info(self, message, verbose_only=False):
        """Display info message"""
        if not verbose_only or self.verbose:
            self.console.print(f"[cyan]ℹ[/cyan] {message}")
    
    def warning(self, message):
        """Display warning message"""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def error(self, message):
        """Display error message"""
        self.console.print(f"[red]✗[/red] {message}")
    
    def success(self, message):
        """Display success message"""
        self.console.print(f"[green]✓[/green] {message}")

# Define supported languages (copied from Streamlit version)
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
    """Create a directory if it doesn't exist."""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        console.print(f"[red]Error creating directory '{directory_path}': {str(e)}[/red]")
        return False

# Path to the prompt template file
PROMPT_TEMPLATE_PATH = os.path.join("config", "prompt.txt")

# Function to load the prompt template
def load_prompt_template() -> str:
    """Load the prompt template from the config file"""
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
        console.print(f"[red]Error loading prompt template: {str(e)}[/red]")
        return "Translate the following text from English to {TARGET_LANGUAGE}: {TEXT_CONTENT}"

# Function to check LM Studio API connection
def check_lm_studio_api_key(api_url: str, api_key: str, model: str) -> Tuple[bool, str]:
    """Check if the LM Studio API server is running and accessible"""
    try:
        # Initialize the OpenAI client with the LM Studio local server
        client = OpenAI(
            base_url=api_url,
            api_key=api_key
        )
        
        # Build a minimal request to test connectivity
        from openai.types.chat import ChatCompletionUserMessageParam
        test_message = ChatCompletionUserMessageParam(role="user", content="Hello")
        response = client.chat.completions.create(
            model=model,
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
            return False, f"Could not connect to LM Studio API at {api_url}. Please make sure LM Studio is running with its API server enabled."
        elif "Timeout" in error_msg:
            return False, "Connection timed out. Is LM Studio running with its API server enabled?"
        else:
            return False, f"Error checking LM Studio API: {error_msg}"

# Function for translation with LM Studio API using LLM
def translate_with_lm_studio(
    text: str, 
    target_lang_code: str, 
    api_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.3,
    debug_mode: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """Translate text from English to the specified language using the LM Studio LLM API"""
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
        console.print(f"Translating to language: {target_language} (code: {target_lang_code})")
        console.print("Prompt template:")
        console.print(prompt_template)
        console.print("Final prompt:")
        console.print(prompt)
    
    try:
        # Initialize the OpenAI client with the LM Studio local server
        client = OpenAI(
            base_url=api_url,
            api_key=api_key
        )
        
        # Make the request to the LM Studio API using the OpenAI client
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4000  # Adjust based on expected response length
        )
        
        if debug_mode:
            console.print("API response received")
        
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
        
        # Try to provide more helpful error messages for common issues
        if "Connection" in str(e):
            error_msg = f"Could not connect to LM Studio API. Please make sure LM Studio is running with the API server enabled at {api_url}"
        elif "Timeout" in str(e):
            error_msg = "LM Studio API request timed out. The model might be processing a large request or not loaded correctly."
        elif "404" in str(e):
            error_msg = f"Model '{model}' not found. Please check that you have the correct model loaded in LM Studio."
            
        return False, error_msg, None

def find_english_text_files() -> Dict[str, Dict[str, Dict]]:
    """Find all English text files in all Lecture folders"""
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

def translate_files(
    english_files: Dict,
    target_languages: List[str],
    api_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.3,
    skip_existing: bool = True,
    debug_mode: bool = False,
    status_manager: StatusManager = None
) -> List[Dict]:
    """Translate all files from English to multiple languages"""
    
    if not target_languages:
        console.print("[red]No target languages specified[/red]")
        return []
    
    all_files = []
    lecture_file_map = {}
    
    # Collect all files and create a flat list for progress tracking
    for course_name, lectures in english_files.items():
        for lecture_name, lecture_data in lectures.items():
            for file_info in lecture_data["files"]:
                all_files.append(file_info)
                lecture_file_map[file_info["path"]] = (course_name, lecture_name, lecture_data)
    
    # Total number of translations = files × languages
    total_operations = len(all_files) * len(target_languages)
    
    if status_manager:
        status_manager.info(f"Processing {len(all_files)} files for {len(target_languages)} languages ({total_operations} total operations)")
    
    results = []
    processed_count = 0
    total_chars_translated = 0
    
    # Process each file for each selected language
    for file_info in all_files:
        file_path = file_info["path"]
        file_type = file_info["type"]  # "regular" or "summary"
        source_folder = file_info["source_folder"]
        
        # Get the associated course and lecture
        course, lecture, lecture_data = lecture_file_map[file_path]
        file_name = os.path.basename(file_path)
        
        # Read the file content once for all languages
        try:
            if status_manager:
                status_manager.info(f"Reading file: {file_name}", verbose_only=True)
            
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
                
                if status_manager:
                    status_manager.info(f"({processed_count}/{total_operations}) {course} - {lecture} - {file_name} → {target_lang_name}")
                
                # Determine output directory and path based on file type and language
                lecture_dir = lecture_data["base_dir"]
                
                # Follow the exact folder naming convention: "[Language] text" and "[Language] Summary text"
                if file_type == "regular":
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                elif file_type == "summary":
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} Summary text")
                else:
                    # Shouldn't happen, but fall back to regular if unknown
                    target_dir = os.path.join(lecture_dir, f"{target_lang_name} text")
                
                # Create the language-specific folder if it doesn't exist
                ensure_directory_exists(target_dir)
                
                # Output file has the same name but in language-specific folder
                target_path = os.path.join(target_dir, file_name)
                
                # Check if the file already exists
                if os.path.exists(target_path) and skip_existing:
                    if status_manager:
                        status_manager.info(f"File already exists in {target_lang_name}: {file_name} - Skipping", verbose_only=True)
                    
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
                if status_manager:
                    status_manager.info(f"Translating to {target_lang_name}", verbose_only=True)
                
                success, message, translated_text = translate_with_lm_studio(
                    content, target_lang_code, api_url, api_key, model, temperature, debug_mode
                )
                
                if success and translated_text:
                    # Save translated text
                    if status_manager:
                        status_manager.info(f"Writing translated {target_lang_name} file", verbose_only=True)
                        
                    try:
                        with open(target_path, 'w', encoding='utf-8') as f:
                            f.write(translated_text)
                        
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
            if status_manager:
                status_manager.error(f"Error processing file {file_name}: {str(e)}")
            
            results.append({
                "file_path": file_path,
                "course": course,
                "lecture": lecture,
                "status": "error",
                "message": f"Error: {str(e)}",
                "language": "All"
            })
    
    if status_manager:
        status_manager.success(f"Completed {processed_count} translation operations with {total_chars_translated:,} characters processed")
    
    return results

def run_translator_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the Translator processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Create status manager
    status_manager = StatusManager(verbose=ctx_obj.get('verbose', False))
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_08_translator')
    
    # Extract settings from config
    target_languages = page_config.get('target_languages', ['es', 'fr', 'de'])
    model = page_config.get('model', 'gemma-3-12b-it-qat')
    temperature = page_config.get('temperature', 0.3)
    api_url = page_config.get('api_url', 'http://127.0.0.1:1234/v1')
    api_key = page_config.get('api_key', 'lm-studio')
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_files": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Scanning input directory: {input_dir}")
    
    # Check for LM Studio API connection
    connection_status, connection_message = check_lm_studio_api_key(api_url, api_key, model)
    
    if not connection_status:
        error_msg = f"Cannot connect to LM Studio API: {connection_message}"
        status_manager.error(error_msg)
        status_manager.info(f"Please ensure LM Studio is running with API server enabled at {api_url}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_files": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.success(connection_message)
    
    # Find English text files
    english_files = find_english_text_files()
    
    if not english_files:
        warning_msg = "No English text files found in input directory"
        status_manager.warning(warning_msg)
        status_manager.info("Looking for folders named 'English text' and 'English Summary text'")
        return {
            "status": "warning",
            "message": warning_msg,
            "statistics": {"total_files": 0, "processed_count": 0, "error_count": 0}
        }
    
    # Count total files
    total_files = sum(
        len(lecture_data["files"]) 
        for course_data in english_files.values() 
        for lecture_data in course_data.values()
    )
    
    status_manager.info(f"Found {total_files} English text files in {len(english_files)} courses")
    status_manager.info(f"Target languages: {', '.join([SUPPORTED_LANGUAGES.get(lang, lang) for lang in target_languages])}")
    
    # Process files with progress tracking
    overall_start_time = time.time()
    
    with DreamletProgress(description="Translating files", total=total_files * len(target_languages)) as progress:
        
        # Translate files
        results = translate_files(
            english_files=english_files,
            target_languages=target_languages,
            api_url=api_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            skip_existing=True,
            debug_mode=False,
            status_manager=status_manager
        )
        
        # Update progress
        progress.update(completed=len(results))
    
    # Calculate statistics
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    total_chars = sum(r.get("original_length", 0) for r in results if r["status"] == "success")
    total_processing_time = time.time() - overall_start_time
    
    # Determine final status
    if error_count > 0 and success_count == 0:
        final_status = "error"
        status_message = f"Failed to translate any files ({error_count} errors)"
    elif error_count > 0:
        final_status = "warning"
        status_message = f"Translated {success_count} files with {error_count} errors ({skipped_count} skipped)"
    elif success_count == 0:
        final_status = "warning"
        status_message = f"No files were translated ({skipped_count} skipped, {error_count} errors)"
    else:
        final_status = "success"
        status_message = f"Successfully translated {success_count} files ({total_chars:,} characters, {skipped_count} skipped)"
    
    # Show summary
    status_manager.success(status_message) if final_status == "success" else \
    status_manager.warning(status_message) if final_status == "warning" else \
    status_manager.error(status_message)
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "english_files_found": total_files,
            "courses_found": len(english_files),
            "target_languages": target_languages
        },
        "processing_results": results,
        "statistics": {
            "total_files": total_files,
            "total_operations": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "total_characters": total_chars,
            "processing_time": total_processing_time
        },
        "settings": {
            "model": model,
            "temperature": temperature,
            "api_url": api_url,
            "target_languages": target_languages
        },
        "api_info": {
            "connection_status": connection_message,
            "model_used": model
        },
        "errors": [r for r in results if r["status"] == "error"],
        "output_files": [r.get("output_path") for r in results if r["status"] == "success" and r.get("output_path")]
    }
    
    # Generate report
    report_path = generate_report("08", "Translation Processing", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

@click.command()
@click.pass_context
def translate_lm_studio(ctx):
    """
    Translate English text files to multiple languages using LM Studio API
    
    This command processes text files in "English text" and "English Summary text" 
    folders and translates them to multiple target languages using a local LM Studio 
    API with LLM models.
    
    All settings are configured in config.json under "page_08_translator":
    - target_languages: List of language codes (e.g., ["es", "fr", "de"])
    - model: LM Studio model name (e.g., "gemma-3-12b-it-qat")
    - temperature: Translation creativity (0.0 to 1.0)
    - api_url: LM Studio API endpoint
    - api_key: API key (usually "lm-studio" for local)
    
    Examples:
        dreamlet run 08                    # Translate with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        from rich.console import Console
        console = Console()
        console.print("[yellow]DRY RUN MODE - No files will be processed[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_08_translator')
        target_languages = page_config.get('target_languages', ['es', 'fr', 'de'])
        model = page_config.get('model', 'gemma-3-12b-it-qat')
        api_url = page_config.get('api_url', 'http://127.0.0.1:1234/v1')
        
        console.print(f"Would translate to languages: {', '.join([SUPPORTED_LANGUAGES.get(lang, lang) for lang in target_languages])}")
        console.print(f"Would use model: {model}")
        console.print(f"Would connect to: {api_url}")
        return
    
    # Run the Translator processing operation
    try:
        results = run_translator_processing(ctx.obj)
        
        # Exit with appropriate code based on results
        if results["status"] == "error":
            sys.exit(1)
        elif results["status"] == "warning":
            sys.exit(2)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        from rich.console import Console
        console = Console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    translate_lm_studio()