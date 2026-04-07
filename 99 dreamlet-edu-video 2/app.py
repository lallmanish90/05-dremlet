import streamlit as st
import os
import sys
from utils.file_operations import ensure_directory_exists, get_input_directory
from utils.image_helpers import increase_image_decompression_limit

# License validation - must be first
if 'license_validated' not in st.session_state:
    try:
        from license_validator import LicenseValidator
        validator = LicenseValidator()
        valid, message = validator.validate_license()
        
        if not valid:
            st.error("🚫 License Validation Failed")
            st.error(f"Error: {message}")
            st.info("Please contact your administrator for assistance.")
            st.stop()
        else:
            st.session_state.license_validated = True
    except Exception as e:
        st.error("🚫 License System Error")
        st.error(f"Cannot initialize license validation: {e}")
        st.stop()

# Increase the Pillow decompression bomb limit for large images
increase_image_decompression_limit()

# Set up the page configuration
st.set_page_config(
    page_title="Dreamlet Educational Video Production System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure input directory exists
ensure_directory_exists(get_input_directory())

# Main page
st.title("Dreamlet Educational Video Production System")
st.subheader("Educational Video Production Automation")

# Introduction
st.markdown("""
This application streamlines the creation of educational videos by automating various aspects of the production pipeline.
The system facilitates the transformation of educational content from transcript and slide files into professional video presentations.

### How to Use This Application:
1. Use the sidebar to navigate between different functions
2. Each page represents a step in the video production workflow
3. Follow the steps in sequential order for best results
4. Ensure your input files follow the expected format and structure

### Input Files Required:
- **Transcript Files** (`.txt` or `.md`): Text to be spoken in the educational video
- **Slide Files** (`.txt` or `.md`): Descriptions of what will appear visually for each slide
- **Presentation Files** (`.pptx`): Visual slides based on slide file descriptions

### Workflow:
1. **Adjust**: Make necessary adjustments to transcript and slide files
2. **Rename**: Fix incorrectly named files
3. **Count**: Verify alignment between transcript sections, slide descriptions, and presentation slides
4. **Save Text**: Break transcript files into sections for TTS processing
5. **TTS**: Convert transcript sections to MP3 audio files
6. **4K Image**: Generate high-resolution images from presentation slides
7. **MP4**: Combine audio and images to create final educational videos
8. **Multilingual Text**: Handle multilingual text processing
9. **Multilingual TTS**: Handle multilingual text-to-speech processing
""")

# Directory structure information
st.header("Folder Structure")
st.markdown("""
The application operates directly on the input folder structure. All file modifications and generated assets
will be created within the same folder structure:

```
input/
├── course_01/
│   ├── lecture_01/
│   │   ├── transcript.txt                 # Original transcript file
│   │   ├── slides.txt                     # Original slide description file
│   │   ├── presentation.pptx              # Original presentation file
│   │   ├── audio/                         # Generated audio files
│   │   │   └── slide_01.mp3, slide_02.mp3, etc.
│   │   ├── images/                        # Extracted slide images
│   │   │   └── slide_01.png, slide_02.png, etc.
│   │   ├── sections/                      # Text broken into sections
│   │   │   └── section_01.txt, section_02.txt, etc.
│   │   └── video.mp4                      # Final generated video
│   └── lecture_02/
│       └── ... (same structure)
└── course_02/
    └── ... (same structure)
```
""")

# API Key Status check
st.header("API Key Status")
# Hardcoded API key as requested by user for local use only
hardcoded_api_key = os.environ.get("OPENAI_API_KEY", "")
# Also check environment variable
env_api_key = os.environ.get("OPENAI_API_KEY")
# Use environment variable if set, otherwise use hardcoded key
api_key = env_api_key if env_api_key else hardcoded_api_key

st.success("✅ OpenAI API key is configured. Text-to-speech and translation features are ready to use.")

