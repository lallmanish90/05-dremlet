import streamlit as st
import os
import re
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    # For newer PIL versions
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    # For older PIL versions
    LANCZOS = Image.LANCZOS
from pptx import Presentation
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

# Import utility functions
from utils.file_operations import (
    get_input_directory,
    find_presentation_files,
    ensure_directory_exists,
    extract_course_lecture_section
)
from utils.image_helpers import increase_image_decompression_limit
from utils.multi_method_converter import (
    ConversionMethod, 
    CONVERSION_METHODS,
    extract_slides_with_method
)

# Increase the Pillow decompression bomb limit for large images
increase_image_decompression_limit()

st.set_page_config(page_title="06 4K Image - Dreamlet", page_icon="🖼️")

# Constants for image processing
LOGO_PATH = 'logo.png'
COPYRIGHT_PATH = 'copyright.txt'
LOGO_SIZE = 250
LOGO_PADDING = 0
LOGO_POSITION = 'top-right'
COPYRIGHT_PADDING = 35
COPYRIGHT_POSITION = 'bottom-center'
FONT_SIZE = 65
FONT_COLOR = (0, 0, 0)  # Black
TARGET_RESOLUTION = (3840, 2160)  # 4K

def read_copyright(file_path):
    """Read copyright text from file"""
    try:
        # Try UTF-8 encoding first
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            
        # Clean up any encoding issues with the copyright symbol
        # Remove any 'A' characters that appear immediately before '©'
        text = re.sub(r'A©', '©', text)
        
        return text
    except UnicodeDecodeError:
        # If UTF-8 fails, try with different encoding
        try:
            with open(file_path, 'r', encoding='cp1252') as f:
                text = f.read().strip()
                # Clean up any encoding issues
                text = re.sub(r'A©', '©', text)
                return text
        except Exception:
            return "© All Rights Reserved"
    except Exception:
        return "© All Rights Reserved"

def get_position(img_width, img_height, element_width, element_height, position, padding):
    """Calculate position based on alignment and padding"""
    if position == 'top-left':
        return (padding, padding)
    elif position == 'top-right':
        return (img_width - element_width - padding, padding)
    elif position == 'bottom-left':
        return (padding, img_height - element_height - padding)
    elif position == 'bottom-right':
        return (img_width - element_width - padding, img_height - element_height - padding)
    elif position == 'bottom-center':
        return ((img_width - element_width) // 2, img_height - element_height - padding)
    else:
        raise ValueError(f"Invalid position: {position}")

def get_font(size):
    """Get a font with fallback options"""
    try:
        # Try to use a common sans-serif font
        return ImageFont.truetype("Arial.ttf", size)
    except IOError:
        try:
            # Fallback to DejaVuSans if Arial is not available
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except IOError:
            # If both fail, use the default font
            return ImageFont.load_default()

def process_image(input_path, output_path, logo, copyright_text):
    """Process an image by adding logo and copyright text"""
    try:
        with Image.open(input_path) as img:
            # Check if the image is already 4K or larger
            if img.width >= TARGET_RESOLUTION[0] and img.height >= TARGET_RESOLUTION[1]:
                processed_img = img.copy()
            else:
                # Upscale the image to 4K while maintaining aspect ratio
                aspect_ratio = img.width / img.height
                if aspect_ratio > 16/9:
                    new_width = TARGET_RESOLUTION[0]
                    new_height = int(TARGET_RESOLUTION[0] / aspect_ratio)
                else:
                    new_height = TARGET_RESOLUTION[1]
                    new_width = int(TARGET_RESOLUTION[1] * aspect_ratio)
                processed_img = img.resize((new_width, new_height), LANCZOS)
            
            # Convert to RGBA if necessary
            if processed_img.mode != 'RGBA':
                processed_img = processed_img.convert('RGBA')

            # Add logo if it exists
            if logo:
                logo_resized = logo.resize((LOGO_SIZE, LOGO_SIZE), LANCZOS)
                logo_pos = get_position(processed_img.width, processed_img.height, 
                                       LOGO_SIZE, LOGO_SIZE, LOGO_POSITION, LOGO_PADDING)
                
                # Create a new image for the logo with an alpha channel
                logo_img = Image.new('RGBA', processed_img.size, (0, 0, 0, 0))
                logo_img.paste(logo_resized, logo_pos, logo_resized)
                
                # Composite the logo onto the processed image
                processed_img = Image.alpha_composite(processed_img, logo_img)

            # Add copyright
            draw = ImageDraw.Draw(processed_img)
            font = get_font(FONT_SIZE)
            
            # Get text size
            text_bbox = draw.textbbox((0, 0), copyright_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            text_pos = get_position(processed_img.width, processed_img.height, 
                                   text_width, text_height, COPYRIGHT_POSITION, COPYRIGHT_PADDING)
            draw.text(text_pos, copyright_text, font=font, fill=FONT_COLOR)

            # Save the processed image with the same format and quality as the original
            if img.format == 'JPEG':
                processed_img = processed_img.convert('RGB')
                processed_img.save(output_path, format=img.format, quality=95, optimize=True, progressive=True)
            elif img.format == 'PNG':
                processed_img.save(output_path, format=img.format, optimize=True)
            else:
                processed_img.save(output_path, format=img.format)
        
        return True
    except Exception as e:
        st.error(f"Error processing {input_path}: {str(e)}")
        return False

def extract_and_upscale_images(pptx_file, output_folder, conversion_method=None, enable_auto_fallback=True, status_mgr=None):
    """
    Extract images from a PPTX file, upscale them to 4K, and save them in the output folder.
    
    Args:
        pptx_file: Path to the PPTX file
        output_folder: Directory to save the extracted images
        conversion_method: Method to use for conversion (libreoffice, python-pptx, pdf2image)
        enable_auto_fallback: Whether to try other methods if the selected one fails
        status_mgr: Optional StatusManager to use for status updates
        
    Returns:
        Tuple of (success, extracted_images, slide_count)
    """
    # Use the multi-method converter
    # If we have a status manager, use it, otherwise fall back to st
    success, message, slide_count = extract_slides_with_method(
        pptx_file, 
        output_folder, 
        method=conversion_method or ConversionMethod.LIBREOFFICE,
        status_text=status_mgr or st,
        enable_auto_fallback=enable_auto_fallback,
        target_resolution=TARGET_RESOLUTION
    )
    
    if not success:
        if status_mgr:
            status_mgr.error(message)
        else:
            st.error(message)
        return False, [], 0
    
    # Gather the paths of the created images
    extracted_images = []
    if slide_count > 0:
        for i in range(1, slide_count + 1):
            image_path = os.path.join(output_folder, f"{i:02d}.png")
            if os.path.exists(image_path):
                extracted_images.append(image_path)
    
    return success, extracted_images, slide_count

def find_presentations() -> List[str]:
    """
    Find all presentation files in the input directory
    
    Returns:
        List of presentation file paths
    """
    input_dir = get_input_directory()
    
    # Find all presentation files
    all_presentations = find_presentation_files(input_dir)
    
    return all_presentations

class StatusManager:
    """A class to manage and simplify status messages during presentation processing"""
    
    def __init__(self, progress_bar, status_text, current_action_text=None):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.current_action_text = current_action_text
        self.current_file = ""
        self.current_action = ""
        self.processed_count = 0
        self.total_count = 0
        self.start_time = datetime.now()
        
    def set_total(self, total):
        """Set the total number of presentations to process"""
        self.total_count = total
        
    def update_progress(self, current_index, filename):
        """Update the progress bar and main status message"""
        self.processed_count = current_index
        self.current_file = filename
        progress = self.processed_count / self.total_count if self.total_count > 0 else 0
        self.progress_bar.progress(progress)
        
        # Calculate and display estimated time remaining
        if self.processed_count > 1:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            time_per_file = elapsed_time / (self.processed_count - 1)  # Exclude current file that just started
            remaining_files = self.total_count - self.processed_count
            remaining_seconds = remaining_files * time_per_file
            remaining_time = str(timedelta(seconds=int(remaining_seconds)))
            
            self.status_text.info(f"Processing {self.processed_count}/{self.total_count}: {filename} (Est. time remaining: {remaining_time})")
        else:
            self.status_text.info(f"Processing {self.processed_count}/{self.total_count}: {filename}")
    
    def update_action(self, message):
        """Update only the current action, not the main status display"""
        self.current_action = message
        if self.current_action_text:
            self.current_action_text.info(message)
        
    def info(self, message):
        """For compatibility with status_text.info but only updates the current action"""
        self.update_action(message)
        
    def warning(self, message):
        """For compatibility with status_text.warning"""
        st.warning(message)
        
    def error(self, message):
        """For compatibility with status_text.error"""
        st.error(message)
        
    def success(self, message):
        """For compatibility with status_text.success"""
        self.status_text.success(message)
        if self.current_action_text:
            self.current_action_text.empty()  # Clear the current action text when we're done

def process_presentations(input_dir: str, progress_bar, status_text, create_without_logo_folder=False, 
                 conversion_method=None, enable_auto_fallback=True, current_action_text=None) -> List[Dict]:
    """
    Process all PPTX files in the input directory structure
    
    Args:
        input_dir: Input directory path
        progress_bar: Streamlit progress bar object
        status_text: Streamlit text area for status updates
        create_without_logo_folder: Whether to create without_logo_png folder for original images
        conversion_method: Method to use for conversion (libreoffice, python-pptx, pdf2image)
        enable_auto_fallback: Whether to try other methods if the selected one fails
        current_action_text: Streamlit text element for displaying current action
        
    Returns:
        List of dictionaries with processing results
    """
    results = []
    
    # Create status manager
    status_mgr = StatusManager(progress_bar, status_text, current_action_text)
    
    # Try to load logo and copyright text
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA") if os.path.exists(LOGO_PATH) else None
        copyright_text = read_copyright(COPYRIGHT_PATH) if os.path.exists(COPYRIGHT_PATH) else "© All Rights Reserved"
    except Exception as e:
        st.warning(f"Could not load logo or copyright: {str(e)}")
        logo = None
        copyright_text = "© All Rights Reserved"
    
    # Find all presentations in the input directory
    all_presentations = find_presentations()
    total_presentations = len(all_presentations)
    status_mgr.set_total(total_presentations)
    
    # Process each presentation
    for i, pptx_file in enumerate(all_presentations):
        # Update progress with file info
        processed_count = i + 1
        file_name = os.path.basename(pptx_file)
        status_mgr.update_progress(processed_count, file_name)
        
        result = {
            "file_path": pptx_file,
            "status": "error",
            "message": "",
            "slide_count": 0,
            "output_dir": ""
        }
        
        try:
            # Get the directory containing the presentation
            pptx_dir = os.path.dirname(pptx_file)
            
            # Check if this is inside another all_pptx directory - avoid nesting
            parent_dir = os.path.basename(pptx_dir)
            if parent_dir == 'all_pptx':
                # Skip processing if this file is already in an all_pptx directory
                result["message"] = "Skipped - file already in all_pptx directory"
                results.append(result)
                continue
            
            # Create 'all_pptx' directory in the same folder as the presentation
            all_pptx_folder = os.path.join(pptx_dir, 'all_pptx')
            os.makedirs(all_pptx_folder, exist_ok=True)
            
            # Create folder with same name as PPTX file for images
            pptx_name = os.path.splitext(os.path.basename(pptx_file))[0]
            lecture_folder = os.path.join(pptx_dir, pptx_name)
            os.makedirs(lecture_folder, exist_ok=True)
            
            # Create "English image" folder inside the lecture folder
            output_folder = os.path.join(lecture_folder, "English image")
            os.makedirs(output_folder, exist_ok=True)
            
            # Create 'without_logo_png' folder inside the output folder only if requested
            without_logo_folder = os.path.join(output_folder, 'without_logo_png')
            if create_without_logo_folder:
                os.makedirs(without_logo_folder, exist_ok=True)
            
            # Check if file is already processed and in all_pptx
            new_pptx_path = os.path.join(all_pptx_folder, os.path.basename(pptx_file))
            if os.path.exists(new_pptx_path):
                # If already processed, just update the result
                result["message"] = "Presentation already processed"
                
                # Count existing images
                png_count = len([f for f in os.listdir(output_folder) 
                               if f.endswith('.png') and not os.path.isdir(os.path.join(output_folder, f))])
                
                result["status"] = "success"
                result["slide_count"] = png_count
                result["output_dir"] = output_folder
                results.append(result)
                continue
                
            # Extract and upscale images from the presentation
            import tempfile
            temp_dir = None
            
            try:
                # Only create and use without_logo_folder if requested
                if create_without_logo_folder:
                    # Ensure the folder exists
                    os.makedirs(without_logo_folder, exist_ok=True)
                    success, extracted_images, slide_count = extract_and_upscale_images(
                        pptx_file, 
                        without_logo_folder,
                        conversion_method=conversion_method,
                        enable_auto_fallback=enable_auto_fallback,
                        status_mgr=status_mgr
                    )
                    
                    # Process each extracted image (add logo and copyright)
                    processed_img_count = 0
                    for img_path in extracted_images:
                        # Original image is in without_logo_folder
                        # Processed image will be in output_folder
                        output_filename = os.path.basename(img_path)
                        output_path = os.path.join(output_folder, output_filename)
                        
                        # Process the image
                        if process_image(img_path, output_path, logo, copyright_text):
                            processed_img_count += 1
                else:
                    # Use a temporary directory that we manage explicitly
                    temp_dir = tempfile.mkdtemp()
                    success, extracted_images, slide_count = extract_and_upscale_images(
                        pptx_file, 
                        temp_dir,
                        conversion_method=conversion_method,
                        enable_auto_fallback=enable_auto_fallback,
                        status_mgr=status_mgr
                    )
                    
                    # Process each extracted image (add logo and copyright)
                    processed_img_count = 0
                    for img_path in extracted_images:
                        # Temporary image is in temp_dir
                        # Processed image will go directly to output_folder
                        output_filename = os.path.basename(img_path)
                        output_path = os.path.join(output_folder, output_filename)
                        
                        # Process the image
                        if process_image(img_path, output_path, logo, copyright_text):
                            processed_img_count += 1
                
                if not success:
                    result["message"] = "Failed to extract images from presentation"
                    results.append(result)
                    continue
            finally:
                # Clean up the temporary directory if it was created
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Move the presentation file to all_pptx folder
            if os.path.exists(pptx_file) and not os.path.exists(new_pptx_path):
                os.rename(pptx_file, new_pptx_path)
            
            # Update result
            result["status"] = "success"
            result["message"] = f"Successfully processed {processed_img_count} images"
            result["slide_count"] = slide_count
            result["output_dir"] = output_folder
        
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
        
        results.append(result)
        
        # Small delay for UI updates
        time.sleep(0.1)
    
    # Ensure progress bar reaches 100% at the end
    progress_bar.progress(1.0)
    
    return results

def main():
    st.title("4K Image")
    st.write("Generate high-resolution 4K images from presentation slides.")
    
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        st.error(f"Input directory not found: {input_dir}")
        st.info("Please create an 'input' directory in the project root and add your files.")
        return
    
    # Find presentations
    all_presentations = find_presentations()
    
    if not all_presentations:
        st.warning("No presentation files found in the input directory.")
        return
    
    # Display number of presentations found
    total_presentations = len(all_presentations)
    st.info(f"Found {total_presentations} presentation files in input directory.")
    
    # Options section
    st.header("Options")
    
    # Option for creating without_logo_png folder
    create_without_logo_folder = st.checkbox("Create 'without_logo_png' folder", value=False, 
                                          help="If checked, a folder containing original images without logo and copyright will be created")
    
    # Conversion method selection
    st.subheader("Conversion Method")
    st.write("Select the method to use for extracting slides from presentations:")
    
    # Create a dropdown for conversion method selection
    conversion_methods = list(CONVERSION_METHODS.items())
    conversion_method = st.selectbox(
        "Select conversion method:",
        options=[method.value for method, _ in conversion_methods],
        format_func=lambda x: CONVERSION_METHODS[x],
        index=0,
        help="Choose the method used to extract slides from presentations"
    )
    
    # Option for automatic fallback
    enable_auto_fallback = st.checkbox(
        "Enable automatic fallback", 
        value=True,
        help="If checked, automatically try other methods if the selected method fails"
    )
    
    # Information about conversion methods
    with st.expander("About Conversion Methods"):
        st.markdown("""
        ### Conversion Methods
        
        #### LibreOffice + pdftoppm (best quality)
        - Uses LibreOffice to convert PPTX to PDF
        - Uses pdftoppm to convert PDF to high-quality images
        - Provides the best visual quality for complex slides
        - Requires LibreOffice and poppler-utils to be installed
        
        #### Direct PPTX processing (fastest)
        - Uses python-pptx to extract slides directly
        - Faster than other methods
        - May not render complex slides as accurately
        - Good for simple presentations with basic elements
        
        #### PDF2Image (most compatible)
        - Uses LibreOffice to convert PPTX to PDF
        - Uses pdf2image library to convert PDF to images
        - More compatible fallback option
        - Slightly lower quality than pdftoppm method
        """)
        
        st.info("💡 Tip: If you encounter issues with one method, try another or enable automatic fallback.")
    
    # Process presentations
    st.header("Extract Presentations")
    
    if st.button("Extract Presentations", disabled=total_presentations == 0):
        if total_presentations == 0:
            st.warning("No presentations found for processing.")
            return
        
        # Process presentations with progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        current_action_text = st.empty()  # For showing the current action
        results_container = st.container()
        
        # Process the presentations with progress tracking
        results = process_presentations(
            input_dir, 
            progress_bar, 
            status_text, 
            create_without_logo_folder,
            conversion_method=conversion_method,
            enable_auto_fallback=enable_auto_fallback,
            current_action_text=current_action_text
        )
        
        # Clear the current action text when done
        current_action_text.empty()
        
        # Complete
        status_text.success(f"Processed {total_presentations} presentations")
        
        # Display results
        with results_container:
            st.subheader("Processing Results")
            
            # Statistics
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = sum(1 for r in results if r["status"] == "error")
            slide_count = sum(r.get("slide_count", 0) for r in results)
            
            st.write(f"✅ Successfully processed: {success_count}")
            st.write(f"❌ Errors: {error_count}")
            st.write(f"📊 Total slides extracted: {slide_count}")
            
            # Detailed results
            for result in results:
                status_icon = "✅" if result["status"] == "success" else "❌"
                file_name = os.path.basename(result["file_path"])
                
                with st.expander(f"{status_icon} {file_name}"):
                    st.write(f"**Status:** {result['status']}")
                    st.write(f"**Message:** {result['message']}")
                    
                    if result["status"] == "success":
                        st.write(f"**Slides extracted:** {result['slide_count']}")
                        st.write(f"**Output directory:** {result['output_dir']}")

if __name__ == "__main__":
    main()
