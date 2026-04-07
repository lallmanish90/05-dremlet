"""
Markdown report generation system

Generates standardized markdown reports for each processing page,
replacing Streamlit's visual output with structured documentation.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

class ReportGenerator:
    """
    Generates standardized markdown reports for processing operations
    
    Each report follows a consistent template and includes:
    - Execution summary with timing
    - Input analysis
    - Processing results
    - Statistics and metrics
    - Error/warning details
    - Output file listings
    """
    
    def __init__(self, page_number: str, page_name: str, output_dir: str = "reports"):
        self.page_number = page_number
        self.page_name = page_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Report data
        self.start_time = datetime.now()
        self.end_time = None
        self.status = "Running"
        self.input_stats = {}
        self.processing_results = []
        self.statistics = {}
        self.errors = []
        self.warnings = []
        self.output_files = []
        
    def set_input_stats(self, **stats):
        """Set input analysis statistics"""
        self.input_stats.update(stats)
    
    def add_processing_result(self, result: Dict[str, Any]):
        """Add a processing result entry"""
        self.processing_results.append(result)
    
    def set_statistics(self, **stats):
        """Set processing statistics"""
        self.statistics.update(stats)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def add_output_file(self, file_path: str, description: str = ""):
        """Add an output file entry"""
        self.output_files.append({
            "path": file_path,
            "description": description,
            "size": self._get_file_size(file_path)
        })
    
    def set_status(self, status: str):
        """Set the final processing status"""
        self.status = status
        if status in ["Success", "Completed", "Warning"]:
            self.end_time = datetime.now()
    
    def _get_file_size(self, file_path: str) -> str:
        """Get human-readable file size"""
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except OSError:
            return "Unknown"
    
    def _format_duration(self) -> str:
        """Format execution duration"""
        if self.end_time:
            duration = self.end_time - self.start_time
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "In progress"
    
    def generate_report(self) -> str:
        """Generate the complete markdown report"""
        if not self.end_time:
            self.end_time = datetime.now()
        
        report_lines = []
        
        # Header
        report_lines.extend([
            f"# Page {self.page_number}: {self.page_name} - Processing Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ])
        
        # Execution Summary
        report_lines.extend([
            "## 📋 Execution Summary",
            "",
            f"- **Start Time**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **End Time**: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Duration**: {self._format_duration()}",
            f"- **Status**: {self.status}",
            "",
        ])
        
        # Input Analysis
        if self.input_stats:
            report_lines.extend([
                "## 📁 Input Analysis",
                "",
            ])
            for key, value in self.input_stats.items():
                report_lines.append(f"- **{key}**: {value}")
            report_lines.append("")
        
        # Processing Results
        if self.processing_results:
            report_lines.extend([
                "## ⚙️ Processing Results",
                "",
            ])
            
            # Create table if results are structured
            if self.processing_results and isinstance(self.processing_results[0], dict):
                # Get all unique keys for table headers
                all_keys = set()
                for result in self.processing_results:
                    all_keys.update(result.keys())
                
                headers = sorted(all_keys)
                
                # Table header
                report_lines.append("| " + " | ".join(headers) + " |")
                report_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Table rows
                for result in self.processing_results:
                    row = []
                    for header in headers:
                        value = result.get(header, "")
                        # Escape pipe characters in values and convert to string
                        str_value = str(value)
                        if isinstance(str_value, str):
                            str_value = str_value.replace("|", "\\|")
                        row.append(str_value)
                    report_lines.append("| " + " | ".join(row) + " |")
            else:
                # Simple list format
                for i, result in enumerate(self.processing_results, 1):
                    report_lines.append(f"{i}. {result}")
            
            report_lines.append("")
        
        # Statistics
        if self.statistics:
            report_lines.extend([
                "## 📊 Statistics",
                "",
            ])
            for key, value in self.statistics.items():
                report_lines.append(f"- **{key}**: {value}")
            report_lines.append("")
        
        # Errors
        if self.errors:
            report_lines.extend([
                "## ❌ Errors",
                "",
            ])
            for i, error in enumerate(self.errors, 1):
                report_lines.append(f"{i}. {error}")
            report_lines.append("")
        
        # Warnings
        if self.warnings:
            report_lines.extend([
                "## ⚠️ Warnings",
                "",
            ])
            for i, warning in enumerate(self.warnings, 1):
                report_lines.append(f"{i}. {warning}")
            report_lines.append("")
        
        # Output Files
        if self.output_files:
            report_lines.extend([
                "## 📤 Output Files",
                "",
                "| File Path | Description | Size |",
                "| --- | --- | --- |",
            ])
            for file_info in self.output_files:
                path = str(file_info["path"]).replace("|", "\\|")
                desc = str(file_info["description"]).replace("|", "\\|")
                size = str(file_info["size"])
                report_lines.append(f"| `{path}` | {desc} | {size} |")
            report_lines.append("")
        
        # Footer
        report_lines.extend([
            "---",
            "",
            f"*Report generated by Dreamlet CLI v1.0.0*",
            f"*Page {self.page_number}: {self.page_name}*"
        ])
        
        return "\n".join(report_lines)
    
    def save_report(self) -> str:
        """Save the report to a markdown file and return the file path"""
        # Generate filename
        filename = f"{self.page_number.zfill(2)}_{self.page_name.lower().replace(' ', '_')}.md"
        file_path = self.output_dir / filename
        
        # Generate and save report
        report_content = self.generate_report()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(file_path)

def generate_report(page_number: str, page_name: str, results: Dict[str, Any], 
                   output_dir: str = "reports") -> str:
    """
    Convenience function to generate a report from results dictionary
    
    Args:
        page_number: Page number (e.g., "05", "10")
        page_name: Human-readable page name
        results: Dictionary containing processing results
        output_dir: Directory to save reports
        
    Returns:
        Path to the generated report file
    """
    generator = ReportGenerator(page_number, page_name, output_dir)
    
    # Extract common fields from results
    if "input_stats" in results:
        generator.set_input_stats(**results["input_stats"])
    
    if "processing_results" in results:
        for result in results["processing_results"]:
            generator.add_processing_result(result)
    
    if "statistics" in results:
        generator.set_statistics(**results["statistics"])
    
    if "errors" in results:
        for error in results["errors"]:
            generator.add_error(error)
    
    if "warnings" in results:
        for warning in results["warnings"]:
            generator.add_warning(warning)
    
    if "output_files" in results:
        for file_info in results["output_files"]:
            if isinstance(file_info, dict):
                generator.add_output_file(
                    file_info.get("path", ""),
                    file_info.get("description", "")
                )
            else:
                generator.add_output_file(str(file_info))
    
    if "status" in results:
        generator.set_status(results["status"])
    else:
        # Determine status based on errors
        if generator.errors:
            generator.set_status("Error")
        elif generator.warnings:
            generator.set_status("Warning")
        else:
            generator.set_status("Success")
    
    return generator.save_report()

def list_reports(output_dir: str = "reports") -> List[Dict[str, str]]:
    """
    List all available reports
    
    Args:
        output_dir: Directory containing reports
        
    Returns:
        List of report information dictionaries
    """
    reports_dir = Path(output_dir)
    if not reports_dir.exists():
        return []
    
    reports = []
    for file_path in reports_dir.glob("*.md"):
        # Extract page number from filename
        filename = file_path.stem
        parts = filename.split("_", 1)
        if len(parts) >= 2:
            page_number = parts[0]
            page_name = parts[1].replace("_", " ").title()
        else:
            page_number = filename
            page_name = "Unknown"
        
        # Get file stats
        stat = file_path.stat()
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        
        reports.append({
            "page_number": page_number,
            "page_name": page_name,
            "filename": file_path.name,
            "path": str(file_path),
            "modified": modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            "size": f"{stat.st_size} bytes"
        })
    
    # Sort by page number
    reports.sort(key=lambda x: x["page_number"])
    return reports