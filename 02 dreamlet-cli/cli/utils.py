"""
Utility functions for CLI operations

Common utilities shared across CLI commands
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import platform
import psutil

console = Console()

def show_system_status(ctx_obj: Dict[str, Any]):
    """
    Display system status and configuration information
    
    Args:
        ctx_obj: Click context object containing global options
    """
    # System information
    system_info = Table(title="System Information")
    system_info.add_column("Component", style="cyan")
    system_info.add_column("Value", style="white")
    
    system_info.add_row("Operating System", platform.system())
    system_info.add_row("Platform", platform.platform())
    system_info.add_row("Python Version", platform.python_version())
    system_info.add_row("CPU Cores", str(psutil.cpu_count()))
    
    # Memory info
    memory = psutil.virtual_memory()
    system_info.add_row("Total Memory", f"{memory.total / (1024**3):.1f} GB")
    system_info.add_row("Available Memory", f"{memory.available / (1024**3):.1f} GB")
    
    console.print(system_info)
    console.print()
    
    # Directory status
    dir_status = Table(title="Directory Status")
    dir_status.add_column("Directory", style="cyan")
    dir_status.add_column("Status", style="white")
    dir_status.add_column("Files", style="yellow")
    
    directories = ["input", "output", "reports", "config"]
    for directory in directories:
        if os.path.exists(directory):
            file_count = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
            dir_status.add_row(directory, "✓ Exists", str(file_count))
        else:
            dir_status.add_row(directory, "✗ Missing", "0")
    
    console.print(dir_status)
    console.print()
    
    # Configuration status
    config_text = Text()
    config_text.append("Configuration File: ", style="bold")
    
    config_file = ctx_obj.get('config_file', 'config.yaml')
    if config_file and os.path.exists(config_file):
        config_text.append(f"✓ {config_file}", style="green")
    else:
        config_text.append("✗ Not found (using defaults)", style="yellow")
    
    config_text.append("\nVerbose Mode: ", style="bold")
    config_text.append("✓ Enabled" if ctx_obj.get('verbose') else "✗ Disabled", 
                      style="green" if ctx_obj.get('verbose') else "dim")
    
    config_text.append("\nQuiet Mode: ", style="bold")
    config_text.append("✓ Enabled" if ctx_obj.get('quiet') else "✗ Disabled", 
                      style="green" if ctx_obj.get('quiet') else "dim")
    
    console.print(Panel(config_text, title="Configuration Status", border_style="blue"))

def validate_input_directory() -> bool:
    """
    Validate that the input directory exists and contains expected structure
    
    Returns:
        True if input directory is valid, False otherwise
    """
    input_dir = Path("input")
    
    if not input_dir.exists():
        console.print("[red]✗[/red] Input directory does not exist")
        console.print("  Run: mkdir input")
        return False
    
    if not input_dir.is_dir():
        console.print("[red]✗[/red] 'input' exists but is not a directory")
        return False
    
    # Check for course directories
    course_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    
    if not course_dirs:
        console.print("[yellow]⚠[/yellow] Input directory is empty")
        console.print("  Add course directories to input/ to begin processing")
        return False
    
    console.print(f"[green]✓[/green] Input directory contains {len(course_dirs)} course(s)")
    return True

def ensure_output_directories():
    """Ensure all necessary output directories exist"""
    directories = ["output", "reports", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def get_course_list() -> List[str]:
    """
    Get list of available courses from input directory
    
    Returns:
        List of course directory names
    """
    input_dir = Path("input")
    
    if not input_dir.exists():
        return []
    
    return [d.name for d in input_dir.iterdir() if d.is_dir()]

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def count_files_by_extension(directory: Path, extensions: List[str]) -> Dict[str, int]:
    """
    Count files by extension in a directory
    
    Args:
        directory: Directory to scan
        extensions: List of extensions to count (e.g., ['.md', '.txt'])
        
    Returns:
        Dictionary mapping extensions to counts
    """
    counts = {ext: 0 for ext in extensions}
    
    if not directory.exists():
        return counts
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in counts:
                counts[ext] += 1
    
    return counts

def show_processing_summary(page_number: str, page_name: str, results: Dict[str, Any]):
    """
    Show a standardized processing summary
    
    Args:
        page_number: Page number (e.g., "05")
        page_name: Page name (e.g., "Move Slides")
        results: Processing results dictionary
    """
    # Create summary panel
    summary_text = Text()
    summary_text.append(f"Page {page_number}: {page_name}\n", style="bold cyan")
    
    # Status
    status = results.get("status", "Unknown")
    if status.lower() in ["success", "completed"]:
        summary_text.append("Status: ", style="bold")
        summary_text.append("✓ Success\n", style="green")
    elif status.lower() in ["warning"]:
        summary_text.append("Status: ", style="bold")
        summary_text.append("⚠ Warning\n", style="yellow")
    else:
        summary_text.append("Status: ", style="bold")
        summary_text.append("✗ Error\n", style="red")
    
    # Statistics
    if "statistics" in results:
        summary_text.append("\nStatistics:\n", style="bold")
        for key, value in results["statistics"].items():
            summary_text.append(f"  {key}: ", style="dim")
            summary_text.append(f"{value}\n", style="white")
    
    # Files processed
    if "files_processed" in results:
        summary_text.append(f"\nFiles Processed: {results['files_processed']}", style="bold")
    
    console.print(Panel(summary_text, title="Processing Complete", border_style="green"))
    
    # Show report location
    report_path = results.get("report_path")
    if report_path:
        console.print(f"[dim]📄 Detailed report saved to: {report_path}[/dim]")

def check_dependencies() -> Dict[str, bool]:
    """
    Check if required system dependencies are available
    
    Returns:
        Dictionary mapping dependency names to availability status
    """
    dependencies = {}
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        dependencies['ffmpeg'] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        dependencies['ffmpeg'] = False
    
    # Check LibreOffice
    try:
        result = subprocess.run(['soffice', '--version'], 
                              capture_output=True, text=True, timeout=5)
        dependencies['libreoffice'] = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        dependencies['libreoffice'] = False
    
    # Check pdftoppm (part of poppler-utils)
    try:
        result = subprocess.run(['pdftoppm', '-h'], 
                              capture_output=True, text=True, timeout=5)
        dependencies['pdftoppm'] = result.returncode == 0 or result.returncode == 1  # Help returns 1
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        dependencies['pdftoppm'] = False
    
    return dependencies

def show_dependency_status():
    """Show the status of system dependencies"""
    dependencies = check_dependencies()
    
    dep_table = Table(title="System Dependencies")
    dep_table.add_column("Dependency", style="cyan")
    dep_table.add_column("Status", style="white")
    dep_table.add_column("Purpose", style="dim")
    
    dep_info = {
        'ffmpeg': 'Video/audio processing',
        'libreoffice': 'PowerPoint to PDF conversion',
        'pdftoppm': 'PDF to image conversion'
    }
    
    for dep, available in dependencies.items():
        status = "✓ Available" if available else "✗ Missing"
        style = "green" if available else "red"
        dep_table.add_row(dep, f"[{style}]{status}[/{style}]", dep_info.get(dep, ""))
    
    console.print(dep_table)
    
    # Show installation hints for missing dependencies
    missing = [dep for dep, available in dependencies.items() if not available]
    if missing:
        console.print()
        console.print("[yellow]⚠ Missing dependencies detected[/yellow]")
        console.print("Install missing dependencies:")
        
        if platform.system() == "Darwin":  # macOS
            console.print("  brew install ffmpeg poppler libreoffice")
        elif platform.system() == "Linux":
            console.print("  sudo apt install ffmpeg poppler-utils libreoffice")
        else:  # Windows
            console.print("  Please install FFmpeg, Poppler, and LibreOffice manually")

def interactive_page_selection() -> str:
    """
    Interactive page selection for CLI
    
    Returns:
        Selected page number as string
    """
    pages = {
        "02": "Rename - Standardize file naming conventions", 
        "03": "Save Text - Break transcripts into slide sections",
        "04": "Remove Unwanted - Clean up unnecessary files",
        "05": "Move Slides - Organize presentation files",
        "06": "4K Image - Generate high-resolution images from PPTX/ZIP (Not yet implemented)",
        "07": "TTS Kokoro - Convert text to speech using Kokoro API (Not yet implemented)",
        "08": "Translator - Translate content to multiple languages (Not yet implemented)",
        "09": "Count New - Validate content alignment (Not yet implemented)",
        "10": "MP4 GPU - Create final videos with hardware acceleration (Not yet implemented)",
        "11": "Verify MP4 - Quality assurance and validation (Not yet implemented)",
        "12": "Delete - File cleanup utilities (Not yet implemented)",
        "13": "Delete Folder - Folder management (Not yet implemented)",
        "14": "Restore PPTX - PowerPoint restoration tools (Not yet implemented)"
    }
    
    console.print("\n[bold cyan]Available Processing Pages:[/bold cyan]")
    
    for page_num, description in pages.items():
        console.print(f"  [yellow]{page_num}[/yellow]: {description}")
    
    console.print()
    
    while True:
        try:
            selection = console.input("[bold]Select page number (or 'q' to quit): [/bold]").strip()
            
            if selection.lower() == 'q':
                console.print("Cancelled.")
                sys.exit(0)
            
            if selection in pages:
                return selection
            else:
                console.print(f"[red]Invalid selection: {selection}[/red]")
                console.print("Please enter a valid page number from the list above.")
        
        except KeyboardInterrupt:
            console.print("\nCancelled.")
            sys.exit(0)