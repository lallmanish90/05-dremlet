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
import time
import json
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from openai import OpenAI

LM_STUDIO_API_KEY = "lm-studio"
LM_STUDIO_API_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_MODEL = "gemma-3-12b-it-qat"
PROMPT_TEMPLATE_PATH = os.path.join("config", "prompt.txt")


def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")


def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def load_prompt_template() -> str:
    """Load the translation prompt template"""
    try:
        if os.path.exists(PROMPT_TEMPLATE_PATH):
            with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        st.error(f"Error loading prompt template: {str(e)}")

    return (
        "You are a professional translator. Translate the following text "
        "from English to {TARGET_LANGUAGE}.\n\n{TEXT_CONTENT}"
    )


def translate_text(text: str, target_language: str) -> Tuple[bool, str, Optional[str]]:
    """Translate text using LM Studio's OpenAI-compatible API"""
    if not text or text.strip() == "":
        return False, "Empty text provided", None

    prompt_template = load_prompt_template()
    prompt = prompt_template.replace("{TARGET_LANGUAGE}", target_language).replace("{TEXT_CONTENT}", text)

    try:
        client = OpenAI(
            base_url=LM_STUDIO_API_URL,
            api_key=LM_STUDIO_API_KEY,
        )

        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        if response and response.choices and response.choices[0].message and response.choices[0].message.content:
            return True, "Translation successful", response.choices[0].message.content.strip()

        return False, "Unexpected API response format", None

    except Exception as e:
        return False, f"Error in translation: {str(e)}", None

st.set_page_config(page_title="13 Convert Text to multiple languages - Dreamlet", page_icon="🌐")

def find_section_files() -> Dict[str, Dict[str, Dict]]:
    """
    Find all section files prepared for multilingual processing
    
    Returns:
        Nested dictionary of course -> lecture -> data
    """
    input_dir = get_input_directory()
    
    # Find language-specific metadata files (metadata_english.json)
    metadata_files = glob.glob(os.path.join(input_dir, "**", "metadata_*.json"), recursive=True)
    
    organized_files = {}
    
    for metadata_path in metadata_files:
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            course = metadata.get("course", "uncategorized")
            lecture = metadata.get("lecture", "unknown")
            language = metadata.get("language", "Unknown")
            
            # Skip if not source language
            if language.lower() != "english":
                continue
            
            course_key = f"Course {course}" if course else "Uncategorized"
            lecture_key = f"Lecture {lecture}" if lecture else "Unknown"
            
            # Get the directory containing the metadata file
            base_dir = os.path.dirname(metadata_path)
            
            # Get language-specific text directory
            text_dir = metadata.get("text_dir")
            if not text_dir or not os.path.exists(text_dir):
                continue
            
            # Find all text files in the text directory
            section_files = glob.glob(os.path.join(text_dir, "*.txt"))
            
            if not section_files:
                continue
            
            # Add to organized files
            if course_key not in organized_files:
                organized_files[course_key] = {}
            
            # Add lecture data
            organized_files[course_key][lecture_key] = {
                "metadata_path": metadata_path,
                "base_dir": base_dir,
                "text_dir": text_dir,
                "section_files": sorted(section_files),
                "count": len(section_files)
            }
        except Exception:
            # Skip problematic metadata files
            continue
    
    return organized_files

def translate_section_files(
    section_files: List[str],
    target_language: str,
    output_dir: str
) -> List[Dict]:
    """
    Translate section files to the target language
    
    Args:
        section_files: List of section file paths
        target_language: Target language for translation
        output_dir: Directory to save translated files
        
    Returns:
        List of processing results
    """
    results = []
    
    for section_file in section_files:
        try:
            # Read the section file
            with open(section_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Skip empty sections
            if not content:
                results.append({
                    "file_path": section_file,
                    "status": "skipped",
                    "message": "Empty section"
                })
                continue
            
            # Create output filename
            file_name = os.path.basename(section_file)
            translated_path = os.path.join(output_dir, file_name)
            
            # Check if file already exists
            if os.path.exists(translated_path):
                results.append({
                    "file_path": section_file,
                    "status": "skipped",
                    "message": "Translated file already exists",
                    "translated_path": translated_path
                })
                continue
            
            # Translate text
            success, message, translated_text = translate_text(content, target_language)
            
            if not success or not translated_text:
                results.append({
                    "file_path": section_file,
                    "status": "error",
                    "message": message
                })
                continue
            
            # Save translated text
            with open(translated_path, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            
            results.append({
                "file_path": section_file,
                "status": "success",
                "message": "Translation successful",
                "translated_path": translated_path,
                "original_length": len(content),
                "translated_length": len(translated_text)
            })
        
        except Exception as e:
            results.append({
                "file_path": section_file,
                "status": "error",
                "message": f"Error: {str(e)}"
            })
    
    return results

def main():
    st.title("13 Convert Text to multiple languages")
    st.write("Translate transcript sections to other languages for multilingual video production.")
    
    # Check for input directory
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an input directory and add content.")
        return
    
    # Find section files organized by language
    organized_files = find_section_files()
    
    if not organized_files:
        st.warning("No language-specific section files found in the input directory.")
        st.info("Please run the Prepare Folders for Multilingual step first.")
        # Show empty UI instead of returning
        organized_files = {}
    
    # Language Settings
    st.header("Translation Settings")
    
    # Target language selection
    target_language = st.selectbox(
        "Select Target Language",
        options=[
            "Spanish", "French", "German", "Italian", "Portuguese", 
            "Russian", "Japanese", "Chinese", "Korean", "Arabic",
            "Hindi", "Bengali", "Dutch", "Swedish", "Polish"
        ],
        index=0  # Default to Spanish
    )
    
    # Section Selection
    st.header("Select Sections for Translation")
    
    # Create organized selection interface with expandable sections
    selected_lectures = {}
    
    # Sort courses numerically
    sorted_courses = sorted(
        organized_files.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    for course in sorted_courses:
        with st.expander(f"Course: {course}"):
            # Option to select all lectures in this course
            all_in_course = st.checkbox(f"Select all lectures in {course}", key=f"all_{course}")
            
            # Sort lectures numerically
            sorted_lectures = sorted(
                organized_files[course].keys(),
                key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
            )
            
            for lecture in sorted_lectures:
                lecture_data = organized_files[course][lecture]
                
                # Display lecture info
                st.write(f"**{lecture}:** {lecture_data['count']} sections")
                
                # Select this lecture
                if all_in_course:
                    selected = True
                    st.write("✅ Selected (from 'Select all')")
                else:
                    selected = st.checkbox(f"Translate {lecture}", key=f"{course}_{lecture}")
                
                if selected:
                    selected_lectures[(course, lecture)] = lecture_data
    
    # Translation Processing
    st.header("Translate Text")
    
    # Calculate total for selected lectures
    if selected_lectures:
        total_sections = sum(data["count"] for data in selected_lectures.values())
        
        st.write(f"**Total selected:** {len(selected_lectures)} lectures, {total_sections} sections")
        
        # Start translation button
        if st.button("Translate Sections", disabled=len(selected_lectures) == 0):
            # Process translation for all selected lectures
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            all_results = []
            processed_count = 0
            
            for (course, lecture), lecture_data in selected_lectures.items():
                # Update status
                status_text.info(f"Translating {course} - {lecture}")
                
                # Create output directory for translated sections
                base_dir = lecture_data["base_dir"]
                target_dir = os.path.join(base_dir, f"{target_language}_text")
                ensure_directory_exists(target_dir)
                
                # Translate sections
                results = translate_section_files(
                    lecture_data["section_files"],
                    target_language,
                    target_dir
                )
                
                all_results.extend(results)
                
                # Create metadata for translated sections
                try:
                    with open(lecture_data["metadata_path"], 'r', encoding='utf-8') as f:
                        original_metadata = json.load(f)
                    
                    # Create new metadata for translated content
                    translated_metadata = original_metadata.copy()
                    translated_metadata["language"] = target_language
                    translated_metadata["original_language"] = "English"
                    translated_metadata["text_dir"] = target_dir
                    
                    # Save metadata
                    translated_metadata_path = os.path.join(
                        base_dir, f"metadata_{target_language.lower()}.json"
                    )
                    with open(translated_metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(translated_metadata, f, indent=2)
                except Exception as e:
                    st.error(f"Error creating metadata: {str(e)}")
                
                # Update progress
                processed_count += 1
                progress = processed_count / len(selected_lectures)
                progress_bar.progress(progress)
                
                # Small delay for UI updates
                time.sleep(0.1)
            
            # Complete
            status_text.success("Translation complete")
            
            # Display results
            with results_container:
                st.subheader("Processing Results")
                
                # Statistics
                success_count = sum(1 for r in all_results if r["status"] == "success")
                skipped_count = sum(1 for r in all_results if r["status"] == "skipped")
                error_count = sum(1 for r in all_results if r["status"] == "error")
                
                st.write(f"✅ Successfully translated: {success_count}")
                st.write(f"⏭️ Skipped: {skipped_count}")
                st.write(f"❌ Errors: {error_count}")
                
                # Detailed results by course and lecture
                for (course, lecture), lecture_data in selected_lectures.items():
                    with st.expander(f"{course} - {lecture}"):
                        # Filter results for this lecture
                        lecture_results = [r for r in all_results if any(
                            r["file_path"] == sf for sf in lecture_data["section_files"]
                        )]
                        
                        lecture_success = sum(1 for r in lecture_results if r["status"] == "success")
                        lecture_skipped = sum(1 for r in lecture_results if r["status"] == "skipped")
                        lecture_error = sum(1 for r in lecture_results if r["status"] == "error")
                        
                        st.write(f"**Results:** {lecture_success} translated, {lecture_skipped} skipped, {lecture_error} errors")
                        
                        # Show sample translations
                        if lecture_success > 0:
                            st.write("**Sample translations:**")
                            
                            # Show up to 3 successful translations as examples
                            success_results = [r for r in lecture_results if r["status"] == "success"]
                            sample_count = min(3, len(success_results))
                            
                            for i in range(sample_count):
                                result = success_results[i]
                                file_name = os.path.basename(result["file_path"])
                                
                                with st.expander(f"Sample {i+1}: {file_name}"):
                                    # Show original text
                                    with open(result["file_path"], 'r', encoding='utf-8') as f:
                                        original_text = f.read().strip()
                                    
                                    # Show translated text
                                    with open(result["translated_path"], 'r', encoding='utf-8') as f:
                                        translated_text = f.read().strip()
                                    
                                    st.write("**Original (English):**")
                                    st.text(original_text[:300] + ("..." if len(original_text) > 300 else ""))
                                    
                                    st.write(f"**Translated ({target_language}):**")
                                    st.text(translated_text[:300] + ("..." if len(translated_text) > 300 else ""))
                        
                        # Error results
                        if lecture_error > 0:
                            st.write("**Errors:**")
                            for result in lecture_results:
                                if result["status"] == "error":
                                    file_name = os.path.basename(result["file_path"])
                                    st.write(f"- {file_name}: {result['message']}")
    else:
        st.info("No lectures selected for translation.")

if __name__ == "__main__":
    main()
