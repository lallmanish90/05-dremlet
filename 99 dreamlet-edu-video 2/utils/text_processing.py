import re
import os
from typing import List, Dict, Tuple, Optional, Union

def extract_slide_blocks(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract slide blocks from transcript text
    
    Args:
        text: Transcript text content
        
    Returns:
        List of tuples (slide_number, slide_content, slide_marker_format)
    """
    # Match patterns for slide markers
    patterns = [
        # Format: [Slide X - Start] ... [Slide X - End] - Standard format
        (r'\[Slide\s+(\d+)\s*-\s*Start\](.*?)\[Slide\s+\1\s*-\s*End\]', '[Slide {} - Start]', '[Slide {} - End]'),
        
        # Format: [Slide X - Start HH:MM] ... [Slide X - End HH:MM] - With timestamps
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+[\d:]+\](.*?)\[Slide\s+\1\s*-\s*End\s+[\d:]+\]', '[Slide {} - Start]', '[Slide {} - End]'),
        
        # Format: [Slide X - Start HH] ... [Slide X - End HH] - With abbreviated timestamps
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+\d+\](.*?)\[Slide\s+\1\s*-\s*End\s+\d+\]', '[Slide {} - Start]', '[Slide {} - End]'),
        
        # Format: [Slide X] ... [End Slide X] - Alternative format
        (r'\[Slide\s+(\d+)\](.*?)\[End\s+Slide\s+\1\]', '[Slide {}]', '[End Slide {}]'),
        
        # Format: ## Slide X ... ## End Slide X - Markdown format
        (r'##\s*Slide\s+(\d+)(.*?)##\s*End\s+Slide\s+\1', '## Slide {}', '## End Slide {}'),
        
        # Additional formats to handle more cases
        
        # Format: [Slide #X - Start] ... [Slide #X - End] - With hash
        (r'\[Slide\s+#(\d+)\s*-\s*Start\](.*?)\[Slide\s+#\1\s*-\s*End\]', '[Slide #{} - Start]', '[Slide #{} - End]'),
        
        # Format: [Slide X] ... [Slide X+1] or [Slide X] ... [End] - Without matching end markers
        (r'\[Slide\s+(\d+)\](.*?)(?=\[Slide\s+\d+\]|\[End\]|$)', '[Slide {}]', '[Slide {} - End]'),
        
        # Format: Slide X: ... Slide X+1: or Slide X: ... End - Without brackets
        (r'Slide\s+(\d+):(.*?)(?=Slide\s+\d+:|End|$)', 'Slide {}:', 'End'),
        
        # Format: [Slide-X] ... [Slide-X-End] - With hyphens
        (r'\[Slide-(\d+)\](.*?)\[Slide-\1-End\]', '[Slide-{}]', '[Slide-{}-End]'),
        
        # Format: Slide X Start ... Slide X End - Without any special characters
        (r'Slide\s+(\d+)\s+Start(.*?)Slide\s+\1\s+End', 'Slide {} Start', 'Slide {} End')
    ]
    
    # Try all patterns
    all_matches = []
    for pattern, start_format, end_format in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            for match in matches:
                slide_number = match[0]
                content = match[1]
                all_matches.append((slide_number, content, (start_format, end_format)))
    
    # If we found any matches across all patterns, sort them by slide number and return
    if all_matches:
        # Sort by numeric slide number
        return sorted(all_matches, key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    
    # Try a fallback approach if no matches were found
    # Look for any indication of slides in the text
    slide_indicators = re.findall(r'(?:Slide|SLIDE)\s+(\d+)', text)
    if slide_indicators:
        # If we found slide indicators but couldn't extract blocks,
        # split the text by slide indicators and create artificial blocks
        sections = []
        for i, slide_num in enumerate(slide_indicators):
            if i < len(slide_indicators) - 1:
                next_slide_pattern = f"(?:Slide|SLIDE)\\s+{slide_indicators[i+1]}"
                section_text = re.split(next_slide_pattern, text, 1)[0]
                text = text.replace(section_text, '', 1)
                sections.append((slide_num, section_text, ('[Slide {} - Start]', '[Slide {} - End]')))
            else:
                # Last slide takes the rest of the text
                sections.append((slide_num, text, ('[Slide {} - Start]', '[Slide {} - End]')))
        
        if sections:
            return sections
    
    return []

def count_slides_in_transcript(text: str) -> int:
    """
    Count the number of slides in a transcript file
    
    Args:
        text: Transcript text content
        
    Returns:
        Number of slides
    """
    slide_blocks = extract_slide_blocks(text)
    return len(slide_blocks)

def count_slides_in_slide_file(text: str) -> int:
    """
    Count the number of slides in a slide description file
    
    Args:
        text: Slide file content
        
    Returns:
        Number of slides
    """
    # Match common slide description headers
    patterns = [
        r'Slide\s+\d+\s*[:-]',  # "Slide X:" or "Slide X -"
        r'^\s*\d+\s*[:-]',      # "X:" or "X -" at the start of a line
        r'^\s*\[Slide\s+\d+\]'  # "[Slide X]" at the start of a line
    ]
    
    count = 0
    for line in text.split('\n'):
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                count += 1
                break
    
    return count

def extract_content_outside_slides(text: str) -> Tuple[str, str, List[Tuple[str, str, str]]]:
    """
    Extract content outside slide markers (pre-content and post-content)
    
    Args:
        text: Transcript text content
        
    Returns:
        Tuple of (pre_content, post_content, slide_blocks)
    """
    slide_blocks = extract_slide_blocks(text)
    
    if not slide_blocks:
        return "", "", []
    
    # Find the position of the first slide start marker
    first_slide_number, first_slide_content, (start_format, _) = slide_blocks[0]
    first_marker = start_format.format(first_slide_number)
    first_marker_pos = text.find(first_marker)
    
    # Find the position of the last slide end marker
    last_slide_number, last_slide_content, (_, end_format) = slide_blocks[-1]
    last_marker = end_format.format(last_slide_number)
    last_marker_pos = text.rfind(last_marker) + len(last_marker)
    
    # Extract pre and post content
    pre_content = text[:first_marker_pos].strip()
    post_content = text[last_marker_pos:].strip()
    
    return pre_content, post_content, slide_blocks

def standardize_slide_markers(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Standardize slide markers to the preferred format [Slide X - Start] and [Slide X - End]
    
    Args:
        text: Transcript text content
        
    Returns:
        Tuple of (standardized_text, list of modifications)
    """
    modifications = []
    standardized_text = text
    
    # Patterns to identify various slide marker formats
    patterns = [
        # [Slide X - Start HH:MM] format
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+([\d:]+)\]', r'[Slide \1 - Start]'),
        
        # [Slide X - End HH:MM] format
        (r'\[Slide\s+(\d+)\s*-\s*End\s+([\d:]+)\]', r'[Slide \1 - End]'),
        
        # [Slide X - Start HH] format (just hours)
        (r'\[Slide\s+(\d+)\s*-\s*Start\s+(\d+)\]', r'[Slide \1 - Start]'),
        
        # [Slide X - End HH] format (just hours)
        (r'\[Slide\s+(\d+)\s*-\s*End\s+(\d+)\]', r'[Slide \1 - End]'),
        
        # [Slide X - Title Slide: Start] format
        (r'\[Slide\s+(\d+)\s*-\s*Title\s+Slide:\s*Start\]', r'[Slide \1 - Start]'),
        
        # [Slide X - Title Slide: End] format
        (r'\[Slide\s+(\d+)\s*-\s*Title\s+Slide:\s*End\]', r'[Slide \1 - End]')
    ]
    
    for pattern, replacement in patterns:
        # Find all matches
        matches = re.findall(pattern, standardized_text)
        
        # Apply replacements
        for match in matches:
            slide_number = match[0] if isinstance(match, tuple) else match
            
            # Construct the original marker based on the pattern
            if "Title Slide" in pattern:
                if "Start" in pattern:
                    original = f"[Slide {slide_number} - Title Slide: Start]"
                else:
                    original = f"[Slide {slide_number} - Title Slide: End]"
                mod_type = "title_slide_format_standardized"
            else:
                timestamp = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                if "Start" in pattern:
                    original = f"[Slide {slide_number} - Start {timestamp}]".strip()
                else:
                    original = f"[Slide {slide_number} - End {timestamp}]".strip()
                mod_type = "timestamp_removed"
            
            new = replacement.replace(r'\1', slide_number)
            
            # Record the modification
            modifications.append({
                "type": mod_type,
                "slide": slide_number,
                "original": original,
                "new": new
            })
            
            # Replace in the text
            standardized_text = standardized_text.replace(original, new)
    
    return standardized_text, modifications

def adjust_transcript_structure(text: str) -> str:
    """
    Adjust transcript structure to ensure consistency
    
    Args:
        text: Transcript text content
        
    Returns:
        Adjusted transcript text
    """
    # First, standardize all slide markers
    standardized_text, _ = standardize_slide_markers(text)
    
    # Then extract content and slide blocks from standardized text
    pre_content, post_content, slide_blocks = extract_content_outside_slides(standardized_text)
    
    if not slide_blocks:
        return standardized_text  # Return the standardized text even if no slide blocks found
    
    # Rebuild the transcript with adjustments
    adjusted_text = ""
    
    # Process slide blocks
    for i, (slide_number, content, (start_format, end_format)) in enumerate(slide_blocks):
        # Format slide markers
        start_marker = start_format.format(slide_number)
        end_marker = end_format.format(slide_number)
        
        # For the first slide, include pre-content
        if i == 0 and pre_content:
            adjusted_text += start_marker + "\n" + pre_content + "\n" + content.strip() + "\n" + end_marker + "\n\n"
        # For the last slide, include post-content
        elif i == len(slide_blocks) - 1 and post_content:
            adjusted_text += start_marker + "\n" + content.strip() + "\n" + post_content + "\n" + end_marker + "\n\n"
        else:
            adjusted_text += start_marker + "\n" + content.strip() + "\n" + end_marker + "\n\n"
    
    return adjusted_text

def break_transcript_into_sections(text: str) -> List[Dict[str, str]]:
    """
    Break transcript into sections for TTS processing
    
    Args:
        text: Transcript text content
        
    Returns:
        List of dictionaries with slide number and content
    """
    slide_blocks = extract_slide_blocks(text)
    
    sections = []
    for slide_number, content, _ in slide_blocks:
        sections.append({
            "slide_number": slide_number,
            "content": content.strip()
        })
    
    return sections

def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS processing
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'__(.*?)__', r'\1', text)      # Underline
    text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
    
    # Remove URLs but keep the link text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove special characters that might affect TTS
    text = re.sub(r'[#*_~`]', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def calculate_word_count(text: str) -> int:
    """
    Calculate the word count in a text
    
    Args:
        text: Text to count words in
        
    Returns:
        Word count
    """
    # Clean the text first
    cleaned_text = clean_text_for_tts(text)
    
    # Split by whitespace and count
    words = cleaned_text.split()
    return len(words)

def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate audio duration based on word count
    
    Args:
        text: Text content
        words_per_minute: Speaking rate (default: 150 WPM)
        
    Returns:
        Estimated duration in seconds
    """
    word_count = calculate_word_count(text)
    
    # Calculate duration in minutes, then convert to seconds
    duration_minutes = word_count / words_per_minute
    duration_seconds = duration_minutes * 60
    
    return duration_seconds

def remove_headers(text: str) -> Tuple[str, int]:
    """
    Remove Markdown and other header formatting from text content
    
    Args:
        text: Text content that may contain headers
        
    Returns:
        Tuple of (text_without_headers, headers_removed_count)
    """
    headers_removed = 0
    modified_text = text
    
    # Pattern for Markdown headers (# Header, ## Subheader, etc.)
    md_header_pattern = r'^(#{1,6})\s+(.*?)$'
    
    # Process text line by line
    lines = modified_text.split('\n')
    for i, line in enumerate(lines):
        # Check for Markdown headers
        md_match = re.match(md_header_pattern, line)
        if md_match:
            # Extract the header content, preserving only the text
            header_content = md_match.group(2)
            lines[i] = header_content
            headers_removed += 1
    
    # Join lines back together
    modified_text = '\n'.join(lines)
    
    return modified_text, headers_removed
