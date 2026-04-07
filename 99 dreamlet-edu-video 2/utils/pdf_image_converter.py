import os
import tempfile
import subprocess
import shutil
from PIL import Image
import glob

def convert_with_pdf2image(pptx_path, output_dir, status_text=None, target_resolution=(3840, 2160)):
    """
    Convert PPTX to images using LibreOffice for PPTX→PDF and pdf2image for PDF→PNG.
    This is more compatible but might be slower than other methods.
    
    Args:
        pptx_path: Path to the PPTX file
        output_dir: Directory to save the extracted images
        status_text: Streamlit text element for status updates
        target_resolution: Target resolution (width, height) for upscaling
        
    Returns:
        Tuple of (success, message, slide_count)
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(pptx_path))[0] + '.pdf')
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        if status_text:
            status_text.info(f"Converting presentation using pdf2image: {os.path.basename(pptx_path)}")
        
        # Step 1: Get LibreOffice path
        libreoffice_path = get_libreoffice_path()
        if not libreoffice_path:
            error_msg = "LibreOffice not found. Please make sure LibreOffice is installed."
            if status_text:
                status_text.error(error_msg)
            return False, error_msg, 0
        
        # Step 2: Convert PPTX to PDF
        try:
            if status_text:
                status_text.info("Converting presentation to PDF...")
            
            process = subprocess.run(
                [libreoffice_path, '--headless', '--convert-to', 'pdf', 
                 '--outdir', temp_dir, pptx_path], 
                check=True, capture_output=True, timeout=120
            )
            
            # Verify PDF was created
            if not os.path.exists(pdf_path):
                error_msg = f"PDF was not created at expected path: {pdf_path}"
                if status_text:
                    status_text.error(error_msg)
                return False, error_msg, 0
                
        except Exception as e:
            error_msg = f"Error converting to PDF: {str(e)}"
            if status_text:
                status_text.error(error_msg)
            return False, error_msg, 0
        
        # Step 3: Convert PDF to images using pdf2image
        try:
            if status_text:
                status_text.info("Converting PDF to images using pdf2image...")
            
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=300,
                fmt="png",
            )
            
            slide_count = len(images)
            
            if slide_count == 0:
                error_msg = "No slides were extracted from the PDF"
                if status_text:
                    status_text.error(error_msg)
                return False, error_msg, 0
            
            # Process each image
            for i, img in enumerate(images, 1):
                # Upscale to target resolution while maintaining aspect ratio
                aspect_ratio = img.width / img.height
                
                if aspect_ratio > target_resolution[0] / target_resolution[1]:
                    # Wider than target
                    new_width = target_resolution[0]
                    new_height = int(target_resolution[0] / aspect_ratio)
                else:
                    # Taller than or equal to target
                    new_height = target_resolution[1]
                    new_width = int(target_resolution[1] * aspect_ratio)
                
                # Resize image
                resized = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Save image to output directory
                output_path = os.path.join(output_dir, f"{i:02d}.png")
                resized.save(output_path, "PNG", optimize=True)
                
                if status_text:
                    status_text.info(f"Processed slide {i}/{slide_count}")
            
            return True, f"Successfully extracted {slide_count} slides", slide_count
            
        except Exception as e:
            error_msg = f"Error converting PDF to images: {str(e)}"
            if status_text:
                status_text.error(error_msg)
            return False, error_msg, 0
    
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def get_libreoffice_path():
    """Get the correct LibreOffice path based on the operating system"""
    import platform
    if platform.system() == 'Darwin':  # macOS
        # Try different possible paths for LibreOffice on macOS
        possible_paths = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            '/Applications/LibreOffice.app/Contents/MacOS/soffice.bin',
            '/opt/homebrew/bin/soffice',
            '/usr/local/bin/soffice'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    else:
        return 'soffice'  # Default path for other systems