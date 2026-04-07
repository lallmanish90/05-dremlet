#!/usr/bin/env python3
"""
Dreamlet Educational Video Production System - CLI Interface

Main entry point for the command-line interface version of the Dreamlet system.
Converts the existing Streamlit application to a CLI while maintaining 100% functional parity.
"""

import click
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add the project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

console = Console()

@click.group()
@click.version_option(version="1.0.0", prog_name="Dreamlet CLI")
@click.pass_context
def cli(ctx):
    """
    Dreamlet Educational Video Production System - CLI Interface
    
    A comprehensive tool for automating educational video production workflows,
    from content processing to final video generation.
    
    All settings are managed through config.json file.
    Use 'dreamlet config create' to create a default configuration file.
    
    Use 'dreamlet COMMAND' to run specific processing pages.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration from config.json
    from cli.config import load_config
    config = load_config()
    
    # Store config in context
    ctx.obj['config'] = config
    ctx.obj['verbose'] = config.verbose
    
    # Create necessary directories
    os.makedirs('reports', exist_ok=True)
    os.makedirs(config.input_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)
    
    # Show welcome message (unless quiet mode)
    welcome_text = Text()
    welcome_text.append("🎬 Dreamlet Educational Video Production System\n", style="bold cyan")
    welcome_text.append("CLI Interface - Convert educational content to professional videos", style="dim")
    welcome_text.append(f"\nConfiguration loaded from: config.json", style="dim")
    
    console.print(Panel(
        welcome_text,
        title="Welcome",
        border_style="cyan"
    ))

@cli.group()
@click.pass_context
def run(ctx):
    """Run processing pages (01-14)"""
    pass

@cli.group()
@click.pass_context
def report(ctx):
    """View and manage processing reports"""
    pass

@cli.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings"""
    pass

@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration"""
    from cli.utils import show_system_status
    show_system_status(ctx.obj)

@config.command()
@click.pass_context
def create(ctx):
    """Create a default config.json file"""
    from cli.config import create_default_config
    config_file = create_default_config()
    if config_file:
        console.print(f"[green]✓[/green] Created default configuration file: {config_file}")
        console.print("Edit this file to customize your settings.")
    else:
        console.print("[red]✗[/red] Failed to create configuration file")

@config.command()
@click.pass_context
def show(ctx):
    """Show current configuration"""
    config = ctx.obj['config']
    
    console.print("\n[bold cyan]Current Configuration:[/bold cyan]")
    console.print(f"Input Directory: {config.input_dir}")
    console.print(f"Output Directory: {config.output_dir}")
    console.print(f"Reports Directory: {config.reports_dir}")
    console.print(f"Verbose Mode: {config.verbose}")
    console.print(f"Skip Existing: {config.skip_existing}")
    console.print(f"Dry Run Mode: {config.dry_run}")
    
    console.print("\n[bold cyan]Page-Specific Settings:[/bold cyan]")
    for page_name, settings in config.page_settings.items():
        console.print(f"\n[yellow]{page_name}:[/yellow]")
        for key, value in settings.items():
            console.print(f"  {key}: {value}")

@config.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.pass_context
def load(ctx, config_file):
    """Load configuration from a specific file"""
    from cli.config import load_config
    try:
        config = load_config(config_file)
        ctx.obj['config'] = config
        console.print(f"[green]✓[/green] Loaded configuration from: {config_file}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load configuration: {e}")

# Import and register all page commands
def register_commands():
    """Register all page commands with the CLI"""
    try:
        # Import implemented page commands
        from cli.commands import (
            cmd_02_rename, cmd_03_save_text, cmd_04_remove_unwanted, cmd_05_move_slides, 
            cmd_06_4k_image, cmd_07_tts_kokoro, cmd_08_translator, cmd_09_count_new, cmd_10_mp4_gpu, 
            cmd_11_verify_mp4, cmd_12_delete, cmd_13_delete_folder, cmd_14_restore_pptx
        )
        
        # Register implemented page commands
        run.add_command(cmd_02_rename.rename_files_cmd, name='02')
        run.add_command(cmd_03_save_text.save_text, name='03')
        run.add_command(cmd_04_remove_unwanted.remove_unwanted, name='04')
        run.add_command(cmd_05_move_slides.move_slides, name='05')
        run.add_command(cmd_06_4k_image.process_4k_images, name='06')
        run.add_command(cmd_07_tts_kokoro.tts_kokoro, name='07')
        run.add_command(cmd_08_translator.translate_lm_studio, name='08')
        run.add_command(cmd_09_count_new.count_validate, name='09')
        run.add_command(cmd_10_mp4_gpu.mp4_gpu, name='10')
        run.add_command(cmd_11_verify_mp4.verify_mp4, name='11')
        run.add_command(cmd_12_delete.delete_lectures, name='12')
        run.add_command(cmd_13_delete_folder.delete_folders_cmd, name='13')
        run.add_command(cmd_14_restore_pptx.restore_files_cmd, name='14')
        
        # Register report commands
        from cli.commands import report_commands
        report.add_command(report_commands.view_report, name='view')
        report.add_command(report_commands.list_reports, name='list')
        report.add_command(report_commands.clean_reports, name='clean')
        report.add_command(report_commands.combine_reports, name='combine')
        
    except ImportError as e:
        # Commands not yet implemented - this is expected during initial setup
        console.print(f"[yellow]Note: Some commands not yet available ({e})[/yellow]")

@cli.command()
@click.argument('pages', required=False)
@click.option('--start', type=int, help='Start page number')
@click.option('--end', type=int, help='End page number')
@click.option('--force', is_flag=True, help='Force execution even if outputs exist')
@click.option('--quiet', is_flag=True, help='Skip confirmation prompts')
@click.pass_context
def run_all(ctx, pages, start, end, force, quiet):
    """
    Run multiple pages in sequence
    
    PAGES can be:
    - Comma-separated list: 02,05,08
    - Range: 02-08
    - Single page: 05
    - If not specified, runs all available pages
    """
    from cli.batch import run_batch_processing
    # Set quiet mode in context
    ctx.obj['quiet'] = quiet
    run_batch_processing(ctx.obj, pages, start, end, force)

if __name__ == '__main__':
    # Register commands before running CLI
    register_commands()
    cli()