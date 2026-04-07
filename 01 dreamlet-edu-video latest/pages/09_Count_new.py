"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

Improved File Verification System
Replaces the complex 09_Count.py with a cleaner, more maintainable architecture
"""

import streamlit as st
import os
import re
import time
import zipfile
import tempfile
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path
import pandas as pd
from enum import Enum
import fnmatch

# Configure Streamlit page
st.set_page_config(page_title="09 Count New - Dreamlet", page_icon="🔢", layout="wide")

# ============================================================================
# CORE DATA STRUCTURES AND INTERFACES
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

# ============================================================================
# FILE PROCESSORS
# ============================================================================

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
                    if image_files_found:
                        # Show first few image files for debugging
                        sample_images = image_files_found[:5]
                        processing_details.append(f"Sample images: {sample_images}")
                
                if not pptx_files_found and not image_files_found:
                    processing_details.append("No PPTX or image files found in ZIP archive")
                    # List some files for debugging
                    sample_files = [f for f in all_files[:10]]  # First 10 files
                    processing_details.append(f"Sample files in ZIP: {sample_files}")
            
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
                    "all_files_in_zip": all_files,
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
# FILE SCANNER AND CATEGORIZATION
# ============================================================================

class FileScanner:
    """Scans directories and categorizes files for verification"""
    
    def __init__(self):
        self.supported_extensions = {
            'pptx': ['.pptx'],
            'zip': ['.zip'],
            'text': ['.txt', '.md'],
            'summary': ['.txt', '.md']
        }
    
    def scan_directory(self, path: str) -> Dict[str, List[str]]:
        """Scan directory and return categorized files"""
        categorized_files = {
            'pptx': [],
            'zip': [],
            'text': [],
            'summary': []
        }
        
        try:
            for root, dirs, files in os.walk(path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    file_category = self._categorize_file(file_path)
                    
                    if file_category:
                        categorized_files[file_category].append(file_path)
        
        except Exception as e:
            st.error(f"Error scanning directory {path}: {str(e)}")
        
        return categorized_files
    
    def _categorize_file(self, file_path: str) -> Optional[str]:
        """Categorize a single file based on path and extension"""
        file_lower = file_path.lower()
        
        # PPTX files
        if file_lower.endswith('.pptx'):
            return 'pptx'
        
        # ZIP files
        if file_lower.endswith('.zip'):
            return 'zip'
        
        # Text files in English text directories
        if ('english text' in file_lower and 
            file_lower.endswith(('.txt', '.md'))):
            return 'text'
        
        # Summary files in English Summary text directories
        if ('english summary text' in file_lower and 
            file_lower.endswith(('.txt', '.md'))):
            return 'summary'
        
        return None
    
    def group_by_lecture(self, categorized_files: Dict[str, List[str]]) -> Dict[str, LectureFiles]:
        """Group files by course and lecture"""
        lecture_groups = {}
        
        # Process all file types
        all_files = []
        for file_type, files in categorized_files.items():
            for file_path in files:
                all_files.append((file_path, file_type))
        
        for file_path, file_type in all_files:
            course_info = extract_course_info(file_path)
            lecture_number = extract_lecture_number(file_path)
            
            # Create unique key for this lecture
            key = f"{course_info.course_number}:{lecture_number}"
            
            if key not in lecture_groups:
                lecture_info = LectureInfo(
                    lecture_number=lecture_number,
                    lecture_directory=os.path.dirname(file_path),
                    course_info=course_info
                )
                lecture_groups[key] = LectureFiles(lecture_info=lecture_info)
            
            # Add file to appropriate list
            if file_type == 'pptx':
                lecture_groups[key].pptx_files.append(file_path)
            elif file_type == 'zip':
                lecture_groups[key].zip_files.append(file_path)
            elif file_type == 'text':
                lecture_groups[key].text_files.append(file_path)
            elif file_type == 'summary':
                lecture_groups[key].summary_files.append(file_path)
        
        return lecture_groups

# ============================================================================
# PROCESSOR MANAGER
# ============================================================================

class ProcessorManager:
    """Manages file processors and coordinates processing"""
    
    def __init__(self):
        self.processors: List[FileProcessor] = []
        self._setup_processors()
    
    def _setup_processors(self):
        """Initialize all processors"""
        pptx_processor = PPTXProcessor()
        self.processors = [
            pptx_processor,
            ZIPProcessor(pptx_processor),
            TextFileProcessor(),
            SummaryFileProcessor()
        ]
        
        # Sort by priority
        self.processors.sort(key=lambda p: p.get_priority())
    
    def get_processors_for_file(self, file_path: str) -> List[FileProcessor]:
        """Get processors that can handle the given file"""
        return [p for p in self.processors if p.can_process(file_path)]
    
    def process_file(self, file_path: str) -> ProcessingResult:
        """Process a single file using the best available processor"""
        processors = self.get_processors_for_file(file_path)
        
        if not processors:
            return ProcessingResult(
                file_path=file_path,
                processor_name="None",
                success=False,
                content_count=0,
                error_message="No suitable processor found"
            )
        
        # Use the highest priority processor
        processor = processors[0]
        return processor.process(file_path)
    
    def process_batch(self, file_paths: List[str]) -> List[ProcessingResult]:
        """Process multiple files"""
        results = []
        for file_path in file_paths:
            result = self.process_file(file_path)
            results.append(result)
        return results

# ============================================================================
# RESULTS AGGREGATION AND DISCREPANCY DETECTION
# ============================================================================

class ResultsAggregator:
    """Aggregates processing results and detects discrepancies"""
    
    def aggregate_results(self, lecture_groups: Dict[str, LectureFiles], 
                         processor_manager: ProcessorManager) -> VerificationResults:
        """Aggregate all results and detect discrepancies"""
        start_time = time.time()
        entries = []
        errors = []
        
        for key, lecture_files in lecture_groups.items():
            entry = self._process_lecture(lecture_files, processor_manager)
            entries.append(entry)
        
        # Calculate statistics
        statistics = self._calculate_statistics(entries)
        
        processing_time = time.time() - start_time
        
        return VerificationResults(
            entries=entries,
            statistics=statistics,
            processing_time=processing_time,
            errors=errors
        )
    
    def _process_lecture(self, lecture_files: LectureFiles, 
                        processor_manager: ProcessorManager) -> VerificationEntry:
        """Process a single lecture and create verification entry"""
        entry = VerificationEntry(
            course_name=lecture_files.lecture_info.course_info.course_name,
            lecture_number=lecture_files.lecture_info.lecture_number
        )
        
        # Process PPTX files
        if lecture_files.pptx_files:
            pptx_file = lecture_files.pptx_files[0]  # Use first PPTX file
            result = processor_manager.process_file(pptx_file)
            if result.success:
                entry.pptx_slides = result.content_count
                entry.processing_methods['pptx'] = result.metadata.get('method', 'unknown')
            else:
                entry.errors.append(f"PPTX processing failed: {result.error_message}")
            entry.file_paths['pptx'] = pptx_file
        
        # Process ZIP files
        if lecture_files.zip_files:
            zip_file = lecture_files.zip_files[0]  # Use first ZIP file
            result = processor_manager.process_file(zip_file)
            if result.success:
                entry.zip_slides = result.content_count
                
                # Create descriptive processing method
                pptx_count = result.metadata.get("total_pptx_files", 0)
                image_count = result.metadata.get("total_image_files", 0)
                
                if pptx_count > 0:
                    entry.processing_methods['zip'] = f'zip_extraction ({pptx_count} PPTX files)'
                elif image_count > 0:
                    entry.processing_methods['zip'] = f'zip_extraction ({image_count} image files)'
                else:
                    entry.processing_methods['zip'] = 'zip_extraction (no content found)'
                
                # Store additional metadata for debugging
                entry.metadata = result.metadata
                
                # Debug: Add more detailed error info if no slides found
                if result.content_count == 0:
                    entry.errors.append(f"ZIP processed successfully but found 0 slides. Files in ZIP: PPTX={pptx_count}, Images={image_count}")
            else:
                entry.errors.append(f"ZIP processing failed: {result.error_message}")
            entry.file_paths['zip'] = zip_file
        
        # Process text files
        if lecture_files.text_files:
            text_file = lecture_files.text_files[0]  # Use first text file as representative
            result = processor_manager.process_file(text_file)
            if result.success:
                entry.text_files = result.content_count
            else:
                entry.errors.append(f"Text processing failed: {result.error_message}")
            entry.file_paths['text'] = result.metadata.get('directory', os.path.dirname(text_file))
        
        # Process summary files
        if lecture_files.summary_files:
            summary_file = lecture_files.summary_files[0]  # Use first summary file as representative
            result = processor_manager.process_file(summary_file)
            if result.success:
                entry.summary_files = result.content_count
            else:
                entry.errors.append(f"Summary processing failed: {result.error_message}")
            entry.file_paths['summary'] = result.metadata.get('directory', os.path.dirname(summary_file))
        
        # Detect discrepancies
        entry.has_discrepancy = self._detect_discrepancy(entry)
        
        return entry
    
    def _detect_discrepancy(self, entry: VerificationEntry) -> bool:
        """Detect if there are discrepancies in the entry"""
        # Get slide count (either from PPTX or ZIP, not both)
        slide_count = entry.pptx_slides if entry.pptx_slides > 0 else entry.zip_slides
        
        # Get text and summary counts
        text_count = entry.text_files
        summary_count = entry.summary_files
        
        # Skip entries with no content at all
        if slide_count == 0 and text_count == 0 and summary_count == 0:
            return False
        
        # Check if all three counts are the same (when they exist)
        counts = []
        if slide_count > 0:
            counts.append(slide_count)
        if text_count > 0:
            counts.append(text_count)
        if summary_count > 0:
            counts.append(summary_count)
        
        # If we have multiple different counts, there's a discrepancy
        if len(set(counts)) > 1:
            return True
        
        # If we have some content but missing others, that's a discrepancy
        has_slides = slide_count > 0
        has_text = text_count > 0
        has_summary = summary_count > 0
        
        content_areas = [has_slides, has_text, has_summary]
        if any(content_areas) and not all(content_areas):
            return True
        
        return False
    
    def _calculate_statistics(self, entries: List[VerificationEntry]) -> VerificationStatistics:
        """Calculate verification statistics"""
        stats = VerificationStatistics()
        stats.total_lectures = len(entries)
        
        for entry in entries:
            if entry.has_discrepancy:
                stats.total_discrepancies += 1
            
            if entry.pptx_slides == 0 and entry.zip_slides == 0:
                stats.missing_pptx += 1
            
            if entry.text_files == 0:
                stats.missing_text += 1
            
            if entry.summary_files == 0:
                stats.missing_summaries += 1
            
            if entry.errors:
                stats.processing_errors += 1
        
        return stats

# ============================================================================
# VERIFICATION CONTROLLER
# ============================================================================

class VerificationController:
    """Main controller that orchestrates the verification process"""
    
    def __init__(self):
        self.file_scanner = FileScanner()
        self.processor_manager = ProcessorManager()
        self.results_aggregator = ResultsAggregator()
    
    def run_verification(self, input_directory: str, progress_callback=None) -> VerificationResults:
        """Run complete verification process"""
        try:
            # Step 1: Scan and categorize files
            if progress_callback:
                progress_callback("Scanning files...", 0.1)
            
            categorized_files = self.file_scanner.scan_directory(input_directory)
            
            # Step 2: Group by lecture
            if progress_callback:
                progress_callback("Grouping files by lecture...", 0.3)
            
            lecture_groups = self.file_scanner.group_by_lecture(categorized_files)
            
            # Step 3: Process and aggregate results
            if progress_callback:
                progress_callback("Processing files and detecting discrepancies...", 0.5)
            
            results = self.results_aggregator.aggregate_results(lecture_groups, self.processor_manager)
            
            if progress_callback:
                progress_callback("Verification complete!", 1.0)
            
            return results
            
        except Exception as e:
            error_results = VerificationResults()
            error_results.errors.append(f"Verification failed: {str(e)}")
            return error_results

# ============================================================================
# STREAMLIT USER INTERFACE
# ============================================================================

def create_results_dataframe(results: VerificationResults, show_only_discrepancies: bool = True) -> pd.DataFrame:
    """Convert verification results to pandas DataFrame for display"""
    data = []
    
    for entry in results.entries:
        # Skip non-discrepancies if requested
        if show_only_discrepancies and not entry.has_discrepancy:
            continue
            
        # Get slide count (either PPTX or ZIP)
        slide_count = entry.pptx_slides if entry.pptx_slides > 0 else entry.zip_slides
        slide_source = "PPTX" if entry.pptx_slides > 0 else "ZIP" if entry.zip_slides > 0 else "None"
        
        data.append({
            "Course": entry.course_name,
            "Lecture": f"Lecture {entry.lecture_number}",
            "Slides": slide_count,
            "Source": slide_source,
            "Text Files": entry.text_files,
            "Summary Files": entry.summary_files,
            "Errors": len(entry.errors)
        })
    
    return pd.DataFrame(data)

def display_statistics(stats: VerificationStatistics):
    """Display verification statistics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Lectures", stats.total_lectures)
    
    with col2:
        st.metric("Discrepancies", stats.total_discrepancies)
    
    with col3:
        st.metric("Missing PPTX", stats.missing_pptx)
    
    with col4:
        st.metric("Processing Errors", stats.processing_errors)



# ============================================================================
# MAIN STREAMLIT APPLICATION
# ============================================================================

def main():
    """Main Streamlit application"""
    st.title("🔢 File Verification System (New)")
    st.markdown("Improved file counting and verification - **Showing only discrepancies**")
    
    # Initialize session state
    if 'verification_results' not in st.session_state:
        st.session_state.verification_results = None
    
    # Input directory selection
    input_dir = get_input_directory()
    st.info(f"Scanning directory: `{input_dir}`")
    
    # Verification controls
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔍 Run Verification", type="primary"):
            # Create progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(message, progress):
                status_text.text(message)
                progress_bar.progress(progress)
            
            # Run verification
            controller = VerificationController()
            results = controller.run_verification(input_dir, progress_callback)
            
            # Store results in session state
            st.session_state.verification_results = results
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            st.success("Verification completed!")
    
    with col2:
        if st.button("🔄 Clear Results"):
            st.session_state.verification_results = None
            st.rerun()
    
    # Display results if available
    if st.session_state.verification_results:
        results = st.session_state.verification_results
        
        # Check for errors
        if results.errors:
            st.error("Verification encountered errors:")
            for error in results.errors:
                st.error(error)
            return
        
        # Display statistics
        st.subheader("📊 Statistics")
        display_statistics(results.statistics)
        
        # Display processing time
        st.info(f"Processing completed in {results.processing_time:.2f} seconds")
        
        # Debug information
        if st.checkbox("Show file discovery debug info"):
            st.subheader("🔍 File Discovery Debug")
            controller = VerificationController()
            categorized_files = controller.file_scanner.scan_directory(input_dir)
            
            st.write("**Files found by category:**")
            for category, files in categorized_files.items():
                st.write(f"- {category.upper()}: {len(files)} files")
                if files and len(files) <= 10:  # Show first 10 files
                    for file in files[:10]:
                        st.write(f"  - `{file}`")
                elif len(files) > 10:
                    st.write(f"  - (showing first 10 of {len(files)} files)")
                    for file in files[:10]:
                        st.write(f"  - `{file}`")
            
            # Test ZIP processing directly
            if categorized_files['zip']:
                st.write("**Testing ZIP processing:**")
                zip_file = categorized_files['zip'][0]
                st.write(f"Testing ZIP file: `{zip_file}`")
                
                # Test ZIP processor directly
                pptx_processor = PPTXProcessor()
                zip_processor = ZIPProcessor(pptx_processor)
                result = zip_processor.process(zip_file)
                
                st.write(f"ZIP processing result:")
                st.write(f"- Success: {result.success}")
                st.write(f"- Content count: {result.content_count}")
                st.write(f"- Error message: {result.error_message}")
                if result.metadata:
                    st.write(f"- Processing details:")
                    for detail in result.metadata.get('processing_details', []):
                        st.write(f"  - {detail}")
        
        # Results table - only discrepancies
        st.subheader("❌ Discrepancies Found")
        
        if results.entries:
            df = create_results_dataframe(results, show_only_discrepancies=True)
            
            if len(df) > 0:
                # Filters
                col1, col2 = st.columns(2)
                
                with col1:
                    courses = ["All"] + sorted(df["Course"].unique().tolist())
                    selected_course = st.selectbox("Filter by Course", courses)
                
                with col2:
                    show_errors_only = st.checkbox("Show only entries with errors")
                
                # Apply filters
                filtered_df = df.copy()
                
                if selected_course != "All":
                    filtered_df = filtered_df[filtered_df["Course"] == selected_course]
                
                if show_errors_only:
                    filtered_df = filtered_df[filtered_df["Errors"] > 0]
                
                # Display filtered table
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show debugging info for ZIP files
                if st.checkbox("Show ZIP processing details"):
                    st.subheader("🔍 ZIP Processing Details")
                    for entry in results.entries:
                        if entry.has_discrepancy and (entry.zip_slides > 0 or 'zip' in entry.file_paths):
                            st.write(f"**{entry.course_name} - Lecture {entry.lecture_number}**")
                            if 'zip' in entry.file_paths:
                                st.write(f"ZIP file: `{entry.file_paths['zip']}`")
                            if 'zip' in entry.processing_methods:
                                st.write(f"Processing method: {entry.processing_methods['zip']}")
                            if entry.metadata:
                                if 'pptx_files_found' in entry.metadata and entry.metadata['pptx_files_found']:
                                    st.write(f"PPTX files in ZIP: {entry.metadata['pptx_files_found']}")
                                if 'image_files_found' in entry.metadata and entry.metadata['image_files_found']:
                                    st.write(f"Image files in ZIP: {len(entry.metadata['image_files_found'])} files")
                                    if len(entry.metadata['image_files_found']) <= 10:
                                        st.write(f"Image files: {entry.metadata['image_files_found']}")
                                    else:
                                        st.write(f"First 10 image files: {entry.metadata['image_files_found'][:10]}")
                                if 'processing_details' in entry.metadata:
                                    st.write("Processing details:")
                                    for detail in entry.metadata['processing_details']:
                                        st.write(f"  - {detail}")
                            if entry.errors:
                                for error in entry.errors:
                                    st.error(error)
                            st.write("---")
                
                # Export functionality
                if st.button("📥 Export Discrepancies to CSV"):
                    csv_data = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"discrepancies_{int(time.time())}.csv",
                        mime="text/csv"
                    )
            else:
                st.success("🎉 No discrepancies found! All files are consistent.")
        
        else:
            st.warning("No files found to verify.")

# Run the application
if __name__ == "__main__":
    main()
else:
    # When imported as a Streamlit page
    main()