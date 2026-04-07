import streamlit as st
import os
import enum
from typing import Dict, List, Tuple, Optional, Any

# Define conversion method enumeration
class ConversionMethod(str, enum.Enum):
    LIBREOFFICE = "libreoffice"
    PYTHON_PPTX = "python-pptx"
    PDF2IMAGE = "pdf2image"

# Conversion method descriptions
CONVERSION_METHODS = {
    ConversionMethod.LIBREOFFICE: "LibreOffice + pdftoppm (best quality)",
    ConversionMethod.PYTHON_PPTX: "Direct PPTX processing (fastest)",
    ConversionMethod.PDF2IMAGE: "PDF2Image (most compatible)"
}

def extract_slides_with_method(
    pptx_path: str, 
    output_dir: str, 
    method: ConversionMethod,
    status_text: Optional[Any] = None,
    enable_auto_fallback: bool = True,
    target_resolution: Tuple[int, int] = (3840, 2160)
) -> Tuple[bool, str, int]:
    """
    Extract slides from a PPTX file using the specified method.
    
    Args:
        pptx_path: Path to the PPTX file
        output_dir: Directory to save the extracted images
        method: Conversion method to use
        status_text: Streamlit text element or StatusManager for status updates
        enable_auto_fallback: If True, automatically try other methods if the selected one fails
        target_resolution: Target resolution for the extracted images
        
    Returns:
        Tuple of (success, message, slide_count)
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if status_text has update_action method (it's a StatusManager)
    if status_text and hasattr(status_text, 'update_action'):
        status_text.update_action(f"Attempting extraction using {CONVERSION_METHODS[method]} method")
    elif status_text:
        status_text.info(f"Attempting extraction using {CONVERSION_METHODS[method]} method")
    
    # Try the selected method first
    success, message, slide_count = _try_method(pptx_path, output_dir, method, status_text, target_resolution)
    
    # If the primary method failed and auto fallback is enabled, try the other methods
    if not success and enable_auto_fallback:
        if status_text and hasattr(status_text, 'update_action'):
            status_text.update_action(f"Primary method failed. Trying fallback methods...")
        elif status_text:
            status_text.warning(f"Primary method failed: {message}")
            status_text.info("Trying fallback methods...")
        
        # Define fallback order based on the primary method
        fallback_methods = get_fallback_methods(method)
        
        for fallback_method in fallback_methods:
            if status_text and hasattr(status_text, 'update_action'):
                status_text.update_action(f"Trying {CONVERSION_METHODS[fallback_method]} method...")
            elif status_text:
                status_text.info(f"Trying {CONVERSION_METHODS[fallback_method]} method...")
                
            success, message, slide_count = _try_method(pptx_path, output_dir, fallback_method, status_text, target_resolution)
            
            if success:
                if status_text and hasattr(status_text, 'update_action'):
                    status_text.update_action(f"Fallback method {CONVERSION_METHODS[fallback_method]} succeeded")
                elif status_text:
                    status_text.success(f"Fallback method {CONVERSION_METHODS[fallback_method]} succeeded")
                break
        
    return success, message, slide_count

def get_fallback_methods(primary_method: ConversionMethod) -> List[ConversionMethod]:
    """
    Get a list of fallback methods to try if the primary method fails.
    
    Args:
        primary_method: The primary conversion method
        
    Returns:
        List of fallback methods in preferred order
    """
    all_methods = list(ConversionMethod)
    # Remove the primary method from the list
    all_methods.remove(primary_method)
    
    # Prioritize methods based on reliability
    if primary_method == ConversionMethod.LIBREOFFICE:
        return [ConversionMethod.PDF2IMAGE, ConversionMethod.PYTHON_PPTX]
    elif primary_method == ConversionMethod.PYTHON_PPTX:
        return [ConversionMethod.LIBREOFFICE, ConversionMethod.PDF2IMAGE]
    else:  # PDF2IMAGE
        return [ConversionMethod.LIBREOFFICE, ConversionMethod.PYTHON_PPTX]

def _try_method(
    pptx_path: str, 
    output_dir: str, 
    method: ConversionMethod,
    status_text: Optional[Any],
    target_resolution: Tuple[int, int]
) -> Tuple[bool, str, int]:
    """
    Try to extract slides using a specific method.
    
    Args:
        pptx_path: Path to the PPTX file
        output_dir: Directory to save the extracted images
        method: Conversion method to use
        status_text: Streamlit text element or StatusManager for status updates
        target_resolution: Target resolution for the extracted images
        
    Returns:
        Tuple of (success, message, slide_count)
    """
    try:
        if method == ConversionMethod.LIBREOFFICE:
            # Use the LibreOffice + pdftoppm method (original implementation)
            from utils.pptx_converter import extract_slides_from_pptx
            return extract_slides_from_pptx(pptx_path, output_dir, status_text)
            
        elif method == ConversionMethod.PYTHON_PPTX:
            # Use direct python-pptx extraction
            from utils.direct_pptx_converter import extract_slides_directly
            return extract_slides_directly(pptx_path, output_dir, status_text, target_resolution)
            
        elif method == ConversionMethod.PDF2IMAGE:
            # Use LibreOffice + pdf2image method
            from utils.pdf_image_converter import convert_with_pdf2image
            return convert_with_pdf2image(pptx_path, output_dir, status_text, target_resolution)
            
        else:
            error_msg = f"Unknown conversion method: {method}"
            if status_text and hasattr(status_text, 'error'):
                status_text.error(error_msg)
            return False, error_msg, 0
            
    except ImportError as e:
        error_msg = f"Required module not available for {method} method: {str(e)}"
        if status_text and hasattr(status_text, 'error'):
            status_text.error(error_msg)
        return False, error_msg, 0
        
    except Exception as e:
        error_msg = f"Error in {method} method: {str(e)}"
        if status_text and hasattr(status_text, 'error'):
            status_text.error(error_msg)
        return False, error_msg, 0