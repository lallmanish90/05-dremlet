"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

STATUS: CURRENT
PURPOSE: Create, save, and run workflow templates for batch execution of the current page pipeline.
MAIN INPUTS:
- workflow definitions
- selected projects and lecture folders under `input/`
MAIN OUTPUTS:
- workflow templates, workflow state, and checkpoints stored under `.dreamlet-cli-state/`
REQUIRED CONFIG / ASSETS:
- `.dreamlet-cli-state/workflow_state`
- `.dreamlet-cli-state/workflow_templates`
- `.dreamlet-cli-state/checkpoints`
EXTERNAL SERVICES:
- none
HARDWARE ASSUMPTIONS:
- none

UX Enhancement: Advanced Workflow Configuration and Template Management
Purpose: Manage workflow templates, batch processing, and automated workflows
Requirements: UX-001 (Comprehensive Workflow Management)
"""

from dreamlet_cli.compat import st
import os
import json
import time
import random
import re
import shutil
import fnmatch
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# ============================================================================
# UTILITY FUNCTIONS - UX_WORKFLOW_MANAGER_v1.2.0 - Last updated: 2025-01-01
# ============================================================================

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def get_output_directory() -> str:
    """Get the path to the output directory"""
    return os.path.join(os.getcwd(), "output")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
    except Exception as e:
        st.error(f"Failed to create directory {directory_path}: {e}")

def get_workflow_state_dir() -> str:
    """Get workflow state directory"""
    state_dir = os.path.join(os.getcwd(), ".dreamlet-cli-state", "workflow_state")
    ensure_directory_exists(state_dir)
    return state_dir

def get_templates_dir() -> str:
    """Get workflow templates directory"""
    templates_dir = os.path.join(os.getcwd(), ".dreamlet-cli-state", "workflow_templates")
    ensure_directory_exists(templates_dir)
    return templates_dir

def get_checkpoints_dir() -> str:
    """Get checkpoints directory"""
    checkpoints_dir = os.path.join(os.getcwd(), ".dreamlet-cli-state", "checkpoints")
    ensure_directory_exists(checkpoints_dir)
    return checkpoints_dir

def save_workflow_state(workflow_id: str, state: Dict) -> bool:
    """Save workflow state to file"""
    try:
        state_file = os.path.join(get_workflow_state_dir(), f"{workflow_id}.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Failed to save workflow state: {e}")
        return False

def load_workflow_state(workflow_id: str) -> Dict:
    """Load workflow state from file"""
    try:
        state_file = os.path.join(get_workflow_state_dir(), f"{workflow_id}.json")
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Failed to load workflow state: {e}")
    return {}

def get_default_workflow_steps() -> List[Dict]:
    """Get default workflow steps based on actual pages in your system"""
    return [
        {
            "id": "01_adjust",
            "name": "Adjust AAA EEE",
            "description": "Split AAA and EEE files into individual content sections",
            "required": True,
            "estimated_time": 300,
            "enabled": True
        },
        {
            "id": "02_rename",
            "name": "Rename Files",
            "description": "Fix incorrectly named files according to standard naming conventions",
            "required": True,
            "estimated_time": 180,
            "enabled": True
        },
        {
            "id": "03_save_text",
            "name": "Save Text Sections",
            "description": "Break transcript and summary files into sections for TTS processing",
            "required": True,
            "estimated_time": 240,
            "enabled": True
        }
    ]

def save_workflow_template(template_name: str, template_data: Dict) -> bool:
    """Save workflow template"""
    try:
        template_file = os.path.join(get_templates_dir(), f"{template_name}.json")
        template_data["created_at"] = datetime.now().isoformat()
        template_data["version"] = "1.0.0"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Failed to save template: {e}")
        return False

def load_workflow_template(template_name: str) -> Dict:
    """Load workflow template"""
    try:
        template_file = os.path.join(get_templates_dir(), f"{template_name}.json")
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Failed to load template: {e}")
    return {}

def get_available_templates() -> List[str]:
    """Get list of available workflow templates"""
    try:
        templates_dir = get_templates_dir()
        templates = []
        if os.path.exists(templates_dir):
            for file in os.listdir(templates_dir):
                if file.endswith('.json'):
                    templates.append(file[:-5])  # Remove .json extension
        return sorted(templates)
    except Exception as e:
        st.error(f"Failed to get templates: {e}")
        return []

def create_checkpoint(workflow_id: str, step_id: str, data: Dict) -> bool:
    """Create a checkpoint for workflow state"""
    try:
        timestamp = int(time.time())
        checkpoint_file = os.path.join(get_checkpoints_dir(), f"{workflow_id}_{step_id}_{timestamp}.json")
        checkpoint_data = {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Failed to create checkpoint: {e}")
        return False

def get_workflow_checkpoints(workflow_id: str) -> List[Dict]:
    """Get available checkpoints for a workflow"""
    checkpoints = []
    try:
        checkpoints_dir = get_checkpoints_dir()
        if os.path.exists(checkpoints_dir):
            for file in os.listdir(checkpoints_dir):
                if file.startswith(f"{workflow_id}_") and file.endswith('.json'):
                    try:
                        with open(os.path.join(checkpoints_dir, file), 'r', encoding='utf-8') as f:
                            checkpoint = json.load(f)
                            checkpoints.append(checkpoint)
                    except Exception:
                        continue
        
        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    except Exception as e:
        st.error(f"Failed to get checkpoints: {e}")
    
    return checkpoints

def validate_workflow_template(template: Dict) -> Tuple[bool, List[str]]:
    """Validate workflow template structure"""
    errors = []
    
    if not isinstance(template, dict):
        errors.append("Template must be a dictionary")
        return False, errors
    
    if "name" not in template:
        errors.append("Template must have a name")
    
    if "steps" not in template:
        errors.append("Template must have steps")
    else:
        steps = template["steps"]
        if not isinstance(steps, list):
            errors.append("Steps must be a list")
        else:
            step_ids = set()
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"Step {i} must be a dictionary")
                    continue
                    
                if "id" not in step:
                    errors.append(f"Step {i} must have an id")
                else:
                    if step["id"] in step_ids:
                        errors.append(f"Duplicate step id: {step['id']}")
                    step_ids.add(step["id"])
                
                if "name" not in step:
                    errors.append(f"Step {i} must have a name")
    
    return len(errors) == 0, errors

def estimate_workflow_time(steps: List[Dict]) -> int:
    """Estimate total workflow execution time"""
    total_time = 0
    for step in steps:
        if step.get("enabled", True):
            total_time += step.get("estimated_time", 300)
    return total_time

def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def find_projects() -> List[str]:
    """Find available projects in input directory"""
    projects = []
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        return projects
    
    try:
        for root, dirs, files in os.walk(input_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Look for directories with relevant files
            if any(f.endswith(('.txt', '.md', '.pptx')) for f in files):
                relative_path = os.path.relpath(root, input_dir)
                if relative_path != '.':
                    projects.append(relative_path)
    except Exception as e:
        st.error(f"Failed to scan projects: {e}")
    
    return sorted(projects)

# ============================================================================
# AUTOMATED EXECUTION FUNCTIONS - COPIED FROM ORIGINAL PAGES (NO SHARED CODE)
# ============================================================================

def execute_workflow_step(step_id: str, project_path: str, step_options: Dict = None) -> Tuple[bool, str, Dict]:
    """Execute a single workflow step programmatically"""
    try:
        if step_options is None:
            step_options = {}
            
        if step_id == "01_adjust":
            # Execute step 01: Adjust AAA EEE with real processing
            create_artifact_c = step_options.get('create_artifact_c', True)
            return execute_step_01_adjust_aaa_eee(project_path, create_artifact_c)
        
        elif step_id == "02_rename":
            # Execute step 02: Rename files with real processing
            return execute_step_02_rename(project_path)
        
        elif step_id == "03_save_text":
            # Execute step 03: Save text sections with real processing
            return execute_step_03_save_text(project_path)
        
        else:
            return False, f"Unknown step: {step_id}", {}
            
    except Exception as e:
        return False, f"Error executing step {step_id}: {str(e)}", {}

# ============================================================================
# STEP 01: AAA/EEE ADJUSTMENT FUNCTIONS (copied from 01_Adjust_AAA_EEE.py)
# ============================================================================

def extract_lecture_number(filename: str) -> Optional[str]:
    """Extract lecture number from filename (e.g., '01-AAA.md' -> '01')"""
    match = re.match(r'^(\d+)-(?:AAA|EEE)\.(md|txt)$', filename)
    return match.group(1) if match else None

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    match = re.match(r'^(\d+)-(?:AAA|EEE)\.(md|txt)$', filename)
    return match.group(2) if match else 'md'

def find_aaa_eee_files(directory: str) -> Tuple[List[str], List[str]]:
    """Find all AAA and EEE files in the directory structure"""
    aaa_files = []
    eee_files = []
    
    for root, _, files in os.walk(directory):
        # Skip processed directory
        if "processed_aaa_eee" in root:
            continue
            
        for file in files:
            if re.match(r'^\d+-AAA\.(md|txt)$', file):
                aaa_files.append(os.path.join(root, file))
            elif re.match(r'^\d+-EEE\.(md|txt)$', file):
                eee_files.append(os.path.join(root, file))
    
    return sorted(aaa_files), sorted(eee_files)

def validate_end_markers(file_path: str, file_type: str) -> Tuple[bool, str]:
    """Validate that the file has the correct end marker or add one if missing"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract lecture number from filename
        filename = os.path.basename(file_path)
        lecture_num = extract_lecture_number(filename)
        
        if not lecture_num:
            return False, "Could not extract lecture number from filename"
        
        # Check for multiple possible end marker patterns
        possible_markers = [
            f"===END OF LECTURE {lecture_num}-{file_type} GENERATION===",
            f"===END OF LECTURE [{lecture_num}]-{file_type} GENERATION===",
            f"===END OF LECTURE {lecture_num} {file_type} GENERATION===",
            f"===END OF LECTURE [{lecture_num}] {file_type} GENERATION==="
        ]
        
        # Check if any valid end marker exists
        for marker in possible_markers:
            if marker in content:
                return True, f"Valid end marker found: {marker}"
        
        # If no end marker found, add one automatically
        if file_type == "AAA":
            if "[SUMMARY TRANSCRIPT]" in content or "Slide" in content:
                standard_marker = f"===END OF LECTURE {lecture_num}-{file_type} GENERATION==="
                updated_content = content.rstrip() + "\n\n" + standard_marker
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                return True, f"Added missing end marker: {standard_marker}"
        
        elif file_type == "EEE":
            if "[GLOSSARY]" in content or "[COMPREHENSIVE NOTES]" in content:
                standard_marker = f"===END OF LECTURE {lecture_num}-{file_type} GENERATION==="
                updated_content = content.rstrip() + "\n\n" + standard_marker
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                return True, f"Added missing end marker: {standard_marker}"
        
        return True, "No end marker found, but allowing processing to continue"
            
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def extract_content_sections(content: str, section_markers: List[str]) -> Dict[str, str]:
    """Extract content between section markers"""
    sections = {}
    
    for i, marker in enumerate(section_markers):
        # Find the start of this section
        start_pattern = f"\\[{re.escape(marker)}\\]"
        start_match = re.search(start_pattern, content)
        
        if not start_match:
            sections[marker] = ""
            continue
        
        start_pos = start_match.end()
        
        # Find the start of the next section or end marker
        if i + 1 < len(section_markers):
            next_pattern = f"\\[{re.escape(section_markers[i + 1])}\\]"
            next_match = re.search(next_pattern, content[start_pos:])
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                # Look for end marker
                end_match = re.search(r"===END OF LECTURE.*?===", content[start_pos:])
                end_pos = start_pos + end_match.start() if end_match else len(content)
        else:
            # This is the last section, find end marker
            end_match = re.search(r"===END OF LECTURE.*?===", content[start_pos:])
            end_pos = start_pos + end_match.start() if end_match else len(content)
        
        # Extract and clean the content
        section_content = content[start_pos:end_pos].strip()
        sections[marker] = section_content
    
    return sections

def split_aaa_file(file_path: str) -> Dict[str, str]:
    """Split AAA file into component sections"""
    aaa_markers = [
        "VIDEO TRANSCRIPT OUTLINE",
        "VIDEO TRANSCRIPT",
        "SLIDE CONTENT",
        "SUMMARY TRANSCRIPT"
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = extract_content_sections(content, aaa_markers)
        
        # Map to output files - always return something, even if empty
        result = {
            'a': sections.get("VIDEO TRANSCRIPT OUTLINE", ""),
            'b': sections.get("VIDEO TRANSCRIPT", ""),
            'c': sections.get("SLIDE CONTENT", ""),
            'd': sections.get("SUMMARY TRANSCRIPT", "")
        }
        
        return result
        
    except Exception as e:
        # Return empty sections instead of empty dict to ensure processing continues
        return {'a': '', 'b': '', 'c': '', 'd': ''}

def split_eee_file(file_path: str) -> Dict[str, str]:
    """Split EEE file into component sections"""
    eee_markers = [
        "COMPREHENSIVE NOTES",
        "LINKEDIN POST",
        "SOCRATIC DIALOGUE",
        "TWEET",
        "FLASHCARDS",
        "GLOSSARY"
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = extract_content_sections(content, eee_markers)
        
        # Map to output files - always return something, even if empty
        result = {
            'e': sections.get("COMPREHENSIVE NOTES", ""),
            'f': sections.get("LINKEDIN POST", ""),
            'g': sections.get("SOCRATIC DIALOGUE", ""),
            'h': sections.get("TWEET", ""),
            'i': sections.get("FLASHCARDS", ""),
            'j': sections.get("GLOSSARY", "")
        }
        
        return result
        
    except Exception as e:
        # Return empty sections instead of empty dict to ensure processing continues
        return {'e': '', 'f': '', 'g': '', 'h': '', 'i': '', 'j': ''}

def save_split_files(base_file_path: str, sections: Dict[str, str], lecture_num: str) -> List[Dict]:
    """Save the split sections to individual files"""
    results = []
    base_dir = os.path.dirname(base_file_path)
    
    # Get the original file extension
    original_filename = os.path.basename(base_file_path)
    file_extension = get_file_extension(original_filename)
    
    for suffix, content in sections.items():
        output_filename = f"{lecture_num}-{suffix}.{file_extension}"
        output_path = os.path.join(base_dir, output_filename)
        
        # Create files even with minimal content to ensure splitting works
        if content and len(content.strip()) > 0:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                results.append({
                    'status': 'success',
                    'file': output_filename,
                    'path': output_path,
                    'size': len(content)
                })
                
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file': output_filename,
                    'error': str(e)
                })
        else:
            # Still log that we attempted to process this section
            results.append({
                'status': 'skipped',
                'file': output_filename,
                'reason': f'No content found for section [{suffix.upper()}]'
            })
    
    return results

def move_file_to_processed(file_path: str) -> bool:
    """Move a file to the processed directory within its respective course folder"""
    try:
        current_dir = os.path.dirname(file_path)
        processed_lecture_dir = os.path.join(current_dir, "processed_aaa_eee")
        
        ensure_directory_exists(processed_lecture_dir)
        
        dest_path = os.path.join(processed_lecture_dir, os.path.basename(file_path))
        
        shutil.move(file_path, dest_path)
        return True
        
    except Exception as e:
        return False

def execute_step_01_adjust_aaa_eee(project_path: str, create_artifact_c: bool = True) -> Tuple[bool, str, Dict]:
    """Execute step 01: Adjust AAA EEE - automated headless version"""
    try:
        # Find AAA and EEE files
        aaa_files, eee_files = find_aaa_eee_files(project_path)
        
        if len(aaa_files) == 0 and len(eee_files) == 0:
            return False, "No AAA or EEE files found in project directory", {}
        
        results = {
            'aaa_results': [],
            'eee_results': [],
            'validation_errors': [],
            'total_processed': 0,
            'total_created': 0,
            'moved_files': [],
            'move_errors': []
        }
        
        # Process AAA files
        for file_path in aaa_files:
            filename = os.path.basename(file_path)
            lecture_num = extract_lecture_number(filename)
            
            if not lecture_num:
                results['validation_errors'].append(f"Could not extract lecture number from {filename}")
                continue
            
            # Validate end marker
            is_valid, validation_msg = validate_end_markers(file_path, "AAA")
            if not is_valid:
                results['validation_errors'].append(f"{filename}: {validation_msg}")
            
            # Split the file
            sections = split_aaa_file(file_path)
            split_results = save_split_files(file_path, sections, lecture_num)
            results['aaa_results'].append({
                'source_file': filename,
                'lecture_num': lecture_num,
                'splits': split_results,
                'original_path': file_path
            })
            results['total_processed'] += 1
            results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
            
            # Move original file to processed directory if splitting was successful
            if any(r['status'] == 'success' for r in split_results):
                if move_file_to_processed(file_path):
                    results['moved_files'].append(filename)
                else:
                    results['move_errors'].append(f"Failed to move {filename}")
        
        # Process EEE files
        for file_path in eee_files:
            filename = os.path.basename(file_path)
            lecture_num = extract_lecture_number(filename)
            
            if not lecture_num:
                results['validation_errors'].append(f"Could not extract lecture number from {filename}")
                continue
            
            # Validate end marker
            is_valid, validation_msg = validate_end_markers(file_path, "EEE")
            if not is_valid:
                results['validation_errors'].append(f"{filename}: {validation_msg}")
            
            # Split the file
            sections = split_eee_file(file_path)
            split_results = save_split_files(file_path, sections, lecture_num)
            results['eee_results'].append({
                'source_file': filename,
                'lecture_num': lecture_num,
                'splits': split_results,
                'original_path': file_path
            })
            results['total_processed'] += 1
            results['total_created'] += len([r for r in split_results if r['status'] == 'success'])
            
            # Move original file to processed directory if splitting was successful
            if any(r['status'] == 'success' for r in split_results):
                if move_file_to_processed(file_path):
                    results['moved_files'].append(filename)
                else:
                    results['move_errors'].append(f"Failed to move {filename}")
        
        # Format success message
        total_processed = results['total_processed']
        total_created = results['total_created']
        moved_files = len(results['moved_files'])
        
        message = f"Processed {total_processed} files, created {total_created} split files, moved {moved_files} originals to processed folder"
        
        return True, message, results
        
    except Exception as e:
        return False, f"Error in step 01: {str(e)}", {}

# ============================================================================
# STEP 02: RENAME FUNCTIONS (copied from 02_Rename.py)
# ============================================================================

def find_files_by_pattern(directory: str, pattern: str) -> List[str]:
    """Find all files matching a pattern in a directory (recursively)"""
    result = []
    for root, _, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            result.append(os.path.join(root, filename))
    return result

def find_transcript_files(directory: str) -> List[str]:
    """Find all transcript files in a directory"""
    transcripts = []
    transcript_patterns = [
        "Lecture*.txt", "Lecture*.md",
        "*lecture*.txt", "*lecture*.md",
        "*transcript*.txt", "*transcript*.md",
        "*artifact_b*.txt", "*artifact_b*.md",
        "*artifact-b*.txt", "*artifact-b*.md",
        "*.txt", "*.md"
    ]
    
    for pattern in transcript_patterns:
        transcripts.extend(find_files_by_pattern(directory, pattern))
    
    # Filter out slide and summary files
    transcripts = [f for f in transcripts if "slide" not in os.path.basename(f).lower()]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-s\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'summary', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-d\.(md|txt)$', os.path.basename(f).lower())]
    
    return list(set(transcripts))

def standardize_lecture_number(lecture: str) -> str:
    """Standardize lecture number to two-digit format"""
    if lecture and lecture.isdigit():
        return f"{int(lecture):02d}"
    return lecture or "00"

def analyze_filename_for_renaming(filename: str) -> Dict:
    """Analyze a filename and suggest corrected naming or deletion"""
    base_name, ext = os.path.splitext(filename)
    
    result = {
        "original": filename,
        "corrected": filename,
        "needs_renaming": False,
        "should_delete": False,
        "type": "unknown",
        "reason": ""
    }
    
    # Check for files that should be deleted first
    if re.search(r'.*outline.*', base_name.lower()):
        result["should_delete"] = True
        result["reason"] = "Outline files not supported"
        result["type"] = "delete"
        return result
    
    # Check for transcript patterns
    transcript_patterns = [
        r'^(.*)lecture(\d+)[-_]*transcript(.*)$',
        r'^lecture[_\s]*(\d+)$',
        r'^lecture[_\s]*(\d+)[_\s]*transcript$',
        r'^(\d+)[-_]*transcript$',
        r'^(\d+)[-_]*b$',
    ]
    
    for pattern in transcript_patterns:
        match = re.search(pattern, base_name.lower())
        if match:
            lecture_num = None
            for group in match.groups():
                if group and group.isdigit():
                    lecture_num = group
                    break
            
            if lecture_num:
                std_lecture = standardize_lecture_number(lecture_num)
                expected_name = f"Lecture {std_lecture}{ext}"
                if filename != expected_name:
                    result["corrected"] = expected_name
                    result["needs_renaming"] = True
                result["type"] = "transcript"
                return result
    
    return result

def execute_step_02_rename(project_path: str) -> Tuple[bool, str, Dict]:
    """Execute step 02: Rename - automated headless version"""
    try:
        # Find transcript files
        transcript_files = find_transcript_files(project_path)
        
        if not transcript_files:
            return True, "No files found that need renaming", {"renamed": 0, "deleted": 0, "errors": 0}
        
        results = {"renamed": 0, "deleted": 0, "errors": 0, "details": []}
        
        for file_path in transcript_files:
            filename = os.path.basename(file_path)
            rename_info = analyze_filename_for_renaming(filename)
            
            try:
                if rename_info.get("should_delete", False):
                    os.remove(file_path)
                    results["deleted"] += 1
                    results["details"].append(f"Deleted: {filename} - {rename_info['reason']}")
                
                elif rename_info.get("needs_renaming", False):
                    original_dir = os.path.dirname(file_path)
                    new_path = os.path.join(original_dir, rename_info["corrected"])
                    
                    if not os.path.exists(new_path):
                        os.rename(file_path, new_path)
                        results["renamed"] += 1
                        results["details"].append(f"Renamed: {filename} -> {rename_info['corrected']}")
                    
            except Exception as e:
                results["errors"] += 1
                results["details"].append(f"Error processing {filename}: {str(e)}")
        
        message = f"Renamed {results['renamed']} files, deleted {results['deleted']} files, {results['errors']} errors"
        return True, message, results
        
    except Exception as e:
        return False, f"Error in step 02: {str(e)}", {}

# ============================================================================
# STEP 03: SAVE TEXT FUNCTIONS (copied from 03_Save_Text.py)
# ============================================================================

def extract_slide_blocks_from_content(content: str) -> List[str]:
    """Extract slide blocks from content using multiple regex patterns"""
    slide_blocks = []
    
    # Pattern 1: Slide X: Title format
    pattern1 = r'Slide\s+(\d+):\s*([^\n]+(?:\n(?!Slide\s+\d+:)[^\n]*)*)'
    matches1 = re.findall(pattern1, content, re.MULTILINE | re.IGNORECASE)
    
    for slide_num, slide_content in matches1:
        clean_content = slide_content.strip()
        if clean_content and len(clean_content) > 10:
            slide_blocks.append(clean_content)
    
    # Pattern 2: **Slide X** format
    pattern2 = r'\*\*Slide\s+(\d+)\*\*\s*([^\n]+(?:\n(?!\*\*Slide\s+\d+\*\*)[^\n]*)*)'
    matches2 = re.findall(pattern2, content, re.MULTILINE | re.IGNORECASE)
    
    for slide_num, slide_content in matches2:
        clean_content = slide_content.strip()
        if clean_content and len(clean_content) > 10:
            slide_blocks.append(clean_content)
    
    return slide_blocks

def create_lecture_directories(base_dir: str, lecture_num: str) -> Tuple[str, str]:
    """Create lecture directory structure"""
    lecture_dir = os.path.join(base_dir, f"Lecture {lecture_num}")
    text_dir = os.path.join(lecture_dir, "English text")
    summary_dir = os.path.join(lecture_dir, "English Summary text")
    
    ensure_directory_exists(text_dir)
    ensure_directory_exists(summary_dir)
    
    return text_dir, summary_dir

def save_text_sections(content: str, output_dir: str, base_filename: str) -> List[Dict]:
    """Save text content broken into sections"""
    results = []
    
    # Extract slide blocks
    slide_blocks = extract_slide_blocks_from_content(content)
    
    if not slide_blocks:
        # If no slide blocks found, split content into chunks
        words = content.split()
        chunk_size = 200  # words per chunk
        slide_blocks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                slide_blocks.append(chunk)
    
    # Save each block as a separate file
    for i, block in enumerate(slide_blocks, 1):
        if block.strip():
            filename = f"{base_filename}_{i:02d}.txt"
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(block.strip())
                
                results.append({
                    'status': 'success',
                    'file': filename,
                    'path': filepath,
                    'size': len(block)
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file': filename,
                    'error': str(e)
                })
    
    return results

def execute_step_03_save_text(project_path: str) -> Tuple[bool, str, Dict]:
    """Execute step 03: Save Text - automated headless version"""
    try:
        # Find transcript and summary files
        transcript_files = []
        summary_files = []
        
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.startswith("Lecture") and file.endswith((".txt", ".md")):
                    file_path = os.path.join(root, file)
                    if "summary" in file.lower():
                        summary_files.append(file_path)
                    else:
                        transcript_files.append(file_path)
        
        if not transcript_files and not summary_files:
            return True, "No transcript or summary files found to process", {"transcript_sections": 0, "summary_sections": 0}
        
        results = {"transcript_sections": 0, "summary_sections": 0, "details": []}
        
        # Process transcript files
        for file_path in transcript_files:
            filename = os.path.basename(file_path)
            
            # Extract lecture number
            match = re.search(r'(\d+)', filename)
            if not match:
                continue
                
            lecture_num = match.group(1).zfill(2)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create directories
                text_dir, _ = create_lecture_directories(project_path, lecture_num)
                
                # Save text sections
                section_results = save_text_sections(content, text_dir, f"Lecture_{lecture_num}")
                successful_sections = len([r for r in section_results if r['status'] == 'success'])
                results["transcript_sections"] += successful_sections
                results["details"].append(f"Processed {filename}: {successful_sections} sections")
                
            except Exception as e:
                results["details"].append(f"Error processing {filename}: {str(e)}")
        
        # Process summary files
        for file_path in summary_files:
            filename = os.path.basename(file_path)
            
            # Extract lecture number
            match = re.search(r'(\d+)', filename)
            if not match:
                continue
                
            lecture_num = match.group(1).zfill(2)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create directories
                _, summary_dir = create_lecture_directories(project_path, lecture_num)
                
                # Save summary sections
                section_results = save_text_sections(content, summary_dir, f"Summary_{lecture_num}")
                successful_sections = len([r for r in section_results if r['status'] == 'success'])
                results["summary_sections"] += successful_sections
                results["details"].append(f"Processed {filename}: {successful_sections} sections")
                
            except Exception as e:
                results["details"].append(f"Error processing {filename}: {str(e)}")
        
        message = f"Created {results['transcript_sections']} transcript sections and {results['summary_sections']} summary sections"
        return True, message, results
        
    except Exception as e:
        return False, f"Error in step 03: {str(e)}", {}

def execute_automated_workflow(workflow_steps: List[Dict], project_path: str, progress_callback=None) -> Dict:
    """Execute an entire workflow automatically"""
    results = {
        "started_at": datetime.now().isoformat(),
        "workflow_id": f"workflow_{int(time.time())}",
        "total_steps": len([s for s in workflow_steps if s.get('enabled', True)]),
        "completed_steps": 0,
        "failed_steps": 0,
        "step_results": [],
        "overall_success": True,
        "completed_at": None,
        "total_duration": 0
    }
    
    enabled_steps = [s for s in workflow_steps if s.get('enabled', True)]
    
    for i, step in enumerate(enabled_steps):
        step_id = step.get('id', f'step_{i}')
        step_name = step.get('name', f'Step {i+1}')
        
        if progress_callback:
            progress_callback(i / len(enabled_steps), f"Executing {step_name}...")
        
        # Execute the step
        success, message, step_data = execute_workflow_step(step_id, project_path, step.get('options', {}))
        
        step_result = {
            "step_id": step_id,
            "step_name": step_name,
            "success": success,
            "message": message,
            "data": step_data,
            "timestamp": datetime.now().isoformat()
        }
        
        results["step_results"].append(step_result)
        
        if success:
            results["completed_steps"] += 1
        else:
            results["failed_steps"] += 1
            results["overall_success"] = False
            # Continue with other steps even if one fails
        
        # Create checkpoint after each step
        create_checkpoint(results["workflow_id"], step_id, step_result)
        
        # Small delay to make progress visible
        time.sleep(0.5)
    
    if progress_callback:
        progress_callback(1.0, "Workflow completed")
    
    results["completed_at"] = datetime.now().isoformat()
    started = datetime.fromisoformat(results["started_at"])
    completed = datetime.fromisoformat(results["completed_at"])
    results["total_duration"] = int((completed - started).total_seconds())
    
    # Save final workflow state
    save_workflow_state(results["workflow_id"], results)
    
    return results

# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_workflow_template_manager():
    """Render the workflow template management interface"""
    st.subheader("📋 Workflow Templates")
    
    # Template creation/editing
    col1, col2 = st.columns([2, 1])
    
    with col1:
        template_name = st.text_input("Template Name", placeholder="e.g., 'Quick Processing', 'Full Pipeline'")
    
    with col2:
        available_templates = get_available_templates()
        if available_templates:
            selected_template = st.selectbox("Load Existing Template", [""] + available_templates)
            if selected_template and st.button("Load Template"):
                template_data = load_workflow_template(selected_template)
                if template_data:
                    st.session_state.loaded_template = template_data
                    st.success(f"Loaded template: {selected_template}")
    
    # Default workflow steps
    default_steps = get_default_workflow_steps()
    
    # Load template data if available
    if hasattr(st.session_state, 'loaded_template') and st.session_state.loaded_template:
        template_steps = st.session_state.loaded_template.get('steps', default_steps)
    else:
        template_steps = default_steps
    
    st.subheader("Configure Workflow Steps")
    
    # Step configuration
    configured_steps = []
    for i, step in enumerate(template_steps):
        with st.expander(f"Step {i+1}: {step.get('name', 'Unnamed Step')}", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                step_name = st.text_input(f"Step Name", value=step.get('name', ''), key=f"step_name_{i}")
                step_desc = st.text_area(f"Description", value=step.get('description', ''), key=f"step_desc_{i}")
            
            with col2:
                step_enabled = st.checkbox("Enabled", value=step.get('enabled', True), key=f"step_enabled_{i}")
                step_required = st.checkbox("Required", value=step.get('required', False), key=f"step_required_{i}")
            
            with col3:
                estimated_time = st.number_input(
                    "Est. Time (sec)", 
                    min_value=0, 
                    value=step.get('estimated_time', 300), 
                    key=f"step_time_{i}"
                )
            
            # Step-specific options
            step_options = {}
            if step.get('id') == '01_adjust':
                step_options['create_artifact_c'] = st.checkbox(
                    "Create artifact-c folder", 
                    value=True, 
                    key=f"artifact_c_{i}"
                )
            
            configured_step = {
                "id": step.get('id', f'step_{i}'),
                "name": step_name,
                "description": step_desc,
                "enabled": step_enabled,
                "required": step_required,
                "estimated_time": estimated_time,
                "options": step_options
            }
            configured_steps.append(configured_step)
    
    # Template actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Template", disabled=not template_name):
            if template_name:
                template_data = {
                    "name": template_name,
                    "description": f"Custom workflow template with {len(configured_steps)} steps",
                    "steps": configured_steps
                }
                
                is_valid, errors = validate_workflow_template(template_data)
                if is_valid:
                    if save_workflow_template(template_name, template_data):
                        st.success(f"Template '{template_name}' saved successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save template")
                else:
                    st.error("Template validation failed:")
                    for error in errors:
                        st.error(f"• {error}")
    
    with col2:
        if st.button("🔄 Reset to Default"):
            if hasattr(st.session_state, 'loaded_template'):
                delattr(st.session_state, 'loaded_template')
            st.rerun()
    
    with col3:
        estimated_time = estimate_workflow_time(configured_steps)
        st.metric("Estimated Time", format_duration(estimated_time))
    
    return configured_steps

def render_workflow_execution():
    """Render the workflow execution interface"""
    st.subheader("🚀 Execute Workflow")
    
    # Project selection
    projects = find_projects()
    if not projects:
        st.warning("No projects found in the input directory. Please add some project folders with content files.")
        return None
    
    selected_project = st.selectbox("Select Project", projects)
    
    if not selected_project:
        return None
    
    project_path = os.path.join(get_input_directory(), selected_project)
    
    # Display project info
    st.info(f"**Project Path:** `{project_path}`")
    
    # Get workflow steps (from template manager or default)
    if 'configured_workflow_steps' in st.session_state:
        workflow_steps = st.session_state.configured_workflow_steps
    else:
        workflow_steps = get_default_workflow_steps()
    
    # Display workflow summary
    enabled_steps = [s for s in workflow_steps if s.get('enabled', True)]
    st.write(f"**Workflow Summary:** {len(enabled_steps)} enabled steps")
    
    for step in enabled_steps:
        st.write(f"• {step.get('name', 'Unnamed Step')} ({format_duration(step.get('estimated_time', 300))})")
    
    st.write(f"**Total Estimated Time:** {format_duration(estimate_workflow_time(enabled_steps))}")
    
    # Execution controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ Start Automated Workflow", type="primary"):
            # Execute workflow
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(progress: float, message: str):
                progress_bar.progress(progress)
                status_text.text(message)
            
            with st.spinner("Executing workflow..."):
                results = execute_automated_workflow(workflow_steps, project_path, progress_callback)
            
            # Display results
            if results["overall_success"]:
                st.success(f"✅ Workflow completed successfully! ({format_duration(results['total_duration'])})")
            else:
                st.error(f"❌ Workflow completed with errors ({format_duration(results['total_duration'])})")
            
            # Detailed results
            with st.expander("Detailed Results", expanded=results["failed_steps"] > 0):
                st.json(results)
            
            # Store results in session state for potential review
            st.session_state.last_workflow_results = results
    
    with col2:
        if st.button("📊 View Previous Results"):
            if hasattr(st.session_state, 'last_workflow_results'):
                st.json(st.session_state.last_workflow_results)
            else:
                st.info("No previous workflow results available")
    
    return workflow_steps

def render_workflow_history():
    """Render workflow execution history"""
    st.subheader("📈 Workflow History")
    
    # Get workflow state files
    state_dir = get_workflow_state_dir()
    if not os.path.exists(state_dir):
        st.info("No workflow history available")
        return
    
    workflow_files = [f for f in os.listdir(state_dir) if f.endswith('.json')]
    
    if not workflow_files:
        st.info("No workflow history available")
        return
    
    # Display workflow history
    for workflow_file in sorted(workflow_files, reverse=True)[:10]:  # Show last 10
        try:
            with open(os.path.join(state_dir, workflow_file), 'r') as f:
                workflow_data = json.load(f)
            
            with st.expander(f"Workflow {workflow_data.get('workflow_id', 'Unknown')} - {workflow_data.get('started_at', 'Unknown time')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Steps", workflow_data.get('total_steps', 0))
                with col2:
                    st.metric("Completed", workflow_data.get('completed_steps', 0))
                with col3:
                    st.metric("Failed", workflow_data.get('failed_steps', 0))
                
                if workflow_data.get('step_results'):
                    st.subheader("Step Results")
                    for step_result in workflow_data['step_results']:
                        status_icon = "✅" if step_result['success'] else "❌"
                        st.write(f"{status_icon} **{step_result['step_name']}**: {step_result['message']}")
        
        except Exception as e:
            st.error(f"Error loading workflow file {workflow_file}: {e}")

# ============================================================================
# MAIN STREAMLIT APP
# ============================================================================

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Workflow Manager",
        page_icon="⚙️",
        layout="wide"
    )
    
    st.title("⚙️ Advanced Workflow Manager")
    st.markdown("*Automate your video processing workflow with configurable templates and batch execution*")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        selected_tab = st.radio(
            "Select Section",
            ["🔧 Template Manager", "🚀 Execute Workflow", "📈 History"],
            index=0
        )
        
        st.header("Quick Stats")
        templates_count = len(get_available_templates())
        projects_count = len(find_projects())
        st.metric("Templates", templates_count)
        st.metric("Projects", projects_count)
    
    # Main content area
    if selected_tab == "🔧 Template Manager":
        configured_steps = render_workflow_template_manager()
        # Store configured steps for use in execution
        st.session_state.configured_workflow_steps = configured_steps
    
    elif selected_tab == "🚀 Execute Workflow":
        render_workflow_execution()
    
    elif selected_tab == "📈 History":
        render_workflow_history()
    
    # Footer
    st.markdown("---")
    st.markdown("*Workflow Manager v1.2.0 - Streamlining your video processing pipeline*")

if __name__ == "__main__":
    main()
