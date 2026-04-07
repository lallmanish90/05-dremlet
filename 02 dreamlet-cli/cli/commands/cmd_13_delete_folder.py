"""
CLI Command: Delete Specific Folders (Page 13)

Converts the Streamlit page 13_Delete_folder.py to CLI interface
while maintaining 100% functional parity.

This command deletes specific folders within lectures without removing 
the entire lecture, supporting both specific folder deletion and 
bulk deletion by folder type.
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
    input_dir = os.path.join(os.getcwd(), "input")
    return input_dir
def find_lecture_folders(input_dir: str) -> Dict:
    """
    Find all lecture folders across the file system and organize them by course and lecture
    
    Args:
        input_dir: Base input directory
        
    Returns:
        Dictionary organized by course, lecture, and folder types
    """
    organized_data = {}
    folder_types = set()  # To track all folder types across all lectures
    
    # First pass: find all courses by looking at top-level directories
    courses = {}
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Consider all top-level directories as potential courses
            courses[item] = item_path
    
    # Find all folders in lecture directories
    for course_name, course_path in courses.items():
        # Initialize course in data structure
        if course_name not in organized_data:
            organized_data[course_name] = {}
        
        # Look for lecture directories within this course
        for item in os.listdir(course_path):
            item_path = os.path.join(course_path, item)
            
            # Skip non-directories and hidden files
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
            
            # Check if this is a lecture directory
            is_lecture = "lecture" in item.lower()
            
            if is_lecture:
                lecture_name = item
                
                # Initialize lecture in data structure
                if lecture_name not in organized_data[course_name]:
                    organized_data[course_name][lecture_name] = {
                        "base_dir": item_path,
                        "folders": {}
                    }
                
                # Look for folders within this lecture
                lecture_folders = {}
                for folder in os.listdir(item_path):
                    folder_path = os.path.join(item_path, folder)
                    
                    # Skip non-directories and hidden files
                    if not os.path.isdir(folder_path) or folder.startswith('.'):
                        continue
                    
                    # Count files in this folder (for display)
                    file_count = sum(len(files) for _, _, files in os.walk(folder_path))
                    
                    # Store folder info
                    lecture_folders[folder] = {
                        "path": folder_path,
                        "file_count": file_count
                    }
                    
                    # Add to global set of folder types
                    folder_types.add(folder)
                
                # Store folders for this lecture
                organized_data[course_name][lecture_name]["folders"] = lecture_folders
    
    # If no lectures found directly, try a deeper search
    if not any(organized_data.values()):
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
            
            # If we couldn't determine the course, use a default name
            if not course_name:
                course_name = "Unknown Course"
            
            # Initialize data structures if needed
            if course_name not in organized_data:
                organized_data[course_name] = {}
                
            # Check for subdirectories (folder types) in this lecture directory
            folders_in_lecture = {}
            
            # Immediate subdirectories (folder types like "English text", "English audio", etc.)
            for folder in dirs:
                folder_path = os.path.join(root, folder)
                
                # Count files in this folder (for display)
                file_count = 0
                for _, _, f in os.walk(folder_path):
                    file_count += len(f)
                
                # Store folder info
                folders_in_lecture[folder] = {
                    "path": folder_path,
                    "file_count": file_count
                }
                
                # Add to global set of folder types
                folder_types.add(folder)
            
            # Store lecture info with its folders
            if lecture_name:
                organized_data[course_name][lecture_name] = {
                    "base_dir": root,
                    "folders": folders_in_lecture
                }
    
    # Store all folder types in the organized data
    organized_data["__folder_types__"] = list(folder_types)
    
    return organized_data

def delete_folders(folders_to_delete: List[str]) -> Dict:
    """
    Delete selected folders
    
    Args:
        folders_to_delete: List of folder paths to delete
        
    Returns:
        Dictionary with results
    """
    result = {
        "deleted": 0,
        "errors": []
    }
    
    for folder_path in folders_to_delete:
        try:
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                result["deleted"] += 1
        except Exception as e:
            result["errors"].append(f"Error deleting folder {folder_path}: {str(e)}")
    
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

def run_delete_folder_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the delete folder processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_13_delete_folder')
    
    # Extract settings from config
    target_folder_types = page_config.get('target_folder_types', [])
    target_courses = page_config.get('target_courses', [])
    deletion_mode = page_config.get('deletion_mode', 'interactive')  # 'interactive', 'bulk', 'specific'
    confirm_deletion = page_config.get('confirm_deletion', True)
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_folders": 0, "deleted_count": 0, "error_count": 1}
        }
    
    console.print(f"[blue]ℹ[/blue] Scanning input directory: {input_dir}")
    console.print(f"[yellow]⚠[/yellow] [bold]WARNING: This operation permanently deletes folders![/bold]")
    
    # Find and organize lecture folders
    console.print(f"[blue]ℹ[/blue] Discovering lecture folders...")
    organized_data = find_lecture_folders(input_dir)
    
    # Extract folder types from the data
    all_folder_types = organized_data.pop("__folder_types__", [])
    all_folder_types.sort()  # Sort alphabetically
    
    if not organized_data:
        error_msg = "No lecture folders found in the input directory"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_folders": 0, "deleted_count": 0, "error_count": 0}
        }
    
    # Count total folders found
    total_folders = 0
    for course_data in organized_data.values():
        for lecture_data in course_data.values():
            total_folders += len(lecture_data["folders"])
    
    console.print(f"[green]✓[/green] Found {total_folders} folders across {len(organized_data)} courses")
    console.print(f"[blue]ℹ[/blue] Available folder types: {', '.join(all_folder_types)}")
    
    # If no specific targets configured, show available options and exit
    if not target_folder_types and not target_courses:
        console.print(f"[blue]ℹ[/blue] No specific folder types or courses configured for deletion")
        console.print(f"[blue]ℹ[/blue] Available folders:")
        
        # Display available options
        table = Table(title="Available Folders for Deletion")
        table.add_column("Course", style="cyan")
        table.add_column("Lecture", style="magenta")
        table.add_column("Folder Type", style="yellow")
        table.add_column("Files", justify="right")
        table.add_column("Path", style="dim")
        
        # Sort courses numerically
        sorted_courses = sorted(organized_data.keys(), key=extract_number)
        
        for course in sorted_courses:
            # Sort lectures numerically
            sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
            for lecture in sorted_lectures:
                lecture_data = organized_data[course][lecture]
                for folder_name, folder_info in sorted(lecture_data["folders"].items()):
                    table.add_row(
                        course,
                        lecture,
                        folder_name,
                        str(folder_info["file_count"]),
                        folder_info["path"]
                    )
        
        console.print(table)
        console.print(f"[blue]ℹ[/blue] To delete specific folders, configure 'target_folder_types' and/or 'target_courses' in config.json")
        
        return {
            "status": "info",
            "message": f"Found {total_folders} folders available for deletion",
            "statistics": {"total_folders": total_folders, "deleted_count": 0, "error_count": 0},
            "available_folder_types": all_folder_types,
            "available_courses": list(sorted_courses)
        }
    
    # Find matching folders based on configuration
    matching_folders = []
    
    # Sort courses numerically
    sorted_courses = sorted(organized_data.keys(), key=extract_number)
    
    for course in sorted_courses:
        # Check if this course should be processed
        if target_courses and course not in target_courses:
            continue
            
        # Sort lectures numerically
        sorted_lectures = sorted(organized_data[course].keys(), key=extract_number)
        
        for lecture in sorted_lectures:
            lecture_data = organized_data[course][lecture]
            
            for folder_name, folder_info in lecture_data["folders"].items():
                # Check if this folder type should be processed
                if target_folder_types and folder_name not in target_folder_types:
                    continue
                    
                matching_folders.append({
                    "course": course,
                    "lecture": lecture,
                    "folder": folder_name,
                    "path": folder_info["path"],
                    "file_count": folder_info["file_count"]
                })
    
    if not matching_folders:
        error_msg = f"No folders match the configured targets (folder_types: {target_folder_types}, courses: {target_courses})"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_folders": total_folders, "deleted_count": 0, "error_count": 0}
        }
    
    # Calculate totals for selected folders
    total_files_to_delete = sum(folder["file_count"] for folder in matching_folders)
    
    console.print(f"[yellow]⚠[/yellow] Selected {len(matching_folders)} folders for deletion:")
    console.print(f"[yellow]⚠[/yellow] This will delete {total_files_to_delete} files across {len(matching_folders)} folders")
    
    # Group by folder type for summary
    folder_summary = {}
    for folder in matching_folders:
        folder_type = folder["folder"]
        if folder_type not in folder_summary:
            folder_summary[folder_type] = {
                "count": 0,
                "file_count": 0
            }
        folder_summary[folder_type]["count"] += 1
        folder_summary[folder_type]["file_count"] += folder["file_count"]
    
    # Show summary
    console.print(f"[blue]ℹ[/blue] Summary by folder type:")
    for folder_type, summary in folder_summary.items():
        console.print(f"  [yellow]{folder_type}[/yellow]: {summary['count']} folders, {summary['file_count']} files")
    
    # Show what will be deleted if verbose
    if ctx_obj.get('verbose', False):
        deletion_table = Table(title="Folders Selected for Deletion")
        deletion_table.add_column("Course", style="cyan")
        deletion_table.add_column("Lecture", style="magenta")
        deletion_table.add_column("Folder Type", style="yellow")
        deletion_table.add_column("Files", justify="right", style="red")
        
        for folder in matching_folders:
            deletion_table.add_row(
                folder["course"],
                folder["lecture"],
                folder["folder"],
                str(folder["file_count"])
            )
        
        console.print(deletion_table)
    
    # Confirmation check
    if confirm_deletion:
        console.print(f"[red]⚠[/red] [bold]This action will permanently delete all selected folders and cannot be undone![/bold]")
        
        if not Confirm.ask("Are you sure you want to proceed with deletion?"):
            console.print(f"[yellow]Operation cancelled by user[/yellow]")
            return {
                "status": "cancelled",
                "message": "Deletion cancelled by user",
                "statistics": {"total_folders": total_folders, "deleted_count": 0, "error_count": 0}
            }
    
    # Perform deletion
    start_time = time.time()
    folders_to_delete = [folder["path"] for folder in matching_folders]
    
    with DreamletProgress(description="Deleting folders", total=len(folders_to_delete)) as progress:
        
        # Delete in batches for better progress updates
        batch_size = max(1, len(folders_to_delete) // 10)
        results = {
            "deleted": 0,
            "errors": []
        }
        
        for i in range(0, len(folders_to_delete), batch_size):
            batch = folders_to_delete[i:i+batch_size]
            progress.update(description=f"Deleting batch {i//batch_size + 1}")
            
            # Delete batch
            batch_result = delete_folders(batch)
            results["deleted"] += batch_result["deleted"]
            results["errors"].extend(batch_result["errors"])
            
            progress.update(advance=len(batch))
    
    # Calculate final statistics
    total_processing_time = time.time() - start_time
    total_errors = len(results["errors"])
    
    # Determine final status
    if total_errors > 0 and results["deleted"] == 0:
        final_status = "error"
        status_message = f"Folder deletion failed with {total_errors} errors"
    elif total_errors > 0:
        final_status = "warning"
        status_message = f"Deleted {results['deleted']} folders with {total_errors} errors"
    else:
        final_status = "success"
        status_message = f"Successfully deleted {results['deleted']} folders"
    
    # Show summary
    console.print(f"[green]✓[/green] {status_message}")
    console.print(f"[blue]ℹ[/blue] Total processing time: {total_processing_time:.1f} seconds")
    
    if total_errors > 0:
        console.print(f"[red]✗[/red] Errors encountered: {total_errors}")
        if ctx_obj.get('verbose', False):
            console.print(f"[red]Error Details:[/red]")
            for error in results["errors"]:
                console.print(f"  [red]✗[/red] {error}")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "total_folders_found": total_folders,
            "courses_found": len(organized_data),
            "folder_types_found": len(all_folder_types),
            "target_folder_types": target_folder_types,
            "target_courses": target_courses
        },
        "statistics": {
            "folders_selected": len(matching_folders),
            "folders_deleted": results["deleted"],
            "files_affected": total_files_to_delete,
            "errors": total_errors,
            "processing_time": f"{total_processing_time:.1f}s"
        },
        "settings": {
            "deletion_mode": deletion_mode,
            "confirm_deletion": confirm_deletion,
            "target_folder_types": target_folder_types,
            "target_courses": target_courses
        },
        "folder_summary": [
            {
                "folder_type": folder_type,
                "count": summary["count"],
                "file_count": summary["file_count"]
            }
            for folder_type, summary in folder_summary.items()
        ],
        "deletion_results": [
            {
                "course": folder["course"],
                "lecture": folder["lecture"],
                "folder_type": folder["folder"],
                "file_count": folder["file_count"],
                "path": folder["path"]
            }
            for folder in matching_folders
        ],
        "errors": results["errors"]
    }
    
    # Generate report
    report_path = generate_report("13", "Delete Specific Folders", report_results)
    console.print(f"[blue]ℹ[/blue] Report saved to: {report_path}", style="dim")
    
    report_results["report_path"] = report_path
    return report_results
@click.command()
@click.pass_context
def delete_folders_cmd(ctx):
    """
    Delete specific folders within lectures without removing entire lectures
    
    This command deletes specific folder types (e.g., "English text", "English audio")
    from selected lectures or across multiple lectures. It supports both targeted
    deletion and bulk operations by folder type.
    
    ⚠️  WARNING: This operation permanently deletes folders and cannot be undone!
    
    Features:
    - Delete specific folder types from selected courses/lectures
    - Bulk deletion of folder types across multiple lectures
    - Comprehensive folder discovery and organization
    - Safety checks and confirmation prompts
    - Detailed reporting of deletion results
    
    All settings are configured in config.json under "page_13_delete_folder":
    - target_folder_types: List of folder types to delete (e.g., ["English text"])
    - target_courses: List of course names to target (empty = all courses)
    - deletion_mode: Mode of operation ("interactive", "bulk", "specific")
    - confirm_deletion: Require confirmation before deletion (default: true)
    
    Examples:
        dreamlet run 13                    # Show available folders for deletion
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
        
    To delete specific folder types, configure target_folder_types and optionally
    target_courses in config.json, then run the command again.
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No folders will be deleted[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_13_delete_folder')
        target_folder_types = page_config.get('target_folder_types', [])
        target_courses = page_config.get('target_courses', [])
        deletion_mode = page_config.get('deletion_mode', 'interactive')
        
        console.print(f"Would delete folder types: {target_folder_types if target_folder_types else 'None configured (would show available)'}")
        console.print(f"Would target courses: {target_courses if target_courses else 'All courses'}")
        console.print(f"Would use deletion mode: {deletion_mode}")
        console.print("Would scan for lecture folders and organize by type")
        return
    
    # Run the delete folder processing operation
    try:
        results = run_delete_folder_processing(ctx.obj)
        
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
    delete_folders_cmd()