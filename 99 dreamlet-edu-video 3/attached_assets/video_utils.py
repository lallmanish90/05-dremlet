import os
import cv2
import numpy as np
from PIL import Image
import ffmpeg

# Define constants
OUTPUT_DIR = 'output'
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'output_video_temp.mp4')
FINAL_OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'final_output_video.mp4')
TEMP_AUDIO = os.path.join(OUTPUT_DIR, 'temp_audio.wav')

def upscale_image(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            return img.resize((3840, 2160), Image.LANCZOS)
    except Exception as e:
        print(f"Error processing image {image_path}: {str(e)}")
        return None

def process_image(image_path):
    img = upscale_image(image_path)
    if img is not None:
        return np.array(img)
    return None

def create_video_from_images(input_dir, image_files, audio_files):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 3, (3840, 2160))

    for img_file, audio_file in zip(image_files, audio_files):
        img_path = os.path.join(input_dir, img_file)
        audio_path = os.path.join(input_dir, audio_file)

        img = process_image(img_path)
        if img is None:
            continue

        audio_duration = float(ffmpeg.probe(audio_path)['streams'][0]['duration'])
        frames = int(audio_duration * 3)

        for _ in range(frames):
            video.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    video.release()
    return f"Created video from {len(image_files)} images and {len(audio_files)} audio files"

def combine_audio_files(input_dir, audio_files):
    if not audio_files:
        print("No audio files to combine.")
        return

    input_audio = [ffmpeg.input(os.path.join(input_dir, audio)) for audio in audio_files]
    if not input_audio:
        print("No valid input audio streams.")
        return
    
    try:
        (
            ffmpeg
            .concat(*input_audio, v=0, a=1)
            .output(TEMP_AUDIO)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(f"Error combining audio files: {e.stderr.decode()}")
        raise
    return f"Combined {len(audio_files)} audio files"

def add_audio_to_video():
    try:
        input_video = ffmpeg.input(OUTPUT_VIDEO)
        input_audio = ffmpeg.input(TEMP_AUDIO)
        (
            ffmpeg
            .output(input_video, input_audio, FINAL_OUTPUT_VIDEO, vcodec='libx264', acodec='aac', strict='experimental')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        os.remove(TEMP_AUDIO)
        os.remove(OUTPUT_VIDEO)
        print(f"Video generation complete. Final output file: {FINAL_OUTPUT_VIDEO}")
    except ffmpeg.Error as e:
        print(f"Error adding audio to video: {e.stderr.decode()}")
        raise
    return f"Added audio to video: {FINAL_OUTPUT_VIDEO}"
