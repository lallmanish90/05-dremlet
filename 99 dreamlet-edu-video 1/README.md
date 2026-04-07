# Dreamlet Educational Video Production System

A comprehensive Streamlit-powered educational video production automation tool that supports multilingual content processing and text-to-speech generation.

## Features

- Interactive Streamlit interface for content management
- Advanced transcript and slide file parsing
- Multilingual text-to-speech generation
- Intelligent file structure normalization
- Modular workflow for educational content creators
- MP4 generation with customizable settings
- Detailed content organization with folder structure

## Project Structure

```
project_root/
├── app.py                     # Main application file
├── pages/                     # Streamlit pages for each workflow step
│   ├── 01_Adjust_Transcript_Only.py    # Adjust transcript files
│   ├── 02_Adjust_Slide_Files_Only.py   # Adjust slide files
│   ├── 03_Remove_unwanted.py           # Remove unwanted content
│   ├── 04_Rename.py                    # Fix incorrectly named files
│   ├── 05_Count.py                     # Verify alignment between transcripts and slides
│   ├── 06_Save_Text.py                 # Break transcript files into sections
│   ├── 07_TTS.py                       # Convert transcript sections to audio
│   ├── 08_TTS_Local.py                 # Local text-to-speech option
│   ├── 09_Move_Slides.py               # Manage slide organization
├── utils/                     # Utility functions
├── input/                     # Input directory for source files
└── output/                    # Output directory for generated files
```

## Running on Replit

This application is optimized to run on Replit without any additional setup required.

### Quick Start

1. The application is already configured to run on Replit
2. The Streamlit server automatically starts on port 5000
3. View the application in the Replit webview

## API Key Configuration

For text-to-speech functionality, you need an OpenAI API key:

1. Set your OpenAI API key as an environment variable through the Replit Secrets
2. Name the secret `OPENAI_API_KEY` and set the value to your actual OpenAI API key

## Working with Files

- Place your input files in the `input` directory
- Generated files will appear in the `output` directory

### Expected Input Format

The application expects content organized as follows:

```
input/
├── course_01/
│   ├── lecture_01/
│   │   ├── transcript.txt     # Original transcript file
│   │   ├── slides.txt         # Original slide description file
│   │   └── presentation.pptx  # Original presentation file
│   └── lecture_02/
│       └── ... (same structure)
└── course_02/
    └── ... (same structure)
```

## Workflow

1. **Adjust Transcript**: Clean and format transcript files
2. **Adjust Slides**: Clean and format slide description files
3. **Remove Unwanted**: Remove unwanted content from files
4. **Rename**: Fix incorrectly named files
5. **Count**: Verify alignment between transcript sections, slide descriptions, and presentation slides
6. **Save Text**: Break transcript files into sections for TTS processing
7. **TTS**: Convert transcript sections to MP3 audio files
8. **TTS Local**: Alternative local text-to-speech option
9. **Move Slides**: Organize slide files for video production