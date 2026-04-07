"""
CLI Command: Restore Files (Page 14)

Converts the Streamlit page 14_restore_pptx.py to CLI interface
while maintaining 100% functional parity.

This command restores files from their processed folders (all_pptx, all_slides, 
all_transcripts, all_summary) back to their original locations.
"""

import click
import os
import sys
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

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
    return os.path.join(os.getcwd(), 'input')

def find_files_by_type(folder_name: str, file_extensions: List[str]) -> Dict[str, List[str]]:
    """
    Find files of specific types in specified folders, organized by course
    
    Args:
        folder_name: Name of the folder to search for (e.g., 'all_pptx', 'all_slides')
        file_extensions: List of file extensions to search for (e.g., ['.pptx'], ['.txt', '.md'])
    
    Returns:
        Dictionary mapping course names to lists of file paths
    """
    input_dir = get_input_directory()
    course_files = {}
    
    # Walk through all directories to find specified folders
    for root, dirs, files in os.walk(input_dir):
        # Check if current directory matches the folder name
        if os.path.basename(root) == folder_name:
            # Find files with specified extensions
            matching_files = []
            for file in files:
                for ext in file_extensions:
                    if file.lower().endswith(ext.lower()):
                        matching_files.append(file)
                        break
            
            if matching_files:
                # Determine the course name from the path structure
                relative_path = os.path.relpath(root, input_dir)
                path_parts = relative_path.split(os.sep)
                
                # The course name should be the first part of the path
                course_name = path_parts[0] if len(path_parts) >= 1 else "Unknown"
                
                # Skip if this doesn't look like a valid course structure
                if course_name in ['.', '..', folder_name]:
                    continue
                
                if course_name not in course_files:
                    course_files[course_name] = []
                
                # Add full paths to the files
                for file in matching_files:
                    full_path = os.path.join(root, file)
                    course_files[course_name].append(full_path)
    
    return course_files

def get_original_location(file_path: str, folder_name: str) -> str:
    """
    Determine the original location of a file
    
    Args:
        file_path: Current path of file in the processed folder
        folder_name: Name of the processed folder (e.g., 'all_pptx', 'all_slides')
        
    Returns:
        Original path where the file should be restored
    """
    # Current path structure: .../lecture/folder_name/filename
    # Original path structure: .../lecture/filename
    
    processed_dir = os.path.dirname(file_path)
    parent_dir = os.path.dirname(processed_dir)
    filename = os.path.basename(file_path)
    
    original_path = os.path.join(parent_dir, filename)
    return original_path
def restore_files(selected_courses: List[str], course_files: Dict[str, List[str]], folder_name: str) -> List[Dict]:
    """
    Restore files from processed folders to their original locations
    
    Args:
        selected_courses: List of course names to process
        course_files: Dictionary mapping course names to file paths
        folder_name: Name of the processed folder (for context in messages)
        
    Returns:
        List of result dictionaries
    """
    results = []
    
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        files = course_files[course_name]
        
        for file_path in files:
            result = {
                "course": course_name,
                "file": os.path.basename(file_path),
                "status": "error",
                "message": "",
                "original_path": "",
                "restored_path": ""
            }
            
            try:
                original_path = get_original_location(file_path, folder_name)
                result["original_path"] = file_path
                result["restored_path"] = original_path
                
                # Check if source file exists
                if not os.path.exists(file_path):
                    result["message"] = f"Source file no longer exists in {folder_name} folder"
                    results.append(result)
                    continue
                
                # Check if destination already exists
                if os.path.exists(original_path):
                    result["message"] = "Destination file already exists - skipping to avoid overwrite"
                    result["status"] = "skipped"
                    results.append(result)
                    continue
                
                # Move the file back to original location
                shutil.move(file_path, original_path)
                
                result["status"] = "success"
                result["message"] = "Successfully restored to original location"
                results.append(result)
                
            except Exception as e:
                result["message"] = f"Error restoring file: {str(e)}"
                results.append(result)
    
    return results

def cleanup_empty_folders(selected_courses: List[str], course_files: Dict[str, List[str]], folder_name: str) -> List[str]:
    """
    Remove empty processed folders after restoration
    
    Args:
        selected_courses: List of course names that were processed
        course_files: Dictionary mapping course names to file paths
        folder_name: Name of the processed folder to clean up
        
    Returns:
        List of folders that were removed
    """
    removed_folders = []
    
    for course_name in selected_courses:
        if course_name not in course_files:
            continue
            
        files = course_files[course_name]
        
        # Get all unique processed folders from the processed files
        processed_folders = set()
        for file_path in files:
            processed_dir = os.path.dirname(file_path)
            processed_folders.add(processed_dir)
        
        # Check each folder and remove if empty
        for folder in processed_folders:
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
                    removed_folders.append(folder)
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not remove empty folder {folder}: {str(e)}")
    
    return removed_folders

def extract_course_number(course_name: str) -> int:
    """Extract course number for sorting"""
    match = re.search(r'(\d+)', course_name)
    return int(match.group(1)) if match else 999

# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def run_restore_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the restore processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_14_restore_pptx')
    
    # Extract settings from config
    file_types = page_config.get('file_types', ['pptx', 'summary', 'slides', 'transcripts'])
    target_courses = page_config.get('target_courses', [])
    cleanup_empty_folders_setting = page_config.get('cleanup_empty_folders', True)
    confirm_restoration = page_config.get('confirm_restoration', True)
    
    # Define file type mappings
    file_type_config = {
        'pptx': {
            'folder_name': 'all_pptx',
            'extensions': ['.pptx'],
            'description': 'PPTX files from all_pptx folders'
        },
        'summary': {
            'folder_name': 'all_summary',
            'extensions': ['.txt', '.md'],
            'description': 'Summary files from all_summary folders'
        },
        'slides': {
            'folder_name': 'all_slides',
            'extensions': ['.txt', '.md'],
            'description': 'Slide files from all_slides folders'
        },
        'transcripts': {
            'folder_name': 'all_transcripts',
            'extensions': ['.txt', '.md'],
            'description': 'Transcript files from all_transcripts folders'
        }
    }
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        console.print(f"[red]✗[/red] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_files": 0, "restored_count": 0, "error_count": 1}
        }
    
    console.print(f"[blue]ℹ[/blue] Scanning input directory: {input_dir}")
    console.print(f"[blue]ℹ[/blue] File types to restore: {', '.join(file_types)}")
    
    # Find files for each type
    all_course_files = {}
    total_files_found = 0
    
    for file_type in file_types:
        if file_type not in file_type_config:
            console.print(f"[yellow]⚠[/yellow] Unknown file type: {file_type}")
            continue
            
        config_info = file_type_config[file_type]
        console.print(f"[blue]ℹ[/blue] Scanning for {config_info['description']}...")
        
        course_files = find_files_by_type(config_info['folder_name'], config_info['extensions'])
        
        if course_files:
            file_count = sum(len(files) for files in course_files.values())
            console.print(f"[green]✓[/green] Found {file_count} {file_type} files across {len(course_files)} courses")
            all_course_files[file_type] = course_files
            total_files_found += file_count
        else:
            console.print(f"[blue]ℹ[/blue] No {file_type} files found in {config_info['folder_name']} folders")
    
    if not all_course_files:
        error_msg = "No files found to restore in any of the specified folders"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_files": 0, "restored_count": 0, "error_count": 0}
        }
    
    console.print(f"[green]✓[/green] Total files available for restoration: {total_files_found}")
    
    # If no specific courses configured, show available options and exit
    if not target_courses:
        console.print(f"[blue]ℹ[/blue] No specific courses configured for restoration")
        console.print(f"[blue]ℹ[/blue] Available files for restoration:")
        
        # Display available options
        table = Table(title="Available Files for Restoration")
        table.add_column("File Type", style="cyan")
        table.add_column("Course", style="magenta")
        table.add_column("Files", justify="right")
        table.add_column("Folder", style="dim")
        
        for file_type, course_files in all_course_files.items():
            config_info = file_type_config[file_type]
            sorted_courses = sorted(course_files.keys(), key=extract_course_number)
            
            for course in sorted_courses:
                file_count = len(course_files[course])
                table.add_row(
                    file_type.upper(),
                    course,
                    str(file_count),
                    config_info['folder_name']
                )
        
        console.print(table)
        console.print(f"[blue]ℹ[/blue] To restore files, configure 'target_courses' in config.json")
        
        # Get all unique courses
        all_courses = set()
        for course_files in all_course_files.values():
            all_courses.update(course_files.keys())
        
        return {
            "status": "info",
            "message": f"Found {total_files_found} files available for restoration",
            "statistics": {"total_files": total_files_found, "restored_count": 0, "error_count": 0},
            "available_courses": sorted(all_courses, key=extract_course_number),
            "file_types_found": list(all_course_files.keys())
        }
    
    # Filter by target courses
    filtered_course_files = {}
    total_selected_files = 0
    
    for file_type, course_files in all_course_files.items():
        filtered_files = {}
        for course in target_courses:
            if course in course_files:
                filtered_files[course] = course_files[course]
                total_selected_files += len(course_files[course])
        
        if filtered_files:
            filtered_course_files[file_type] = filtered_files
    
    if not filtered_course_files:
        error_msg = f"No files found for the configured target courses: {target_courses}"
        console.print(f"[yellow]⚠[/yellow] {error_msg}")
        return {
            "status": "warning",
            "message": error_msg,
            "statistics": {"total_files": total_files_found, "restored_count": 0, "error_count": 0}
        }
    
    console.print(f"[yellow]⚠[/yellow] Selected {total_selected_files} files for restoration from {len(target_courses)} courses")
    
    # Show what will be restored if verbose
    if ctx_obj.get('verbose', False):
        restoration_table = Table(title="Files Selected for Restoration")
        restoration_table.add_column("File Type", style="cyan")
        restoration_table.add_column("Course", style="magenta")
        restoration_table.add_column("Files", justify="right", style="green")
        
        for file_type, course_files in filtered_course_files.items():
            for course, files in course_files.items():
                restoration_table.add_row(
                    file_type.upper(),
                    course,
                    str(len(files))
                )
        
        console.print(restoration_table)
    
    # Confirmation check
    if confirm_restoration:
        console.print(f"[yellow]⚠[/yellow] This will restore files from processed folders back to their original locations")
        
        if not Confirm.ask("Are you sure you want to proceed with restoration?"):
            console.print(f"[yellow]Operation cancelled by user[/yellow]")
            return {
                "status": "cancelled",
                "message": "Restoration cancelled by user",
                "statistics": {"total_files": total_files_found, "restored_count": 0, "error_count": 0}
            }
    
    # Perform restoration
    all_results = []
    start_time = time.time()
    

    with DreamletProgress(description="Restoring files", total=total_selected_files) as progress:
        
        for file_type, course_files in filtered_course_files.items():
            config_info = file_type_config[file_type]
            progress.update(description=f"Restoring {file_type} files")
            
            # Restore files for this type
            results = restore_files(target_courses, course_files, config_info['folder_name'])
            
            # Add file type to results
            for result in results:
                result['file_type'] = file_type
                all_results.append(result)
            
            progress.update(advance=len(results))
    
    # Clean up empty folders if requested
    removed_folders = []
    if cleanup_empty_folders_setting:
        console.print(f"[blue]ℹ[/blue] Cleaning up empty folders...")
        
        for file_type, course_files in filtered_course_files.items():
            config_info = file_type_config[file_type]
            folders_removed = cleanup_empty_folders(target_courses, course_files, config_info['folder_name'])
            removed_folders.extend(folders_removed)
        
        if removed_folders:
            console.print(f"[green]✓[/green] Removed {len(removed_folders)} empty folders")
    
    # Calculate final statistics
    total_processing_time = time.time() - start_time
    success_count = sum(1 for r in all_results if r["status"] == "success")
    skipped_count = sum(1 for r in all_results if r["status"] == "skipped")
    error_count = sum(1 for r in all_results if r["status"] == "error")
    
    # Determine final status
    if error_count > 0 and success_count == 0:
        final_status = "error"
        status_message = f"File restoration failed with {error_count} errors"
    elif error_count > 0:
        final_status = "warning"
        status_message = f"Restored {success_count} files with {error_count} errors, {skipped_count} skipped"
    elif success_count == 0 and skipped_count > 0:
        final_status = "warning"
        status_message = f"All {skipped_count} files already exist at destination (skipped)"
    else:
        final_status = "success"
        status_message = f"Successfully restored {success_count} files, {skipped_count} skipped"
    
    # Show summary
    console.print(f"[green]✓[/green] {status_message}")
    console.print(f"[blue]ℹ[/blue] Total processing time: {total_processing_time:.1f} seconds")
    
    if error_count > 0:
        console.print(f"[red]✗[/red] Errors encountered: {error_count}")
    
    # Display detailed results if verbose
    if ctx_obj.get('verbose', False) and all_results:
        results_table = Table(title="Restoration Results")
        results_table.add_column("File Type", style="cyan")
        results_table.add_column("Course", style="magenta")
        results_table.add_column("File", style="blue")
        results_table.add_column("Status", style="bold")
        results_table.add_column("Message", style="dim")
        
        for result in all_results[:20]:  # Show first 20 results
            status_style = "green" if result["status"] == "success" else "red" if result["status"] == "error" else "yellow"
            status_text = result["status"].upper()
            
            results_table.add_row(
                result["file_type"].upper(),
                result["course"],
                result["file"][:30] + "..." if len(result["file"]) > 30 else result["file"],
                f"[{status_style}]{status_text}[/{status_style}]",
                result["message"][:50] + "..." if len(result["message"]) > 50 else result["message"]
            )
        
        console.print(results_table)
        
        if len(all_results) > 20:
            console.print(f"... and {len(all_results) - 20} more results")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "total_files_found": total_files_found,
            "file_types_processed": list(filtered_course_files.keys()),
            "target_courses": target_courses
        },
        "statistics": {
            "files_restored": success_count,
            "files_skipped": skipped_count,
            "errors": error_count,
            "empty_folders_removed": len(removed_folders),
            "processing_time": f"{total_processing_time:.1f}s"
        },
        "settings": {
            "file_types": file_types,
            "cleanup_empty_folders": cleanup_empty_folders_setting,
            "confirm_restoration": confirm_restoration,
            "target_courses": target_courses
        },
        "processing_results": [
            {
                "file_type": result["file_type"],
                "course": result["course"],
                "file": result["file"],
                "status": result["status"],
                "message": result["message"],
                "original_path": result["original_path"],
                "restored_path": result["restored_path"]
            }
            for result in all_results
        ],
        "removed_folders": removed_folders,
        "errors": [result["message"] for result in all_results if result["status"] == "error"]
    }
    
    # Generate report
    try:
        report_path = generate_report("14", "Restore Files", report_results)
        console.print(f"[blue]ℹ[/blue] Report saved to: {report_path}", style="dim")
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        console.print(f"[yellow]Continuing without report...[/yellow]")
        report_path = None
    
    report_results["report_path"] = report_path
    return report_results

# ============================================================================
# CLI COMMAND
# ============================================================================

@click.command()
@click.pass_context
def restore_files_cmd(ctx):
    """
    Restore files from processed folders back to their original locations
    
    This command restores files from their processed folders (all_pptx, all_slides, 
    all_transcripts, all_summary) back to their original locations. This reverses 
    the file movement performed by various processing steps.
    
    Features:
    - Restore PPTX files from all_pptx folders
    - Restore summary files from all_summary folders  
    - Restore slide files from all_slides folders
    - Restore transcript files from all_transcripts folders
    - Selective restoration by course and file type
    - Safety checks to prevent overwriting existing files
    - Automatic cleanup of empty processed folders
    - Comprehensive restoration reporting
    
    All settings are configured in config.json under "page_14_restore_pptx":
    - file_types: List of file types to restore (pptx, summary, slides, transcripts)
    - target_courses: List of course names to target (empty = show available)
    - cleanup_empty_folders: Remove empty folders after restoration (default: true)
    - confirm_restoration: Require confirmation before restoration (default: true)
    
    Examples:
        dreamlet run 14                    # Show available files for restoration
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
        
    To restore specific files, configure target_courses and file_types in config.json,
    then run the command again.
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be restored[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_14_restore_pptx')
        file_types = page_config.get('file_types', ['pptx', 'summary', 'slides', 'transcripts'])
        target_courses = page_config.get('target_courses', [])
        cleanup_empty_folders_setting = page_config.get('cleanup_empty_folders', True)
        
        console.print(f"Would restore file types: {file_types}")
        console.print(f"Would target courses: {target_courses if target_courses else 'None configured (would show available)'}")
        console.print(f"Would cleanup empty folders: {cleanup_empty_folders_setting}")
        console.print("Would scan for files in processed folders and restore to original locations")
        return
    
    # Run the restore processing operation
    try:
        results = run_restore_processing(ctx.obj)
        
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
    restore_files_cmd()