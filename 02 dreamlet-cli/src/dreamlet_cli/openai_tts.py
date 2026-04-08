from __future__ import annotations

import os
import re
from typing import Optional

from openai import OpenAI


def get_input_directory() -> str:
    return os.path.join(os.getcwd(), "input")


def get_output_directory() -> str:
    return get_input_directory()


def ensure_directory_exists(directory_path: str) -> None:
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def clean_text_for_tts(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[#*_~`]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_word_count(text: str) -> int:
    return len(clean_text_for_tts(text).split())


def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    return (calculate_word_count(text) / words_per_minute) * 60


def get_available_voices(model_type: str | None = None):
    legacy = [
        {"id": "alloy", "name": "Alloy", "gender": "Neutral", "description": "Balanced default voice"},
        {"id": "echo", "name": "Echo", "gender": "Male", "description": "Clear and steady"},
        {"id": "fable", "name": "Fable", "gender": "Neutral", "description": "Expressive narrative voice"},
        {"id": "onyx", "name": "Onyx", "gender": "Male", "description": "Deep voice"},
        {"id": "nova", "name": "Nova", "gender": "Female", "description": "Bright voice"},
        {"id": "shimmer", "name": "Shimmer", "gender": "Female", "description": "Warm voice"},
    ]
    new = [
        {"id": "alloy", "name": "Alloy", "gender": "Neutral", "description": "Balanced default voice"},
        {"id": "ash", "name": "Ash", "gender": "Male", "description": "Calm voice"},
        {"id": "ballad", "name": "Ballad", "gender": "Neutral", "description": "Storytelling voice"},
        {"id": "coral", "name": "Coral", "gender": "Female", "description": "Bright voice"},
        {"id": "echo", "name": "Echo", "gender": "Male", "description": "Clear and steady"},
        {"id": "sage", "name": "Sage", "gender": "Neutral", "description": "Measured voice"},
        {"id": "shimmer", "name": "Shimmer", "gender": "Female", "description": "Warm voice"},
        {"id": "verse", "name": "Verse", "gender": "Neutral", "description": "Expressive voice"},
    ]
    if model_type == "new":
        return new
    return legacy


def tts_cost_estimation(text_or_count, model: str = "tts-1") -> float:
    if isinstance(text_or_count, str):
        character_count = len(clean_text_for_tts(text_or_count))
    else:
        character_count = int(text_or_count)

    rates = {
        "tts-1": 15.0,
        "tts-1-hd": 30.0,
        "gpt-4o-mini-tts": 12.0,
    }
    rate = rates.get(model, rates["tts-1"])
    return (character_count / 1_000_000) * rate


def convert_text_to_speech(
    text: str,
    output_path: str,
    voice: str = "alloy",
    model: str = "tts-1",
    response_format: str = "mp3",
    instructions: Optional[str] = None,
):
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False, "OPENAI_API_KEY is not set"

        ensure_directory_exists(os.path.dirname(output_path))
        client = OpenAI(api_key=api_key)
        cleaned = clean_text_for_tts(text)

        request = {
            "model": model,
            "voice": voice,
            "input": cleaned,
            "response_format": response_format,
        }
        if instructions:
            request["instructions"] = instructions

        response = client.audio.speech.create(**request)
        response.stream_to_file(output_path)
        return True, "Text-to-speech conversion successful"
    except Exception as exc:
        return False, f"Error in text-to-speech conversion: {exc}"
