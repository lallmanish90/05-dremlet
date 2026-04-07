import os
import subprocess
import platform
import tempfile
import glob
import shutil
import time
from PIL import Image
import streamlit as st

def get_libreoffice_path():
    """Get the correct LibreOffice path based on the operating system"""
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

def convert_to_pdf(pptx_path, status_text=None):
    """Convert PPTX to PDF using LibreOffice"""
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(pptx_path))[0] + '.pdf')
    
    try:
        # Get the correct LibreOffice path
        libreoffice_path = get_libreoffice_path()
        if not libreoffice_path:
            error_msg = "LibreOffice not found. Please make sure LibreOffice is installed."
            if status_text:
                status_text.error(error_msg)
            return None, temp_dir, error_msg
            
        # Use soffice (LibreOffice) to convert PPTX to PDF
        if status_text:
            status_text.info(f"Converting presentation to PDF using LibreOffice...")
            
        try:
            # Run LibreOffice headless to convert to PDF, outputting to our temp directory
            process = subprocess.run(
                [libreoffice_path, '--headless', '--convert-to', 'pdf', 
                 '--outdir', temp_dir, pptx_path], 
                check=True, capture_output=True, timeout=120
            )
            
            # Check if PDF was created
            expected_pdf_name = os.path.splitext(os.path.basename(pptx_path))[0] + '.pdf'
            pdf_path = os.path.join(temp_dir, expected_pdf_name)
            
            if not os.path.exists(pdf_path):
                error_msg = f"PDF was not created at expected path: {pdf_path}"
                if status_text:
                    status_text.error(error_msg)
                return None, temp_dir, error_msg
                
            return pdf_path, temp_dir, None
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error converting to PDF: {e}"
            if e.output:
                error_msg += f"\nCommand output: {e.output.decode()}"
            if status_text:
                status_text.error(error_msg)
            return None, temp_dir, error_msg
            
        except subprocess.TimeoutExpired:
            error_msg = "LibreOffice conversion process timed out (120 seconds)"
            if status_text:
                status_text.error(error_msg)
            return None, temp_dir, error_msg
            
    except FileNotFoundError:
        error_msg = "LibreOffice (soffice) not found. Please install LibreOffice."
        if status_text:
            status_text.error(error_msg)
        return None, temp_dir, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during PDF conversion: {str(e)}"
        if status_text:
            status_text.error(error_msg)
        return None, temp_dir, error_msg

def convert_pdf_to_images(pdf_path, output_dir, status_text=None):
    """Convert PDF to PNG images using pdftoppm or pdf2image"""
    try:
        if status_text:
            status_text.info(f"Converting PDF to images...")
            
        # Create a temporary directory for initial images
        temp_img_dir = tempfile.mkdtemp()
        success = False
        error_msg = None
        
        # First try pdftoppm for better performance (if available)
        try:
            # Use pdftoppm to convert PDF pages to PNG images
            # -png: output format
            # -r 300: resolution 300 DPI (good quality without excessive file size)
            if status_text:
                status_text.info("Attempting conversion with pdftoppm...")
                
            process = subprocess.run(
                ['pdftoppm', '-png', '-r', '300', pdf_path, 
                 os.path.join(temp_img_dir, 'slide')], 
                check=True, capture_output=True, timeout=120
            )
            
            # Check if any images were created
            image_files = sorted(glob.glob(os.path.join(temp_img_dir, 'slide-*.png')))
            if image_files:
                success = True
            else:
                error_msg = "No images were created from the PDF"
                
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Try the alternative method if pdftoppm fails
            if status_text:
                status_text.warning(f"pdftoppm method failed: {str(e)}")
                status_text.info("Trying alternative method with pdf2image...")
                
            try:
                # Use pdf2image as a fallback
                from pdf2image import convert_from_path
                
                # Convert PDF to images
                images = convert_from_path(
                    pdf_path,
                    dpi=300,
                    output_folder=temp_img_dir,
                    fmt="png",
                    output_file="slide",
                    paths_only=True
                )
                
                # Check if any images were created
                image_files = sorted(glob.glob(os.path.join(temp_img_dir, 'slide-*.png')))
                if not image_files:
                    # Fallback to whatever pdf2image returned
                    image_files = sorted(images) if images else []
                
                if image_files:
                    success = True
                else:
                    error_msg = "No images were created from the PDF using pdf2image"
            except Exception as pdf2image_error:
                error_msg = f"Both pdftoppm and pdf2image methods failed: {str(pdf2image_error)}"
                if status_text:
                    status_text.error(error_msg)
        
        # If we didn't get any images, return error
        if not success and not image_files:
            if status_text:
                status_text.error(error_msg or "Failed to extract images from PDF")
            return False, error_msg or "Failed to extract images from PDF"
        
        # Process and move each image to the final output directory
        for i, image_file in enumerate(image_files, 1):
            # Create new filename with format 01.png, 02.png, etc.
            new_filename = os.path.join(output_dir, f'{i:02d}.png')
            
            try:
                # Open and upscale the image to 4K
                with Image.open(image_file) as img:
                    # Upscale the image to 4K (3840x2160) maintaining aspect ratio
                    width, height = img.size
                    aspect_ratio = width / height
                    
                    if aspect_ratio > 16/9:  # Wider than 16:9
                        new_width = 3840
                        new_height = int(3840 / aspect_ratio)
                    else:  # Taller than or equal to 16:9
                        new_height = 2160
                        new_width = int(2160 * aspect_ratio)
                    
                    # Set a maximum size to prevent decompression bomb errors
                    # 178,956,970 is the limit mentioned in the error message
                    max_pixels = 178956970
                    if new_width * new_height > max_pixels:
                        scale_factor = (max_pixels / (new_width * new_height)) ** 0.5
                        new_width = int(new_width * scale_factor)
                        new_height = int(new_height * scale_factor)
                        
                        if status_text:
                            status_text.warning(f"Slide {i} was too large, resizing to prevent memory errors.")
                    
                    # Resize with high-quality interpolation
                    upscaled_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Save the upscaled image with new filename
                    upscaled_img.save(new_filename, 'PNG', optimize=True)
            except Exception as e:
                error_msg = f"Error processing image {image_file}: {str(e)}"
                if status_text:
                    status_text.error(error_msg)
                continue
                
        # Return success
        return True, None
            
    except Exception as e:
        error_msg = f"Unexpected error during image conversion: {str(e)}"
        if status_text:
            status_text.error(error_msg)
        return False, error_msg
    finally:
        # Clean up the temporary directory
        if 'temp_img_dir' in locals() and os.path.exists(temp_img_dir):
            shutil.rmtree(temp_img_dir, ignore_errors=True)

def extract_slides_from_pptx(pptx_path, output_dir, status_text=None):
    """
    Extract slides from a PPTX file, convert to 4K images, and save them.
    
    Args:
        pptx_path: Path to the PPTX file
        output_dir: Directory to save the extracted images
        status_text: Streamlit text element for status updates
        
    Returns:
        Tuple of (success, message, slide_count)
    """
    temp_dir = None
    pdf_path = None
    
    try:
        # Step 1: Convert PPTX to PDF
        if status_text:
            status_text.info(f"Processing presentation: {os.path.basename(pptx_path)}")
        
        pdf_path, temp_dir, error = convert_to_pdf(pptx_path, status_text)
        if error:
            return False, error, 0
            
        # Step 2: Convert PDF to images
        success, error = convert_pdf_to_images(pdf_path, output_dir, status_text)
        if not success:
            return False, error, 0
            
        # Count the number of images extracted
        image_count = len([f for f in os.listdir(output_dir) if f.endswith('.png') and f[0].isdigit()])
        
        return True, f"Successfully extracted {image_count} slides", image_count
        
    except Exception as e:
        error_msg = f"Error extracting slides: {str(e)}"
        if status_text:
            status_text.error(error_msg)
        return False, error_msg, 0
        
    finally:
        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass