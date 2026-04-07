import os
from PIL import Image
import glob
import subprocess
import platform

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

def convert_to_pdf(pptx_path):
    """Convert PPTX to PDF using LibreOffice"""
    pdf_path = os.path.splitext(pptx_path)[0] + '.pdf'
    
    # Get the correct LibreOffice path
    libreoffice_path = get_libreoffice_path()
    if not libreoffice_path:
        print("LibreOffice not found. Please make sure LibreOffice is installed.")
        return None
    
    # Use soffice (LibreOffice) to convert PPTX to PDF
    try:
        subprocess.run([libreoffice_path, '--headless', '--convert-to', 'pdf', pptx_path], 
                      check=True, capture_output=True)
        return pdf_path
    except subprocess.CalledProcessError as e:
        print(f"Error converting to PDF: {e}")
        print(f"Command output: {e.output.decode() if e.output else 'No output'}")
        return None
    except FileNotFoundError:
        print("LibreOffice (soffice) not found. Please install LibreOffice.")
        return None

def upscale_to_4k(image):
    """Upscale image to 4K resolution (3840x2160) maintaining aspect ratio"""
    width, height = image.size
    aspect_ratio = width / height
    
    if aspect_ratio > 16/9:  # Wider than 16:9
        new_width = 3840
        new_height = int(3840 / aspect_ratio)
    else:  # Taller than or equal to 16:9
        new_height = 2160
        new_width = int(2160 * aspect_ratio)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def process_pptx(pptx_path):
    # Create output directory with same name as PPTX file
    output_dir = os.path.splitext(pptx_path)[0]
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert PPTX to PDF
    pdf_path = convert_to_pdf(pptx_path)
    if not pdf_path:
        print(f"Failed to process {pptx_path}")
        return
    
    try:
        # Convert PDF to images using pdftoppm if available
        subprocess.run(['pdftoppm', '-png', '-r', '300', pdf_path, 
                       os.path.join(output_dir, 'slide')], check=True)
        
        # Process all generated PNG files and rename them
        for i, png_file in enumerate(sorted(glob.glob(os.path.join(output_dir, 'slide-*.png'))), 1):
            with Image.open(png_file) as img:
                # Upscale to 4K
                upscaled_img = upscale_to_4k(img)
                # Create new filename with format 01.png, 02.png, etc.
                new_filename = os.path.join(output_dir, f'{i:02d}.png')
                # Save the upscaled image with new filename
                upscaled_img.save(new_filename, 'PNG')
                # Remove the old file
                os.remove(png_file)
            print(f'Processed slide {i:02d} from {pptx_path}')
        
    except subprocess.CalledProcessError as e:
        print(f"Error converting PDF to images: {e}")
        print(f"Command output: {e.output.decode() if e.output else 'No output'}")
    except FileNotFoundError:
        print("pdftoppm not found. Please install poppler-utils.")
    finally:
        # Clean up the temporary PDF file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def main():
    # Find all PPTX files in current directory
    pptx_files = glob.glob('*.pptx')
    
    if not pptx_files:
        print("No PPTX files found in current directory")
        return
    
    for pptx_file in pptx_files:
        print(f'Processing {pptx_file}...')
        process_pptx(pptx_file)
        print(f'Finished processing {pptx_file}')

if __name__ == '__main__':
    main() 