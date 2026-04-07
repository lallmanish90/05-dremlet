"""
CLI Command: Save Text (Page 03)

Converts the Streamlit page 03_Save_Text.py to CLI interface
while maintaining 100% functional parity.
"""

import click
import os
import sys
import re
import time
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from rich.console import Console
from rich.table import Table

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress, StatusManager
from cli.reports import generate_report
from cli.config import load_config

console = Console()

# ===== BUSINESS LOGIC EXTRACTED FROM STREAMLIT PAGE =====
# All functions below are extracted from pages/03_Save_Text.py

def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def extract_slide_blocks(text: str) -> List[Tuple[str, str, str]]:
    """Extract slide blocks from transcript text"""
    # Standard pattern for [Slide X - Start] ... [Slide X - End] format
    pattern = r'\[Slide\s+(\d+)\s*-\s*Start\](.*?)\[Slide\s+\1\s*-\s*End\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        result = []
        for match in matches:
            slide_number = match[0]
            content = match[1].strip()
            result.append((slide_number, content, ('[Slide {} - Start]', '[Slide {} - End]')))
        
        return sorted(result, key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    
    return []

def extract_video_transcript_section(text: str) -> str:
    """Extract the [VIDEO TRANSCRIPT] section from AAA file"""
    # Find the VIDEO TRANSCRIPT section
    start_pattern = r'\[VIDEO TRANSCRIPT\]'
    end_pattern = r'\[SLIDE CONTENT\]'
    
    start_match = re.search(start_pattern, text)
    if not start_match:
        return ""
    
    end_match = re.search(end_pattern, text)
    if not end_match:
        # If no SLIDE CONTENT section, look for SUMMARY TRANSCRIPT
        end_pattern = r'\[SUMMARY TRANSCRIPT\]'
        end_match = re.search(end_pattern, text)
        if not end_match:
            return ""
    
    start_pos = start_match.end()
    end_pos = end_match.start()
    
    return text[start_pos:end_pos].strip()

def extract_summary_transcript_section(text: str) -> str:
    """Extract the [SUMMARY TRANSCRIPT] section from AAA file"""
    # Find the SUMMARY TRANSCRIPT section
    start_pattern = r'\[SUMMARY TRANSCRIPT\]'
    end_pattern = r'===END OF LECTURE.*?GENERATION==='
    
    start_match = re.search(start_pattern, text)
    if not start_match:
        return ""
    
    end_match = re.search(end_pattern, text)
    if not end_match:
        # If no end marker, take everything after SUMMARY TRANSCRIPT
        return text[start_match.end():].strip()
    
    start_pos = start_match.end()
    end_pos = end_match.start()
    
    return text[start_pos:end_pos].strip()

def get_transcript_files(input_dir):
    """Get all files that contain transcript content"""
    result = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Only include markdown and text files
            if file_ext not in ['.md', '.txt']:
                continue
                
            # Skip files in all_transcripts or all_summary folders
            if 'all_transcripts' in file_path or 'all_summary' in file_path:
                continue
            
            # Skip files in "English text" or "English Summary text" folders
            if 'English text' in file_path or 'English Summary text' in file_path:
                continue
            
            # Include files that have "Lecture" in the filename OR end with "-AAA.md"
            is_lecture_file = 'lecture' in file_name.lower()
            is_aaa_file = file_name.lower().endswith('-aaa.md')
            
            if is_lecture_file or is_aaa_file:
                # Check if file is not inside a Lecture folder
                is_in_lecture_folder = any('lecture' in part.lower() for part in Path(root).parts)
                if not is_in_lecture_folder:
                    result.append(file_path)
    
    return result

def get_summary_files(input_dir):
    """Get all files that contain summary content"""
    result = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Only include markdown and text files
            if file_ext not in ['.md', '.txt']:
                continue
                
            # Skip files in all_transcripts or all_summary folders
            if 'all_transcripts' in file_path or 'all_summary' in file_path:
                continue
            
            # Skip files in "English text" or "English Summary text" folders
            if 'English text' in file_path or 'English Summary text' in file_path:
                continue
            
            # Include AAA files (which contain summary transcript) OR traditional summary files
            is_aaa_file = file_name.lower().endswith('-aaa.md')
            has_summary_markers = any(marker in file_name.lower() for marker in ['-summary', '-d.', '-artifact-d.'])
            is_eee_file = file_name.lower().endswith('-eee.md')
            
            if is_aaa_file or has_summary_markers or is_eee_file:
                # Check if file is not inside a Lecture folder
                is_in_lecture_folder = any('lecture' in part.lower() for part in Path(root).parts)
                if not is_in_lecture_folder:
                    result.append(file_path)
    
    return result

def process_transcript_file(file_path):
    """Process a single transcript file"""
    try:
        # Get file info
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # Extract lecture number from filename
        # Try "Lecture XX" pattern first
        match = re.search(r'lecture\s*(\d+)', file_name.lower())
        if match:
            lecture_num = match.group(1)
        else:
            # Try "XX-AAA.md" pattern
            match = re.search(r'(\d+)-aaa\.md', file_name.lower())
            lecture_num = match.group(1) if match else "Unknown"
        
        # Create lecture folder name
        lecture_folder_name = f"Lecture {lecture_num.zfill(2)}"
        
        # Create directories
        all_transcripts_folder = os.path.join(dir_path, 'all_transcripts')
        os.makedirs(all_transcripts_folder, exist_ok=True)
        
        lecture_folder = os.path.join(dir_path, lecture_folder_name)
        os.makedirs(lecture_folder, exist_ok=True)
        
        english_text_folder = os.path.join(lecture_folder, "English text")
        os.makedirs(english_text_folder, exist_ok=True)
        
        # Read the file and extract slide blocks
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if this is an AAA file (contains VIDEO TRANSCRIPT section)
        if '[VIDEO TRANSCRIPT]' in content:
            # Extract VIDEO TRANSCRIPT section and then extract slide blocks
            transcript_section = extract_video_transcript_section(content)
            slide_blocks = extract_slide_blocks(transcript_section)
        else:
            # Use original extraction for other file types
            slide_blocks = extract_slide_blocks(content)
        
        # Process each slide block
        for slide_number, slide_content, _ in slide_blocks:
            output_filename = f"{slide_number.zfill(2)}.txt"
            output_path = os.path.join(english_text_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(slide_content.strip())
        
        # Move the original file to all_transcripts folder
        new_transcript_path = os.path.join(all_transcripts_folder, file_name)
        if not os.path.exists(new_transcript_path):
            shutil.copy2(file_path, new_transcript_path)
            os.remove(file_path)
        
        return {
            "status": "success", 
            "file": file_name, 
            "slides": len(slide_blocks),
            "message": f"Processed {len(slide_blocks)} slides"
        }
    except Exception as e:
        # Just use basename of the file_path directly
        return {
            "status": "error", 
            "file": os.path.basename(file_path), 
            "slides": 0,
            "message": str(e)
        }

def process_summary_file(file_path):
    """Process a single summary file"""
    try:
        # Get file info
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # Extract lecture number from filename
        match = re.search(r'(\d+)', file_name)
        lecture_num = match.group(1) if match else "Unknown"
        
        # Create lecture folder name
        lecture_folder_name = f"Lecture {lecture_num.zfill(2)}"
        
        # Create directories
        all_summary_folder = os.path.join(dir_path, 'all_summary')
        os.makedirs(all_summary_folder, exist_ok=True)
        
        lecture_folder = os.path.join(dir_path, lecture_folder_name)
        os.makedirs(lecture_folder, exist_ok=True)
        
        english_summary_folder = os.path.join(lecture_folder, "English Summary text")
        os.makedirs(english_summary_folder, exist_ok=True)
        
        # Read the file and extract slide blocks
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if this is an AAA file (contains SUMMARY TRANSCRIPT section)
        if '[SUMMARY TRANSCRIPT]' in content:
            # Extract SUMMARY TRANSCRIPT section and then extract slide blocks
            summary_section = extract_summary_transcript_section(content)
            slide_blocks = extract_slide_blocks(summary_section)
        else:
            # Use original extraction for other file types
            slide_blocks = extract_slide_blocks(content)
        
        # Process each slide block
        for slide_number, slide_content, _ in slide_blocks:
            output_filename = f"{slide_number.zfill(2)}.txt"
            output_path = os.path.join(english_summary_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(slide_content.strip())
        
        # Move the original file to all_summary folder
        new_summary_path = os.path.join(all_summary_folder, file_name)
        if not os.path.exists(new_summary_path):
            shutil.copy2(file_path, new_summary_path)
            os.remove(file_path)
        
        return {
            "status": "success", 
            "file": file_name, 
            "slides": len(slide_blocks),
            "message": f"Processed {len(slide_blocks)} slides"
        }
    except Exception as e:
        # Make sure file_name is defined even in case of error
        try:
            # If file_name was already defined earlier in the function
            file_name
        except NameError:
            # If not, define it now
            file_name = os.path.basename(file_path)
            
        return {
            "status": "error", 
            "file": file_name, 
            "slides": 0,
            "message": str(e)
        }

# ===== CLI IMPLEMENTATION =====

def run_save_text(ctx_obj: Dict[str, Any], force: bool = False, process_summaries: bool = True) -> Dict[str, Any]:
    """
    Main function to run the save text operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Create status manager
    status_manager = StatusManager(verbose=ctx_obj.get('verbose', False))
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"transcript_files": 0, "summary_files": 0, "total_slides": 0, "error_count": 1}
        }
    
    status_manager.info(f"Scanning input directory: {input_dir}")
    
    # Find transcript and summary files
    transcript_files = get_transcript_files(input_dir)
    summary_files = get_summary_files(input_dir) if process_summaries else []
    
    if not transcript_files and not summary_files:
        warning_msg = "No transcript or summary files found for processing"
        status_manager.warning(warning_msg)
        return {
            "status": "warning",
            "message": warning_msg,
            "statistics": {"transcript_files": 0, "summary_files": 0, "total_slides": 0, "error_count": 0}
        }
    
    status_manager.info(f"Found {len(transcript_files)} transcript files and {len(summary_files)} summary files")
    
    # Show file analysis if verbose
    if ctx_obj.get('verbose', False):
        show_file_analysis(transcript_files, summary_files, status_manager)
    
    results = {
        "transcript_results": [],
        "summary_results": [],
        "statistics": {
            "transcript_files": len(transcript_files),
            "summary_files": len(summary_files),
            "total_slides": 0,
            "error_count": 0
        }
    }
    
    # Process transcript files
    if transcript_files:
        status_manager.info(f"Processing {len(transcript_files)} transcript files...")
        
        with DreamletProgress(description="Processing transcript files", total=len(transcript_files)) as progress:
            for i, file_path in enumerate(transcript_files):
                file_name = os.path.basename(file_path)
                progress.update(completed=i, description=f"Processing {file_name}")
                
                result = process_transcript_file(file_path)
                results["transcript_results"].append(result)
                
                if result["status"] == "success":
                    results["statistics"]["total_slides"] += result["slides"]
                    status_manager.info(f"✓ {file_name}: {result['slides']} slides", verbose_only=True)
                else:
                    results["statistics"]["error_count"] += 1
                    status_manager.error(f"✗ {file_name}: {result['message']}")
            
            progress.update(completed=len(transcript_files))
    
    # Process summary files
    if summary_files:
        status_manager.info(f"Processing {len(summary_files)} summary files...")
        
        with DreamletProgress(description="Processing summary files", total=len(summary_files)) as progress:
            for i, file_path in enumerate(summary_files):
                file_name = os.path.basename(file_path)
                progress.update(completed=i, description=f"Processing {file_name}")
                
                result = process_summary_file(file_path)
                results["summary_results"].append(result)
                
                if result["status"] == "success":
                    results["statistics"]["total_slides"] += result["slides"]
                    status_manager.info(f"✓ {file_name}: {result['slides']} slides", verbose_only=True)
                else:
                    results["statistics"]["error_count"] += 1
                    status_manager.error(f"✗ {file_name}: {result['message']}")
            
            progress.update(completed=len(summary_files))
    
    # Calculate final statistics
    success_count = sum(1 for r in results["transcript_results"] + results["summary_results"] if r["status"] == "success")
    
    # Determine final status
    if results["statistics"]["error_count"] > 0:
        final_status = "error"
        status_message = f"Completed with {results['statistics']['error_count']} errors"
    elif success_count == 0:
        final_status = "warning"
        status_message = "No files were processed successfully"
    else:
        final_status = "success"
        status_message = f"Successfully processed {success_count} files, created {results['statistics']['total_slides']} slide sections"
    
    # Show summary
    status_manager.success(status_message) if final_status == "success" else \
    status_manager.warning(status_message) if final_status == "warning" else \
    status_manager.error(status_message)
    
    # Show processing summary
    if not ctx_obj.get('quiet', False):
        show_processing_summary(results, status_manager)
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "transcript_files_found": len(transcript_files),
            "summary_files_found": len(summary_files)
        },
        "processing_results": results["transcript_results"] + results["summary_results"],
        "statistics": results["statistics"],
        "errors": [r["message"] for r in results["transcript_results"] + results["summary_results"] if r["status"] == "error"],
        "warnings": [],
        "output_files": []
    }
    
    # Generate report
    report_path = generate_report("03", "Save Text", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

def show_file_analysis(transcript_files: List[str], summary_files: List[str], status_manager: StatusManager):
    """Show file analysis in terminal format"""
    
    if transcript_files:
        console.print("\n[bold cyan]Transcript Files to Process:[/bold cyan]")
        
        transcript_table = Table()
        transcript_table.add_column("Course", style="cyan")
        transcript_table.add_column("Filename", style="white")
        
        for file_path in transcript_files:
            course_dir = os.path.basename(os.path.dirname(file_path))
            file_name = os.path.basename(file_path)
            transcript_table.add_row(course_dir, file_name)
        
        console.print(transcript_table)
    
    if summary_files:
        console.print("\n[bold yellow]Summary Files to Process:[/bold yellow]")
        
        summary_table = Table()
        summary_table.add_column("Course", style="cyan")
        summary_table.add_column("Filename", style="white")
        
        for file_path in summary_files:
            course_dir = os.path.basename(os.path.dirname(file_path))
            file_name = os.path.basename(file_path)
            summary_table.add_row(course_dir, file_name)
        
        console.print(summary_table)

def show_processing_summary(results: Dict, status_manager: StatusManager):
    """Show processing summary in terminal format"""
    
    # Create summary table
    summary_table = Table(title="Processing Summary")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Count", style="yellow")
    
    summary_table.add_row("Transcript Files Processed", str(len(results["transcript_results"])))
    summary_table.add_row("Summary Files Processed", str(len(results["summary_results"])))
    summary_table.add_row("Total Slide Sections Created", str(results["statistics"]["total_slides"]))
    summary_table.add_row("Errors", str(results["statistics"]["error_count"]))
    
    console.print(summary_table)
    
    # Show detailed results if there were errors
    error_results = [r for r in results["transcript_results"] + results["summary_results"] if r["status"] == "error"]
    if error_results:
        console.print("\n[bold red]Processing Errors:[/bold red]")
        
        error_table = Table()
        error_table.add_column("File", style="white")
        error_table.add_column("Error Message", style="red")
        
        for result in error_results:
            error_table.add_row(result["file"], result["message"])
        
        console.print(error_table)

@click.command()
@click.pass_context
def save_text(ctx):
    """
    Break transcript and summary files into sections for TTS processing
    
    This command processes transcript and summary files by extracting slide blocks
    and creating individual text files for each slide section.
    
    All settings are configured in config.json under "page_03_save_text":
    - section_markers: Markers to identify slide sections
    - min_section_length: Minimum length for valid sections
    - preserve_formatting: Whether to preserve original formatting
    - skip_summaries: Whether to skip processing summary files
    
    Examples:
        dreamlet run 03                    # Process with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_03_save_text')
    
    # Extract settings from config
    skip_summaries = page_config.get('skip_summaries', False)
    force = not config.skip_existing  # Inverse of skip_existing
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be processed[/yellow]")
        console.print(f"Would process with settings: skip_summaries={skip_summaries}, force={force}")
        return
    
    # Run the save text operation
    try:
        results = run_save_text(ctx.obj, force, not skip_summaries)
        
        # Exit with appropriate code based on results
        if results["status"] == "error":
            sys.exit(1)
        elif results["status"] == "warning":
            sys.exit(2)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    save_text()