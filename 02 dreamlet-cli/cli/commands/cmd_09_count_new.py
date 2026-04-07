"""
CLI Command: Count & Validate Files (Page 09)

Converts the Streamlit page 09_Count_new.py to CLI interface
while maintaining 100% functional parity.

This command provides comprehensive file verification and counting for the 
educational video production workflow, validating PPTX slides, ZIP archives,
and text files across all courses and lectures.
"""

import click
import os
import sys
import re
import time
import zipfile
import tempfile
import subprocess
import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional, Set
from pathlib import Path
from enum import Enum

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.progress import DreamletProgress
from cli.reports import generate_report
from cli.config import load_config
from rich.console import Console
from rich.table import Table

console = Console()

class StatusManager:
    """CLI-compatible status manager for validation processing"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.console = Console()
        
    def info(self, message, verbose_only=False):
        """Display info message"""
        if not verbose_only or self.verbose:
            self.console.print(f"[cyan]ℹ[/cyan] {message}")
    
    def warning(self, message):
        """Display warning message"""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def error(self, message):
        """Display error message"""
        self.console.print(f"[red]✗[/red] {message}")
    
    def success(self, message):
        """Display success message"""
        self.console.print(f"[green]✓[/green] {message}")

# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================

@dataclass
class ProcessingResult:
    """Result of processing a single file"""
    file_path: str
    processor_name: str
    success: bool
    content_count: int  # slides, files, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processing_time: float = 0.0

@dataclass
class CourseInfo:
    """Information about a course"""
    course_name: str
    course_number: str
    base_directory: str

@dataclass
class LectureInfo:
    """Information about a lecture"""
    lecture_number: str
    lecture_directory: str
    course_info: CourseInfo

@dataclass
class LectureFiles:
    """Files associated with a lecture"""
    lecture_info: LectureInfo
    pptx_files: List[str] = field(default_factory=list)
    zip_files: List[str] = field(default_factory=list)
    text_files: List[str] = field(default_factory=list)
    summary_files: List[str] = field(default_factory=list)

@dataclass
class VerificationEntry:
    """Single entry in verification results"""
    course_name: str
    lecture_number: str
    pptx_slides: int = 0
    zip_slides: int = 0
    text_files: int = 0
    summary_files: int = 0
    has_discrepancy: bool = False
    file_paths: Dict[str, str] = field(default_factory=dict)
    processing_methods: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VerificationStatistics:
    """Statistics about verification results"""
    total_lectures: int = 0
    total_discrepancies: int = 0
    missing_pptx: int = 0
    missing_text: int = 0
    missing_summaries: int = 0
    format_errors: int = 0
    processing_errors: int = 0

@dataclass
class VerificationResults:
    """Complete verification results"""
    entries: List[VerificationEntry] = field(default_factory=list)
    statistics: VerificationStatistics = field(default_factory=VerificationStatistics)
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)

# ============================================================================
# FILE PROCESSORS
# ============================================================================

class FileProcessor(ABC):
    """Abstract base class for file processors"""
    
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file"""
        pass
    
    @abstractmethod
    def process(self, file_path: str) -> ProcessingResult:
        """Process the file and return results"""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get processor priority (lower number = higher priority)"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get processor name"""
        pass

class PPTXProcessor(FileProcessor):
    """Processor for PPTX files with multiple fallback methods"""
    
    def can_process(self, file_path: str) -> bool:
        return file_path.lower().endswith('.pptx')
    
    def get_priority(self) -> int:
        return 1
    
    def get_name(self) -> str:
        return "PPTX Processor"
    
    def process(self, file_path: str) -> ProcessingResult:
        start_time = time.time()
        
        # Method 1: python-pptx
        try:
            import pptx
            presentation = pptx.Presentation(file_path)
            slide_count = len(presentation.slides)
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=True,
                content_count=slide_count,
                metadata={"method": "python-pptx"},
                processing_time=processing_time
            )
        except Exception as e:
            # Method 2: zipfile approach
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    slide_files = [f for f in zip_ref.namelist() 
                                 if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
                    slide_count = len(slide_files)
                    processing_time = time.time() - start_time
                    
                    return ProcessingResult(
                        file_path=file_path,
                        processor_name=self.get_name(),
                        success=True,
                        content_count=slide_count,
                        metadata={"method": "zipfile"},
                        processing_time=processing_time
                    )
            except Exception as zip_error:
                # Method 3: LibreOffice fallback
                try:
                    slide_count = self._count_with_libreoffice(file_path)
                    processing_time = time.time() - start_time
                    
                    return ProcessingResult(
                        file_path=file_path,
                        processor_name=self.get_name(),
                        success=True,
                        content_count=slide_count,
                        metadata={"method": "libreoffice"},
                        processing_time=processing_time
                    )
                except Exception as lo_error:
                    processing_time = time.time() - start_time
                    return ProcessingResult(
                        file_path=file_path,
                        processor_name=self.get_name(),
                        success=False,
                        content_count=0,
                        error_message=f"All methods failed. Last error: {str(lo_error)}",
                        processing_time=processing_time
                    )
    
    def _count_with_libreoffice(self, pptx_path: str) -> int:
        """Count slides using LibreOffice conversion"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert to PDF
            pdf_output = os.path.join(temp_dir, "presentation.pdf")
            
            # Try libreoffice command
            lo_command = [
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", temp_dir, pptx_path
            ]
            
            try:
                subprocess.run(lo_command, check=True, capture_output=True, timeout=60)
            except (FileNotFoundError, subprocess.CalledProcessError):
                # Try soffice as fallback
                lo_command[0] = "soffice"
                subprocess.run(lo_command, check=True, capture_output=True, timeout=60)
            
            if not os.path.exists(pdf_output):
                raise Exception("LibreOffice failed to convert PPTX to PDF")
            
            # Count pages using pdfinfo
            try:
                pdfinfo_command = ["pdfinfo", pdf_output]
                result = subprocess.run(pdfinfo_command, check=True, capture_output=True, text=True, timeout=10)
                
                for line in result.stdout.split("\n"):
                    if "Pages:" in line:
                        return int(line.split("Pages:")[1].strip())
            except Exception:
                pass
            
            raise Exception("Could not determine page count from PDF")

class ZIPProcessor(FileProcessor):
    """Processor for ZIP files containing slide images"""
    
    def __init__(self, pptx_processor: PPTXProcessor):
        self.pptx_processor = pptx_processor
        # Common image extensions for slides
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    
    def can_process(self, file_path: str) -> bool:
        return file_path.lower().endswith('.zip')
    
    def get_priority(self) -> int:
        return 2
    
    def get_name(self) -> str:
        return "ZIP Processor"
    
    def process(self, file_path: str) -> ProcessingResult:
        start_time = time.time()
        
        try:
            total_slides = 0
            image_files_found = []
            pptx_files_found = []
            processing_details = []
            
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                raise Exception(f"ZIP file does not exist: {file_path}")
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # List all files in ZIP for debugging
                all_files = [f.filename for f in zip_ref.filelist if not f.is_dir()]
                processing_details.append(f"Total files in ZIP: {len(all_files)}")
                
                # First, try to find PPTX files (original logic)
                for file_info in zip_ref.filelist:
                    filename_lower = file_info.filename.lower()
                    
                    # Skip directories and system files
                    if file_info.is_dir() or filename_lower.startswith('__macosx/') or filename_lower.startswith('.'):
                        continue
                        
                    if filename_lower.endswith('.pptx'):
                        pptx_files_found.append(file_info.filename)
                        processing_details.append(f"Found PPTX: {file_info.filename} (size: {file_info.file_size} bytes)")
                        
                        try:
                            # Extract PPTX to temporary location and process
                            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
                                temp_file.write(zip_ref.read(file_info.filename))
                                temp_pptx_path = temp_file.name
                            
                            # Process the extracted PPTX
                            pptx_result = self.pptx_processor.process(temp_pptx_path)
                            if pptx_result.success:
                                total_slides += pptx_result.content_count
                                processing_details.append(f"✓ {file_info.filename}: {pptx_result.content_count} slides (method: {pptx_result.metadata.get('method', 'unknown')})")
                            else:
                                processing_details.append(f"✗ {file_info.filename}: ERROR - {pptx_result.error_message}")
                                
                        except Exception as pptx_error:
                            processing_details.append(f"✗ {file_info.filename}: Exception during processing - {str(pptx_error)}")
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_pptx_path)
                            except:
                                pass
                
                # If no PPTX files found, count image files as slides
                if not pptx_files_found:
                    processing_details.append("No PPTX files found, counting image files as slides...")
                    
                    for file_info in zip_ref.filelist:
                        filename_lower = file_info.filename.lower()
                        
                        # Skip directories and system files
                        if file_info.is_dir() or filename_lower.startswith('__macosx/') or filename_lower.startswith('.'):
                            continue
                        
                        # Check if it's an image file
                        file_ext = os.path.splitext(filename_lower)[1]
                        if file_ext in self.image_extensions:
                            image_files_found.append(file_info.filename)
                            total_slides += 1
                    
                    processing_details.append(f"Found {len(image_files_found)} image files")
                
                if not pptx_files_found and not image_files_found:
                    processing_details.append("No PPTX or image files found in ZIP archive")
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=True,
                content_count=total_slides,
                metadata={
                    "pptx_files_found": pptx_files_found,
                    "image_files_found": image_files_found,
                    "total_pptx_files": len(pptx_files_found),
                    "total_image_files": len(image_files_found),
                    "processing_details": processing_details
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=False,
                content_count=0,
                error_message=f"ZIP processing failed: {str(e)}",
                processing_time=processing_time
            )

class TextFileProcessor(FileProcessor):
    """Processor for text files in English text directories"""
    
    def can_process(self, file_path: str) -> bool:
        # Check if file is in an "English text" directory
        return ("english text" in file_path.lower() and 
                file_path.lower().endswith(('.txt', '.md')))
    
    def get_priority(self) -> int:
        return 3
    
    def get_name(self) -> str:
        return "Text File Processor"
    
    def process(self, file_path: str) -> ProcessingResult:
        start_time = time.time()
        
        try:
            # Count files in the same directory
            directory = os.path.dirname(file_path)
            file_count = len([f for f in os.listdir(directory) 
                            if f.lower().endswith(('.txt', '.md'))])
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=True,
                content_count=file_count,
                metadata={"directory": directory},
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=False,
                content_count=0,
                error_message=str(e),
                processing_time=processing_time
            )

class SummaryFileProcessor(FileProcessor):
    """Processor for summary text files"""
    
    def can_process(self, file_path: str) -> bool:
        # Check if file is in an "English Summary text" directory
        return ("english summary text" in file_path.lower() and 
                file_path.lower().endswith(('.txt', '.md')))
    
    def get_priority(self) -> int:
        return 4
    
    def get_name(self) -> str:
        return "Summary File Processor"
    
    def process(self, file_path: str) -> ProcessingResult:
        start_time = time.time()
        
        try:
            # Count files in the same directory
            directory = os.path.dirname(file_path)
            file_count = len([f for f in os.listdir(directory) 
                            if f.lower().endswith(('.txt', '.md'))])
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=True,
                content_count=file_count,
                metadata={"directory": directory},
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                file_path=file_path,
                processor_name=self.get_name(),
                success=False,
                content_count=0,
                error_message=str(e),
                processing_time=processing_time
            )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def extract_course_info(file_path: str) -> CourseInfo:
    """Extract course information from file path"""
    parts = Path(file_path).parts
    
    # Look for course pattern in path parts
    course_name = "Unknown Course"
    course_number = "999"
    base_directory = ""
    
    for i, part in enumerate(parts):
        # Look for patterns like "31 Course Name" or "389 Web3 Economics"
        if re.match(r'^\d{1,3}\s+', part):
            course_name = part
            course_number = re.match(r'^(\d{1,3})', part).group(1)
            base_directory = str(Path(*parts[:i+1]))
            break
    
    return CourseInfo(
        course_name=course_name,
        course_number=course_number,
        base_directory=base_directory
    )

def extract_lecture_number(file_path: str) -> str:
    """Extract lecture number from file path"""
    # Try filename first
    filename = os.path.basename(file_path)
    match = re.search(r'lecture[\_\s-]*(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1).zfill(2)
    
    # Try directory names
    parts = Path(file_path).parts
    for part in parts:
        if 'lecture' in part.lower():
            match = re.search(r'lecture[\_\s-]*(\d+)', part, re.IGNORECASE)
            if match:
                return match.group(1).zfill(2)
    
    return "00"

def discover_lecture_files(input_dir: str, supported_file_types: List[str]) -> Dict[str, LectureFiles]:
    """Discover all lecture files in the input directory"""
    lecture_files_map = {}
    
    # Walk through all directories
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # Check if file type is supported
            if file_ext.lstrip('.') not in supported_file_types:
                continue
            
            # Extract course and lecture information
            course_info = extract_course_info(file_path)
            lecture_number = extract_lecture_number(file_path)
            
            # Create unique key for this lecture
            lecture_key = f"{course_info.course_name}_{lecture_number}"
            
            # Initialize lecture files if not exists
            if lecture_key not in lecture_files_map:
                lecture_info = LectureInfo(
                    lecture_number=lecture_number,
                    lecture_directory=os.path.dirname(file_path),
                    course_info=course_info
                )
                lecture_files_map[lecture_key] = LectureFiles(lecture_info=lecture_info)
            
            # Categorize the file
            if file_path.lower().endswith('.pptx'):
                lecture_files_map[lecture_key].pptx_files.append(file_path)
            elif file_path.lower().endswith('.zip'):
                lecture_files_map[lecture_key].zip_files.append(file_path)
            elif "english text" in file_path.lower() and "summary" not in file_path.lower():
                lecture_files_map[lecture_key].text_files.append(file_path)
            elif "english summary text" in file_path.lower():
                lecture_files_map[lecture_key].summary_files.append(file_path)
    
    return lecture_files_map

def run_verification(
    input_dir: str,
    supported_file_types: List[str],
    verification_methods: List[str],
    show_only_discrepancies: bool = True,
    include_debug_info: bool = False,
    status_manager: StatusManager = None
) -> VerificationResults:
    """Run comprehensive file verification"""
    
    start_time = time.time()
    
    # Initialize processors
    pptx_processor = PPTXProcessor()
    zip_processor = ZIPProcessor(pptx_processor)
    text_processor = TextFileProcessor()
    summary_processor = SummaryFileProcessor()
    
    processors = [pptx_processor, zip_processor, text_processor, summary_processor]
    
    # Discover all lecture files
    if status_manager:
        status_manager.info("Discovering lecture files...")
    
    lecture_files_map = discover_lecture_files(input_dir, supported_file_types)
    
    if not lecture_files_map:
        if status_manager:
            status_manager.warning("No lecture files found")
        return VerificationResults(
            entries=[],
            statistics=VerificationStatistics(),
            processing_time=time.time() - start_time,
            errors=["No lecture files found in input directory"]
        )
    
    if status_manager:
        status_manager.info(f"Found {len(lecture_files_map)} lectures to verify")
    
    # Process each lecture
    verification_entries = []
    processing_errors = []
    
    for lecture_key, lecture_files in lecture_files_map.items():
        if status_manager:
            status_manager.info(f"Verifying {lecture_files.lecture_info.course_info.course_name} - Lecture {lecture_files.lecture_info.lecture_number}", verbose_only=True)
        
        entry = VerificationEntry(
            course_name=lecture_files.lecture_info.course_info.course_name,
            lecture_number=lecture_files.lecture_info.lecture_number
        )
        
        # Process PPTX files
        for pptx_file in lecture_files.pptx_files:
            result = pptx_processor.process(pptx_file)
            if result.success:
                entry.pptx_slides = result.content_count
                entry.file_paths["pptx"] = pptx_file
                entry.processing_methods["pptx"] = result.metadata.get("method", "unknown")
            else:
                entry.errors.append(f"PPTX processing failed: {result.error_message}")
                processing_errors.append(result.error_message)
        
        # Process ZIP files
        for zip_file in lecture_files.zip_files:
            result = zip_processor.process(zip_file)
            if result.success:
                entry.zip_slides = result.content_count
                entry.file_paths["zip"] = zip_file
                entry.processing_methods["zip"] = "zip_analysis"
                if include_debug_info:
                    entry.metadata["zip_details"] = result.metadata
            else:
                entry.errors.append(f"ZIP processing failed: {result.error_message}")
                processing_errors.append(result.error_message)
        
        # Process text files
        if lecture_files.text_files:
            # Just count the files (they're all in the same directory)
            entry.text_files = len(lecture_files.text_files)
            entry.file_paths["text"] = lecture_files.text_files[0]  # Representative file
        
        # Process summary files
        if lecture_files.summary_files:
            # Just count the files (they're all in the same directory)
            entry.summary_files = len(lecture_files.summary_files)
            entry.file_paths["summary"] = lecture_files.summary_files[0]  # Representative file
        
        # Check for discrepancies
        slide_counts = [count for count in [entry.pptx_slides, entry.zip_slides] if count > 0]
        if len(slide_counts) > 1 and len(set(slide_counts)) > 1:
            entry.has_discrepancy = True
        
        # Add to results if not filtering or has discrepancy
        if not show_only_discrepancies or entry.has_discrepancy or entry.errors:
            verification_entries.append(entry)
    
    # Calculate statistics
    statistics = VerificationStatistics(
        total_lectures=len(lecture_files_map),
        total_discrepancies=sum(1 for e in verification_entries if e.has_discrepancy),
        missing_pptx=sum(1 for e in verification_entries if e.pptx_slides == 0),
        missing_text=sum(1 for e in verification_entries if e.text_files == 0),
        missing_summaries=sum(1 for e in verification_entries if e.summary_files == 0),
        format_errors=len(processing_errors),
        processing_errors=len(processing_errors)
    )
    
    processing_time = time.time() - start_time
    
    return VerificationResults(
        entries=verification_entries,
        statistics=statistics,
        processing_time=processing_time,
        errors=processing_errors
    )

def run_count_validate_processing(ctx_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the Count & Validate processing operation
    This replaces the Streamlit page's main() function
    """
    # Get configuration from context
    config = ctx_obj.get('config')
    
    # Create status manager
    status_manager = StatusManager(verbose=ctx_obj.get('verbose', False))
    
    # Get page configuration
    from cli.config import get_page_config
    page_config = get_page_config(config, 'page_09_count_validate')
    
    # Extract settings from config
    show_only_discrepancies = page_config.get('show_only_discrepancies', True)
    include_debug_info = page_config.get('include_debug_info', False)
    supported_file_types = page_config.get('supported_file_types', ['pptx', 'zip', 'txt', 'md'])
    verification_methods = page_config.get('verification_methods', ['python-pptx', 'zipfile', 'libreoffice'])
    
    # Validate input directory
    input_dir = config.input_dir
    if not os.path.exists(input_dir):
        error_msg = f"Input directory not found: {input_dir}"
        status_manager.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "statistics": {"total_lectures": 0, "processed_count": 0, "error_count": 1}
        }
    
    status_manager.info(f"Scanning input directory: {input_dir}")
    status_manager.info(f"Supported file types: {', '.join(supported_file_types)}")
    status_manager.info(f"Verification methods: {', '.join(verification_methods)}")
    
    # Run verification with progress tracking
    overall_start_time = time.time()
    
    with DreamletProgress(description="Verifying files", total=100) as progress:
        
        # Run verification
        results = run_verification(
            input_dir=input_dir,
            supported_file_types=supported_file_types,
            verification_methods=verification_methods,
            show_only_discrepancies=show_only_discrepancies,
            include_debug_info=include_debug_info,
            status_manager=status_manager
        )
        
        # Update progress
        progress.update(completed=100)
    
    # Calculate final statistics
    total_processing_time = time.time() - overall_start_time
    
    # Determine final status
    if results.statistics.processing_errors > 0 and len(results.entries) == 0:
        final_status = "error"
        status_message = f"Verification failed with {results.statistics.processing_errors} errors"
    elif results.statistics.total_discrepancies > 0:
        final_status = "warning"
        status_message = f"Found {results.statistics.total_discrepancies} discrepancies in {results.statistics.total_lectures} lectures"
    elif results.statistics.total_lectures == 0:
        final_status = "warning"
        status_message = "No lectures found to verify"
    else:
        final_status = "success"
        status_message = f"Verified {results.statistics.total_lectures} lectures successfully"
    
    # Show summary
    status_manager.success(status_message) if final_status == "success" else \
    status_manager.warning(status_message) if final_status == "warning" else \
    status_manager.error(status_message)
    
    # Display summary table if verbose
    if ctx_obj.get('verbose', False) and results.entries:
        table = Table(title="Verification Results")
        table.add_column("Course", style="cyan")
        table.add_column("Lecture", style="magenta")
        table.add_column("PPTX Slides", justify="right")
        table.add_column("ZIP Slides", justify="right")
        table.add_column("Text Files", justify="right")
        table.add_column("Summary Files", justify="right")
        table.add_column("Status", style="bold")
        
        for entry in results.entries[:10]:  # Show first 10 entries
            status_style = "red" if entry.has_discrepancy else "green"
            status_text = "DISCREPANCY" if entry.has_discrepancy else "OK"
            
            table.add_row(
                entry.course_name[:30] + "..." if len(entry.course_name) > 30 else entry.course_name,
                entry.lecture_number,
                str(entry.pptx_slides),
                str(entry.zip_slides),
                str(entry.text_files),
                str(entry.summary_files),
                f"[{status_style}]{status_text}[/{status_style}]"
            )
        
        console.print(table)
        
        if len(results.entries) > 10:
            console.print(f"... and {len(results.entries) - 10} more entries")
    
    # Prepare results for report generation
    report_results = {
        "status": final_status,
        "message": status_message,
        "input_stats": {
            "input_directory": input_dir,
            "supported_file_types": supported_file_types,
            "verification_methods": verification_methods
        },
        "verification_results": results,
        "statistics": {
            "total_lectures": results.statistics.total_lectures,
            "total_discrepancies": results.statistics.total_discrepancies,
            "missing_pptx": results.statistics.missing_pptx,
            "missing_text": results.statistics.missing_text,
            "missing_summaries": results.statistics.missing_summaries,
            "processing_errors": results.statistics.processing_errors,
            "processing_time": total_processing_time
        },
        "settings": {
            "show_only_discrepancies": show_only_discrepancies,
            "include_debug_info": include_debug_info,
            "supported_file_types": supported_file_types,
            "verification_methods": verification_methods
        },
        "errors": results.errors,
        "entries": [
            {
                "course_name": entry.course_name,
                "lecture_number": entry.lecture_number,
                "pptx_slides": entry.pptx_slides,
                "zip_slides": entry.zip_slides,
                "text_files": entry.text_files,
                "summary_files": entry.summary_files,
                "has_discrepancy": entry.has_discrepancy,
                "errors": entry.errors
            }
            for entry in results.entries
        ]
    }
    
    # Generate report
    report_path = generate_report("09", "Count & Validate Files", report_results)
    status_manager.info(f"Report saved to: {report_path}", verbose_only=True)
    
    report_results["report_path"] = report_path
    return report_results

@click.command()
@click.pass_context
def count_validate(ctx):
    """
    Count and validate files across all courses and lectures
    
    This command provides comprehensive file verification for the educational 
    video production workflow. It counts slides in PPTX files, images in ZIP 
    archives, and text files in various directories, then identifies discrepancies.
    
    All settings are configured in config.json under "page_09_count_validate":
    - show_only_discrepancies: Show only lectures with mismatched counts
    - include_debug_info: Include detailed processing information
    - supported_file_types: List of file extensions to process
    - verification_methods: Methods to use for verification
    
    Examples:
        dreamlet run 09                    # Verify with settings from config.json
        dreamlet config show               # View current configuration
        dreamlet config create             # Create default config.json
    """
    
    # Get configuration
    config = ctx.obj['config']
    
    # Check for dry run mode
    if config.dry_run:
        from rich.console import Console
        console = Console()
        console.print("[yellow]DRY RUN MODE - No files will be processed[/yellow]")
        
        from cli.config import get_page_config
        page_config = get_page_config(config, 'page_09_count_validate')
        supported_file_types = page_config.get('supported_file_types', ['pptx', 'zip', 'txt', 'md'])
        verification_methods = page_config.get('verification_methods', ['python-pptx', 'zipfile', 'libreoffice'])
        show_only_discrepancies = page_config.get('show_only_discrepancies', True)
        
        console.print(f"Would verify file types: {', '.join(supported_file_types)}")
        console.print(f"Would use methods: {', '.join(verification_methods)}")
        console.print(f"Show only discrepancies: {show_only_discrepancies}")
        return
    
    # Run the Count & Validate processing operation
    try:
        results = run_count_validate_processing(ctx.obj)
        
        # Exit with appropriate code based on results
        if results["status"] == "error":
            sys.exit(1)
        elif results["status"] == "warning":
            sys.exit(2)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        from rich.console import Console
        console = Console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    count_validate()