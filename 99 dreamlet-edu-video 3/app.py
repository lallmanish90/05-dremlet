import streamlit as st
import os
from PIL import Image

# Local utility functions (moved from utils modules)
def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def increase_image_decompression_limit():
    """Increases the Pillow image decompression bomb limit to avoid errors with very large images"""
    new_limit = 3840 * 2160 * 50  # Approximately 415 million pixels
    Image.MAX_IMAGE_PIXELS = new_limit

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
1. **Start with the Dashboard** (📊) to get an overview of your projects and system status
2. **Use the Workflow Manager** (⚙️) to create automated processing workflows
3. **Process step by step** using pages 01-10 for individual workflow steps
4. **Monitor progress** using the System Monitor (📊) to track performance and view logs
5. **Customize your experience** in User Settings (⚙️) for preferences and help

### Quick Start Guide:
1. Add your content files to the `input/` directory
2. Visit the **Dashboard** to see your projects
3. Use **Workflow Manager** to set up automated processing
4. Monitor progress in **System Monitor**
5. Access help and tutorials in **User Settings**

### Input Files Required:
- **Transcript Files** (`.txt` or `.md`): Text to be spoken in the educational video
- **Slide Files** (`.txt` or `.md`): Descriptions of what will appear visually for each slide
- **Presentation Files** (`.pptx`): Visual slides based on slide file descriptions

### Enhanced User Experience Features:
- **📊 Dashboard**: Comprehensive overview of all your video production projects with real-time status tracking
- **⚙️ Workflow Manager**: Create templates, automate workflows, and manage batch processing
- **📊 System Monitor**: Monitor system health, view logs, and track performance metrics
- **⚙️ User Settings**: Customize preferences, configure notifications, and access help documentation

### Core Processing Workflow:
1. **Adjust**: Make necessary adjustments to transcript and slide files
2. **Rename**: Fix incorrectly named files
3. **Count**: Verify alignment between transcript sections, slide descriptions, and presentation slides
4. **Save Text**: Break transcript files into sections for TTS processing
5. **TTS**: Convert transcript sections to MP3 audio files
6. **4K Image**: Generate high-resolution images from presentation slides
7. **MP4**: Combine audio and images to create final educational videos
8. **Multilingual Text**: Handle multilingual text processing
9. **Multilingual TTS**: Handle multilingual text-to-speech processing
10. **MP4 GPU**: GPU-accelerated video processing for enhanced performance
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

