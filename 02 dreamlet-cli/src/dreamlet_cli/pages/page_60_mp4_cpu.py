"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: LEGACY
PURPOSE: Older CPU-only MP4 generation page retained as a fallback reference path.
MAIN INPUTS:
- lecture image folders
- lecture audio folders
MAIN OUTPUTS:
- MP4 files written under `output/`
REQUIRED CONFIG / ASSETS:
- `input/` and `output/` directories
EXTERNAL SERVICES:
- local `ffmpeg` / `ffprobe`
HARDWARE ASSUMPTIONS:
- CPU-only rendering path
REPLACED BY:
- `pages/10 Render MP4 Videos.py`
"""

from dreamlet_cli.compat import st
import os
import re
import time
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import cv2
from PIL import Image
import ffmpeg
import subprocess

def ensure_directory_exists(directory_path: str) -> None:
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


st.set_page_config(page_title="11 MP4 - Dreamlet", page_icon="🎬")

# Define fixed input and output directories
INPUT_DIR = os.path.join(os.getcwd(), "input")
OUTPUT_DIR = os.path.join(os.getcwd(), "output")


def find_language_folders(lecture_dir: str) -> List[str]:
    """
    Find all language folders in a lecture directory (like 'English', 'Spanish', etc.)
    
    Args:
        lecture_dir: Path to lecture directory
    
    Returns:
        List of language names
    """
    languages = []

    for folder in os.listdir(lecture_dir):
        # Check for folders ending with 'audio' or 'image'
        if folder.endswith(" audio") or folder.endswith(" image"):
            # Extract language name (everything before ' audio' or ' image')
            lang = folder.split(" ")[0]
            if lang and lang not in languages:
                languages.append(lang)

    return languages


def find_image_files(lecture_dir: str, language: str = "English") -> List[str]:
    """
    Find all image files in a lecture directory for a specific language
    If language-specific images are not found, fall back to English images
    
    Args:
        lecture_dir: Path to lecture directory
        language: Language to find images for (default: English)
    
    Returns:
        List of sorted image file paths
    """
    # Look in the "<Language> image" folder
    lang_images_dir = os.path.join(lecture_dir, f"{language} image")
    if os.path.exists(lang_images_dir) and os.path.isdir(lang_images_dir):
        image_files = get_sorted_files(lang_images_dir,
                                       file_type="image",
                                       full_path=True)
        if image_files:
            return image_files
    
    # If not English and no images found, fall back to English images
    if language != "English":
        english_images_dir = os.path.join(lecture_dir, "English image")
        if os.path.exists(english_images_dir) and os.path.isdir(english_images_dir):
            image_files = get_sorted_files(english_images_dir,
                                           file_type="image",
                                           full_path=True)
            if image_files:
                return image_files

    # Return empty list if no image folder or no files found
    return []


def find_audio_files(lecture_dir: str,
                     language: str = "English",
                     summary: bool = False) -> List[str]:
    """
    Find all audio files in a lecture directory for a specific language
    
    Args:
        lecture_dir: Path to lecture directory
        language: Language to find audio for (default: English)
        summary: Whether to find summary audio files (default: False)
    
    Returns:
        List of sorted audio file paths
    """
    # Look in the "<Language> audio" or "<Language> Summary audio" folder
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_dir, folder_name)
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        audio_files = get_sorted_files(lang_audio_dir,
                                       file_type="audio",
                                       full_path=True)
        if audio_files:
            return audio_files

    # Return empty list if no audio folder or no files found
    return []


def find_processed_lectures() -> Dict[str, Dict[str, Dict]]:
    """
    Find all lectures with audio and image files ready for MP4 generation
    
    Returns:
        Nested dictionary of subject -> course -> section -> lecture -> data
    """
    if not os.path.exists(INPUT_DIR):
        return {}

    # Dictionary to store all found lectures
    organized_data = {}

    # Recursively walk through the input directory
    for root, dirs, files in os.walk(INPUT_DIR):
        # Skip utility folders
        if any(util_folder in root for util_folder in
               ["all_pptx", "all_slides", "all_transcripts"]):
            continue

        # Skip non-lecture folders (must contain at least English language folders)
        has_english_images = "English image" in dirs
        has_english_audio = "English audio" in dirs

        # Skip if doesn't have both English image and English audio folders
        if not (has_english_images and has_english_audio):
            continue

        # Get the lecture folder path (the current root)
        lecture_dir = root

        # Find all available languages in this lecture folder
        languages = find_language_folders(lecture_dir)

        # Find English files as base requirement (for backward compatibility)
        english_image_files = find_image_files(lecture_dir, "English")
        english_audio_files = find_audio_files(lecture_dir, "English")

        # Skip if no English image or audio files found (minimum requirement)
        if not english_image_files or not english_audio_files:
            continue

        # Extract path components for proper organization
        # Remove the input directory prefix to get the relative path
        rel_path = os.path.relpath(lecture_dir, INPUT_DIR)
        path_components = rel_path.split(os.sep)

        # The last component is the lecture name
        lecture_name = path_components[-1]

        # Extract subject, course, and section if available
        subject = None
        course = None
        section = None

        # Determine subject, course, and section based on folder hierarchy
        if len(path_components) > 3:  # subject/course/section/lecture
            subject = path_components[0]
            course = path_components[1]
            section = path_components[2]
        elif len(path_components
                 ) > 2:  # subject/course/lecture or course/section/lecture
            # Try to determine if the second component is a course or a section
            if any(section_keyword in path_components[1].lower()
                   for section_keyword in ["section", "part", "module"]):
                course = path_components[0]
                section = path_components[1]
            else:
                subject = path_components[0]
                course = path_components[1]
        elif len(path_components) > 1:  # course/lecture
            course = path_components[0]

        # If lecture name doesn't contain "Lecture", try to identify lecture number from folder name
        lecture_match = re.search(r'lecture\s*(\d+)', lecture_name,
                                  re.IGNORECASE)
        if lecture_match:
            lecture_display = f"Lecture {lecture_match.group(1)}"
        else:
            # Check if the name is just a number (e.g., "01", "02")
            number_match = re.match(r'^\s*(\d+)\s*$', lecture_name)
            if number_match:
                lecture_display = f"Lecture {number_match.group(1)}"
            else:
                lecture_display = lecture_name

        # Organize by subject and course
        subject_key = subject if subject else "Main"
        course_key = course if course else "Main Course"
        section_key = section if section else "Main Section"

        # Add entries to the dictionary at appropriate levels
        if subject_key not in organized_data:
            organized_data[subject_key] = {}

        if course_key not in organized_data[subject_key]:
            organized_data[subject_key][course_key] = {}

        if section_key not in organized_data[subject_key][course_key]:
            organized_data[subject_key][course_key][section_key] = {}

        # Build language data
        language_data = {}
        for language in languages:
            # Find regular audio and image files
            image_files = find_image_files(lecture_dir, language)
            audio_files = find_audio_files(lecture_dir,
                                           language,
                                           summary=False)

            # Find summary audio files
            summary_audio_files = find_audio_files(lecture_dir,
                                                   language,
                                                   summary=True)

            # Check if we have both regular and summary audio files
            has_regular_audio = len(audio_files) > 0
            has_summary_audio = len(summary_audio_files) > 0

            # Add data for this language if at least regular files are available
            if image_files and audio_files:
                language_data[language] = {
                    "image_files":
                    image_files,
                    "audio_files":
                    audio_files,
                    "audio_count":
                    len(audio_files),
                    "image_count":
                    len(image_files),
                    "count_match":
                    len(audio_files) == len(image_files),
                    "has_summary_audio":
                    has_summary_audio,
                    "summary_audio_files":
                    summary_audio_files,
                    "summary_audio_count":
                    len(summary_audio_files),
                    "summary_count_match":
                    len(summary_audio_files) == len(image_files)
                }

        # Add lecture data with English as default language
        has_english_summary = "English Summary audio" in dirs
        english_summary_audio_files = find_audio_files(lecture_dir,
                                                       "English",
                                                       summary=True)

        organized_data[subject_key][course_key][section_key][
            lecture_display] = {
                "path":
                lecture_dir,
                "image_files":
                english_image_files,  # Default to English files
                "audio_files":
                english_audio_files,  # Default to English files
                "audio_count":
                len(english_audio_files),
                "image_count":
                len(english_image_files),
                "count_match":
                len(english_audio_files) == len(english_image_files),
                "has_summary_audio":
                has_english_summary,
                "summary_audio_files":
                english_summary_audio_files,
                "summary_audio_count":
                len(english_summary_audio_files),
                "summary_count_match":
                len(english_summary_audio_files) == len(english_image_files),
                "output_name":
                f"{lecture_name}.mp4",
                "languages":
                languages,
                "language_data":
                language_data
            }

    return organized_data


def get_sorted_files(directory: str,
                     file_type: str,
                     full_path: bool = False) -> List[str]:
    """
    Get sorted list of files of a specific type
    
    Args:
        directory: Directory to search in
        file_type: Type of files to search for ('image' or 'audio')
        full_path: Whether to return full file paths or just filenames
        
    Returns:
        List of sorted filenames or file paths
    """
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
    else:
        raise ValueError("Invalid file_type. Use 'image' or 'audio'.")

    if not os.path.exists(directory):
        return []

    # Get all files with matching extensions
    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and f.lower().endswith(extensions)
    ]

    # Sort numerically by the number in the filename
    sorted_files = sorted(files,
                          key=lambda f: int(os.path.splitext(f)[0])
                          if os.path.splitext(f)[0].isdigit() else 999)

    # Return full paths if requested
    if full_path:
        return [os.path.join(directory, f) for f in sorted_files]
    else:
        return sorted_files


def generate_output_path(lecture_path: str, language: str = "English") -> str:
    """
    Generate the output path for the MP4 file
    
    Args:
        lecture_path: Path to the lecture directory
        language: Language for the MP4 file (default: English)
        
    Returns:
        Output path for the MP4 file
    """
    # Get the relative path from the input directory
    rel_path = os.path.relpath(lecture_path, INPUT_DIR)

    # Split the path into components
    path_components = rel_path.split(os.sep)

    # Get the lecture name (last component)
    lecture_name = path_components[-1]

    # For the output structure, we need to correctly identify the course and section
    course = None
    section = None

    # Based on the screenshot: input/3 Course/Section 01/Lecture 01
    # Should generate: output/<Language>/3 Course/Section 01/Lecture 01.mp4

    # Extract components - we care about finding the course and section names
    # from the input path, regardless of other path components
    if len(path_components) >= 3:  # At least course/section/lecture
        # The course is typically 2 levels up from the lecture (-3)
        course = path_components[-3]
        # The section is typically 1 level up from the lecture (-2)
        section = path_components[-2]
    elif len(path_components) == 2:  # Just course/lecture
        course = path_components[0]
        section = "Main Section"  # Default section name
    else:  # Just lecture
        course = "Main Course"  # Default course name
        section = "Main Section"  # Default section name

    # Create the output directory path with language-specific folder
    output_dir_path = os.path.join(OUTPUT_DIR, language, course, section)

    # Create the output directory
    ensure_directory_exists(output_dir_path)

    # Generate the output file path
    output_file = os.path.join(output_dir_path, f"{lecture_name}.mp4")

    return output_file


def upscale_image(
    image_path: str, target_resolution: Tuple[int, int] = (3840, 2160)
) -> np.ndarray:
    """
    Load and upscale an image to target resolution
    
    Args:
        image_path: Path to the image file
        target_resolution: Target resolution (width, height)
        
    Returns:
        Upscaled image as numpy array
    """
    # Load the image using PIL for high-quality upscaling
    img = Image.open(image_path)

    # Resize the image to 4K using high-quality Lanczos resampling
    img_resized = img.resize(target_resolution, Image.LANCZOS)

    # Convert to numpy array for OpenCV compatibility
    img_array = np.array(img_resized)

    # Convert to RGB if the image is in RGBA mode
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

    return img_array


def create_video_from_images_and_audio(image_files: List[str],
                                       audio_files: List[str],
                                       output_path: str,
                                       fps: int = 3) -> Tuple[bool, str]:
    """
    Generate an MP4 video from images and audio files
    
    Args:
        image_files: List of image file paths
        audio_files: List of audio file paths
        output_path: Path to save the output video
        fps: Frames per second (default: 3)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create a temporary directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare output video file for temporary segments
            temp_video = os.path.join(temp_dir, "temp_video.mp4")
            temp_audio = os.path.join(temp_dir, "temp_audio.wav")
            segments_dir = os.path.join(temp_dir, "segments")
            os.makedirs(segments_dir, exist_ok=True)

            # Create temporary video segments
            segment_files = []

            # Process each image and corresponding audio
            for i, (img_file,
                    audio_file) in enumerate(zip(image_files, audio_files)):
                # Upscale image to 4K
                img = upscale_image(img_file)
                upscaled_img_path = os.path.join(temp_dir,
                                                 f"upscaled_{i:03d}.png")
                cv2.imwrite(upscaled_img_path,
                            cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

                # Get audio duration
                duration_cmd = [
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of",
                    "default=noprint_wrappers=1:nokey=1", audio_file
                ]

                duration_result = subprocess.run(duration_cmd,
                                                 capture_output=True,
                                                 text=True,
                                                 check=True)

                duration = float(duration_result.stdout.strip())

                # Create segment with image and audio
                segment_path = os.path.join(segments_dir,
                                            f"segment_{i:03d}.mp4")
                segment_files.append(segment_path)

                # Generate video segment
                segment_cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-framerate",
                    str(fps), "-i", upscaled_img_path, "-i", audio_file,
                    "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
                    "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", "-t",
                    str(duration), segment_path
                ]

                subprocess.run(segment_cmd, check=True, capture_output=True)

            # Create a file list for concatenation
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")

            # Concatenate all segments
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                concat_file, "-c", "copy", temp_video
            ]

            subprocess.run(concat_cmd, check=True, capture_output=True)

            # Optimize for streaming with proper encoding
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-c:v", "libx264", "-preset",
                "medium", "-crf", "22", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "faststart", output_path
            ]

            subprocess.run(final_cmd, check=True, capture_output=True)

            return True, f"Video successfully generated at {output_path}"

    except subprocess.CalledProcessError as e:
        return False, f"FFmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
    except Exception as e:
        return False, f"Error generating video: {str(e)}"


def generate_mp4_for_lecture(lecture_data: Dict,
                             fps: int,
                             language: str = "English",
                             summary: bool = False,
                             force_create: bool = False) -> Dict:
    """
    Generate MP4 for a lecture in the specified language
    
    Args:
        lecture_data: Dictionary with lecture data
        fps: Frames per second
        language: Language for the MP4 (default: English)
        summary: Whether to generate a summary video (default: False)
        force_create: Whether to force create the MP4 even if it already exists (default: False)
        
    Returns:
        Dictionary with processing results
    """
    result = {
        "lecture_path": lecture_data["path"],
        "status": "error",
        "message": "",
        "output_path": "",
        "language": language,
        "summary": summary
    }

    try:
        # Get lecture path
        lecture_path = lecture_data["path"]

        # Find language-specific files
        image_files = find_image_files(lecture_path, language)
        audio_files = find_audio_files(lecture_path, language, summary)

        # Check if we have files for this language
        if not image_files:
            result[
                "message"] = f"No {language} image files found for this lecture"
            return result

        if not audio_files:
            audio_type = "Summary audio" if summary else "audio"
            result[
                "message"] = f"No {language} {audio_type} files found for this lecture"
            return result

        # Check if counts match
        if len(image_files) != len(audio_files):
            audio_type = "Summary audio" if summary else "audio"
            result[
                "message"] = f"Count mismatch: {len(image_files)} images, {len(audio_files)} {audio_type} files"
            return result

        # Get the lecture name (last component of path)
        rel_path = os.path.relpath(lecture_path, INPUT_DIR)
        path_components = rel_path.split(os.sep)
        lecture_name = path_components[-1]

        # Generate output path with language
        output_path = generate_output_path(lecture_path, language)

        # If summary video, modify the output filename to include "(summary)"
        if summary:
            # Extract directory and filename
            output_dir = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            name, ext = os.path.splitext(filename)

            # Create new filename with "(summary)" suffix
            new_filename = f"{name}(summary){ext}"
            output_path = os.path.join(output_dir, new_filename)

        # Check if MP4 already exists and skip if not forcing recreation
        if not force_create and os.path.exists(output_path):
            result["status"] = "skipped"
            result[
                "message"] = "MP4 file already exists (use 'Force Create MP4s' to recreate)"
            result["output_path"] = output_path
            return result

        # Generate MP4
        success, message = create_video_from_images_and_audio(
            image_files, audio_files, output_path, fps)

        if not success:
            result["message"] = message
            return result

        # Update result
        result["status"] = "success"
        video_type = "summary video" if summary else "video"
        result[
            "message"] = f"Successfully generated {language} {video_type}: {message}"
        result["output_path"] = output_path

        return result
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        return result


def main():
    st.title("mp4 - CPU")
    st.write(
        "Combine audio and images to create final educational videos in multiple languages."
    )

    # Introduction in a collapsible section
    with st.expander("About this page"):
        st.markdown("""
        This page combines slide images with their corresponding audio files to create educational videos in different languages.
        
        ### Key Features:
        - **Multi-language Support**: Generate videos in any language where audio and image files are available
        - **Regular & Summary Videos**: Generate both full lectures and summary versions
        - **Intelligent File Matching**: Matches files based on their numeric filenames
        - **Structured Output**: Creates organized MP4 files in language-specific directories
        - **4K Quality**: All videos are upscaled to 4K (3840x2160) resolution
        
        ### Required Folder Structure:
        Each lecture folder must contain language-specific folders:
        - `<Language> image` - Contains numbered image files (1.png, 2.png, etc.)
        - `<Language> audio` - Contains matching numbered audio files (1.mp3, 2.mp3, etc.)
        - `<Language> Summary audio` - Contains matching numbered summary audio files (1.mp3, 2.mp3, etc.)
        
        ### Output Structure:
        MP4 files will be saved with the following path structure:
        ```
        # Regular videos
        /output/<Language>/<Course>/<Section>/<Lecture>.mp4
        
        # Summary videos
        /output/<Language>/<Course>/<Section>/<Lecture> (summary).mp4
        ```
        
        This hierarchical structure ensures proper organization of content across multiple languages.
        """)

    # Ensure input and output directories exist without showing them
    ensure_directory_exists(INPUT_DIR)
    ensure_directory_exists(OUTPUT_DIR)

    # Find lectures with processed audio and images
    organized_data = find_processed_lectures()

    if not organized_data:
        st.warning("No lectures with matching image and audio files found.")
        st.info(
            "Each lecture folder must contain matching .png and .mp3 files in language-specific folders (e.g., 'English image' and 'English audio')."
        )
        return

    # Video Settings
    st.header("Video Settings")

    # Language Selection
    # Collect all available languages from all lectures
    all_languages = set()
    for subject in organized_data.values():
        for course in subject.values():
            for section in course.values():
                for lecture in section.values():
                    if "languages" in lecture:
                        all_languages.update(lecture["languages"])

    # Sort languages with English first
    sorted_languages = sorted(all_languages)
    if "English" in sorted_languages:
        sorted_languages.remove("English")
        sorted_languages = ["English"] + sorted_languages

    # Default to English if available
    default_language = "English" if "English" in sorted_languages else sorted_languages[
        0] if sorted_languages else None

    # Language selection dropdown
    selected_language = st.selectbox(
        "Select Language for MP4 Generation",
        sorted_languages,
        index=sorted_languages.index(default_language)
        if default_language else 0)

    st.info(
        f"Creating MP4s in {selected_language} language. Output will be saved to: `/output/{selected_language}/...`"
    )

    # Default FPS is 3 as specified in the requirements
    fps = 3
    st.info(
        f"Using frame rate: {fps} FPS (optimized for static slides with smooth transitions)"
    )

    # Select lectures for MP4 generation
    st.header("Select Lectures for MP4 Generation")

    # Create selection interface with expandable sections
    selected_lectures = {}

    # Add Select All/None buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✓ Select All Courses"):
            # Store in session state
            if 'select_all' not in st.session_state:
                st.session_state.select_all = True
            else:
                st.session_state.select_all = True
            st.rerun()

    with col2:
        if st.button("✗ Unselect All Courses"):
            # Store in session state
            if 'select_all' in st.session_state:
                st.session_state.select_all = False
            st.rerun()

    # Default select all setting
    select_all = st.session_state.get('select_all', False)

    # Get all courses directly (skipping subject level)
    all_courses = []
    for subject in organized_data:
        for course in organized_data[subject]:
            if (subject, course) not in all_courses:
                all_courses.append((subject, course))

    # Sort courses
    all_courses.sort(key=lambda x: x[1])  # Sort by course name

    # Display each course as a separate expander
    for subject, course in all_courses:
        # Create an expander for each course
        with st.expander(f"Course: {course}"):
            # Option to select all lectures in this course across all sections
            all_in_course = st.checkbox(
                f"Select all in {course}",
                key=f"all_{subject}_{course}",
                value=select_all  # Set initial value based on select all button
            )

            # Display each section in this course
            for section in sorted(organized_data[subject][course].keys()):
                st.markdown(f"##### Section: {section}")

                # Sort lectures by number if available
                lecture_keys = list(
                    organized_data[subject][course][section].keys())
                sorted_lectures = sorted(
                    lecture_keys,
                    key=lambda x: int(re.search(r'\d+', x).group())
                    if re.search(r'\d+', x) else 999)

                for lecture in sorted_lectures:
                    lecture_data = organized_data[subject][course][section][
                        lecture]

                    # Check if the selected language is available for this lecture
                    has_language = selected_language in lecture_data.get(
                        "languages", [])

                    # If the language data exists and has count match info, use it; otherwise default to English
                    if selected_language in lecture_data.get(
                            "language_data",
                        {}) and "count_match" in lecture_data["language_data"][
                            selected_language]:
                        lang_data = lecture_data["language_data"][
                            selected_language]
                        count_match = lang_data["count_match"]
                        audio_count = lang_data["audio_count"]
                        image_count = lang_data["image_count"]
                        has_summary_audio = lang_data.get(
                            "has_summary_audio", False)
                        summary_count_match = lang_data.get(
                            "summary_count_match", False)
                        summary_audio_count = lang_data.get(
                            "summary_audio_count", 0)
                    else:
                        # Fall back to English data but mark as unavailable
                        count_match = False
                        audio_count = 0
                        image_count = 0
                        has_summary_audio = False
                        summary_count_match = False
                        summary_audio_count = 0

                    # Show lecture information
                    status_icon = "✅" if has_language and count_match else "⚠️"

                    if not has_language:
                        status_text = f" (No {selected_language} files available)"
                    elif not count_match:
                        status_text = f" ({selected_language} count mismatch)"
                    else:
                        status_text = ""

                    # Show summary status
                    if has_summary_audio and summary_count_match:
                        summary_status = f"✅ {summary_audio_count} summary audio files"
                    elif has_summary_audio and not summary_count_match:
                        summary_status = f"⚠️ {summary_audio_count} summary audio files (count mismatch)"
                    else:
                        summary_status = "❌ No summary audio files"

                    lecture_info = (
                        f"{status_icon} {lecture}: "
                        f"{audio_count} {selected_language} audio files, "
                        f"{image_count} {selected_language} image files{status_text}\n"
                        f"     {summary_status}")

                    if all_in_course:
                        selected = has_language and count_match  # Only select if language available and counts match
                        st.write(
                            f"{lecture_info} {'(Selected)' if selected else '(Skipped)'}"
                        )
                    else:
                        # Only allow selection if language is available and counts match
                        selected = st.checkbox(
                            lecture_info,
                            key=
                            f"{subject}_{course}_{section}_{lecture}_{selected_language}",
                            disabled=not (has_language and count_match))

                    if selected:
                        selected_lectures[(subject, course, section,
                                           lecture)] = lecture_data

    # Generate MP4s
    st.header("Generate MP4s")

    # Option to generate summary videos
    col1, col2 = st.columns(2)

    with col1:
        generate_regular = st.checkbox(
            "Generate Regular Videos",
            value=True,
            help=
            "Generate regular videos using language audio files and image files"
        )

    with col2:
        generate_summary = st.checkbox(
            "Generate Summary Videos",
            value=True,
            help=
            "Generate summary videos using language summary audio files and image files"
        )

    # Add checkbox for force creating MP4s
    force_create = st.checkbox(
        "Force Create MP4s",
        value=False,
        help=
        "When unchecked, skip creating MP4s for lectures that already have an MP4 file. When checked, always recreate MP4s even if they already exist."
    )

    if st.button("Generate MP4s",
                 disabled=len(selected_lectures) == 0
                 or not (generate_regular or generate_summary)):
        if not selected_lectures:
            st.warning("No lectures selected for MP4 generation.")
            return

        if not (generate_regular or generate_summary):
            st.warning(
                "Please select at least one video type to generate (Regular or Summary)."
            )
            return

        # Process lectures with progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        time_estimate = st.empty()
        results_container = st.container()

        results = []
        start_time = time.time()

        # Calculate total number of videos to generate
        total_videos = len(selected_lectures) * (
            (1 if generate_regular else 0) + (1 if generate_summary else 0))

        # Counter for progress tracking
        video_count = 0

        # Process each selected lecture
        for _, ((subject, course, section, lecture),
                lecture_data) in enumerate(selected_lectures.items()):
            # First, generate regular video if selected
            if generate_regular:
                # Update status
                status_text.info(
                    f"Processing {video_count+1}/{total_videos}: {subject} - {course} - {section} - {lecture} (Regular)"
                )

                # Generate regular MP4 with the selected language
                result = generate_mp4_for_lecture(
                    lecture_data,
                    fps,
                    selected_language,
                    summary=False,  # Regular video
                    force_create=force_create)

                # Add metadata for display
                result["subject"] = subject
                result["course"] = course
                result["section"] = section
                result["lecture"] = lecture
                result["type"] = "Regular"
                results.append(result)

                # Update progress and time estimation
                video_count += 1
                progress = video_count / total_videos
                progress_bar.progress(progress)

                # Estimate remaining time
                if video_count > 0:
                    elapsed_time = time.time() - start_time
                    items_processed = video_count
                    items_remaining = total_videos - video_count

                    # Estimate remaining time based on average time per item so far
                    avg_time_per_item = elapsed_time / items_processed
                    estimated_time_remaining = avg_time_per_item * items_remaining

                    # Format into minutes and seconds
                    minutes_remaining = int(estimated_time_remaining // 60)
                    seconds_remaining = int(estimated_time_remaining % 60)

                    # Display estimated time remaining
                    time_estimate.info(
                        f"Estimated time remaining: {minutes_remaining} minutes, {seconds_remaining} seconds"
                    )

            # Next, generate summary video if selected
            if generate_summary:
                # Update status
                status_text.info(
                    f"Processing {video_count+1}/{total_videos}: {subject} - {course} - {section} - {lecture} (Summary)"
                )

                # Generate summary MP4 with the selected language
                result = generate_mp4_for_lecture(
                    lecture_data,
                    fps,
                    selected_language,
                    summary=True,  # Summary video
                    force_create=force_create)

                # Add metadata for display
                result["subject"] = subject
                result["course"] = course
                result["section"] = section
                result["lecture"] = lecture
                result["type"] = "Summary"
                results.append(result)

                # Update progress and time estimation
                video_count += 1
                progress = video_count / total_videos
                progress_bar.progress(progress)

                # Estimate remaining time
                if video_count > 0:
                    elapsed_time = time.time() - start_time
                    items_processed = video_count
                    items_remaining = total_videos - video_count

                    # Estimate remaining time based on average time per item so far
                    avg_time_per_item = elapsed_time / items_processed
                    estimated_time_remaining = avg_time_per_item * items_remaining

                    # Format into minutes and seconds
                    minutes_remaining = int(estimated_time_remaining // 60)
                    seconds_remaining = int(estimated_time_remaining % 60)

                    # Display estimated time remaining
                    time_estimate.info(
                        f"Estimated time remaining: {minutes_remaining} minutes, {seconds_remaining} seconds"
                    )

        # Complete
        time_estimate.empty()
        status_text.success(
            f"Processed {video_count} videos for {len(selected_lectures)} lectures"
        )

        # Display results
        with results_container:
            st.subheader("Processing Results")

            # Statistics
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = sum(1 for r in results if r["status"] == "error")
            skipped_count = sum(1 for r in results if r["status"] == "skipped")

            st.write(f"✅ Successfully generated: {success_count}")
            st.write(f"⏭️ Skipped (already exists): {skipped_count}")
            st.write(f"❌ Errors: {error_count}")

            # Detailed results
            for result in results:
                if result["status"] == "success":
                    status_icon = "✅"
                elif result["status"] == "skipped":
                    status_icon = "⏭️"
                else:
                    status_icon = "❌"

                # Include video type in display name
                video_type = result.get("type", "")
                display_name = f"{result['subject']} - {result['course']} - {result['section']} - {result['lecture']} ({video_type})"

                with st.expander(f"{status_icon} {display_name}"):
                    st.write(f"**Status:** {result['status']}")
                    st.write(f"**Type:** {video_type}")
                    st.write(f"**Message:** {result['message']}")

                    if result["status"] in ["success", "skipped"]:
                        st.write(f"**Output:** {result['output_path']}")


if __name__ == "__main__":
    main()
