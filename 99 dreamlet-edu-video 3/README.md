# Project Name

A Streamlit application for processing documents and media files.

## System Requirements

This project requires several system-level dependencies that were previously managed by Replit. You'll need to install these on your system:

### Required System Dependencies

#### Image Processing Libraries

- **libjpeg** - JPEG image processing
- **libwebp** - WebP image format support
- **libtiff** - TIFF image format support
- **libimagequant** - Image quantization library
- **lcms2** - Color management system
- **freetype** - Font rendering library
- **openjpeg** - JPEG 2000 codec

#### Video/Audio Processing

- **ffmpeg-full** - Complete FFmpeg suite for video/audio processing

#### PDF Processing

- **poppler-utils** - PDF rendering and manipulation utilities

#### Office Documents

- **libreoffice** - For processing office document formats

#### System Libraries

- **libGL** & **libGLU** - OpenGL libraries
- **libxcrypt** - Extended crypt library
- **tcl** & **tk** - GUI toolkit libraries
- **zlib** - Compression library
- **glibcLocales** - Locale support

### Installation Instructions

#### macOS (using Homebrew)

```bash
brew install ffmpeg poppler freetype jpeg libwebp libtiff openjpeg lcms2 libreoffice
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg poppler-utils libfreetype6-dev libjpeg-dev libwebp-dev libtiff-dev libopenjp2-7-dev liblcms2-dev libreoffice libgl1-mesa-dev libglu1-mesa-dev libxcrypt-dev tcl tk zlib1g-dev
```

#### CentOS/RHEL/Fedora

```bash
sudo dnf install ffmpeg poppler-utils freetype-devel libjpeg-devel libwebp-devel libtiff-devel openjpeg2-devel lcms2-devel libreoffice mesa-libGL-devel mesa-libGLU-devel libxcrypt-devel tcl tk zlib-devel
```

## Python Dependencies

Install Python dependencies using uv (recommended) or pip:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Running the Application

```bash
streamlit run app.py --server.port 5000
```

The application will be available at `http://localhost:5000`.

## Development

This project uses:

- **Python 3.11+**
- **Streamlit** for the web interface
- **uv** for dependency management
- Various image/video processing libraries

## Project Structure

- `app.py` - Main Streamlit application
- `pages/` - Additional Streamlit pages
- `config/` - Configuration files
- `input/` - Input files directory
- `output/` - Output files directory
- `attached_assets/` - Static assets and documentation


## Features

### 06_4K_Image_pptx_zip.py
Processes both PPTX presentations and ZIP archives containing images:
- **PPTX**: Converts slides to 4K images using LibreOffice/python-pptx/pdf2image
- **ZIP**: Extracts images, sorts by numeric prefix (1_, 2_, 3_...), upscales to 4K
- Adds logo (top-right) and copyright (bottom-center) to all images
- Output: Sequential 01.png, 02.png files in `Lecture XX/English image/` folders
- Fixed: ZIP files now create proper `Lecture XX/English image/` folder structure matching PPTX files