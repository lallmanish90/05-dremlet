# Dreamlet Edu Video

Dreamlet Edu Video is a multi-page Streamlit application for turning course materials into finished educational videos.

At a high level, the app helps you:
- prepare and normalize transcript / slide files
- split source content into usable sections
- generate 4K images from PPTX or ZIP inputs
- generate audio with multiple TTS providers
- validate file alignment before rendering
- create MP4 videos
- support multilingual translation and multilingual TTS workflows

## Current Project Shape

This repository is not a minimal app. It contains:
- active workflow pages
- newer "final" consolidated pages
- older legacy pages
- backup pages
- packaging metadata for Python

The main app entrypoint is:
- `app.py`

The main Streamlit page folder is:
- `pages/`

## Main Workflow

The practical workflow in the current app is:

1. Adjust raw transcript / AAA / EEE content
2. Rename files into the expected format
3. Save transcript and summary sections
4. Clean or move supporting slide files
5. Generate 4K images from PPTX / ZIP
6. Generate TTS audio
7. Verify counts and fix MP4 mismatches if needed
8. Render MP4 videos
9. Verify generated MP4 output
10. Run multilingual preparation / translation / multilingual TTS if needed

## Important Pages

The core active-looking pages are:
- `pages/01 Prepare AAA EEE.py`
- `pages/02 Rename Lecture Files.py`
- `pages/03 Split Text Sections.py`
- `pages/04 Clean Unwanted Files.py`
- `pages/05 Move Slide Files.py`
- `pages/06 Generate 4K Images.py`
- `pages/07 Generate Audio with Kokoro.py`
- `pages/08 Translate with Ollama.py`
- `pages/08 Translate with LM Studio.py`
- `pages/08 Validate File Counts.py`
- `pages/09 Repair MP4 Inputs.py`
- `pages/10 Render MP4 Videos.py`
- `pages/11 Verify MP4 Output.py`
- `pages/11_Workflow_Manager.py`
- `pages/12 Delete Files.py`
- `pages/13 Delete Folders.py`
- `pages/14 Restore PPTX Files.py`
- `pages/15 Generate Audio with Inworld.py`

Additional multilingual pages:
- `pages/52 Create Multilingual Folder Structure.py`
- `pages/53 Convert Text to Multiple Languages.py`
- `pages/54 Generate Multilingual Audio.py`
- `pages/55 Generate Audio with OpenAI.py`

Legacy / alternate / backup pages are also present:
- `pages/50_Legacy_Files_Header.py`
- `pages/56_TTS_Kokoro_old.py`
- `pages/57_TTS_Kokoro_GPU_old.py`
- `pages/58 Legacy Translator Lecto.py`
- `pages/59_count_old.py`
- `pages/60 Legacy MP4 CPU.py`
- `pages/61_Adjust_Transcript_Only.py`
- `pages/99_01_Rename_BACKUP.py`
- `pages/99_02_Adjust_AAA_EEE_BACKUP.py`
- `pages/99_03_Save_Text_BACKUP.py`

## Newer Consolidated Pages

Two important newer pages exist alongside older variants:
- `pages/06 Generate 4K Images.py`
- `pages/10 Render MP4 Videos.py`

These appear to be newer consolidated "final" versions of the 4K image and MP4 GPU flows, while older named variants still remain in the repo.

## Installation

### Python

Setup:

```bash
uv sync
```

### System Dependencies

You need external system tools for media and document handling, especially:
- `ffmpeg`
- `poppler`
- `libreoffice`
- image libraries used by Pillow / OpenCV

On macOS with Homebrew:

```bash
brew install ffmpeg poppler freetype jpeg libwebp libtiff openjpeg lcms2 libreoffice
```

## Running The App

```bash
streamlit run app.py --server.port 5000
```

Then open:

```text
http://localhost:5000
```

## Folder Layout

Important project paths:

- `app.py` - main Streamlit landing page
- `pages/` - processing tools and workflow pages
- `config/` - prompt and verification config
- `config/logo.png` - branding asset used in image workflows
- `config/copyright.txt` - copyright text used in image workflows
- `config/computers.txt` - machine notes for supported hardware
- `input/` - source course content
- `output/` - generated outputs

## Config Files

Important config files:
- `config/prompt.txt` - translation prompt template
- `config/mp4_verification.json` - MP4 verification configuration

## Packaging Notes

This project now uses a single Python packaging source:
- `pyproject.toml`

Use that file as the source of truth for dependencies and environment setup.

## Codebase Convention

`pages/` follows a strict self-contained-page rule from `CODING_CONVENTIONS.md`:
- each page keeps its own helper logic
- pages do not import utilities from other pages
- duplication across pages is intentional in the current architecture

## Current State

This codebase is functional but not fully cleaned up:
- active pages and legacy pages coexist
- newer consolidated pages exist beside older variants
- some documentation / packaging layers reflect older states of the project

Treat this repository as a powerful working toolbox rather than a fully simplified final product.
