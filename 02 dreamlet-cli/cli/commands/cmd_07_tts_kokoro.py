"""
CLI Command: TTS Kokoro (Page 07)

Converts the Streamlit page 07_TTS_Kokoro.py to CLI interface
while maintaining 100% functional parity.

This command converts transcript and summary sections to audio files using 
local Kokoro Text-to-Speech API with GPU acceleration support.
"""

import click
import os
import sys
import re
import time
import json
import requests
import fnmatch
import glob
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress
from cli.reports import generate_report
from cli.config import load_config
from rich.console import Console

console = Console()

class StatusManager:
    """CLI-compatible status manager for TTS processing"""
    
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

# Local utility functions (copied from Streamlit version)
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

def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate audio duration based on word count"""
    word_count = calculate_word_count(text)
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60

# Kokoro API integration functions
def get_available_voices(api_url: str) -> List[Dict[str, str]]:
    """Get available voices from the Kokoro API"""
    try:
        response = requests.get(f"{api_url}/audio/voices")
        voices_data = response.json()
        
        voice_list = []
        for voice_id in voices_data.get("voices", []):
            parts = voice_id.split('_')
            
            if len(parts) >= 2:
                language_code = parts[0]
                voice_name = parts[1]
                
                language_name = "English"
                gender = "Female"
                
                if language_code == "am" or language_code == "bm" or language_code == "em" or language_code == "hm" or language_code == "im" or language_code == "jm" or language_code == "pm" or language_code == "zm":
                    gender = "Male"
                
                if language_code == "bf" or language_code == "bm":
                    language_name = "British English"
                elif language_code == "ef" or language_code == "em":
                    language_name = "European English"
                elif language_code == "ff":
                    language_name = "French"
                elif language_code == "hf" or language_code == "hm":
                    language_name = "Hindi"
                elif language_code == "if" or language_code == "im":
                    language_name = "Italian"
                elif language_code == "jf" or language_code == "jm":
                    language_name = "Japanese"
                elif language_code == "pf" or language_code == "pm":
                    language_name = "Portuguese"
                elif language_code == "zf" or language_code == "zm":
                    language_name = "Chinese"
                
                description = f"{language_name} voice"
                
                voice_list.append({
                    "id": voice_id,
                    "name": voice_name.capitalize(),
                    "gender": gender,
                    "language": language_name,
                    "description": description
                })
        
        return sorted(voice_list, key=lambda x: (x["language"], x["name"]))
    
    except Exception as e:
        console.print(f"[red]Error retrieving voices from Kokoro API: {str(e)}[/red]")
        return []

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
    api_url: str = "http://localhost:8880/v1"
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
                "normalize": normalize_text
            }
        }
        
        if enable_timestamps:
            params["timestamps"] = True
        
        response = requests.post(
            f"{api_url}/audio/speech",
            json=params
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
                console.print(f"[yellow]Generated audio successfully, but could not parse timestamps: {str(e)}[/yellow]")
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return True, "Text-to-speech conversion successful", timestamps
    
    except Exception as e:
        return False, f"Error in text-to-speech conversion: {str(e)}", None

def check_connection(api_url: str) -> Tuple[bool, str]:
    """Check if the Kokoro API is accessible"""
    try:
        response = requests.get(f"{api_url}/audio/voices", timeout=5)
        if response.status_code == 200:
            return True, "Connected to Kokoro API"
        else:
            return False, f"API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Connection error: Could not connect to Kokoro API ({api_url})"
    except requests.exceptions.Timeout:
        return False, "Connection timeout: Kokoro API did not respond in time"
    except Exception as e:
        return False, f"Error checking Kokoro API connection: {str(e)}"
        
def check_gpu_availability(api_url: str) -> Tuple[bool, str]:
    """Check if the Kokoro API is using GPU"""
    try:
        response = requests.get(f"{api_url}/debug/system", timeout=5)
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
    "tm": "Turkish"
}

def get_language_from_voice_id(voice_id: str) -> str:
    """Extract the language name from a voice ID"""
    prefix = voice_id.split('_')[0]
    return LANGUAGE_MAP.get(prefix, "Unknown")

def find_language_section_files(language: str = "English") -> Dict[str, Dict[str, Dict]]:
    """Find all section files for a specific language created by the previous step"""
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
    save_timestamps: bool = False,
    api_url: str = "http://localhost:8880/v1",
    status_manager: StatusManager = None
) -> List[Dict]:
    """Generate TTS for a list of section files"""
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
            success, message, timestamps = convert_text_to_speech(
                text=content,
                voice=voice,
                model=model,
                output_path=output_path,
                response_format=response_format,
                speed=speed,
                enable_timestamps=enable_timestamps,
                normalize_text=normalize_text,
                save_timestamps=save_timestamps,
                api_url=api_url
            )
            
            # Stop timing
            processing_time = time.time() - start_time
            
            if success:
                # Add additional statistics
                result = {
                    "success": True,
                    "file": file_path,
                    "output": output_path,
                    "status": "processed",
                    "message": message,
                    "processing_time": processing_time,
                    "word_count": word_count,
                    "timestamps": timestamps
                }
                
                # Add to results list
                results.append(result)
            else:
                # Add failure information
                result = {
                    "success": False,
                    "file": file_path,
                    "status": "failed",
                    "message": message,
                    "processing_time": processing_time,
                    "word_count": word_count
                }
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

def run_tts_kokoro_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the TTS Kokoro processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Create status manager
    status_manager = StatusManager(verbose=ctx_obj.get('verbose', False))
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_07_tts_kokoro')
    
    # Extract settings from config
    languages = page_config.get('languages', ['English'])
    voice = page_config.get('voice', 'af_bella')
    audio_format = page_config.get('audio_format', 'mp3')
    speed = page_config.get('speed', 1.0)
    normalize_text = page_config.get('normalize_text', True)
    enable_timestamps = page_config.get('enable_timestamps', False)
    save_timestamps = page_config.get('save_timestamps', False)
    api_url = page_config.get('api_url', 'http://localhost:8880/v1')
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_languages": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Scanning input directory: {input_dir}")
    
    # Check for Kokoro API connection
    connection_status, connection_message = check_connection(api_url)
    
    if not connection_status:
        error_msg = f"Cannot connect to Kokoro API: {connection_message}"
        status_manager.error(error_msg)
        status_manager.info(f"Please ensure the Kokoro TTS server is running at {api_url}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_languages": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.success(connection_message)
    
    # Check GPU availability
    gpu_available, gpu_message = check_gpu_availability(api_url)
    if gpu_available:
        status_manager.success(f"🚀 {gpu_message}")
    else:
        status_manager.warning(f"💻 {gpu_message} - Processing may be slower")
        status_manager.info("For better performance, ensure CUDA and PyTorch GPU support are properly configured")
    
    # Get available voices
    available_voices = get_available_voices(api_url)
    if not available_voices:
        error_msg = "No voices available from Kokoro API"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_languages": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Found {len(available_voices)} available voices")
    
    # Process each language
    all_language_results = {}
    total_languages = len(languages)
    processed_languages = 0
    overall_start_time = time.time()
    
    status_manager.info(f"Processing {total_languages} languages: {', '.join(languages)}")
    
    with DreamletProgress(description="Processing languages", total=total_languages) as progress:
        
        for language in languages:
            status_manager.info(f"Processing language: {language}")
            
            # Find files for this language
            language_files = find_language_section_files(language=language)
            
            if not language_files:
                status_manager.warning(f"No files found for {language}. Skipping.")
                all_language_results[language] = []
                processed_languages += 1
                progress.update(completed=processed_languages)
                continue
            
            # Create results container for this language
            language_results = []
            
            # Count total sections for this language
            total_sections = 0
            for course, lectures in language_files.items():
                for lecture, lecture_data in lectures.items():
                    total_sections += len(lecture_data["transcript"]["section_files"])
                    total_sections += len(lecture_data["summary"]["section_files"])
            
            status_manager.info(f"Found {total_sections} sections for {language}")
            
            # Process each lecture for this language
            for course, lectures in language_files.items():
                for lecture, lecture_data in lectures.items():
                    status_manager.info(f"Processing {course} - {lecture}", verbose_only=True)
                    
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
                            voice=voice,
                            model="kokoro",
                            output_dir=transcript_audio_dir,
                            response_format=audio_format,
                            speed=speed,
                            normalize_text=normalize_text,
                            enable_timestamps=enable_timestamps,
                            save_timestamps=save_timestamps,
                            api_url=api_url,
                            status_manager=status_manager
                        )
                        language_results.extend(transcript_results)
                    
                    # Process summary files
                    if lecture_data["summary"]["section_files"]:
                        summary_results = generate_tts_for_sections(
                            section_files=lecture_data["summary"]["section_files"],
                            voice=voice,
                            model="kokoro",
                            output_dir=summary_audio_dir,
                            response_format=audio_format,
                            speed=speed,
                            normalize_text=normalize_text,
                            enable_timestamps=enable_timestamps,
                            save_timestamps=save_timestamps,
                            api_url=api_url,
                            status_manager=status_manager
                        )
                        language_results.extend(summary_results)
            
            # Store results for this language
            all_language_results[language] = language_results
            
            # Calculate language statistics
            success_count = sum(1 for r in language_results if r["success"])
            failure_count = sum(1 for r in language_results if not r["success"])
            total_words = sum(r.get("word_count", 0) for r in language_results)
            
            status_manager.success(f"{language} complete: {success_count}/{len(language_results)} files processed ({total_words:,} words)")
            
            processed_languages += 1
            progress.update(completed=processed_languages)
    
    # Calculate overall statistics
    total_files = sum(len(results) for results in all_language_results.values())
    total_successes = sum(sum(1 for r in results if r["success"]) for results in all_language_results.values())
    total_failures = total_files - total_successes
    overall_success_rate = (total_successes / total_files) * 100 if total_files > 0 else 0
    total_words = sum(sum(r.get("word_count", 0) for r in results) for results in all_language_results.values())
    total_processing_time = time.time() - overall_start_time
    
    # Determine final status
    if total_failures > 0 and total_successes == 0:
        final_status = "error"
        status_message = f"Failed to process any files ({total_failures} errors)"
    elif total_failures > 0:
        final_status = "warning"
        status_message = f"Processed {total_successes} files with {total_failures} errors ({overall_success_rate:.1f}% success rate)"
    elif total_files == 0:
        final_status = "warning"
        status_message = "No files were found to process"
    else:
        final_status = "success"
        status_message = f"Successfully processed {total_successes} files ({total_words:,} words, {overall_success_rate:.1f}% success rate)"
    
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
            "languages_processed": languages,
            "total_languages": total_languages
        },
        "processing_results": all_language_results,
        "statistics": {
            "total_languages": total_languages,
            "total_files": total_files,
            "processed_count": total_successes,
            "error_count": total_failures,
            "success_rate": overall_success_rate,
            "total_words": total_words,
            "processing_time": total_processing_time
        },
        "settings": {
            "voice": voice,
            "audio_format": audio_format,
            "speed": speed,
            "normalize_text": normalize_text,
            "enable_timestamps": enable_timestamps,
            "save_timestamps": save_timestamps,
            "api_url": api_url
        },
        "api_info": {
            "connection_status": connection_message,
            "gpu_status": gpu_message,
            "available_voices": len(available_voices)
        },
        "errors": [r for results in all_language_results.values() for r in results if not r["success"]],
        "output_files": [r.get("output") for results in all_language_results.values() for r in results if r["success"] and r.get("output")]
    }
    
    # Generate report
    report_path = generate_report("07", "TTS Kokoro Processing", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

@click.command()
@click.pass_context
def tts_kokoro(ctx):
    """
    Convert transcript and summary sections to audio files using Kokoro TTS
    
    This command processes text files in language-specific folders (e.g., "English text", 
    "English Summary text") and converts them to audio using the local Kokoro Text-to-Speech API.
    
    All settings are configured in config.json under "page_07_tts_kokoro":
    - languages: List of languages to process (e.g., ["English"])
    - voice: Voice ID to use (e.g., "af_bella")
    - audio_format: Output format ("mp3" or "wav")
    - speed: Speech speed (0.5 to 2.0)
    - normalize_text: Clean text for better TTS
    - enable_timestamps: Generate word-level timestamps
    - save_timestamps: Save timestamps to JSON files
    - api_url: Kokoro API endpoint
    
    Examples:
        dreamlet run 07                    # Process with settings from config.json
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
        page_config = get_page_config(config, 'page_07_tts_kokoro')
        languages = page_config.get('languages', ['English'])
        voice = page_config.get('voice', 'af_bella')
        audio_format = page_config.get('audio_format', 'mp3')
        api_url = page_config.get('api_url', 'http://localhost:8880/v1')
        
        console.print(f"Would process languages: {', '.join(languages)}")
        console.print(f"Would use voice: {voice}")
        console.print(f"Would generate {audio_format} files")
        console.print(f"Would connect to: {api_url}")
        return
    
    # Run the TTS Kokoro processing operation
    try:
        results = run_tts_kokoro_processing(ctx.obj)
        
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
    tts_kokoro()