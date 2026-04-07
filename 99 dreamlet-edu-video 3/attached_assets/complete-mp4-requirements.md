# Complete MP4 Generation Requirements

## 1. Overview

The MP4 generation feature is designed to combine audio files with corresponding slide images to create educational videos with properly timed slide transitions. This document outlines the specific requirements for implementing this feature in the Dreamlet Educational Video Production System.

## 2. Feature Purpose

To combine properly matched audio files and slide images into high-quality educational videos with accurately timed slide transitions, maintaining synchronization between audio narration and visual content.

## 3. Input Structure

### 3.1 Input Folder Structure
The system processes folders with the following structure:
```
input/
  ├── [Subject Folder]/
  │   ├── [Course Folder]/
  │   │   ├── [Section Folder]/
  │   │   │   ├── Lecture XX/
  │   │   │   │   ├── Images/
  │   │   │   │   │   ├── 01.png
  │   │   │   │   │   ├── 02.png
  │   │   │   │   │   └── ...
  │   │   │   │   └── Music/
  │   │   │   │       ├── 01.mp3
  │   │   │   │       ├── 02.mp3
  │   │   │   │       └── ...
  │   │   │   ├── all_pptx/
  │   │   │   ├── all_slides/
  │   │   │   └── all_transcripts/
  │   │   └── [Other Section Folders]
  │   └── [Other Course Folders]
  └── [Other Subject Folders]
```

### 3.2 Variable Structure Considerations
The application must handle multiple variations in this structure:
1. Subject level may be absent (courses directly in input folder)
2. Section level may be absent (files directly in course folders)
3. Both subject and section levels may be absent

### 3.3 File Matching
The system must match each image file with its corresponding audio file based on their numbered filename (e.g., 01.png with 01.mp3), and combine them in the correct sequence to create a complete educational video.

## 4. Output Structure

### 4.1 Output Folder Structure
```
output/
  ├── [Subject Folder]/
  │   ├── [Course Folder]/
  │   │   ├── [Section Folder]/
  │   │   │   ├── Lecture 01.mp4
  │   │   │   ├── Lecture 02.mp4
  │   │   │   └── ...
  │   │   └── [Other Section Folders]
  │   └── [Other Course Folders]
  └── [Other Subject Folders]
```

### 4.2 Key Output Structure Rules
1. **Subject, Course, and Section folders** are preserved in the output with the same names and hierarchy as in the input.
2. **Lecture folders are NOT preserved** in the output structure. Instead, the MP4 files are named after their source lecture folders and placed directly in the respective section folder.
3. **Utility folders** like "all_pptx", "all_slides", and "all_transcripts" are NOT included in the output structure.
4. **MP4 file naming convention**: The MP4 files should be named exactly the same as their source lecture folder names with the .mp4 extension (e.g., "Lecture 01.mp4").

### 4.3 Example File Path Transformations
1. **Standard Structure**:
   - Input: `input/Subject A/Course XYZ/Section 01/Lecture 05/Images/` and `.../Music/`
   - Output: `output/Subject A/Course XYZ/Section 01/Lecture 05.mp4`

2. **No Section Level**:
   - Input: `input/Subject A/Course XYZ/Lecture 05/Images/` and `.../Music/`
   - Output: `output/Subject A/Course XYZ/Lecture 05.mp4`

3. **No Subject Level**:
   - Input: `input/Course XYZ/Section 01/Lecture 05/Images/` and `.../Music/`
   - Output: `output/Course XYZ/Section 01/Lecture 05.mp4`

4. **Minimal Structure**:
   - Input: `input/Course XYZ/Lecture 05/Images/` and `.../Music/`
   - Output: `output/Course XYZ/Lecture 05.mp4`

## 5. User Interface Requirements

### 5.1 Input Selection
- System must provide controls for selecting the root input directory
- System must provide an option to specify the output directory (defaulting to "output" in the project root)

### 5.2 Processing Options
- System must provide an option to process all detected lecture folders or select specific lectures
- System must provide options for handling already processed lectures (skip, overwrite, or prompt)

### 5.3 Progress Tracking
- System must implement a Streamlit progress bar showing:
  - Overall progress across all lectures being processed
  - Current lecture being processed
  - Current processing stage (image processing, audio combining, etc.)

### 5.4 Status Display
- System must display processing statistics:
  - Number of lectures processed
  - Number of images and audio files in each lecture
  - Processing time
  - Success/failure status for each lecture

## 6. Functional Requirements

### 6.1 File Discovery and Matching
- System must traverse the input directory structure recursively to find lecture folders
- System must identify lecture folders that contain both an "Images" subfolder and a "Music" subfolder
- System must match audio files with corresponding slide images based on their numerical filename (e.g., 01.png with 01.mp3)
- System must verify that the number of audio files matches the number of slide images
- System must sort files numerically to ensure correct sequence (01, 02, 03, etc.)
- System must handle multi-digit numbering correctly (e.g., 01 comes before 10)

### 6.2 Image Processing
- System must load and process each image file
- System must upscale images to 4K resolution (3840x2160) using high-quality interpolation (Lanczos algorithm)
- System must convert images to the appropriate format for video processing
- System must handle various image formats (JPG, JPEG, PNG, BMP)

### 6.3 Audio Processing
- System must load and process each audio file
- System must determine the duration of each audio file
- System must combine multiple audio files into a single audio track in the correct sequence
- System must handle various audio formats (MP3, WAV, OGG)

### 6.4 Video Generation
- System must create a video with static slides where each slide duration is synchronized with its corresponding audio duration
- System must maintain a frame rate of 3 FPS for smooth transitions while keeping slides static
- System must calculate the appropriate number of frames for each slide based on its audio duration
- System must combine the processed images into a video file using the OpenCV library
- System must add the combined audio to the video using ffmpeg
- System must encode the video using H.264 video codec and AAC audio codec for compatibility
- System must generate the output at 4K resolution (3840x2160)

### 6.5 Output Handling
- System must create the appropriate output directory structure mirroring the input structure
- System must save the final MP4 file directly in the appropriate section folder with the lecture folder name
- System must clean up temporary files after successful processing
- System must handle file naming conflicts appropriately

### 6.6 Error Handling
- System must display appropriate error messages when:
  - Number of images doesn't match number of audio files
  - Image or audio files cannot be processed
  - Output directory cannot be written to
  - Insufficient disk space
- System must handle errors gracefully without crashing
- System must continue processing other lectures even if one lecture fails
- System must log all errors for review

## 7. Technical Requirements

### 7.1 Performance
- System must process files efficiently, with appropriate progress indicators
- System must implement caching where appropriate to improve performance
- System must efficiently handle image upscaling to 4K resolution
- System must optimize memory usage when processing large files
- System must be able to process multiple lectures in batch mode
- System must support recursive directory traversal to find all lecture folders regardless of depth in the folder structure

### 7.2 Dependencies
- System requires the following libraries:
  - Streamlit for the user interface
  - OpenCV (cv2) for image processing and video generation
  - PIL/Pillow for high-quality image upscaling
  - ffmpeg-python for audio and video manipulation
  - NumPy for efficient array operations
  - tqdm for progress tracking in CLI mode

## 8. Integration with Streamlit

### 8.1 Page Implementation
- The MP4 generation feature must be implemented as Page 07 in the Streamlit application
- The implementation file must be named "07MP4.py" following the project naming convention
- The page must integrate with the overall application navigation

### 8.2 UI Components
- All user interface components must be implemented using Streamlit
- Progress must be displayed using Streamlit progress bars
- File selection must use Streamlit's file uploader or path input mechanism
- Status information must be displayed using appropriate Streamlit components

## 9. Implementation Approach

The implementation should follow the approach used in the existing code:
- Use OpenCV for image processing and video frame generation
- Use ffmpeg for audio/video encoding and composition
- Process images at 4K resolution (3840x2160)
- Maintain timing synchronization between audio and slides
- Use the folder traversal logic to process all eligible folders
- Clean up temporary files after successful processing

## 10. Code Reference

The following code snippets illustrate the key operations for the MP4 generation process:

### 10.1 Video Creation from Images
```python
def create_video_from_images(input_dir, image_files, audio_files):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 3, (3840, 2160))

    for img_file, audio_file in zip(image_files, audio_files):
        img_path = os.path.join(input_dir, img_file)
        audio_path = os.path.join(input_dir, audio_file)

        img = process_image(img_path)
        if img is None:
            continue

        # Calculate frames based on audio duration
        audio_duration = float(ffmpeg.probe(audio_path)['streams'][0]['duration'])
        frames = int(audio_duration * 3)  # 3 fps for smooth transitions

        for _ in range(frames):
            video.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    video.release()
    return f"Created video from {len(image_files)} images and {len(audio_files)} audio files"
```

### 10.2 Audio Combination
```python
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
```

### 10.3 Adding Audio to Video
```python
def add_audio_to_video():
    try:
        input_video = ffmpeg.input(OUTPUT_VIDEO)
        input_audio = ffmpeg.input(TEMP_AUDIO)
        (
            ffmpeg
            .output(input_video, input_audio, FINAL_OUTPUT_VIDEO, 
                   vcodec='libx264', acodec='aac', strict='experimental')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        os.remove(TEMP_AUDIO)
        os.remove(OUTPUT_VIDEO)
    except ffmpeg.Error as e:
        print(f"Error adding audio to video: {e.stderr.decode()}")
        raise
    return f"Added audio to video: {FINAL_OUTPUT_VIDEO}"
```

### 10.4 Finding Matching Files
```python
def get_sorted_files(directory, file_type):
    if file_type == 'image':
        extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        search_dir = os.path.join(directory, 'Images')
    elif file_type == 'audio':
        extensions = ('.mp3', '.wav', '.ogg')
        search_dir = os.path.join(directory, 'Music')
    else:
        raise ValueError("Invalid file_type. Use 'image' or 'audio'.")
    
    if not os.path.exists(search_dir):
        return []
    
    files = [f for f in os.listdir(search_dir) if os.path.isfile(os.path.join(search_dir, f)) 
             and f.lower().endswith(extensions)]
    
    # Sort numerically by the number in the filename
    return sorted(files, key=lambda f: int(os.path.splitext(f)[0]))
```

### 10.5 Output Path Generation
```python
def generate_output_path(input_path, root_input_path, root_output_path):
    # Get the relative path from the root input path
    relative_path = os.path.relpath(input_path, root_input_path)
    
    # Split the path to identify components
    path_components = relative_path.split(os.sep)
    
    # Extract lecture name (last component)
    lecture_name = path_components[-1]
    
    # Remove the lecture folder from the path components
    path_components = path_components[:-1]
    
    # Create the output directory path
    output_dir = os.path.join(root_output_path, *path_components)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the full output file path with mp4 extension
    output_file = os.path.join(output_dir, f"{lecture_name}.mp4")
    
    return output_file
```
