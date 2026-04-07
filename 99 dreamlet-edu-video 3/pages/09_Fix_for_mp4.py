"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent
"""

import streamlit as st
import os
import re
import shutil
from typing import Dict, List, Tuple

# --- Start of code copied from 10_mp4_GPU.py ---

# Define fixed input directory
INPUT_DIR = os.path.join(os.getcwd(), "input")

def get_sorted_files(directory: str,
                    file_type: str,
                    full_path: bool = False) -> List[str]:
    """
    Get sorted list of files of a specific type
    """
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
    else:
        return []

    if not os.path.exists(directory):
        return []

    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and f.lower().endswith(extensions)
    ]

    try:
        sorted_files = sorted(files,
                             key=lambda f: int(os.path.splitext(f)[0]))
    except (ValueError, TypeError):
        def sort_key(f):
            match = re.match(r'(\d+)', f)
            return int(match.group(1)) if match else 999
        sorted_files = sorted(files, key=sort_key)

    if full_path:
        return [os.path.join(directory, f) for f in sorted_files]
    else:
        return sorted_files

def find_language_folders(lecture_dir: str) -> List[str]:
    """
    Find all language folders in a lecture directory.
    """
    languages = []
    if not os.path.isdir(lecture_dir):
        return languages

    for folder in os.listdir(lecture_dir):
        if folder.endswith(" audio") or folder.endswith(" image"):
            lang = folder.rsplit(' ', 1)[0]
            if lang and lang not in languages:
                languages.append(lang)
    return languages

def find_image_files(lecture_dir: str, language: str = "English") -> List[str]:
    """
    Find all image files in a lecture directory for a specific language.
    """
    lang_images_dir = os.path.join(lecture_dir, f"{language} image")
    if os.path.exists(lang_images_dir) and os.path.isdir(lang_images_dir):
        image_files = get_sorted_files(lang_images_dir, file_type="image", full_path=True)
        if image_files:
            return image_files
    
    if language != "English":
        english_images_dir = os.path.join(lecture_dir, "English image")
        if os.path.exists(english_images_dir) and os.path.isdir(english_images_dir):
            image_files = get_sorted_files(english_images_dir, file_type="image", full_path=True)
            if image_files:
                return image_files
    return []

def find_audio_files(lecture_dir: str, language: str = "English", summary: bool = False) -> List[str]:
    """
    Find all audio files in a lecture directory for a specific language.
    """
    folder_name = f"{language} Summary audio" if summary else f"{language} audio"
    lang_audio_dir = os.path.join(lecture_dir, folder_name)
    if os.path.exists(lang_audio_dir) and os.path.isdir(lang_audio_dir):
        audio_files = get_sorted_files(lang_audio_dir, file_type="audio", full_path=True)
        if audio_files:
            return audio_files
    return []

def find_processed_lectures() -> Dict[str, Dict[str, Dict]]:
    """
    Find all lectures with audio and image files ready for MP4 generation
    """
    if not os.path.exists(INPUT_DIR):
        return {}

    organized_data = {}

    for root, dirs, files in os.walk(INPUT_DIR):
        if any(util_folder in root for util_folder in
              ["all_pptx", "all_slides", "all_transcripts"]):
            continue

        if not ("English image" in dirs and "English audio" in dirs):
            continue

        lecture_dir = root
        languages = find_language_folders(lecture_dir)
        english_image_files = find_image_files(lecture_dir, "English")
        english_audio_files = find_audio_files(lecture_dir, "English")

        if not english_image_files or not english_audio_files:
            continue

        rel_path = os.path.relpath(lecture_dir, INPUT_DIR)
        path_components = rel_path.split(os.sep)
        lecture_name = path_components[-1]

        subject, course, section = None, None, None
        if len(path_components) > 3:
            subject, course, section = path_components[0], path_components[1], path_components[2]
        elif len(path_components) > 2:
            if any(keyword in path_components[1].lower() for keyword in ["section", "part", "module"]):
                course, section = path_components[0], path_components[1]
            else:
                subject, course = path_components[0], path_components[1]
        elif len(path_components) > 1:
            course = path_components[0]

        lecture_match = re.search(r'lecture\s*(\d+)', lecture_name, re.IGNORECASE)
        if lecture_match:
            lecture_display = f"Lecture {lecture_match.group(1)}"
        else:
            number_match = re.match(r'^\s*(\d+)\s*$', lecture_name)
            if number_match:
                lecture_display = f"Lecture {number_match.group(1)}"
            else:
                lecture_display = lecture_name

        subject_key, course_key, section_key = subject or "Main", course or "Main Course", section or "Main Section"

        organized_data.setdefault(subject_key, {}).setdefault(course_key, {}).setdefault(section_key, {})[lecture_display] = {
            "path": lecture_dir,
            "languages": languages,
            "language_data": {}
        }

        for language in languages:
            image_files = find_image_files(lecture_dir, language)
            audio_files = find_audio_files(lecture_dir, language, summary=False)
            summary_audio_files = find_audio_files(lecture_dir, language, summary=True)

            organized_data[subject_key][course_key][section_key][lecture_display]["language_data"].setdefault(language, {
                "image_files": image_files,
                "audio_files": audio_files,
                "audio_count": len(audio_files),
                "image_count": len(image_files),
                "count_match": len(audio_files) == len(image_files),
                "has_summary_audio": len(summary_audio_files) > 0,
                "summary_audio_files": summary_audio_files,
                "summary_audio_count": len(summary_audio_files),
                "summary_count_match": len(summary_audio_files) == len(image_files),
            })

    return organized_data

# --- End of copied code ---

def fix_image_mismatch(lecture_path: str, language: str, target_count: int, current_images: List[str]) -> Tuple[bool, str]:
    """
    Fix image count mismatch by removing excess and renaming files
    Returns (success, message)
    """
    try:
        excess = len(current_images) - target_count
        
        if excess == 2:
            # Remove first and last images
            files_to_remove = [current_images[0], current_images[-1]]
            remaining_files = current_images[1:-1]
        elif excess > 2:
            # Remove proportionally from start and end
            start_remove = excess // 2
            end_remove = excess - start_remove
            files_to_remove = current_images[:start_remove] + current_images[-end_remove:]
            remaining_files = current_images[start_remove:-end_remove if end_remove > 0 else None]
        else:
            return False, f"Cannot handle excess of {excess} images"
        
        # Create backup directory
        backup_dir = os.path.join(os.path.dirname(current_images[0]), "backup_before_fix")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup all files first
        for file_path in current_images:
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
        
        # Delete excess files
        for file_path in files_to_remove:
            os.remove(file_path)
        
        # Rename remaining files to maintain sequence (01.png, 02.png, etc.)
        for i, old_path in enumerate(remaining_files):
            file_ext = os.path.splitext(old_path)[1]
            new_name = f"{i+1:02d}{file_ext}"
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if old_path != new_path:
                os.rename(old_path, new_path)
        
        return True, f"Successfully fixed: removed {len(files_to_remove)} images, renamed {len(remaining_files)} images"
        
    except Exception as e:
        return False, f"Error fixing images: {str(e)}"

def duplicate_last_image(lecture_path: str, language: str, current_images: List[str], target_count: int) -> Tuple[bool, str]:
    """
    Duplicate the last image to match audio count
    Returns (success, message)
    """
    try:
        if not current_images:
            return False, "No images to duplicate"
        
        last_image = current_images[-1]
        file_ext = os.path.splitext(last_image)[1]
        
        # Create backup directory
        backup_dir = os.path.join(os.path.dirname(last_image), "backup_before_fix")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup all files first
        for file_path in current_images:
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
        
        # Duplicate last image
        new_name = f"{target_count:02d}{file_ext}"
        new_path = os.path.join(os.path.dirname(last_image), new_name)
        shutil.copy2(last_image, new_path)
        
        return True, f"Successfully duplicated last image to match audio count"
        
    except Exception as e:
        return False, f"Error duplicating image: {str(e)}"

def main():
    st.title("🔧 Fix MP4 Mismatches")
    st.write("Automatically fix lectures with mismatched image and audio file counts.")

    if not os.path.exists(INPUT_DIR):
        st.error(f"Input directory not found: {INPUT_DIR}")
        return

    organized_data = find_processed_lectures()

    if not organized_data:
        st.warning("No lectures with matching image and audio files found.")
        return

    # Fixed to English only - no language selector needed
    selected_language = "English"

    # Initialize session state
    if 'confirm_fixes' not in st.session_state:
        st.session_state.confirm_fixes = False
    if 'select_all_fixable' not in st.session_state:
        st.session_state.select_all_fixable = False
    
    # Collect all mismatched lectures
    mismatched_lectures = []
    for subject, courses in organized_data.items():
        for course, sections in courses.items():
            for section, lectures in sections.items():
                for lecture, lecture_data in lectures.items():
                    if selected_language in lecture_data.get("languages", []):
                        lang_data = lecture_data.get("language_data", {}).get(selected_language, {})
                        audio_count = lang_data.get("audio_count", 0)
                        image_count = lang_data.get("image_count", 0)
                        summary_audio_count = lang_data.get("summary_audio_count", 0)
                        
                        # Check for fixable mismatches
                        if audio_count > 0 and image_count > 0 and summary_audio_count > 0:
                            if audio_count == summary_audio_count:
                                if image_count == audio_count + 2:  # Images +2 excess
                                    mismatched_lectures.append({
                                        'key': f"{subject}_{course}_{section}_{lecture}",
                                        'display': f"{lecture} ({course})",
                                        'path': lecture_data['path'],
                                        'language': selected_language,
                                        'audio_count': audio_count,
                                        'image_count': image_count,
                                        'summary_count': summary_audio_count,
                                        'fix_type': 'remove_excess',
                                        'image_files': lang_data.get('image_files', [])
                                    })
                                elif image_count == audio_count - 1:  # Images -1 (audio +1)
                                    mismatched_lectures.append({
                                        'key': f"{subject}_{course}_{section}_{lecture}",
                                        'display': f"{lecture} ({course})",
                                        'path': lecture_data['path'],
                                        'language': selected_language,
                                        'audio_count': audio_count,
                                        'image_count': image_count,
                                        'summary_count': summary_audio_count,
                                        'fix_type': 'duplicate_last',
                                        'image_files': lang_data.get('image_files', [])
                                    })

    # Fixable lectures section - collapsible and closed by default
    with st.expander(f"🔧 Fixable Lectures ({len(mismatched_lectures)} found)", expanded=False):
        if not mismatched_lectures:
            st.info("No fixable mismatches found. Only lectures with exactly +2 excess images or -1 images (when audio counts match) can be automatically fixed.")
        else:
            # Select All / Unselect All buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✓ Select All", key="select_all_btn"):
                    st.session_state.select_all_fixable = True
                    st.rerun()
            
            with col2:
                if st.button("✗ Unselect All", key="unselect_all_btn"):
                    st.session_state.select_all_fixable = False
                    st.rerun()
            
            st.markdown("---")
            
            # Show fixable lectures with checkboxes
            selected_fixes = []
            for lecture_info in mismatched_lectures:
                fix_description = ""
                if lecture_info['fix_type'] == 'remove_excess':
                    fix_description = f"Remove 2 excess images ({lecture_info['image_count']} → {lecture_info['audio_count']})"
                elif lecture_info['fix_type'] == 'duplicate_last':
                    fix_description = f"Duplicate last image ({lecture_info['image_count']} → {lecture_info['audio_count']})"
                
                # Single line format with checkbox
                checkbox_value = st.session_state.select_all_fixable
                is_selected = st.checkbox(
                    f"🔧 {lecture_info['display']}: {lecture_info['audio_count']} audio • {lecture_info['image_count']} images • {lecture_info['summary_count']} summary - {fix_description}",
                    key=f"fix_{lecture_info['key']}", 
                    value=checkbox_value
                )
                
                if is_selected:
                    selected_fixes.append(lecture_info)
            
            # Apply fixes section
            if selected_fixes:
                st.markdown("---")
                st.write(f"**Ready to fix {len(selected_fixes)} lecture(s)**")
                
                if not st.session_state.confirm_fixes:
                    if st.button("🔧 Apply Selected Fixes", type="primary", key="apply_fixes_btn"):
                        st.session_state.confirm_fixes = True
                        st.rerun()
                else:
                    st.warning("⚠️ This will permanently modify files! Backups will be created automatically.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm - Apply Fixes", type="primary", key="confirm_apply"):
                            # Apply fixes
                            progress_bar = st.progress(0)
                            status_container = st.container()
                            
                            for i, lecture_info in enumerate(selected_fixes):
                                with status_container:
                                    st.write(f"🔄 Fixing {lecture_info['display']}...")
                                
                                success = False
                                message = ""
                                
                                if lecture_info['fix_type'] == 'remove_excess':
                                    success, message = fix_image_mismatch(
                                        lecture_info['path'],
                                        lecture_info['language'],
                                        lecture_info['audio_count'],
                                        lecture_info['image_files']
                                    )
                                elif lecture_info['fix_type'] == 'duplicate_last':
                                    success, message = duplicate_last_image(
                                        lecture_info['path'],
                                        lecture_info['language'],
                                        lecture_info['image_files'],
                                        lecture_info['audio_count']
                                    )
                                
                                with status_container:
                                    if success:
                                        st.success(f"✅ {lecture_info['display']}: {message}")
                                    else:
                                        st.error(f"❌ {lecture_info['display']}: {message}")
                                
                                progress_bar.progress((i + 1) / len(selected_fixes))
                            
                            st.success("🎉 All selected fixes have been applied!")
                            st.session_state.confirm_fixes = False
                            st.session_state.select_all_fixable = False
                            
                            if st.button("🔄 Refresh Page", key="refresh_after_fix"):
                                st.rerun()
                    
                    with col2:
                        if st.button("❌ Cancel", key="cancel_fixes"):
                            st.session_state.confirm_fixes = False
                            st.rerun()

    # All lectures status section
    st.header("📋 All Lectures Status")
    
    all_courses = []
    for subject, courses in organized_data.items():
        for course in courses:
            if (subject, course) not in all_courses:
                all_courses.append((subject, course))

    all_courses.sort(key=lambda x: x[1])

    for subject, course in all_courses:
        with st.expander(f"📚 {course}", expanded=False):
            for section in sorted(organized_data[subject][course].keys()):
                st.subheader(f"📖 {section}")

                lecture_keys = list(organized_data[subject][course][section].keys())
                sorted_lectures = sorted(
                    lecture_keys,
                    key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
                )

                for lecture in sorted_lectures:
                    lecture_data = organized_data[subject][course][section][lecture]
                    has_language = selected_language in lecture_data.get("languages", [])
                    
                    lang_data = lecture_data.get("language_data", {}).get(selected_language, {})
                    audio_count = lang_data.get("audio_count", 0)
                    image_count = lang_data.get("image_count", 0)
                    summary_audio_count = lang_data.get("summary_audio_count", 0)
                    
                    # Three-way comparison: images == regular audio == summary audio
                    three_way_match = (has_language and 
                                     audio_count > 0 and 
                                     image_count > 0 and 
                                     summary_audio_count > 0 and
                                     audio_count == image_count == summary_audio_count)

                    # Check if fixable
                    is_fixable = False
                    fix_note = ""
                    if has_language and audio_count > 0 and image_count > 0 and summary_audio_count > 0:
                        if audio_count == summary_audio_count:
                            if image_count == audio_count + 2:
                                is_fixable = True
                                fix_note = " (Fixable: -2 images)"
                            elif image_count == audio_count - 1:
                                is_fixable = True
                                fix_note = " (Fixable: +1 image)"

                    if three_way_match:
                        status_icon = "✅"
                    elif is_fixable:
                        status_icon = "🔧"
                    else:
                        status_icon = "⚠️"
                    
                    # Single line format as requested
                    st.write(f"{status_icon} {lecture} (English): {audio_count} audio • {image_count} images • {summary_audio_count} summary{fix_note}")

if __name__ == "__main__":
    main()