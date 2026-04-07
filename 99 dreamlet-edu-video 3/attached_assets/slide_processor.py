#!/usr/bin/env python3
"""
Lecture Slide Converter
----------------------
Simple utility to convert lecture slide notes from a timestamped format to a clean format.
This script will:
1. Process all files in the input directory
2. Remove timestamp information
3. Clean unwanted content
4. Handle duplicate slide markers (using only the first occurrence)
5. Overwrite original files in-place

Usage: Simply run this script without arguments
    python slide_processor.py

The script will process all .md and .txt files in the 'input' directory.
"""

import os
import re
import glob
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def extract_slides_from_content(content):
    """
    Extract slides from content, handling multiple slide sequences.
    Handles both timestamped format [Slide N - Start: MM:SS] and 
    already-converted format [Slide N - Start].
    
    Args:
        content (str): The file content to extract slides from
        
    Returns:
        list: List of (slide_num, content) tuples
    """
    # Fix incomplete slide markers (missing closing brackets)
    content = re.sub(r'\[Slide (\d+) - End: (\d+:\d+)(?!\])', r'[Slide \1 - End: \2]', content)
    
    # Remove Word Count line that might appear after slide markers
    content = re.sub(r'(\[Slide \d+ - End.*?\])\s*\n\s*Word Count:\s*\d+\s*\n', r'\1\n', content)
    
    # Create a standardized version of the content with all timestamps removed
    # This helps when there are mixed formats for the same slide number
    standardized_content = re.sub(r'\[Slide (\d+) - Start: \d+:\d+\]', r'[Slide \1 - Start]', content)
    standardized_content = re.sub(r'\[Slide (\d+) - End: \d+:\d+\]', r'[Slide \1 - End]', standardized_content)
    
    # Find all slide start markers with their positions in the standardized content
    slide_markers = [(int(m.group(1)), m.start()) for m in re.finditer(r'\[Slide (\d+) - Start\]', standardized_content)]
    
    if not slide_markers:
        logging.warning("No slide markers found in the standardized content. Trying original content.")
        # Fallback to original content if standardization didn't work
        slide_markers = [(int(m.group(1)), m.start()) for m in re.finditer(r'\[Slide (\d+) - Start(?::\s*\d+:\d+)?\]', content)]
        if not slide_markers:
            logging.warning("No slide markers found in the content.")
            return []
    
    # Create a dictionary to collect slide content - one entry per slide number
    slide_content_map = {}
    
    # Try multiple patterns to extract slide content from both standardized and original content
    slide_patterns = [
        (standardized_content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End\]'),  # No timestamps
        (content, r'\[Slide (\d+) - Start: (\d+:\d+)\](.*?)\[Slide \1 - End: (\d+:\d+)\]'),  # Both timestamps
        (content, r'\[Slide (\d+) - Start: (\d+:\d+)\](.*?)\[Slide \1 - End\]'),  # Start timestamp only
        (content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End: (\d+:\d+)\]'),  # End timestamp only
        (content, r'\[Slide (\d+) - Start\](.*?)\[Slide \1 - End\]')  # No timestamps (original)
    ]
    
    # Try each pattern to extract slide content
    for content_to_use, pattern in slide_patterns:
        for match in re.finditer(pattern, content_to_use, re.DOTALL):
            slide_num = int(match.group(1))
            
            # Determine content group based on the pattern
            if "Start: " in pattern and "End: " in pattern:  # Both timestamps
                slide_content = match.group(3).strip()
            else:  # Either no timestamps or only one timestamp
                slide_content = match.group(2).strip()
            
            # Clean the slide content
            slide_content = clean_slide_content(slide_content)
            
            # Keep content for each slide number (first match only)
            if slide_num not in slide_content_map:
                slide_content_map[slide_num] = slide_content
                logging.info(f"Extracted content for Slide {slide_num}")
    
    # If we didn't find any slides using patterns, try a last resort approach
    if not slide_content_map:
        logging.warning("No slides extracted with regular patterns. Attempting manual extraction...")
        
        # Find all start markers in the original content
        start_markers = list(re.finditer(r'\[Slide (\d+) - Start(?::\s*\d+:\d+)?\]', content))
        end_markers = list(re.finditer(r'\[Slide (\d+) - End(?::\s*\d+:\d+)?\]', content))
        
        # Build dictionaries of positions
        start_positions = {}
        for match in start_markers:
            slide_num = int(match.group(1))
            if slide_num not in start_positions:  # Take first occurrence only
                start_positions[slide_num] = match.end()
        
        end_positions = {}
        for match in end_markers:
            slide_num = int(match.group(1))
            if slide_num not in end_positions:  # Take first occurrence only
                end_positions[slide_num] = match.start()
        
        # Extract content between markers
        for slide_num in sorted(set(start_positions.keys()) & set(end_positions.keys())):
            start_pos = start_positions[slide_num]
            end_pos = end_positions[slide_num]
            
            if start_pos < end_pos:
                slide_content = content[start_pos:end_pos].strip()
                slide_content = clean_slide_content(slide_content)
                slide_content_map[slide_num] = slide_content
                logging.info(f"Manually extracted content for Slide {slide_num}")
    
    # Convert the map to a list of tuples and sort by slide number
    slides = [(str(num), content) for num, content in slide_content_map.items()]
    slides.sort(key=lambda x: int(x[0]))
    
    if not slides:
        logging.error("Failed to extract any slides after trying all methods.")
    
    return slides

def clean_slide_content(content):
    """
    Clean the slide content by removing unwanted elements.
    
    Args:
        content (str): The slide content to clean
        
    Returns:
        str: The cleaned slide content
    """
    # Remove lines containing "transcript" or "duration" (often metadata)
    lines = content.split('\n')
    lines = [line for line in lines if 'transcript' not in line.lower() and 'duration' not in line.lower()]
    
    # Remove Markdown headers (e.g., # Header, ## Subheader)
    lines = [re.sub(r'^#+\s+', '', line) for line in lines]
    
    # Remove text inside brackets that mentions music or other stage directions
    # (e.g., [Mysterious music fades in], [Audience applause])
    lines = [re.sub(r'\[.*?music.*?\]', '', line) for line in lines]
    lines = [re.sub(r'\[.*?applause.*?\]', '', line) for line in lines]
    
    # Remove timestamp information in format [MM:SS - NN:SS]
    lines = [re.sub(r'\[\d+:\d+\s*-\s*\d+:\d+\]', '', line) for line in lines]
    
    # Remove "Word Count: NNN" lines
    lines = [line for line in lines if not re.match(r'^\s*Word Count:\s*\d+\s*$', line)]
    
    # Remove empty lines (that might be left after removing content)
    lines = [line for line in lines if line.strip()]
    
    # Remove bracketed placeholders like [Name]
    lines = [re.sub(r'\[Name\]', 'Professor', line) for line in lines]
    
    # Handle formatting: bold/italic - we keep the content but remove the markdown syntax
    lines = [re.sub(r'\*\*(.*?)\*\*', r'\1', line) for line in lines]  # Bold
    lines = [re.sub(r'\*(.*?)\*', r'\1', line) for line in lines]      # Italic
    
    # Remove any lines that are purely metadata (like "_Duration: 20 minutes (1200 words)_")
    lines = [line for line in lines if not re.match(r'^\s*_.*?_\s*$', line)]
    
    # Join the lines back together
    return '\n'.join(lines)

def format_slides(slides):
    """
    Apply standard formatting to slides.
    
    Args:
        slides (list): List of (slide_num, content) tuples
        
    Returns:
        str: Formatted content
    """
    formatted_lines = []
    for i, (slide_num, content) in enumerate(slides):
        formatted_lines.append(f"[Slide {slide_num} - Start]")
        
        # Add empty line after first slide start tag only
        if i == 0:
            formatted_lines.append("")
                
        formatted_lines.append(content)
        formatted_lines.append(f"[Slide {slide_num} - End]")
        
        # Add empty line after each slide
        formatted_lines.append("")
    
    return '\n'.join(formatted_lines)

def convert_file(file_path):
    """
    Convert a single file from timestamped format to clean format and overwrite it.
    
    Args:
        file_path (str): Path to the file to convert
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logging.info(f"Processing {file_path}...")
        
        # Read the input file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup of original file
        backup_file = f"{file_path}.bak"
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Created backup at {backup_file}")
        except Exception as e:
            logging.warning(f"Failed to create backup: {e}")
        
        # Extract slides from content
        slides = extract_slides_from_content(content)
        
        if not slides:
            logging.error(f"No valid slides found in {file_path}")
            return False
        
        # Format slides
        formatted_content = format_slides(slides)
        
        # Verify the formatted content before writing to ensure no duplicate slide markers
        has_duplicates = False
        slide_counts = {}
        
        # Count occurrences of each slide marker in the formatted content
        for match in re.finditer(r'\[Slide (\d+) - Start\]', formatted_content):
            slide_num = match.group(1)
            slide_counts[slide_num] = slide_counts.get(slide_num, 0) + 1
        
        # Check for duplicates
        for slide_num, count in slide_counts.items():
            if count > 1:
                logging.error(f"Error: Formatted content still contains {count} occurrences of [Slide {slide_num} - Start]")
                has_duplicates = True
        
        # If duplicates found, try another approach - last resort recovery
        if has_duplicates:
            logging.warning("Attempting to recover by processing only unique slide numbers...")
            
            # Extract unique slide numbers and their content
            unique_slides = []
            seen_slide_nums = set()
            
            for slide_num, slide_content in slides:
                if slide_num not in seen_slide_nums:
                    unique_slides.append((slide_num, slide_content))
                    seen_slide_nums.add(slide_num)
            
            # Sort by slide number
            unique_slides.sort(key=lambda x: int(x[0]))
            
            # Format the unique slides
            formatted_content = format_slides(unique_slides)
        
        # Overwrite the original file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        logging.info(f"Successfully converted {file_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error converting {file_path}: {e}")
        return False

def process_directory(input_dir):
    """
    Process all markdown and text files in a directory.
    
    Args:
        input_dir (str): Path to the input directory
        
    Returns:
        tuple: (success_count, total_count)
    """
    # Find all markdown and text files
    md_files = glob.glob(os.path.join(input_dir, "*.md"))
    txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
    all_files = md_files + txt_files
    
    # Exclude backup files
    all_files = [f for f in all_files if not f.endswith('.bak')]
    
    success_count = 0
    total_count = len(all_files)
    
    if total_count == 0:
        logging.warning(f"No .md or .txt files found in {input_dir}")
        return 0, 0
    
    for file_path in all_files:
        if convert_file(file_path):
            success_count += 1
    
    # Clean up all backup files after successful conversion
    backup_files = glob.glob(os.path.join(input_dir, "*.bak"))
    ba_files = glob.glob(os.path.join(input_dir, "*.ba"))
    md_ba_files = glob.glob(os.path.join(input_dir, "*.md.ba"))
    all_backup_files = backup_files + ba_files + md_ba_files
    
    if all_backup_files:
        logging.info(f"Cleaning up {len(all_backup_files)} backup files...")
        for backup_file in all_backup_files:
            try:
                os.remove(backup_file)
                logging.info(f"Removed backup file: {backup_file}")
            except Exception as e:
                logging.warning(f"Failed to remove backup file {backup_file}: {e}")
    
    logging.info(f"Processed {success_count} of {total_count} files in {input_dir}")
    return success_count, total_count

def main():
    """
    Convert and overwrite ALL files in the input directory.
    No arguments needed, just run this script.
    """
    import sys
    
    # Check if any arguments were provided
    if len(sys.argv) > 1:
        # Use the provided directory or file
        path = sys.argv[1]
        if os.path.isdir(path):
            input_dir = path
            logging.info(f"Using provided directory: {input_dir}")
        elif os.path.isfile(path):
            # Process a single file
            if convert_file(path):
                logging.info(f"Successfully converted {path}")
                return 0
            else:
                logging.error(f"Failed to convert {path}")
                return 1
        else:
            logging.error(f"Provided path does not exist: {path}")
            return 1
    # No arguments, use default behavior
    elif os.path.exists("input") and os.path.isdir("input"):
        input_dir = "input"
        logging.info("Using 'input' directory for processing files.")
    else:
        input_dir = "."
        logging.info("No 'input' directory found, processing files in current directory.")
    
    # Find all markdown and text files in the input directory
    md_files = glob.glob(os.path.join(input_dir, "*.md"))
    txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
    all_files = md_files + txt_files
    
    if not all_files:
        logging.warning(f"No .md or .txt files found in {input_dir}. Please add files and try again.")
        return 1
    
    # Process all files in the input directory in-place (overwriting originals)
    logging.info(f"Converting and overwriting ALL {len(all_files)} files in the '{input_dir}' directory...")
    
    success_count, total_count = process_directory(input_dir)
    
    if success_count == 0:
        logging.error(f"Failed to convert any files in {input_dir}.")
        return 1
    
    logging.info(f"Successfully converted {success_count} of {total_count} files.")
    logging.info(f"CONVERSION COMPLETE! Your files have been cleaned and formatted.")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())