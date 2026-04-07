import os
import time
import json
import base64
from typing import Dict, List, Optional, Tuple
import streamlit as st
from openai import OpenAI

# Set up OpenAI client
def get_openai_client():
    # Hardcoded API key as requested by user for local use only
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    # Also check environment variable as fallback
    env_api_key = os.environ.get("OPENAI_API_KEY")
    
    # Use environment variable if set, otherwise use hardcoded key
    final_api_key = env_api_key if env_api_key else api_key
    
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    return OpenAI(api_key=final_api_key)

def get_available_voices(model_type: str = "all") -> List[Dict[str, str]]:
    """
    Get a list of available TTS voices from OpenAI
    
    Args:
        model_type: Filter voices by model type ("legacy", "new", or "all")
    
    Returns:
        List of dictionaries with voice information
    """
    # Legacy OpenAI TTS voices (tts-1 and tts-1-hd)
    legacy_voices = [
        {"id": "alloy", "name": "Alloy", "gender": "neutral", "description": "Neutral and balanced voice", "model_compat": ["tts-1", "tts-1-hd"]},
        {"id": "echo", "name": "Echo", "gender": "male", "description": "Deep and resonant male voice", "model_compat": ["tts-1", "tts-1-hd"]},
        {"id": "fable", "name": "Fable", "gender": "female", "description": "Expressive female voice with warm tone", "model_compat": ["tts-1", "tts-1-hd"]},
        {"id": "onyx", "name": "Onyx", "gender": "male", "description": "Authoritative and deep male voice", "model_compat": ["tts-1", "tts-1-hd"]},
        {"id": "nova", "name": "Nova", "gender": "female", "description": "Energetic and upbeat female voice", "model_compat": ["tts-1", "tts-1-hd"]},
        {"id": "shimmer", "name": "Shimmer", "gender": "female", "description": "Clear and professional female voice", "model_compat": ["tts-1", "tts-1-hd"]}
    ]
    
    # New GPT-4o-mini-TTS voices (includes all legacy voices plus new ones)
    new_voices = legacy_voices + [
        {"id": "coral", "name": "Coral", "gender": "female", "description": "Warm and friendly female voice", "model_compat": ["gpt-4o-mini-tts"]},
        {"id": "ash", "name": "Ash", "gender": "male", "description": "Calm and measured male voice", "model_compat": ["gpt-4o-mini-tts"]},
        {"id": "ballad", "name": "Ballad", "gender": "male", "description": "Melodic and expressive male voice", "model_compat": ["gpt-4o-mini-tts"]},
        {"id": "sage", "name": "Sage", "gender": "neutral", "description": "Wise and knowledgeable neutral voice", "model_compat": ["gpt-4o-mini-tts"]},
        {"id": "shimmer", "name": "Shimmer", "gender": "female", "description": "Clear and professional female voice", "model_compat": ["gpt-4o-mini-tts"]}
    ]
    
    # Filter voices based on model_type
    if model_type == "legacy":
        return legacy_voices
    elif model_type == "new":
        return [voice for voice in new_voices if "gpt-4o-mini-tts" in voice["model_compat"]]
    else:  # "all"
        return new_voices

def tts_cost_estimation(text: str, model: str = "tts-1") -> float:
    """
    Estimate the cost of TTS conversion
    
    Args:
        text: Text to be converted
        model: TTS model (default: tts-1)
        
    Returns:
        Estimated cost in USD
    """
    # Current OpenAI TTS pricing
    # Legacy models:
    # For tts-1: $0.015 per 1,000 characters
    # For tts-1-hd: $0.030 per 1,000 characters
    # 
    # New model (pricing might need to be updated once official):
    # For gpt-4o-mini-tts: Using $0.015 per 1,000 characters as placeholder
    
    char_count = len(text)
    
    if model == "tts-1":
        rate = 0.015 / 1000
    elif model == "tts-1-hd":
        rate = 0.030 / 1000
    elif model == "gpt-4o-mini-tts":
        # Using a placeholder rate until official pricing is available
        # Update this with the correct pricing when available
        rate = 0.015 / 1000  # Assuming same as tts-1 until confirmed
    else:
        rate = 0.015 / 1000  # Default to tts-1 pricing
    
    estimated_cost = char_count * rate
    return estimated_cost

def convert_text_to_speech(
    text: str, 
    output_path: str, 
    voice: str = "nova", 
    model: str = "tts-1",
    response_format: str = "mp3",
    instructions: str = None
) -> Tuple[bool, str]:
    """
    Convert text to speech using OpenAI's TTS API
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        voice: Voice to use for synthesis
        model: Model to use ("tts-1", "tts-1-hd", or "gpt-4o-mini-tts")
        response_format: Audio format ("mp3", "opus", "aac", "flac", "wav", "pcm")
        instructions: Optional instructions for speech style (e.g., "Speak in a cheerful tone")
        
    Returns:
        Tuple of (success, message)
    """
    client = get_openai_client()
    if not client:
        return False, "OpenAI client initialization failed"
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Prepare API call parameters
        params = {
            "model": model,
            "voice": voice,
            "input": text
        }
        
        # Add optional parameters if provided
        if response_format != "mp3":
            params["response_format"] = response_format
            
        if instructions and model == "gpt-4o-mini-tts":
            params["instructions"] = instructions
        
        # Use streaming API for the new model
        if model == "gpt-4o-mini-tts":
            with client.audio.speech.with_streaming_response.create(**params) as response:
                response.stream_to_file(output_path)
        else:
            # Legacy API for older models
            response = client.audio.speech.create(**params)
            response.stream_to_file(output_path)
        
        return True, f"Audio saved to {output_path}"
    except Exception as e:
        return False, f"Error in TTS conversion: {str(e)}"

def translate_text(
    text: str, 
    target_language: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Translate text to target language using OpenAI
    
    Args:
        text: Text to translate
        target_language: Target language code or name
        
    Returns:
        Tuple of (success, message, translated_text)
    """
    client = get_openai_client()
    if not client:
        return False, "OpenAI client initialization failed", None
    
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_language} while preserving the formatting and meaning."},
                {"role": "user", "content": text}
            ]
        )
        
        translated_text = response.choices[0].message.content.strip()
        return True, "Translation successful", translated_text
    except Exception as e:
        return False, f"Error in translation: {str(e)}", None
