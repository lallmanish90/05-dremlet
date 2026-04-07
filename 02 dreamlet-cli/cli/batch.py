"""
Batch processing functionality for running multiple pages in sequence
"""

import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.text import Text
import time

from cli.progress import DreamletProgress, StatusManager
from cli.reports import generate_report

console = Console()

def parse_page_range(pages: Optional[str], start: Optional[int], end: Optional[int]) -> List[str]:
    """
    Parse page selection into a list of page numbers
    
    Args:
        pages: Comma-separated list of pages (e.g., "01,05,10")
        start: Start page number
        end: End page number
        
    Returns:
        List of page numbers as strings
    """
    if pages:
        # Parse comma-separated list
        page_list = []
        for page in pages.split(','):
            page = page.strip()
            if page:
                page_list.append(page.zfill(2))
        return page_list
    
    elif start is not None and end is not None:
        # Parse range
        return [str(i).zfill(2) for i in range(start, end + 1)]
    
    elif start is not None:
        # From start to end (14)
        return [str(i).zfill(2) for i in range(start, 15)]
    
    else:
        # All pages
        return [str(i).zfill(2) for i in range(1, 15)]

def get_page_info() -> Dict[str, Dict[str, str]]:
    """
    Get information about all available pages
    
    Returns:
        Dictionary mapping page numbers to page info
    """
    return {
        "02": {"name": "Rename", "description": "Standardize file naming conventions"},
        "03": {"name": "Save Text", "description": "Break transcripts into slide sections"},
        "04": {"name": "Remove Unwanted", "description": "Clean up unnecessary files"},
        "05": {"name": "Move Slides", "description": "Organize presentation files"},
        "06": {"name": "4K Image", "description": "Generate high-resolution images from PPTX/ZIP"},
        "07": {"name": "TTS Kokoro", "description": "Convert text to speech using Kokoro API"},
        "08": {"name": "Translator", "description": "Translate content to multiple languages"},
        "09": {"name": "Count New", "description": "Validate content alignment"},
        "10": {"name": "MP4 GPU", "description": "Create final videos with hardware acceleration"},
        "11": {"name": "Verify MP4", "description": "Quality assurance and validation"},
        "12": {"name": "Delete", "description": "File cleanup utilities"},
        "13": {"name": "Delete Folder", "description": "Folder management"},
        "14": {"name": "Restore PPTX", "description": "PowerPoint restoration tools"}
    }

def run_single_page(page_number: str, ctx_obj: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """
    Run a single page processing
    
    Args:
        page_number: Page number to run (e.g., "05")
        ctx_obj: Click context object
        force: Force execution even if outputs exist
        
    Returns:
        Processing results dictionary
    """
    page_info = get_page_info()
    
    if page_number not in page_info:
        return {
            "status": "error",
            "message": f"Invalid page number: {page_number}",
            "page_number": page_number
        }
    
    page_name = page_info[page_number]["name"]
    
    try:
        # Import and run the appropriate command
        if page_number == "02":
            from cli.commands.cmd_02_rename import run_rename_files
            return run_rename_files(ctx_obj, force)
        elif page_number == "03":
            from cli.commands.cmd_03_save_text import run_save_text
            return run_save_text(ctx_obj, force)
        elif page_number == "04":
            from cli.commands.cmd_04_remove_unwanted import run_remove_unwanted
            return run_remove_unwanted(ctx_obj, force)
        elif page_number == "05":
            from cli.commands.cmd_05_move_slides import run_move_slides
            return run_move_slides(ctx_obj, force)
        else:
            return {
                "status": "error",
                "message": f"Page {page_number} not yet implemented",
                "page_number": page_number
            }
    
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Page {page_number} command not available: {e}",
            "page_number": page_number
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error running page {page_number}: {e}",
            "page_number": page_number
        }

def run_batch_processing(ctx_obj: Dict[str, Any], pages: Optional[str], 
                        start: Optional[int], end: Optional[int], force: bool = False):
    """
    Run batch processing for multiple pages
    
    Args:
        ctx_obj: Click context object
        pages: Comma-separated list of pages
        start: Start page number
        end: End page number
        force: Force execution even if outputs exist
    """
    # Parse page selection
    page_list = parse_page_range(pages, start, end)
    page_info = get_page_info()
    
    if not page_list:
        console.print("[red]✗[/red] No pages selected for processing")
        return
    
    # Show batch processing plan
    console.print(f"\n[bold cyan]Batch Processing Plan[/bold cyan]")
    console.print(f"Pages to process: {len(page_list)}")
    
    plan_text = Text()
    for i, page_num in enumerate(page_list, 1):
        if page_num in page_info:
            plan_text.append(f"{i:2d}. ", style="dim")
            plan_text.append(f"Page {page_num}: ", style="yellow")
            plan_text.append(f"{page_info[page_num]['name']}\n", style="white")
        else:
            plan_text.append(f"{i:2d}. ", style="dim")
            plan_text.append(f"Page {page_num}: ", style="red")
            plan_text.append("Invalid page number\n", style="red")
    
    console.print(Panel(plan_text, title="Processing Plan", border_style="cyan"))
    
    # Confirm execution (unless in quiet mode)
    if not ctx_obj.get('quiet', False):
        try:
            confirm = console.input("\n[bold]Proceed with batch processing? [y/N]: [/bold]").strip().lower()
            if confirm not in ['y', 'yes']:
                console.print("Batch processing cancelled.")
                return
        except KeyboardInterrupt:
            console.print("\nBatch processing cancelled.")
            return
    
    # Execute batch processing
    console.print(f"\n[bold green]Starting Batch Processing[/bold green]")
    
    batch_results = []
    start_time = time.time()
    
    with Progress() as progress:
        batch_task = progress.add_task("[cyan]Batch Progress", total=len(page_list))
        
        for i, page_num in enumerate(page_list):
            # Update batch progress
            progress.update(batch_task, completed=i)
            
            if page_num in page_info:
                page_name = page_info[page_num]["name"]
                console.print(f"\n[bold]Processing Page {page_num}: {page_name}[/bold]")
                
                # Run the page
                result = run_single_page(page_num, ctx_obj, force)
                result["page_number"] = page_num
                result["page_name"] = page_name
                batch_results.append(result)
                
                # Show immediate result
                if result["status"] == "success":
                    console.print(f"[green]✓[/green] Page {page_num} completed successfully")
                elif result["status"] == "warning":
                    console.print(f"[yellow]⚠[/yellow] Page {page_num} completed with warnings")
                else:
                    console.print(f"[red]✗[/red] Page {page_num} failed: {result.get('message', 'Unknown error')}")
            else:
                # Invalid page number
                result = {
                    "status": "error",
                    "message": f"Invalid page number: {page_num}",
                    "page_number": page_num,
                    "page_name": "Unknown"
                }
                batch_results.append(result)
                console.print(f"[red]✗[/red] Invalid page number: {page_num}")
        
        # Complete batch progress
        progress.update(batch_task, completed=len(page_list))
    
    # Calculate batch statistics
    end_time = time.time()
    total_duration = end_time - start_time
    
    success_count = sum(1 for r in batch_results if r["status"] == "success")
    warning_count = sum(1 for r in batch_results if r["status"] == "warning")
    error_count = sum(1 for r in batch_results if r["status"] == "error")
    
    # Show batch summary
    console.print(f"\n[bold cyan]Batch Processing Complete[/bold cyan]")
    
    summary_text = Text()
    summary_text.append(f"Total Pages: {len(page_list)}\n", style="bold")
    summary_text.append(f"Successful: {success_count}\n", style="green")
    summary_text.append(f"Warnings: {warning_count}\n", style="yellow")
    summary_text.append(f"Errors: {error_count}\n", style="red")
    summary_text.append(f"Duration: {total_duration:.1f} seconds\n", style="dim")
    
    console.print(Panel(summary_text, title="Batch Summary", border_style="green"))
    
    # Show detailed results if there were errors or warnings
    if error_count > 0 or warning_count > 0:
        console.print("\n[bold]Detailed Results:[/bold]")
        
        for result in batch_results:
            if result["status"] in ["error", "warning"]:
                status_icon = "⚠" if result["status"] == "warning" else "✗"
                status_color = "yellow" if result["status"] == "warning" else "red"
                
                console.print(f"[{status_color}]{status_icon}[/{status_color}] "
                            f"Page {result['page_number']}: {result.get('message', 'No details')}")
    
    # Generate batch report
    batch_report_data = {
        "status": "success" if error_count == 0 else "error" if error_count > 0 else "warning",
        "statistics": {
            "total_pages": len(page_list),
            "successful_pages": success_count,
            "warning_pages": warning_count,
            "error_pages": error_count,
            "duration_seconds": total_duration
        },
        "processing_results": batch_results,
        "input_stats": {
            "pages_requested": ", ".join(page_list),
            "force_mode": force
        }
    }
    
    report_path = generate_report("batch", "Batch Processing", batch_report_data)
    console.print(f"\n[dim]📄 Batch report saved to: {report_path}[/dim]")
    
    # Exit with appropriate code
    if error_count > 0:
        sys.exit(1)
    elif warning_count > 0:
        sys.exit(2)
    else:
        sys.exit(0)