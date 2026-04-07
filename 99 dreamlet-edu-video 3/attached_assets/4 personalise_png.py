import os
import stat
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# Constants (moved from config.ini)
LOGO_PATH = 'logo.png'
COPYRIGHT_PATH = 'copyright.txt'
INPUT_FOLDER = 'input'
# OUTPUT_FOLDER = 'output'  # This line can be removed
LOGO_SIZE = 250
LOGO_PADDING = 0
LOGO_POSITION = 'top-right'
COPYRIGHT_PADDING = 35
COPYRIGHT_POSITION = 'bottom-center'
FONT_SIZE = 65
FONT_COLOR = (0, 0, 0)  # Black

def read_copyright(file_path):
    import re
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
    try:
        with Image.open(input_path) as img:
            # Check if the image is already 4K or larger
            if img.width >= 3840 and img.height >= 2160:
                processed_img = img.copy()
            else:
                # Upscale the image to 4K while maintaining aspect ratio
                aspect_ratio = img.width / img.height
                if aspect_ratio > 16/9:
                    new_width = 3840
                    new_height = int(3840 / aspect_ratio)
                else:
                    new_height = 2160
                    new_width = int(2160 * aspect_ratio)
                processed_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to RGBA if necessary
            if processed_img.mode != 'RGBA':
                processed_img = processed_img.convert('RGBA')

            # Add logo
            logo_resized = logo.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
            logo_pos = get_position(processed_img.width, processed_img.height, LOGO_SIZE, LOGO_SIZE, LOGO_POSITION, LOGO_PADDING)
            
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
            
            text_pos = get_position(processed_img.width, processed_img.height, text_width, text_height, COPYRIGHT_POSITION, COPYRIGHT_PADDING)
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
        print(f"Error processing {input_path}: {str(e)}")
        return False

def ask_user_preference():
    while True:
        choice = input("This file has already been processed. What would you like to do?\n"
                       "1. Skip this and all future already-processed files\n"
                       "2. Process this and all future already-processed files\n"
                       "3. Ask me every time\n"
                       "Enter your choice (1/2/3): ")
        if choice in ['1', '2', '3']:
            return int(choice)
        print("Invalid choice. Please enter 1, 2, or 3.")

def main():
    print("Starting script...")
    # Load logo and copyright text (keep error messages if loading fails)
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        copyright_text = read_copyright(COPYRIGHT_PATH)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Error: {str(e)}")
        return

    if not os.path.exists(INPUT_FOLDER):
        print(f"Error: Input folder not found at {INPUT_FOLDER}")
        return

    total_files = sum(1 for root, _, files in os.walk(INPUT_FOLDER) for file in files if file.lower().endswith(('.png', '.jpg', '.jpeg')))
    processed_files = 0
    skipped_files = 0
    user_preference = None
    
    with tqdm(total=total_files, desc="Processing images", unit="image") as pbar:
        for root, _, files in os.walk(INPUT_FOLDER):
            if os.path.basename(root).startswith("Lecture"):
                without_logo_folder = os.path.join(root, 'without_logo_png')
                os.makedirs(without_logo_folder, exist_ok=True)

                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        input_path = os.path.join(root, file)
                        without_logo_path = os.path.join(without_logo_folder, file)
                        
                        if not os.path.exists(without_logo_path):
                            os.rename(input_path, without_logo_path)
                        
                        if os.path.exists(input_path):
                            if user_preference is None:
                                user_preference = ask_user_preference()
                            
                            if user_preference in [1, 3] and user_preference == 1 or (user_preference == 3 and ask_user_preference() == 1):
                                skipped_files += 1
                                pbar.update(1)
                                continue
                        
                        if process_image(without_logo_path, input_path, logo, copyright_text):
                            processed_files += 1
                            pbar.update(1)
                        else:
                            skipped_files += 1
                            pbar.update(1)

    print(f"\nProcessing completed. Processed: {processed_files}, Skipped: {skipped_files}")

if __name__ == "__main__":
    main()
