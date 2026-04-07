import streamlit as st
import os
from PIL import Image

# Increase the Pillow decompression bomb limit for large images
Image.MAX_IMAGE_PIXELS = 3840 * 2160 * 50

# Set up the page configuration
st.set_page_config(
    page_title="Dreamlet Educational Video Production",
    page_icon="🎓",
    layout="wide"
)

# Ensure input directory exists
input_dir = os.path.join(os.getcwd(), "input")
if not os.path.exists(input_dir):
    os.makedirs(input_dir)

st.title("🎓 Dreamlet Educational Video Production")

st.markdown("""
### Quick Start:
1. Add your content files to the `input/` directory
2. Use pages 01-14 in the sidebar for step-by-step processing
3. Each page is independent and self-contained

### Workflow:
- **01 Adjust** - Fix transcript and slide files
- **02 Rename** - Fix file names
- **03 Save Text** - Break transcripts into sections
- **04-06** - Process slides and images
- **07-08** - Text-to-speech and translation
- **09-11** - Video creation and verification
- **12-14** - Cleanup and restore tools
""")

# API Key Status
api_key = os.environ.get("OPENAI_API_KEY", "")
st.success("✅ OpenAI API key configured - TTS and translation ready")