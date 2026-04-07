# Dreamlet Educational Video Production System

A comprehensive Streamlit-based application for automating educational video production workflows, from content processing to final video generation.

## 🎯 Overview

This system streamlines the creation of educational videos by automating various aspects of the production pipeline. It transforms educational content from transcript and slide files into professional video presentations through a series of processing steps.

## ✨ Key Features

- **📊 Dashboard**: Complete project overview with real-time status tracking
- **🔄 Workflow Management**: Automated processing pipelines with templates
- **📈 Progress Tracking**: Real-time progress monitoring with pause/resume capability
- **🛠️ Content Processing**: 14 specialized tools for different production stages
- **🌐 Multilingual Support**: Text processing and TTS in multiple languages
- **🎬 Video Generation**: High-quality 4K image and MP4 video creation
- **📱 User-Friendly Interface**: Intuitive web-based interface with contextual help

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **System Dependencies** (see Installation section below)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dreamlet-video-production
   ```

2. **Quick Installation (Recommended)**
   ```bash
   # Run the installation script
   ./install.sh
   ```

3. **Manual Installation**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

3. **Install system dependencies**

   **macOS (using Homebrew):**
   ```bash
   brew install ffmpeg poppler freetype jpeg libwebp libtiff openjpeg lcms2 libreoffice
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install ffmpeg poppler-utils libfreetype6-dev libjpeg-dev libwebp-dev libtiff-dev libopenjp2-7-dev liblcms2-dev libreoffice libgl1-mesa-dev libglu1-mesa-dev libxcrypt-dev tcl tk zlib1g-dev
   ```

4. **Run the application**
   ```bash
   streamlit run app.py --server.port 5000
   ```

   Access the application at `http://localhost:5000`

## 📁 Project Structure

```
dreamlet-video-production/
├── app.py                          # Main Streamlit application
├── pyproject.toml                  # Python project config & dependencies
├── install.sh                      # Quick installation script
├── pages/                          # Processing workflow pages
│   ├── 01_Adjust_AAA_EEE.py       # Content splitting and organization
│   ├── 02_Rename.py                # File renaming utilities
│   ├── 03_Save_Text.py             # Text section management
│   ├── 04_Remove_unwanted.py       # Content cleanup
│   ├── 05_Move_Slides.py           # Slide organization
│   ├── 06_4K_Image_pptx_zip.py     # High-resolution image generation
│   ├── 07_TTS_Kokoro.py            # Text-to-speech processing
│   ├── 09_Count_new.py             # Content validation and counting
│   ├── 09_Fix_for_mp4.py           # MP4 preparation fixes
│   ├── 10_mp4_GPU.py               # GPU-accelerated video processing
│   ├── 11_Verify_mp4.py            # Video quality verification
│   ├── 12_Delete.py                # File cleanup utilities
│   ├── 13_Delete_folder.py         # Folder management
│   └── 14_restore_pptx.py          # PowerPoint restoration
├── config/                         # Application configuration and assets
│   ├── copyright.txt               # Copyright notice
│   ├── logo.png                    # Application logo
│   ├── mp4_verification.json       # Video verification settings
│   └── prompt.txt                  # Processing prompts
├── docs/                           # Documentation and specifications
│   └── user-experience-enhancements-requirements.json
├── input/                          # Source content directory
└── output/                         # Generated content directory
```

## 🔧 Core Workflow

### 1. Content Preparation
- **AAA Files**: Video transcripts, outlines, and slide content
- **EEE Files**: Comprehensive notes, social media content, flashcards
- **PowerPoint Files**: Visual presentation slides

### 2. Processing Pipeline
1. **Adjust & Split** - Organize and split content files into sections
2. **Rename** - Standardize file naming conventions
3. **Count & Validate** - Verify content alignment and completeness
4. **Save Text** - Break content into processable sections
5. **Generate Images** - Create 4K images from presentations
6. **Text-to-Speech** - Convert text to high-quality audio
7. **Video Creation** - Combine audio and visuals into final videos

### 3. Output Generation
- **High-resolution images** (4K quality)
- **Professional audio** (MP3 format)
- **Final videos** (MP4 format)
- **Organized file structure** for easy management

## 🎛️ Application Pages

### Main Dashboard (`app.py`)
- Project overview and status tracking
- Quick access to all processing tools
- System health monitoring
- User preferences and settings

### Processing Tools (`pages/`)

| Page | Purpose | Input | Output |
|------|---------|-------|--------|
| **01_Adjust_AAA_EEE** | Split content files into sections | AAA/EEE files | Individual content sections |
| **02_Rename** | Standardize file names | Mixed file names | Consistent naming |
| **03_Save_Text** | Manage text sections | Text files | Organized sections |
| **04_Remove_unwanted** | Clean up content | Raw content | Cleaned content |
| **05_Move_Slides** | Organize presentations | Slide files | Organized slides |
| **06_4K_Image_pptx_zip** | Generate high-res images | PPTX/ZIP files | 4K PNG images |
| **07_TTS_Kokoro** | Text-to-speech conversion | Text sections | MP3 audio files |
| **09_Count_new** | Validate content alignment | All content | Validation report |
| **09_Fix_for_mp4** | Prepare for video creation | Content files | MP4-ready files |
| **10_mp4_GPU** | Create final videos | Audio + Images | MP4 videos |
| **11_Verify_mp4** | Quality assurance | MP4 files | Verification report |
| **12_Delete** | File cleanup | Selected files | Clean workspace |
| **13_Delete_folder** | Folder management | Selected folders | Organized structure |
| **14_restore_pptx** | Restore presentations | Backup files | Restored PPTX |

## 🔧 Configuration

### API Keys
The application uses OpenAI API for text processing and translation features. Configure your API key:

1. **Environment Variable** (recommended):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Direct Configuration**: The app includes fallback configuration for local development.

### Processing Settings
- **Video Quality**: 4K resolution (3840x2160)
- **Audio Format**: MP3, high quality
- **Image Format**: PNG with transparency support
- **Text Processing**: UTF-8 encoding with multilingual support

## 📋 Input File Requirements

### Content Files
- **Transcript Files**: `.txt` or `.md` format
- **Slide Descriptions**: `.txt` or `.md` format  
- **Presentation Files**: `.pptx` format
- **Archive Files**: `.zip` containing images

### File Naming Conventions
- **AAA Files**: `XX-AAA.md` (e.g., `01-AAA.md`)
- **EEE Files**: `XX-EEE.md` (e.g., `01-EEE.md`)
- **Presentations**: `XX.pptx` or descriptive names

### Directory Structure
```
input/
├── Course_Name/
│   ├── Lecture_01/
│   │   ├── 01-AAA.md
│   │   ├── 01-EEE.md
│   │   └── presentation.pptx
│   └── Lecture_02/
│       └── ...
└── Another_Course/
    └── ...
```

## 🎨 Features in Detail

### Content Splitting (AAA/EEE)
- **AAA Sections**: Video Transcript Outline, Video Transcript, Slide Content, Summary
- **EEE Sections**: Comprehensive Notes, LinkedIn Post, Socratic Dialogue, Tweet, Flashcards, Glossary
- **Automatic Organization**: Creates structured folder hierarchy
- **Validation**: Checks for missing content and sequence gaps

### Image Processing
- **4K Resolution**: Professional quality output (3840x2160)
- **Logo Integration**: Automatic logo placement
- **Copyright Protection**: Embedded copyright notices
- **Format Support**: PPTX presentations and ZIP archives
- **Batch Processing**: Handle multiple files simultaneously

### Video Generation
- **GPU Acceleration**: Faster processing with GPU support
- **Quality Control**: Automated verification and validation
- **Flexible Output**: Multiple resolution and format options
- **Progress Tracking**: Real-time processing updates

## 🛠️ Development

### Code Organization
- **Self-Contained Pages**: Each page contains all required functionality
- **No Shared Dependencies**: Pages operate independently
- **Modular Design**: Easy to add new processing steps
- **Error Handling**: Comprehensive error recovery and reporting

### Adding New Features
1. Create new page in `pages/` directory
2. Follow existing naming convention
3. Include all required functions within the page
4. Add navigation link in main app
5. Update documentation

## 🔍 Troubleshooting

### Common Issues

**Missing System Dependencies**
```bash
# Check FFmpeg installation
ffmpeg -version

# Check LibreOffice installation
libreoffice --version
```

**API Key Issues**
- Verify OpenAI API key is set correctly
- Check API quota and billing status
- Ensure key has required permissions

**File Processing Errors**
- Verify input file formats match requirements
- Check file permissions and accessibility
- Ensure sufficient disk space for processing

**Performance Issues**
- Monitor system resources during processing
- Consider GPU acceleration for video tasks
- Adjust batch sizes for large datasets

### Getting Help
1. Check the application's built-in help system
2. Review processing logs in the System Monitor
3. Verify input file formats and structure
4. Check system resource availability

## 📄 License

This project is licensed under the MIT License. See the copyright.txt file for additional copyright information.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the existing code style
4. Test thoroughly with sample data
5. Submit a pull request with detailed description

## 📞 Support

For technical support or questions:
- Review the built-in help documentation
- Check the troubleshooting section above
- Verify system requirements and dependencies
- Test with sample data to isolate issues

---

**© Presented by Nirmala © Bhairavi Educational Initiative. All rights reserved.**