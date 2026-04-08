import os
from pathlib import Path
import re
import shutil

import streamlit as st
from PIL import Image


APP_DIR = Path(__file__).resolve().parent
PAGES_DIR = APP_DIR / "pages"


def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")


def increase_image_decompression_limit() -> None:
    """Increase Pillow's decompression bomb limit for very large images"""
    Image.MAX_IMAGE_PIXELS = 3840 * 2160 * 50


def page(file_name: str, title: str, icon: str = ""):
    return st.Page(str(PAGES_DIR / file_name), title=title, icon=icon)


def get_output_directory() -> str:
    """Get the path to the output directory"""
    return os.path.join(os.getcwd(), "output")


def build_homepage_context() -> dict:
    input_dir = Path(get_input_directory())
    output_dir = Path(get_output_directory())

    input_counts = {
        "courses": 0,
        "lectures": 0,
        "aaa_files": 0,
        "eee_files": 0,
        "transcript_files": 0,
        "slide_files": 0,
        "pptx_files": 0,
    }
    generated_counts = {
        "text_section_files": 0,
        "summary_section_files": 0,
        "audio_folders": 0,
        "image_folders": 0,
        "language_folders": 0,
        "mp4_files": 0,
    }

    if input_dir.exists():
        input_counts["courses"] = sum(
            1 for path in input_dir.iterdir() if path.is_dir() and not path.name.startswith(".")
        )

        for path in input_dir.rglob("*"):
            if path.is_dir():
                if re.search(r"lecture\s*\d+", path.name, re.IGNORECASE):
                    input_counts["lectures"] += 1
                if path.name.endswith(" audio"):
                    generated_counts["audio_folders"] += 1
                if path.name.endswith(" image"):
                    generated_counts["image_folders"] += 1
                continue

            if not path.is_file():
                continue

            name = path.name
            if re.match(r"^\d+-AAA\.(md|txt)$", name):
                input_counts["aaa_files"] += 1
            elif re.match(r"^\d+-EEE\.(md|txt)$", name):
                input_counts["eee_files"] += 1
            elif re.match(r"^Lecture\s*\d+\.(md|txt)$", name, re.IGNORECASE):
                input_counts["transcript_files"] += 1
            elif re.match(r"^\d+-slides\.(md|txt)$", name, re.IGNORECASE):
                input_counts["slide_files"] += 1
            elif name.lower().endswith(".pptx"):
                input_counts["pptx_files"] += 1

            parent_name = path.parent.name
            if parent_name == "English text":
                generated_counts["text_section_files"] += 1
            elif parent_name == "English Summary text":
                generated_counts["summary_section_files"] += 1

    if output_dir.exists():
        generated_counts["language_folders"] = sum(
            1 for path in output_dir.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        generated_counts["mp4_files"] = sum(
            1 for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".mp4"
        )

    blockers = []
    if input_counts["courses"] == 0:
        blockers.append("No course folders found in `input/`.")
    if input_counts["aaa_files"] != input_counts["eee_files"]:
        blockers.append(
            f"AAA / EEE mismatch detected: {input_counts['aaa_files']} AAA vs {input_counts['eee_files']} EEE."
        )
    if not shutil.which("ffmpeg"):
        blockers.append("`ffmpeg` is not available in PATH.")
    if not shutil.which("libreoffice"):
        blockers.append("`libreoffice` is not available in PATH.")
    if not os.environ.get("OPENAI_API_KEY"):
        blockers.append("`OPENAI_API_KEY` is not set for OpenAI-powered pages.")

    return {
        "input": input_counts,
        "generated": generated_counts,
        "blockers": blockers,
    }


def get_recommended_next_step(context: dict) -> dict:
    input_counts = context["input"]
    generated = context["generated"]

    if input_counts["aaa_files"] > 0 or input_counts["eee_files"] > 0:
        return {
            "title": "Adjust AAA EEE",
            "reason": "Raw AAA / EEE source files were detected and should be normalized first.",
        }
    if input_counts["transcript_files"] > 0 and generated["text_section_files"] == 0:
        return {
            "title": "Save Text",
            "reason": "Lecture transcript files exist, but section text files have not been generated yet.",
        }
    if input_counts["pptx_files"] > 0 and generated["image_folders"] == 0:
        return {
            "title": "4K Image Final",
            "reason": "Presentations were detected, but no generated image folders exist yet.",
        }
    if generated["text_section_files"] > 0 and generated["audio_folders"] == 0:
        return {
            "title": "TTS Kokoro",
            "reason": "Section text files exist, but no generated audio folders were found.",
        }
    if generated["audio_folders"] > 0 and generated["image_folders"] > 0 and generated["mp4_files"] == 0:
        return {
            "title": "MP4 Final",
            "reason": "Audio and image folders exist, so the next step is rendering MP4 output.",
        }
    if generated["mp4_files"] > 0:
        return {
            "title": "Verify MP4",
            "reason": "Rendered MP4 files exist and should be verified before you move on.",
        }
    return {
        "title": "Count New",
        "reason": "Use validation to inspect the current filesystem state and identify the next workflow step.",
    }


def build_workflow_status(context: dict) -> list[dict]:
    input_counts = context["input"]
    generated = context["generated"]

    def status(complete: bool, ready: bool) -> str:
        if complete:
            return "complete"
        if ready:
            return "ready"
        return "not started"

    return [
        {
            "name": "Prepare",
            "status": status(
                complete=(input_counts["aaa_files"] > 0 or input_counts["transcript_files"] > 0 or input_counts["slide_files"] > 0),
                ready=(input_counts["courses"] > 0),
            ),
            "detail": "AAA / EEE, transcript, slide, or PPTX source files are present.",
        },
        {
            "name": "Split Text",
            "status": status(
                complete=(generated["text_section_files"] > 0 or generated["summary_section_files"] > 0),
                ready=(input_counts["aaa_files"] > 0 or input_counts["transcript_files"] > 0),
            ),
            "detail": "Section files in `English text` / `English Summary text` folders.",
        },
        {
            "name": "Generate Images",
            "status": status(
                complete=(generated["image_folders"] > 0),
                ready=(input_counts["pptx_files"] > 0),
            ),
            "detail": "Lecture image folders such as `English image`.",
        },
        {
            "name": "Generate Audio",
            "status": status(
                complete=(generated["audio_folders"] > 0),
                ready=(generated["text_section_files"] > 0),
            ),
            "detail": "Lecture audio folders such as `English audio`.",
        },
        {
            "name": "Validate",
            "status": status(
                complete=(generated["mp4_files"] > 0),
                ready=(generated["audio_folders"] > 0 and generated["image_folders"] > 0),
            ),
            "detail": "Counts and prerequisites can be checked once audio and images exist.",
        },
        {
            "name": "Render Video",
            "status": status(
                complete=(generated["mp4_files"] > 0),
                ready=(generated["audio_folders"] > 0 and generated["image_folders"] > 0),
            ),
            "detail": "MP4 output under `output/`.",
        },
    ]


def build_navigation():
    return {
        "Overview": [
            st.Page(render_homepage, title="Home", icon="🎓", default=True),
        ],
        "Core Workflow": [
            page("01_Adjust_AAA_EEE.py", "Adjust AAA EEE", "📄"),
            page("02_Rename.py", "Rename", "✏️"),
            page("03_Save_Text.py", "Save Text", "💾"),
            page("04_Remove_unwanted.py", "Remove Unwanted", "🧹"),
            page("05_Move_Slides.py", "Move Slides", "📄"),
            page("06.py", "4K Image Final", "🖼️"),
            page("07_TTS_Kokoro.py", "TTS Kokoro", "🔊"),
        ],
        "Translation & Multilingual": [
            page("08_Ollama.py", "Ollama", "🌍"),
            page("08_Translator_LM_Studio.py", "Translator LM Studio", "🌐"),
            page("15_inworld_TTS.py", "Inworld TTS", "🗣️"),
            page("52_multilingual_folder_structure.py", "Multilingual Folder Structure", "🌍"),
            page("53_Convert_Text_to_multiple_languages.py", "Convert Text to Multiple Languages", "🌐"),
            page("54_Multilingual_TTS.py", "Multilingual TTS", "🔊"),
            page("55_TTS_Open_AI.py", "TTS Open AI", "🗣️"),
        ],
        "Validation & Video": [
            page("09_Count_new.py", "Count New", "🔢"),
            page("09_Fix_for_mp4.py", "Fix for MP4", "🔧"),
            page("10.py", "MP4 Final", "🎬"),
            page("11_Verify_mp4.py", "Verify MP4", "📊"),
        ],
        "Maintenance & Recovery": [
            page("12_Delete.py", "Delete", "🗑️"),
            page("13_Delete_folder.py", "Delete Folder", "🗂️"),
            page("14_restore_pptx.py", "Restore PPTX", "↩️"),
        ],
        "Legacy & Alternate": [
            page("06_4K_Image.py", "4K Image", "🖼️"),
            page("06_4K_Image_pptx_zip.py", "4K Image PPTX ZIP", "🖼️"),
            page("09_Count.py", "Count", "🔢"),
            page("10_mp4_GPU.py", "MP4 GPU", "🎬"),
            page("58_Translator_Lecto.py", "Translator Lecto", "🌐"),
            page("60_mp4_CPU.py", "MP4 CPU", "🎬"),
        ],
    }


def render_homepage() -> None:
    context = build_homepage_context()
    next_step = get_recommended_next_step(context)
    workflow_status = build_workflow_status(context)

    st.title("Dreamlet Edu Video")
    st.subheader("File-based workflow for turning course materials into audio, images, and videos.")
    st.caption("This homepage reflects the current state of the files on disk, not a generic workflow description.")

    st.header("Input Status")
    input_counts = context["input"]
    input_cols = st.columns(7)
    input_metrics = [
        ("Courses", input_counts["courses"]),
        ("Lectures", input_counts["lectures"]),
        ("AAA Files", input_counts["aaa_files"]),
        ("EEE Files", input_counts["eee_files"]),
        ("Transcripts", input_counts["transcript_files"]),
        ("Slides", input_counts["slide_files"]),
        ("PPTX", input_counts["pptx_files"]),
    ]
    for column, (label, value) in zip(input_cols, input_metrics):
        with column:
            st.metric(label, value)

    st.header("Current Blockers")
    if context["blockers"]:
        for blocker in context["blockers"]:
            st.warning(blocker)
    else:
        st.success("No immediate blockers detected from the current filesystem and environment checks.")

    st.header("Recommended Next Step")
    st.write(f"**{next_step['title']}**")
    st.caption(next_step["reason"])

    st.header("Workflow Status")
    for stage in workflow_status:
        st.write(f"**{stage['name']}** — {stage['status'].title()}")
        st.caption(stage["detail"])

    st.header("Generated Assets")
    generated = context["generated"]
    output_cols = st.columns(4)
    output_metrics = [
        ("MP4 Files", generated["mp4_files"]),
        ("Language Folders", generated["language_folders"]),
        ("Audio Folders", generated["audio_folders"]),
        ("Image Folders", generated["image_folders"]),
    ]
    for column, (label, value) in zip(output_cols, output_metrics):
        with column:
            st.metric(label, value)

    with st.expander("Expected Input Naming", expanded=False):
        st.markdown(
            """
- `NN-AAA.md` / `NN-EEE.md` for raw AAA / EEE generation files
- `Lecture NN.md` for transcript files
- `NN-slides.md` for slide description files
- `NN.pptx` for presentations
"""
        )

    with st.expander("Filesystem Layout Reference", expanded=False):
        st.markdown(
            """
Dreamlet works directly on the filesystem:

- `input/` contains course folders and lecture assets
- `English text`, `English audio`, and `English image` live under lecture folders
- `output/` stores rendered MP4 files
"""
        )

    with st.expander("Dependency Notes", expanded=False):
        st.markdown(
            """
Important system dependencies used by the workflow include:

- `ffmpeg`
- `libreoffice`
- `poppler`
- provider-specific services such as Kokoro or LM Studio when those pages are used
"""
        )


def main() -> None:
    increase_image_decompression_limit()
    ensure_directory_exists(get_input_directory())

    st.set_page_config(
        page_title="Dreamlet Educational Video Production System",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    navigation = st.navigation(build_navigation(), position="sidebar", expanded=True)
    navigation.run()


main()
