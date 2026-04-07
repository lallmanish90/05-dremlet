"""
Rich progress bar utilities for CLI interface

Provides consistent progress tracking across all commands,
replacing Streamlit progress bars with rich terminal equivalents.
"""

from typing import Optional, Callable, Any
from rich.progress import (
    Progress, 
    TaskID, 
    BarColumn, 
    TextColumn, 
    TimeRemainingColumn,
    TimeElapsedColumn,
    SpinnerColumn,
    MofNCompleteColumn
)
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
import time

console = Console()

class DreamletProgress:
    """
    Custom progress manager for Dreamlet CLI operations
    
    Provides consistent progress tracking with rich terminal output,
    replacing Streamlit's progress bars and status messages.
    """
    
    def __init__(self, description: str = "Processing", total: Optional[int] = None):
        self.description = description
        self.total = total
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn() if total else TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn() if total else TextColumn(""),
            console=console,
            expand=True
        )
        self.task_id: Optional[TaskID] = None
        self.is_started = False
    
    def start(self) -> 'DreamletProgress':
        """Start the progress tracking"""
        if not self.is_started:
            self.progress.start()
            self.task_id = self.progress.add_task(
                self.description, 
                total=self.total
            )
            self.is_started = True
        return self
    
    def update(self, advance: Optional[int] = None, completed: Optional[int] = None, 
               description: Optional[str] = None, **kwargs):
        """Update progress"""
        if self.task_id is not None:
            update_kwargs = {}
            if advance is not None:
                update_kwargs['advance'] = advance
            if completed is not None:
                update_kwargs['completed'] = completed
            if description is not None:
                update_kwargs['description'] = description
            update_kwargs.update(kwargs)
            
            self.progress.update(self.task_id, **update_kwargs)
    
    def set_total(self, total: int):
        """Set or update the total for the progress bar"""
        self.total = total
        if self.task_id is not None:
            self.progress.update(self.task_id, total=total)
    
    def finish(self, message: Optional[str] = None):
        """Complete the progress and optionally show a completion message"""
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=self.total or 100)
        
        if self.is_started:
            self.progress.stop()
            self.is_started = False
        
        if message:
            console.print(f"[green]✓[/green] {message}")
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

class StatusManager:
    """
    Status message manager for CLI operations
    
    Replaces Streamlit's st.info(), st.success(), st.error(), st.warning()
    with rich console equivalents.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.console = Console()
    
    def info(self, message: str, verbose_only: bool = False):
        """Display info message (replaces st.info)"""
        if not verbose_only or self.verbose:
            self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def success(self, message: str):
        """Display success message (replaces st.success)"""
        self.console.print(f"[green]✓[/green] {message}")
    
    def warning(self, message: str):
        """Display warning message (replaces st.warning)"""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def error(self, message: str):
        """Display error message (replaces st.error)"""
        self.console.print(f"[red]✗[/red] {message}")
    
    def debug(self, message: str):
        """Display debug message (only in verbose mode)"""
        if self.verbose:
            self.console.print(f"[dim]🔍 {message}[/dim]")

def create_file_progress(files: list, description: str = "Processing files") -> DreamletProgress:
    """
    Create a progress bar for file processing operations
    
    Args:
        files: List of files to process
        description: Description for the progress bar
        
    Returns:
        DreamletProgress instance configured for file processing
    """
    return DreamletProgress(description=description, total=len(files))

def create_step_progress(steps: list, description: str = "Processing steps") -> DreamletProgress:
    """
    Create a progress bar for step-by-step operations
    
    Args:
        steps: List of steps to process
        description: Description for the progress bar
        
    Returns:
        DreamletProgress instance configured for step processing
    """
    return DreamletProgress(description=description, total=len(steps))

def show_processing_summary(title: str, stats: dict, verbose: bool = False):
    """
    Display a processing summary panel
    
    Args:
        title: Title for the summary panel
        stats: Dictionary of statistics to display
        verbose: Whether to show detailed information
    """
    summary_text = Text()
    
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            summary_text.append(f"{key}: ", style="bold")
            summary_text.append(f"{value}\n", style="cyan")
        else:
            summary_text.append(f"{key}: ", style="bold")
            summary_text.append(f"{value}\n")
    
    console.print(Panel(
        summary_text,
        title=f"📊 {title}",
        border_style="green"
    ))

def show_error_summary(title: str, errors: list):
    """
    Display an error summary panel
    
    Args:
        title: Title for the error panel
        errors: List of error messages
    """
    if not errors:
        return
    
    error_text = Text()
    for i, error in enumerate(errors, 1):
        error_text.append(f"{i}. ", style="bold red")
        error_text.append(f"{error}\n")
    
    console.print(Panel(
        error_text,
        title=f"❌ {title}",
        border_style="red"
    ))

# Compatibility functions for existing Streamlit code
def st_progress_replacement(value: float) -> None:
    """
    Replacement for st.progress() calls in existing code
    This is a simple fallback - ideally code should use DreamletProgress
    """
    # This is a simple implementation - in practice, the calling code
    # should be refactored to use DreamletProgress properly
    pass

def st_info_replacement(message: str) -> None:
    """Replacement for st.info() calls"""
    console.print(f"[blue]ℹ[/blue] {message}")

def st_success_replacement(message: str) -> None:
    """Replacement for st.success() calls"""
    console.print(f"[green]✓[/green] {message}")

def st_error_replacement(message: str) -> None:
    """Replacement for st.error() calls"""
    console.print(f"[red]✗[/red] {message}")

def st_warning_replacement(message: str) -> None:
    """Replacement for st.warning() calls"""
    console.print(f"[yellow]⚠[/yellow] {message}")