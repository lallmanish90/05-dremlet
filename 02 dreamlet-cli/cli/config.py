"""
Configuration management for Dreamlet CLI

All settings are managed through config.json file.
No command-line flags - everything is configured via JSON.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class DreamletConfig:
    """Configuration class for Dreamlet CLI"""
    
    # General settings
    input_dir: str = "input"
    output_dir: str = "output"
    reports_dir: str = "reports"
    verbose: bool = False
    skip_existing: bool = True
    dry_run: bool = False
    
    # Page-specific settings
    page_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.page_settings is None:
            self.page_settings = {}

def load_config(config_file: Optional[str] = None) -> DreamletConfig:
    """
    Load configuration from JSON file
    
    Args:
        config_file: Path to configuration file (optional, defaults to config.json)
        
    Returns:
        DreamletConfig object with loaded settings
    """
    # Start with default configuration
    config = DreamletConfig()
    
    # Determine config file path
    if config_file:
        config_path = Path(config_file)
    else:
        config_path = Path("config.json")
    
    # Load from file if it exists
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Load general settings
            if 'general' in file_config:
                general = file_config['general']
                config.input_dir = general.get('input_dir', config.input_dir)
                config.output_dir = general.get('output_dir', config.output_dir)
                config.verbose = general.get('verbose', config.verbose)
                config.skip_existing = general.get('skip_existing', config.skip_existing)
                config.dry_run = general.get('dry_run', config.dry_run)
            
            # Store all page-specific settings
            for key, value in file_config.items():
                if key != 'general':
                    config.page_settings[key] = value
                    
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
            print("Using default configuration.")
    else:
        print(f"Config file {config_path} not found. Using default configuration.")
        print("A default config.json file has been created for you.")
        create_default_config()
    
    # Ensure directories exist
    os.makedirs(config.input_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.reports_dir, exist_ok=True)
    
    return config

def get_page_config(config: DreamletConfig, page_name: str) -> Dict[str, Any]:
    """
    Get configuration settings for a specific page
    
    Args:
        config: DreamletConfig object
        page_name: Name of the page (e.g., "page_06_4k_image")
        
    Returns:
        Dictionary of page-specific settings
    """
    return config.page_settings.get(page_name, {})

def create_default_config(config_file: str = "config.json") -> str:
    """
    Create a default configuration file
    
    Args:
        config_file: Path to create the config file
        
    Returns:
        Path to the created config file
    """
    default_config = {
        "general": {
            "input_dir": "input",
            "output_dir": "output",
            "verbose": True,
            "skip_existing": True,
            "dry_run": False
        },
        "page_02_rename": {
            "patterns": {
                "remove_prefixes": ["Copy of ", "copy of ", "COPY OF "],
                "standardize_extensions": True,
                "fix_spacing": True
            }
        },
        "page_03_save_text": {
            "section_markers": ["Slide ", "Section ", "Part "],
            "min_section_length": 50,
            "preserve_formatting": True
        },
        "page_04_remove_unwanted": {
            "supported_extensions": [".txt", ".md", ".pptx", ".zip", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".mp4"],
            "delete_empty_folders": True
        },
        "page_05_move_slides": {
            "target_folder": "all_slides",
            "organize_by_type": True
        },
        "page_06_4k_image": {
            "conversion_method": "libreoffice",
            "enable_auto_fallback": True,
            "create_without_logo": False,
            "target_resolution": [3840, 2160],
            "logo_path": "config/logo.png",
            "copyright_path": "config/copyright.txt"
        },
        "page_07_tts_kokoro": {
            "languages": ["English"],
            "voice": "af_bella",
            "audio_format": "mp3",
            "speed": 1.0,
            "normalize_text": True,
            "enable_timestamps": False,
            "save_timestamps": False,
            "api_url": "http://localhost:8880/v1"
        },
        "page_08_translator": {
            "target_languages": ["es", "fr", "de"],
            "model": "gemma-3-12b-it-qat",
            "temperature": 0.3,
            "api_url": "http://127.0.0.1:1234/v1",
            "api_key": "lm-studio"
        }
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default configuration file: {config_file}")
        return config_file
    except Exception as e:
        print(f"Error creating config file {config_file}: {e}")
        return ""