#!/usr/bin/env python3
"""
Fix problematic folder structure in the input directory
"""

import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

def fix_folder_structure():
    """Fix the problematic folder structure"""
    
    input_dir = Path("input")
    
    # Define the problematic folders and their better names
    folder_mappings = {
        "107 Artificial Intelligence Theoretical Foundations & Advanced Models": "course_107_ai_foundations",
        "14 Artificial Intelligence in Cybersecurity": "course_14_ai_cybersecurity"
    }
    
    console.print("[bold cyan]🔧 Fixing Folder Structure[/bold cyan]")
    console.print("\nProblematic folder names found:")
    
    for old_name, new_name in folder_mappings.items():
        old_path = input_dir / old_name
        new_path = input_dir / new_name
        
        if old_path.exists():
            console.print(f"[red]❌ {old_name}[/red]")
            console.print(f"[green]✅ {new_name}[/green]")
            console.print()
    
    # Ask for confirmation
    if not Confirm.ask("\nProceed with renaming these folders?"):
        console.print("Operation cancelled.")
        return
    
    # Perform the renaming
    console.print("\n[bold]Renaming folders...[/bold]")
    
    for old_name, new_name in folder_mappings.items():
        old_path = input_dir / old_name
        new_path = input_dir / new_name
        
        if old_path.exists():
            try:
                # Rename the folder
                old_path.rename(new_path)
                console.print(f"[green]✓[/green] Renamed: {old_name} → {new_name}")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to rename {old_name}: {e}")
        else:
            console.print(f"[yellow]⚠[/yellow] Folder not found: {old_name}")
    
    console.print("\n[bold green]✅ Folder structure fixed![/bold green]")
    console.print("\nNew structure:")
    
    # Show the new structure
    for folder in input_dir.iterdir():
        if folder.is_dir():
            console.print(f"  📁 {folder.name}")

if __name__ == "__main__":
    fix_folder_structure()