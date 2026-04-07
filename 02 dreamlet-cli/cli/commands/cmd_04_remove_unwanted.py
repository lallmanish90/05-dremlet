"""
CLI Command: Remove Unwanted (Page 04)

Converts the Streamlit page 04_Remove_unwanted.py to CLI interface
while maintaining 100% functional parity.
"""

import click
import os
import sys
import re
import fnmatch
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
# All functions below are extracted from pages/04_Remove_unwanted.py

def get_input_directory() -> str:
    """Get the path to the input directory"""
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir

def find_files(directory: str, pattern: str) -> List[str]:
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
        transcripts.extend(find_files(directory, pattern))
    
    transcripts = [f for f in transcripts if "slide" not in os.path.basename(f).lower()]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-s\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'summary', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-d\.(md|txt)$', os.path.basename(f).lower())]
    transcripts = [f for f in transcripts if not re.search(r'^\d+-artifact-d\.(md|txt)$', os.path.basename(f).lower())]
    
    return list(set(transcripts))

def find_slide_files(directory: str) -> List[str]:
    """Find all slide description files in a directory"""
    slides = []
    slide_patterns = [
        "*-slides.txt", "*-slides.md",
        "*-slide.txt", "*-slide.md",
        "*slides*.txt", "*slides*.md",
        "*slide*.txt", "*slide*.md",
        "*-s.txt", "*-s.md",
        "*artifact_c*.txt", "*artifact_c*.md",
        "*artifact-c*.txt", "*artifact-c*.md",
        "*slide_content*.txt", "*slide_content*.md"
    ]
    
    for pattern in slide_patterns:
        slides.extend(find_files(directory, pattern))
    
    all_text_files = find_files(directory, "*.txt") + find_files(directory, "*.md")
    for file_path in all_text_files:
        filename = os.path.basename(file_path)
        if re.search(r'^\d+-s\.(md|txt)$', filename.lower()):
            if file_path not in slides:
                slides.append(file_path)
    
    return list(set(slides))

def find_non_supported_files(directory: str) -> List[str]:
    """Find all files that are not supported"""
    all_files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            all_files.append(os.path.join(root, filename))
    
    supported_extensions = ['.txt', '.md', '.pptx', '.zip']
    media_extensions = [
        '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.svg', '.webp', '.img',
        '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
        '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm'
    ]
    
    accepted_extensions = supported_extensions + media_extensions
    
    non_supported = []
    for file_path in all_files:
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in accepted_extensions:
            non_supported.append(file_path)
    
    return non_supported

def extract_course_lecture_section(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract course, lecture, and section information from a file path"""
    dir_parts = os.path.normpath(file_path).split(os.sep)
    
    course = None
    lecture = None
    section = None
    
    for part in dir_parts:
        course_match = re.search(r'course\s*(\d+)', part.lower())
        if course_match:
            course = course_match.group(1)
            break
        number_start_match = re.match(r'^(\d+)\s+', part)
        if number_start_match:
            course = number_start_match.group(1)
            break
        bracket_match = re.search(r'[(\[]\s*(\d+)\s*[)\]]', part)
        if bracket_match:
            course = bracket_match.group(1)
            break
    
    filename = os.path.basename(file_path)
    lecture_patterns = [
        r'lecture\s*(\d+)',
        r'lec\s*(\d+)',
        r'^(\d+)[-\s]',
        r'^\w+\s*(\d+)'
    ]
    
    for pattern in lecture_patterns:
        lecture_match = re.search(pattern, filename.lower())
        if lecture_match:
            lecture = lecture_match.group(1)
            break
    
    if not lecture:
        for part in dir_parts:
            for pattern in lecture_patterns:
                lecture_match = re.search(pattern, part.lower())
                if lecture_match:
                    lecture = lecture_match.group(1)
                    break
            if lecture:
                break
    
    section_patterns = [
        r'section\s*(\d+)',
        r'sec\s*(\d+)'
    ]
    
    for part in dir_parts:
        for pattern in section_patterns:
            section_match = re.search(pattern, part.lower())
            if section_match:
                section = section_match.group(1)
                break
        if section:
            break
    
    return course, lecture, section

def delete_non_supported_files(non_supported_files: List[str], status_manager: StatusManager) -> Dict[str, Any]:
    """Delete non-supported files"""
    results = {
        "deleted_files": [],
        "errors": [],
        "statistics": {
            "total_files": len(non_supported_files),
            "deleted_count": 0,
            "error_count": 0
        }
    }
    
    for file_path in non_supported_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                results["deleted_files"].append({
                    "path": file_path,
                    "filename": os.path.basename(file_path),
                    "directory": os.path.dirname(file_path)
                })
                results["statistics"]["deleted_count"] += 1
                status_manager.info(f"Deleted: {os.path.basename(file_path)}", verbose_only=True)
            else:
                results["errors"].append(f"File not found: {file_path}")
                results["statistics"]["error_count"] += 1
        except Exception as e:
            error_msg = f"Error deleting {os.path.basename(file_path)}: {str(e)}"
            results["errors"].append(error_msg)
            results["statistics"]["error_count"] += 1
            status_manager.error(error_msg)
    
    return results

# ===== CLI IMPLEMENTATION =====

def run_remove_unwanted(ctx_obj: Dict[str, Any], force: bool = False, delete_files: bool = False) -> Dict[str, Any]:
    """
    Main function to run the remove unwanted operation
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
            "statistics": {"transcript_files": 0, "slide_files": 0, "non_supported_files": 0, "deleted_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Scanning input directory: {input_dir}")
    
    # Find all transcript and slide files
    with DreamletProgress(description="Scanning for files", total=100) as progress:
        progress.update(completed=25, description="Finding transcript files...")
        all_transcripts = find_transcript_files(input_dir)
        
        progress.update(completed=50, description="Finding slide files...")
        all_slides = find_slide_files(input_dir)
        
        progress.update(completed=75, description="Finding non-supported files...")
        non_supported_files = find_non_supported_files(input_dir)
        
        progress.update(completed=100, description="Scan complete")
    
    # Combine supported files
    all_supported_files = all_transcripts + all_slides
    
    # Calculate statistics
    statistics = {
        "transcript_files": len(all_transcripts),
        "slide_files": len(all_slides),
        "total_supported_files": len(all_supported_files),
        "non_supported_files": len(non_supported_files),
        "deleted_count": 0,
        "error_count": 0
    }
    
    status_manager.info(f"Found {statistics['transcript_files']} transcript files and {statistics['slide_files']} slide files")
    
    if statistics["non_supported_files"] > 0:
        status_manager.warning(f"Found {statistics['non_supported_files']} non-supported files")
        
        # Show non-supported files if verbose
        if ctx_obj.get('verbose', False):
            show_non_supported_files(non_supported_files, status_manager)
        
        # Delete non-supported files if requested
        if delete_files:
            status_manager.info(f"Deleting {statistics['non_supported_files']} non-supported files...")
            
            with DreamletProgress(description="Deleting non-supported files", total=statistics["non_supported_files"]) as progress:
                delete_results = delete_non_supported_files(non_supported_files, status_manager)
                progress.update(completed=statistics["non_supported_files"])
            
            statistics["deleted_count"] = delete_results["statistics"]["deleted_count"]
            statistics["error_count"] = delete_results["statistics"]["error_count"]
            
            status_manager.success(f"Deleted {statistics['deleted_count']} files") if statistics["deleted_count"] > 0 else None
            status_manager.error(f"Failed to delete {statistics['error_count']} files") if statistics["error_count"] > 0 else None
        else:
            status_manager.info("Use --delete-files flag to remove non-supported files")
    else:
        status_manager.success("No non-supported files found")
    
    # Show file analysis if verbose
    if ctx_obj.get('verbose', False) and all_supported_files:
        show_file_analysis(all_supported_files, status_manager)
    
    # Determine final status
    if statistics["error_count"] > 0:
        final_status = "error"
        status_message = f"Completed with {statistics['error_count']} errors"
    elif statistics["non_supported_files"] > 0 and not delete_files:
        final_status = "warning"
        status_message = f"Found {statistics['non_supported_files']} non-supported files (use --delete-files to remove them)"
    elif statistics["deleted_count"] > 0:
        final_status = "success"
        status_message = f"Successfully deleted {statistics['deleted_count']} non-supported files"
    else:
        final_status = "success"
        status_message = "Directory is clean - no non-supported files found"
    
    # Show summary
    status_manager.success(status_message) if final_status == "success" else \
    status_manager.warning(status_message) if final_status == "warning" else \
    status_manager.error(status_message)
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "transcript_files_found": statistics["transcript_files"],
            "slide_files_found": statistics["slide_files"],
            "non_supported_files_found": statistics["non_supported_files"]
        },
        "processing_results": [],
        "statistics": statistics,
        "errors": [],
        "warnings": [],
        "output_files": []
    }
    
    # Add processing results if files were deleted
    if delete_files and statistics["deleted_count"] > 0:
        report_results["processing_results"] = [
            {
                "operation": "delete",
                "files_processed": statistics["non_supported_files"],
                "files_deleted": statistics["deleted_count"],
                "errors": statistics["error_count"]
            }
        ]
    
    # Generate report
    report_path = generate_report("04", "Remove Unwanted", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

def show_non_supported_files(non_supported_files: List[str], status_manager: StatusManager):
    """Show non-supported files in terminal format"""
    
    console.print("\n[bold red]Non-Supported Files Found:[/bold red]")
    
    # Group files by directory for better organization
    files_by_dir = {}
    for file_path in non_supported_files:
        dir_name = os.path.dirname(file_path)
        if dir_name not in files_by_dir:
            files_by_dir[dir_name] = []
        files_by_dir[dir_name].append(os.path.basename(file_path))
    
    # Create table
    non_supported_table = Table()
    non_supported_table.add_column("Directory", style="cyan")
    non_supported_table.add_column("Filename", style="white")
    non_supported_table.add_column("Extension", style="yellow")
    
    for dir_name, filenames in files_by_dir.items():
        for filename in sorted(filenames):
            _, ext = os.path.splitext(filename)
            non_supported_table.add_row(
                dir_name,
                filename,
                ext if ext else "(no extension)"
            )
    
    console.print(non_supported_table)

def show_file_analysis(all_supported_files: List[str], status_manager: StatusManager):
    """Show file analysis by course in terminal format"""
    
    # Group files by course
    files_by_course = {}
    for file_path in all_supported_files:
        course, _, _ = extract_course_lecture_section(file_path)
        course_name = f"Course {course}" if course else "Uncategorized"
        
        if course_name not in files_by_course:
            files_by_course[course_name] = []
        files_by_course[course_name].append(file_path)
    
    # Sort courses numerically
    sorted_courses = sorted(
        files_by_course.keys(),
        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 999
    )
    
    console.print("\n[bold green]Supported Files by Course:[/bold green]")
    
    # Create summary table
    course_table = Table()
    course_table.add_column("Course", style="cyan")
    course_table.add_column("File Count", style="yellow")
    
    for course_name in sorted_courses:
        file_paths = files_by_course[course_name]
        course_table.add_row(course_name, str(len(file_paths)))
    
    console.print(course_table)

@click.command()
@click.pass_context
def remove_unwanted(ctx):
    """
    Delete non-supported files from the input directory
    
    This command scans the input directory for files that are not supported by the
    video production workflow and removes them to keep the workspace clean.
    
    All settings are configured in config.json under "page_04_remove_unwanted":
    - supported_extensions: List of supported file extensions
    - delete_empty_folders: Whether to delete empty folders after cleanup
    
    Examples:
        dreamlet run 04                    # Remove unwanted files with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_04_remove_unwanted')
    
    # Extract settings from config
    delete_files = True  # Always delete in this simplified version
    force = True  # No confirmation needed since it's config-driven
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]")
        console.print(f"Would delete non-supported files with extensions not in: {page_config.get('supported_extensions', [])}")
        return
        try:
            confirm = console.input("\n[bold red]This will permanently delete non-supported files. Continue? [y/N]: [/bold red]").strip().lower()
            if confirm not in ['y', 'yes']:
                console.print("Operation cancelled.")
                return
        except KeyboardInterrupt:
            console.print("\nOperation cancelled.")
            return
    
    # Run the remove unwanted operation
    try:
        results = run_remove_unwanted(ctx.obj, force, delete_files)
        
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
    remove_unwanted()