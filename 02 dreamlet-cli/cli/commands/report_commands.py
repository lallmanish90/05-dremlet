"""
CLI Commands for report management

Provides commands to view, list, and manage processing reports
"""

import click
import os
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.pager import Pager

from cli.reports import list_reports

console = Console()

@click.command()
@click.argument('page_number', required=False)
@click.option('--pager', is_flag=True, help='Use pager for long reports')
@click.option('--raw', is_flag=True, help='Show raw markdown without formatting')
@click.pass_context
def view_report(ctx, page_number, pager, raw):
    """
    View a processing report
    
    PAGE_NUMBER: The page number to view (e.g., 05, 10, batch)
    
    Examples:
        dreamlet report view 05        # View page 05 report
        dreamlet report view batch     # View batch processing report
        dreamlet report view 10 --pager  # Use pager for long report
    """
    
    if not page_number:
        # Interactive selection
        reports = list_reports()
        if not reports:
            console.print("[yellow]No reports found[/yellow]")
            console.print("Run some processing pages first to generate reports")
            return
        
        console.print("\n[bold cyan]Available Reports:[/bold cyan]")
        for i, report in enumerate(reports, 1):
            console.print(f"  [yellow]{i}[/yellow]. Page {report['page_number']}: {report['page_name']} ({report['modified']})")
        
        try:
            selection = console.input("\n[bold]Select report number (or 'q' to quit): [/bold]").strip()
            if selection.lower() == 'q':
                return
            
            index = int(selection) - 1
            if 0 <= index < len(reports):
                page_number = reports[index]['page_number']
            else:
                console.print(f"[red]Invalid selection: {selection}[/red]")
                return
        except (ValueError, KeyboardInterrupt):
            console.print("Cancelled.")
            return
    
    # Find the report file
    reports = list_reports()
    report_file = None
    
    for report in reports:
        if report['page_number'] == page_number:
            report_file = report['path']
            break
    
    if not report_file or not os.path.exists(report_file):
        console.print(f"[red]Report not found for page {page_number}[/red]")
        console.print("Available reports:")
        for report in reports:
            console.print(f"  - Page {report['page_number']}: {report['page_name']}")
        return
    
    # Read and display the report
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if raw:
            # Show raw markdown
            if pager:
                with console.pager():
                    console.print(content)
            else:
                console.print(content)
        else:
            # Show formatted markdown
            markdown = Markdown(content)
            if pager:
                with console.pager():
                    console.print(markdown)
            else:
                console.print(markdown)
    
    except Exception as e:
        console.print(f"[red]Error reading report: {e}[/red]")

@click.command()
@click.option('--sort', type=click.Choice(['page', 'name', 'date']), default='page', 
              help='Sort reports by page number, name, or date')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.pass_context
def list_reports(ctx, sort, reverse):
    """
    List all available processing reports
    
    Shows a table of all generated reports with their status and metadata.
    
    Examples:
        dreamlet report list              # List all reports
        dreamlet report list --sort date  # Sort by modification date
        dreamlet report list --reverse    # Reverse sort order
    """
    
    reports = list_reports()
    
    if not reports:
        console.print("[yellow]No reports found[/yellow]")
        console.print("Run some processing pages first to generate reports")
        console.print("\nExample: dreamlet run 05")
        return
    
    # Sort reports
    if sort == 'page':
        reports.sort(key=lambda x: x['page_number'], reverse=reverse)
    elif sort == 'name':
        reports.sort(key=lambda x: x['page_name'], reverse=reverse)
    elif sort == 'date':
        reports.sort(key=lambda x: x['modified'], reverse=reverse)
    
    # Create table
    table = Table(title=f"Processing Reports ({len(reports)} found)")
    table.add_column("Page", style="cyan", width=6)
    table.add_column("Name", style="white", min_width=20)
    table.add_column("Modified", style="dim", width=19)
    table.add_column("Size", style="yellow", width=10)
    table.add_column("File", style="dim")
    
    for report in reports:
        table.add_row(
            report['page_number'],
            report['page_name'],
            report['modified'],
            report['size'],
            report['filename']
        )
    
    console.print(table)
    
    # Show usage hint
    console.print(f"\n[dim]💡 Use 'dreamlet report view <page>' to view a specific report[/dim]")

@click.command()
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.option('--keep', type=int, help='Keep only the N most recent reports')
@click.argument('pages', nargs=-1)
@click.pass_context
def clean_reports(ctx, confirm, keep, pages):
    """
    Clean up old or specific processing reports
    
    PAGES: Specific page numbers to clean (optional)
    
    Examples:
        dreamlet report clean             # Clean all reports (with confirmation)
        dreamlet report clean --confirm   # Clean all reports without confirmation
        dreamlet report clean --keep 5    # Keep only 5 most recent reports
        dreamlet report clean 05 10       # Clean only page 05 and 10 reports
    """
    
    reports = list_reports()
    
    if not reports:
        console.print("[yellow]No reports found to clean[/yellow]")
        return
    
    # Determine which reports to clean
    if pages:
        # Clean specific pages
        reports_to_clean = [r for r in reports if r['page_number'] in pages]
        if not reports_to_clean:
            console.print(f"[yellow]No reports found for pages: {', '.join(pages)}[/yellow]")
            return
    elif keep:
        # Keep only N most recent reports
        reports.sort(key=lambda x: x['modified'], reverse=True)
        reports_to_clean = reports[keep:]
    else:
        # Clean all reports
        reports_to_clean = reports
    
    if not reports_to_clean:
        console.print("[yellow]No reports to clean[/yellow]")
        return
    
    # Show what will be cleaned
    console.print(f"\n[bold red]Reports to be deleted ({len(reports_to_clean)}):[/bold red]")
    for report in reports_to_clean:
        console.print(f"  - Page {report['page_number']}: {report['page_name']} ({report['modified']})")
    
    # Confirmation
    if not confirm:
        try:
            response = console.input(f"\n[bold]Delete {len(reports_to_clean)} reports? [y/N]: [/bold]").strip().lower()
            if response not in ['y', 'yes']:
                console.print("Cancelled.")
                return
        except KeyboardInterrupt:
            console.print("\nCancelled.")
            return
    
    # Delete reports
    deleted_count = 0
    errors = []
    
    for report in reports_to_clean:
        try:
            os.remove(report['path'])
            deleted_count += 1
            console.print(f"[dim]Deleted: {report['filename']}[/dim]")
        except Exception as e:
            errors.append(f"Failed to delete {report['filename']}: {e}")
    
    # Show results
    if deleted_count > 0:
        console.print(f"\n[green]✓[/green] Deleted {deleted_count} reports")
    
    if errors:
        console.print(f"\n[red]Errors ({len(errors)}):[/red]")
        for error in errors:
            console.print(f"  - {error}")

@click.command()
@click.option('--output', '-o', help='Output file path for combined report')
@click.option('--format', type=click.Choice(['markdown', 'html']), default='markdown',
              help='Output format')
@click.argument('pages', nargs=-1)
@click.pass_context
def combine_reports(ctx, output, format, pages):
    """
    Combine multiple reports into a single document
    
    PAGES: Page numbers to combine (if not specified, combines all)
    
    Examples:
        dreamlet report combine                    # Combine all reports
        dreamlet report combine 05 06 07          # Combine specific pages
        dreamlet report combine -o summary.md     # Save to specific file
        dreamlet report combine --format html     # Generate HTML output
    """
    
    reports = list_reports()
    
    if not reports:
        console.print("[yellow]No reports found to combine[/yellow]")
        return
    
    # Filter reports if specific pages requested
    if pages:
        reports = [r for r in reports if r['page_number'] in pages]
        if not reports:
            console.print(f"[yellow]No reports found for pages: {', '.join(pages)}[/yellow]")
            return
    
    # Sort reports by page number
    reports.sort(key=lambda x: x['page_number'])
    
    # Generate output filename if not provided
    if not output:
        if pages:
            page_list = "_".join(pages)
            output = f"combined_report_{page_list}.{format.lower()}"
        else:
            output = f"combined_report_all.{format.lower()}"
    
    console.print(f"Combining {len(reports)} reports into {output}...")
    
    try:
        with open(output, 'w', encoding='utf-8') as f:
            if format == 'html':
                # HTML format
                f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                f.write("<title>Dreamlet Processing Reports</title>\n")
                f.write("<style>body{font-family:Arial,sans-serif;margin:40px;}</style>\n")
                f.write("</head>\n<body>\n")
                f.write("<h1>Dreamlet Processing Reports</h1>\n")
                f.write(f"<p>Generated: {reports[0]['modified']}</p>\n")
            else:
                # Markdown format
                f.write("# Dreamlet Processing Reports\n\n")
                f.write(f"**Generated**: {reports[0]['modified']}\n\n")
                f.write("---\n\n")
            
            # Add each report
            for i, report in enumerate(reports):
                if format == 'html':
                    f.write(f"<h2>Page {report['page_number']}: {report['page_name']}</h2>\n")
                else:
                    f.write(f"## Page {report['page_number']}: {report['page_name']}\n\n")
                
                # Read and include report content
                with open(report['path'], 'r', encoding='utf-8') as report_file:
                    content = report_file.read()
                    
                    if format == 'html':
                        # Convert markdown to HTML (basic conversion)
                        content = content.replace('\n', '<br>\n')
                        content = content.replace('**', '<strong>').replace('**', '</strong>')
                        content = content.replace('*', '<em>').replace('*', '</em>')
                        f.write(f"<div>{content}</div>\n")
                    else:
                        f.write(content)
                        f.write("\n\n---\n\n")
            
            if format == 'html':
                f.write("</body>\n</html>\n")
        
        console.print(f"[green]✓[/green] Combined report saved to: {output}")
        
    except Exception as e:
        console.print(f"[red]Error creating combined report: {e}[/red]")