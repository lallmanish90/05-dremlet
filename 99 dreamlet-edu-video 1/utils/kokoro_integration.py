import os
import time
import json
import requests
from typing import Dict, List, Optional, Tuple
import streamlit as st

# Kokoro API endpoint (running locally)
KOKORO_API_URL = "http://localhost:8880/v1"

def get_available_voices() -> List[Dict[str, str]]:
    """
    Get available voices from the Kokoro API
    
    Returns:
        List of voice information dictionaries
    """
    try:
        response = requests.get(f"{KOKORO_API_URL}/audio/voices")
        voices_data = response.json()
        
        # Parse the voice data and format it for display
        voice_list = []
        for voice_id in voices_data.get("voices", []):
            # Extract basic information from the voice ID
            # Voice IDs are in format like "af_bella", "am_echo", etc.
            parts = voice_id.split('_')
            
            if len(parts) >= 2:
                language_code = parts[0]
                voice_name = parts[1]
                
                # Determine gender and language
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
                
                # Create a description field like OpenAI's format
                description = f"{language_name} voice"
                
                voice_list.append({
                    "id": voice_id,
                    "name": voice_name.capitalize(),
                    "gender": gender,
                    "language": language_name,
                    "description": description
                })
        
        # Sort voices by language, then by name
        return sorted(voice_list, key=lambda x: (x["language"], x["name"]))
    
    except Exception as e:
        st.error(f"Error retrieving voices from Kokoro API: {str(e)}")
        return []

def tts_cost_estimation(word_count: int, model: str = "kokoro") -> float:
    """
    Estimate cost for TTS processing (always returns 0 for local Kokoro TTS)
    
    Args:
        word_count: Number of words in the text
        model: TTS model (always "kokoro" for now)
        
    Returns:
        Estimated cost (always 0 for local Kokoro TTS)
    """
    # Local Kokoro TTS has no direct API costs
    return 0.0

def generate_combined_voice(voice_weights: Dict[str, float]) -> Tuple[bool, str, Optional[str]]:
    """
    Generate a combined voice string for direct use in TTS API
    
    Args:
        voice_weights: Dictionary mapping voice IDs to their weights
        
    Returns:
        Tuple of (success, message, combined_voice_string or None)
    """
    if not voice_weights:
        return False, "No voices specified for combination", None
    
    try:
        # Format the voice combination string
        # Format: voice1(weight1)+voice2(weight2)+...
        voice_combination = "+".join([f"{voice}({int(weight)})" for voice, weight in voice_weights.items()])
        
        # Return the combined voice string for direct use in the TTS API
        # No need to save the voice - we'll use the combination string directly
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
    save_timestamps: bool = False
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Convert text to speech using Kokoro's TTS API
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        voice: Voice to use for synthesis
        model: Model to use (always "kokoro" for now)
        response_format: Audio format ("mp3", "wav")
        speed: Speech speed (default: 1.0)
        enable_timestamps: Generate word-level timestamps
        normalize_text: Apply text normalization
        save_timestamps: Save timestamps to a JSON file alongside the audio
        
    Returns:
        Tuple of (success, message, timestamps if requested)
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Prepare API call parameters
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
        
        # Add timestamp options if enabled
        if enable_timestamps:
            params["timestamps"] = True
        
        # Make the API call
        response = requests.post(
            f"{KOKORO_API_URL}/audio/speech",
            json=params
        )
        
        if response.status_code != 200:
            return False, f"API request failed with status {response.status_code}: {response.text}", None
        
        # Check if we have timestamps in the response headers
        timestamps = None
        if enable_timestamps and 'x-timestamps' in response.headers:
            try:
                timestamps = json.loads(response.headers['x-timestamps'])
                
                # Save timestamps to a JSON file if requested
                if save_timestamps:
                    timestamps_path = os.path.splitext(output_path)[0] + '.json'
                    with open(timestamps_path, 'w', encoding='utf-8') as f:
                        json.dump(timestamps, f, indent=2)
            except Exception as e:
                st.warning(f"Generated audio successfully, but could not parse timestamps: {str(e)}")
        
        # Save the audio file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return True, "Text-to-speech conversion successful", timestamps
    
    except Exception as e:
        return False, f"Error in text-to-speech conversion: {str(e)}", None

def check_connection() -> Tuple[bool, str]:
    """
    Check if the Kokoro API is accessible
    
    Returns:
        Tuple of (connected, message)
    """
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
    """
    Check if the Kokoro API is using GPU
    
    Returns:
        Tuple of (gpu_available, details)
    """
    try:
        response = requests.get(f"{KOKORO_API_URL}/debug/system", timeout=5)
        if response.status_code == 200:
            system_info = response.json()
            # Check if there's GPU information in the system info
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