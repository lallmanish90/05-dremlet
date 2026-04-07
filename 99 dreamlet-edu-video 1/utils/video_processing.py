import os
import subprocess
import glob
from typing import List, Dict, Tuple, Optional
import tempfile
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_sorted_files(directory: str, file_type: str) -> List[str]:
    """
    Get sorted list of files of a specific type with full paths
    
    Args:
        directory: Directory to search in
        file_type: Type of files to search for ('image' or 'audio')
        
    Returns:
        List of sorted file paths
    """
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
    else:
        raise ValueError("Invalid file_type. Use 'image' or 'audio'.")
    
    if not os.path.exists(directory):
        return []
    
    # Get all files with matching extensions
    files = [os.path.join(directory, f) for f in os.listdir(directory) 
             if os.path.isfile(os.path.join(directory, f)) and 
             f.lower().endswith(extensions)]
    
    # Sort numerically by the number in the filename
    return sorted(files, key=lambda f: int(os.path.splitext(os.path.basename(f))[0]) 
                  if os.path.splitext(os.path.basename(f))[0].isdigit() else 999)

def upscale_image(image_path: str, target_resolution: Tuple[int, int] = (3840, 2160)) -> np.ndarray:
    """
    Load and upscale an image to target resolution
    
    Args:
        image_path: Path to the image file
        target_resolution: Target resolution (width, height)
        
    Returns:
        Upscaled image as numpy array
    """
    # Load the image using PIL for high-quality upscaling
    img = Image.open(image_path)
    
    # Resize the image to 4K using high-quality Lanczos resampling
    img_resized = img.resize(target_resolution, Image.LANCZOS)
    
    # Convert to numpy array for OpenCV compatibility
    img_array = np.array(img_resized)
    
    # Convert to RGB if the image is in RGBA mode
    if img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    
    return img_array

def generate_mp4_from_slides_and_audio(
    image_dir: str, 
    audio_dir: str, 
    output_path: str, 
    fps: int = 3
) -> Tuple[bool, str]:
    """
    Generate MP4 video from slides and audio
    
    Args:
        image_dir: Directory containing slide images
        audio_dir: Directory containing audio files
        output_path: Path to save the output video
        fps: Frames per second (default: 3)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Get list of slide images and audio files
        slides = get_sorted_files(image_dir, "image")
        audio_files = get_sorted_files(audio_dir, "audio")
        
        if not slides:
            return False, "No slide images found"
        
        if not audio_files:
            return False, "No audio files found"
        
        # Ensure slide and audio counts match
        if len(slides) != len(audio_files):
            return False, f"Mismatch between slide count ({len(slides)}) and audio count ({len(audio_files)})"
        
        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create segment videos for each slide + audio pair
            segment_files = []
            
            for i, (slide, audio) in enumerate(zip(slides, audio_files)):
                segment_path = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
                segment_files.append(segment_path)
                
                # Upscale image to 4K if needed (doing this here ensures we only process images as needed)
                upscaled_image_path = os.path.join(temp_dir, f"upscaled_{i:03d}.png")
                img = upscale_image(slide, (3840, 2160))
                cv2.imwrite(upscaled_image_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                
                # Get audio duration
                duration_command = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", audio
                ]
                
                duration_result = subprocess.run(
                    duration_command, 
                    capture_output=True, 
                    text=True,
                    check=True
                )
                
                duration = float(duration_result.stdout.strip())
                
                # Create video segment with 4K resolution
                ffmpeg_command = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-framerate", str(fps),
                    "-i", upscaled_image_path,
                    "-i", audio,
                    "-c:v", "libx264", "-tune", "stillimage",
                    "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    "-t", str(duration),
                    segment_path
                ]
                
                subprocess.run(ffmpeg_command, check=True, capture_output=True)
            
            # Step 2: Create a file list for concatenation
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as f:
                for segment in segment_files:
                    f.write(f"file '{segment}'\n")
            
            # Step 3: Concatenate all segments
            temp_output = os.path.join(temp_dir, "temp_output.mp4")
            concat_command = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                temp_output
            ]
            
            subprocess.run(concat_command, check=True, capture_output=True)
            
            # Step 4: Optimize for web streaming with proper encoding
            final_command = [
                "ffmpeg", "-y",
                "-i", temp_output,
                "-c:v", "libx264", "-preset", "medium", 
                "-crf", "22",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "faststart",
                output_path
            ]
            
            subprocess.run(final_command, check=True, capture_output=True)
            
            return True, f"Video successfully generated at {output_path}"
    except subprocess.CalledProcessError as e:
        return False, f"FFmpeg error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}"
    except Exception as e:
        return False, f"Error generating video: {str(e)}"

def count_mp4_duration(mp4_path: str) -> Tuple[bool, float]:
    """
    Count the duration of an MP4 video
    
    Args:
        mp4_path: Path to MP4 file
        
    Returns:
        Tuple of (success, duration_in_seconds)
    """
    try:
        # Use ffprobe to get duration
        ffprobe_command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", mp4_path
        ]
        
        result = subprocess.run(
            ffprobe_command, 
            capture_output=True, 
            text=True,
            check=True
        )
        
        duration = float(result.stdout.strip())
        return True, duration
    except subprocess.CalledProcessError:
        return False, 0.0
    except Exception:
        return False, 0.0
