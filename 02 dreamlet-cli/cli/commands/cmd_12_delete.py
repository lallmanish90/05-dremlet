"""
CLI Command: Delete Lecture Files (Page 12)

Converts the Streamlit page 12_Delete.py to CLI interface
while maintaining 100% functional parity.

This command permanently deletes all files and directories related to 
specific lectures, including files in all_* folders.
"""

import click
import os
import sys
import re
import time
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress
from cli.reports import generate_report
from cli.config import load_config
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()

# ============================================================================
# UTILITY FUNCTIONS (copied from original page)
# ============================================================================

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def extract_course_lecture_section(file_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract course, lecture, and section information from a file path"""
    dir_parts = os.path.normpath(file_path).split(os.sep)
    course, lecture, section = None, None, None
    
    for part in dir_parts:
        if not course:
            course_match = re.search(r'course\s*(\d+)', part.lower())
            if course_match:
                course = course_match.group(1)
    
    filename = os.path.basename(file_path)
    for pattern in [r'lecture\s*(\d+)', r'lec\s*(\d+)', r'^(\d+)[-\s]']:
        lecture_match = re.search(pattern, filename.lower())
        if lecture_match:
            lecture = lecture_match.group(1)
            break
    
    return course, lecture, section

def find_lecture_files(input_dir: str) -> Dict:
    """
    Find all lecture files across the file system and organize them by course and lecture
    
    Args:
        input_dir: Base input directory
        
    Returns:
        Dictionary organized by course and lecture
    """
    organized_data = {}
    
    # Find all lecture directories
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Check if this is a lecture directory (contains "lecture" in name)
        parts = Path(root).parts
        
        # Check if directory name contains "lecture"
        is_lecture_dir = any(
            "lecture" in part.lower() 
            for part in parts
        )
        
        if not is_lecture_dir:
            continue
            
        # Extract lecture info
        course_name = None
        lecture_name = None
        
        # Find lecture name (directory with "lecture" in it)
        for i, part in enumerate(parts):
            if "lecture" in part.lower():
                lecture_name = part
                # Course is typically the parent directory of lecture
                if i > 0:
                    course_name = parts[i-1]
                break
        
        # Skip if we couldn't determine both course and lecture
        if not course_name or not lecture_name:
            continue
            
        # Initialize data structures if needed
        if course_name not in organized_data:
            organized_data[course_name] = {}
            
        # Initialize lecture data with base directory
        if lecture_name not in organized_data[course_name]:
            organized_data[course_name][lecture_name] = {
                "base_dir": root,
                "files_to_delete": set(),
                "directories_to_delete": set(),
                "file_count": 0,
                "directory_count": 0
            }
            
        # First, add the lecture directory itself
        organized_data[course_name][lecture_name]["directories_to_delete"].add(root)
        
        # Find all files in this lecture directory
        lecture_files = []
        for r, d, f in os.walk(root):
            # Add all files
            for file in f:
                file_path = os.path.join(r, file)
                organized_data[course_name][lecture_name]["files_to_delete"].add(file_path)
                lecture_files.append(file_path)
            
            # Add all subdirectories
            for directory in d:
                dir_path = os.path.join(r, directory)
                organized_data[course_name][lecture_name]["directories_to_delete"].add(dir_path)
    
        # Find lecture number to use for matching files in all_* folders
        lecture_num = None
        lecture_num_match = re.search(r'lecture\s*(\d+)', lecture_name.lower())
        if lecture_num_match:
            lecture_num = lecture_num_match.group(1)
        
        if lecture_num:
            # Find files in all_transcripts, all_summary, all_pptx, and all_slides that match this lecture
            for folder_name in ['all_transcripts', 'all_summary', 'all_pptx', 'all_slides']:
                # Navigate from course directory
                course_dir = os.path.dirname(root)
                all_folder = os.path.join(course_dir, folder_name)
                
                if os.path.exists(all_folder) and os.path.isdir(all_folder):
                    # Find files with matching lecture number
                    for file in os.listdir(all_folder):
                        file_path = os.path.join(all_folder, file)
                        
                        # Check if file is related to this lecture
                        if re.search(rf'lecture\s*{lecture_num}\b', file.lower()) or re.search(rf'\b{lecture_num}\b', file):
                            organized_data[course_name][lecture_name]["files_to_delete"].add(file_path)
                            lecture_files.append(file_path)
        
        # Update counts
        organized_data[course_name][lecture_name]["file_count"] = len(organized_data[course_name][lecture_name]["files_to_delete"])
        organized_data[course_name][lecture_name]["directory_count"] = len(organized_data[course_name][lecture_name]["directories_to_delete"])
    
    return organized_data

def delete_lecture(lecture_data: Dict) -> Dict:
    """
    Delete all files and directories for a lecture
    
    Args:
        lecture_data: Dictionary with lecture data
        
    Returns:
        Dictionary with results
    """
    result = {
        "files_deleted": 0,
        "directories_deleted": 0,
        "errors": []
    }
    
    # First delete individual files to clean up directories
    for file_path in sorted(lecture_data["files_to_delete"]):
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                result["files_deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting file {file_path}: {str(e)}")
    
    # Delete directories in reverse order (deepest first)
    for dir_path in sorted(lecture_data["directories_to_delete"], reverse=True):
        try:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # Try to delete, but only if empty (safety check)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    result["directories_deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting directory {dir_path}: {str(e)}")
    
    return result

def extract_number(name: str) -> int:
    """Extract number from course or lecture name for sorting"""
    match = re.search(r'\d+', name)
    if match:
        return int(match.group())
    return 999

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def run_delete_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the delete processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_12_delete')
    
    # Extract settings from config
    target_courses = page_config.get('target_courses', [])
    target_lectures = page_config.get('target_lectures', [])
    confirm_deletion = page_config.get('confirm_deletion', True)
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_lectures": 0, "deleted_count": 0, "error_count": 1}
        }
    
    console.print(f"[blue]ℹ[/blue] Scanning input directory: {input_dir}")
    console.print(f"[yellow]⚠[/yellow] [bold]WARNING: This operation permanently deletes files![/bold]")
    
    # Find and organize lecture files
    console.print(f"[blue]ℹ[/blue] Discovering lecture files...")
    organized_data = find_lecture_files(input_dir)
    
    if not organized_data:
        error_msg = "No lecture files found in the input directory"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_lectures": 0, "deleted_count": 0, "error_count": 0}
        }
    
    # Count total lectures found
    total_lectures = sum(len(lectures) for lectures in organized_data.values())
    console.print(f"[green]✓[/green] Found {total_lectures} lectures across {len(organized_data)} courses")
    
    # Filter lectures based on configuration
    selected_lectures = {}
    
    # Sort courses numerically
    sorted_courses = sorted(organized_data.keys(), key=extract_number)
    
    for course in sorted_courses:
        # Check if this course should be processed
        if target_courses and course not in target_courses:
            continue
            
        # Sort lectures numerically
        sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
        
        for lecture in sorted_lectures:
            # Check if this lecture should be processed
            if target_lectures and lecture not in target_lectures:
                continue
                
            lecture_data = organized_data[course][lecture]
            selected_lectures[(course, lecture)] = lecture_data
    
    # If no specific targets configured, show available options and exit
    if not target_courses and not target_lectures:
        console.print(f"[blue]ℹ[/blue] No specific courses or lectures configured for deletion")
        console.print(f"[blue]ℹ[/blue] Available courses and lectures:")
        
        # Display available options
        table = Table(title="Available Lectures for Deletion")
        table.add_column("Course", style="cyan")
        table.add_column("Lecture", style="magenta")
        table.add_column("Files", justify="right")
        table.add_column("Directories", justify="right")
        table.add_column("Base Directory", style="dim")
        
        for course in sorted_courses:
            sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
            for lecture in sorted_lectures:
                lecture_data = organized_data[course][lecture]
                table.add_row(
                    course,
                    lecture,
                    str(lecture_data["file_count"]),
                    str(lecture_data["directory_count"]),
                    lecture_data["base_dir"]
                )
        
        console.print(table)
        console.print(f"[blue]ℹ[/blue] To delete specific lectures, configure 'target_courses' and/or 'target_lectures' in config.json")
        
        return {
            "status": "info",
            "message": f"Found {total_lectures} lectures available for deletion",
            "statistics": {"total_lectures": total_lectures, "deleted_count": 0, "error_count": 0},
            "available_courses": list(sorted_courses),
            "available_lectures": {course: list(organized_data[course].keys()) for course in sorted_courses}
        }
    
    if not selected_lectures:
        error_msg = f"No lectures match the configured targets (courses: {target_courses}, lectures: {target_lectures})"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_lectures": total_lectures, "deleted_count": 0, "error_count": 0}
        }
    
    # Calculate totals for selected lectures
    total_files_to_delete = sum(data["file_count"] for data in selected_lectures.values())
    total_directories_to_delete = sum(data["directory_count"] for data in selected_lectures.values())
    
    console.print(f"[yellow]⚠[/yellow] Selected {len(selected_lectures)} lectures for deletion:")
    console.print(f"[yellow]⚠[/yellow] This will delete {total_files_to_delete} files and {total_directories_to_delete} directories")
    
    # Show what will be deleted
    if ctx_obj.get('verbose', False):
        deletion_table = Table(title="Lectures Selected for Deletion")
        deletion_table.add_column("Course", style="cyan")
        deletion_table.add_column("Lecture", style="magenta")
        deletion_table.add_column("Files", justify="right", style="red")
        deletion_table.add_column("Directories", justify="right", style="red")
        
        for (course, lecture), data in selected_lectures.items():
            deletion_table.add_row(
                course,
                lecture,
                str(data["file_count"]),
                str(data["directory_count"])
            )
        
        console.print(deletion_table)
    
    # Confirmation check
    if confirm_deletion:
        console.print(f"[red]⚠[/red] [bold]This action will permanently delete all selected files and cannot be undone![/bold]")
        
        if not Confirm.ask("Are you sure you want to proceed with deletion?"):
            console.print(f"[yellow]Operation cancelled by user[/yellow]")
            return {
                "status": "cancelled",
                "message": "Deletion cancelled by user",
                "statistics": {"total_lectures": total_lectures, "deleted_count": 0, "error_count": 0}
            }
    
    # Perform deletion
    results = []
    start_time = time.time()
    
    with DreamletProgress(description="Deleting lectures", total=len(selected_lectures)) as progress:
        
        for i, ((course, lecture), lecture_data) in enumerate(selected_lectures.items()):
            progress.update(description=f"Deleting {course} - {lecture}")
            
            # Delete files and directories
            result = delete_lecture(lecture_data)
            
            # Add to results
            results.append({
                "course": course,
                "lecture": lecture,
                "files_deleted": result["files_deleted"],
                "directories_deleted": result["directories_deleted"],
                "errors": len(result["errors"]),
                "error_details": result["errors"]
            })
            
            progress.update(advance=1)
    
    # Calculate final statistics
    total_processing_time = time.time() - start_time
    total_files_deleted = sum(r["files_deleted"] for r in results)
    total_dirs_deleted = sum(r["directories_deleted"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    
    # Determine final status
    if total_errors > 0 and total_files_deleted == 0:
        final_status = "error"
        status_message = f"Deletion failed with {total_errors} errors"
    elif total_errors > 0:
        final_status = "warning"
        status_message = f"Deleted {len(selected_lectures)} lectures with {total_errors} errors"
    else:
        final_status = "success"
        status_message = f"Successfully deleted {len(selected_lectures)} lectures"
    
    # Show summary
    console.print(f"[green]✓[/green] {status_message}")
    console.print(f"[blue]ℹ[/blue] Files deleted: {total_files_deleted}")
    console.print(f"[blue]ℹ[/blue] Directories deleted: {total_dirs_deleted}")
    console.print(f"[blue]ℹ[/blue] Total processing time: {total_processing_time:.1f} seconds")
    
    if total_errors > 0:
        console.print(f"[red]✗[/red] Errors encountered: {total_errors}")
    
    # Display detailed results if verbose
    if ctx_obj.get('verbose', False) and results:
        results_table = Table(title="Deletion Results")
        results_table.add_column("Course", style="cyan")
        results_table.add_column("Lecture", style="magenta")
        results_table.add_column("Files Deleted", justify="right", style="green")
        results_table.add_column("Dirs Deleted", justify="right", style="green")
        results_table.add_column("Errors", justify="right", style="red")
        
        for result in results:
            error_style = "red" if result["errors"] > 0 else "green"
            results_table.add_row(
                result["course"],
                result["lecture"],
                str(result["files_deleted"]),
                str(result["directories_deleted"]),
                f"[{error_style}]{result['errors']}[/{error_style}]"
            )
        
        console.print(results_table)
        
        # Show error details if any
        if total_errors > 0:
            console.print(f"[red]Error Details:[/red]")
            for result in results:
                if result["errors"] > 0:
                    console.print(f"[red]{result['course']} - {result['lecture']}:[/red]")
                    for error in result["error_details"]:
                        console.print(f"  [red]✗[/red] {error}")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "total_lectures_found": total_lectures,
            "courses_found": len(organized_data),
            "target_courses": target_courses,
            "target_lectures": target_lectures
        },
        "statistics": {
            "lectures_selected": len(selected_lectures),
            "files_deleted": total_files_deleted,
            "directories_deleted": total_dirs_deleted,
            "errors": total_errors,
            "processing_time": f"{total_processing_time:.1f}s"
        },
        "settings": {
            "confirm_deletion": confirm_deletion,
            "target_courses": target_courses,
            "target_lectures": target_lectures
        },
        "deletion_results": [
            {
                "course": result["course"],
                "lecture": result["lecture"],
                "files_deleted": result["files_deleted"],
                "directories_deleted": result["directories_deleted"],
                "errors": result["errors"]
            }
            for result in results
        ],
        "errors": [
            f"{result['course']} - {result['lecture']}: {error}"
            for result in results
            for error in result["error_details"]
        ]
    }
    
    # Generate report
    report_path = generate_report("12", "Delete Lecture Files", report_results)
    console.print(f"[blue]ℹ[/blue] Report saved to: {report_path}", style="dim")
    
    report_results["report_path"] = report_path
    return report_results

@click.command()
@click.pass_context
def delete_lectures(ctx):
    """
    Delete all files and directories related to specific lectures
    
    This command permanently deletes all files related to selected lectures,
    including files in lecture directories and matching files in all_* folders
    (all_transcripts, all_summary, all_pptx, all_slides).
    
    ⚠️  WARNING: This operation permanently deletes files and cannot be undone!
    
    Features:
    - Comprehensive lecture file discovery across directory structure
    - Deletion of lecture directories and all contained files
    - Cleanup of related files in all_* folders based on lecture numbers
    - Safety checks and confirmation prompts
    - Detailed reporting of deletion results
    
    All settings are configured in config.json under "page_12_delete":
    - target_courses: List of course names to delete (empty = show available)
    - target_lectures: List of lecture names to delete (empty = show available)  
    - confirm_deletion: Require confirmation before deletion (default: true)
    
    Examples:
        dreamlet run 12                    # Show available lectures for deletion
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
        
    To delete specific lectures, configure target_courses and/or target_lectures
    in config.json, then run the command again.
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be deleted[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_12_delete')
        target_courses = page_config.get('target_courses', [])
        target_lectures = page_config.get('target_lectures', [])
        
        console.print(f"Would delete courses: {target_courses if target_courses else 'None configured (would show available)'}")
        console.print(f"Would delete lectures: {target_lectures if target_lectures else 'None configured (would show available)'}")
        console.print("Would scan for lecture files and related files in all_* folders")
        return
    
    # Run the delete processing operation
    try:
        results = run_delete_processing(ctx.obj)
        
        # Exit with appropriate code based on results
        if results["status"] == "error":
            sys.exit(1)
        elif results["status"] == "warning":
            sys.exit(2)
        elif results["status"] == "cancelled":
            sys.exit(130)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    delete_lectures()