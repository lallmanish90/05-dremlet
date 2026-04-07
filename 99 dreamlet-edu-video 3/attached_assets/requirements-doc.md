# Project Requirements Document: Dreamlet Educational Video Production System

## 1. Introduction

### 1.1 Purpose
This document outlines the requirements for the Dreamlet Educational Video Production System, a multi-functional Streamlit application designed to streamline the creation of educational videos by automating various aspects of the production pipeline.

### 1.2 Project Scope
The system will facilitate the transformation of educational content from transcript and slide files into professional video presentations through a series of nine specialized processing functions, each represented by a dedicated page in the application.

### 1.3 Document Conventions
- **Must/Shall** - Mandatory requirement
- **Should** - Recommended requirement
- **May/Can** - Optional requirement

## 2. System Overview

### 2.1 System Description
The Dreamlet Educational Video Production System is designed to automate and streamline the process of creating educational videos from transcript files, slide description files, and PowerPoint presentations. The system combines these elements to produce high-quality educational videos with synchronized audio and visual content.

### 2.2 System Context
The system operates on a flexible file structure containing transcript, slide, and presentation files organized by subject, course, and section. It performs various operations on these files to generate the components needed for educational video production.

### 2.3 User Classes and Characteristics
- **Content Managers**: Responsible for managing and organizing educational content
- **Video Production Staff**: Responsible for creating and editing educational videos
- **Quality Assurance Team**: Responsible for ensuring consistency and quality

### 2.4 Development Platform
- **The application must be developed using Streamlit**
- All pages and functionality must be implemented as Streamlit components
- The application must leverage Streamlit's interactive features for user input and data visualization

## 3. Input Content Types

### 3.1 Transcript Files
- **Content**: Text to be spoken in the educational video
- **Format**: `.txt` or `.md` files
- **Structure**: Divided into sections corresponding to individual slides
- **Purpose**: Source for audio narration

### 3.2 Slide Files
- **Content**: Descriptions of what will appear visually for each slide
- **Format**: `.txt` or `.md` files
- **Structure**: Numbered slide entries with descriptions
- **Purpose**: Blueprint for presentation creation

### 3.3 Presentation Files
- **Content**: Visual slides based on slide file descriptions
- **Format**: `.pptx` files only
- **Structure**: Series of slides matching the slide file specifications
- **Purpose**: Visual component of the final video

### 3.4 Content Relationship
- Each transcript section corresponds to one slide in the slide file
- Each slide description in the slide file corresponds to one slide in the presentation file
- All three must maintain perfect alignment for proper video production

## 4. Input Folder Structure

### 4.1 Standard Structure Hierarchy
```
input/
  ├── subject_folder_1/
  │   ├── course_folder_1/
  │   │   ├── section_folder_1/
  │   │   │   ├── transcript.txt
  │   │   │   ├── slides.txt
  │   │   │   ├── presentation.pptx
  │   │   │   └── ...
  │   │   ├── section_folder_2/
  │   │   └── ...
  │   ├── course_folder_2/
  │   └── ...
  └── subject_folder_2/
      └── ...
```

### 4.2 Variable Structure Considerations
The application must handle multiple variations in this structure:

1. **Incomplete Hierarchy**
   - Subject level may be absent (courses directly in input folder)
   - Section level may be absent (files directly in course folders)
   - Both subject and section levels may be absent

2. **Dynamic Path Handling**
   - The application must recursively identify and process target files regardless of path depth
   - Path parsing logic must adapt to the available structure components

### 4.3 Output Structure
- The system must create an "output" folder in the project root
- Output files must maintain the exact same folder structure as the input folder
- All processed files and generated content must be organized within this mirrored structure

## 5. Application Structure

### 5.1 Pages Overview
1. **01 Adjust** - Make necessary adjustments to transcript and slide files
2. **02 Rename** - Fix incorrectly named files
3. **03 Count** - Verify alignment between transcript sections, slide descriptions, and presentation slides
4. **04 Save Text** - Break transcript files into sections for TTS processing
5. **05 TTS** - Convert transcript sections to MP3 audio files
6. **06 4K Image** - Generate high-resolution images from presentation slides
7. **07 MP4** - Combine audio and images to create final educational videos
8. **08 Multilingual Text** - Handle multilingual text processing
9. **09 Multilingual TTS** - Handle multilingual text-to-speech processing

### 5.2 Workflow Overview
```
Transcript Files → Slide Files → Presentation Files → Video Production Pipeline
       ↓                ↓               ↓
    Adjust  →        Rename  →        Count
       ↓
   Save Text
       ↓
      TTS            4K Image
       ↓                ↓
       └───────→    MP4    ←───────┘
                      ↓
              Final Educational Video
```

### 5.3 File Naming Convention
- Each page will be numbered with a two-digit prefix (01-09)
- Logic for each page will be stored in separate files
- Example: Page "01 Adjust" will have corresponding logic file "01Adjust.py"

## 6. Detailed Page Requirements

### 6.1 Page 01: Adjust
#### 6.1.1 Purpose
To make necessary adjustments to transcript and slide files to ensure consistency and correctness, particularly focusing on handling content before first slides and after last slides.

#### 6.1.2 User Interface Components
- Adjustment controls for transcript files
- Adjustment controls for slide files
- Batch processing options
- Progress indicators (must use Streamlit progress bar)
- Status display showing processed files

#### 6.1.3 Functionality
- Process transcript files to identify and fix slide structure consistency
- Identify files containing "[Slide X - Start]" and "[Slide X - End]" markers
- Extract content outside slide markers (pre-content and post-content)
- Properly incorporate pre-content into first slide and post-content into last slide
- Reconstruct files with corrected structure
- Provide detailed logging of processing activities
- Skip files without proper slide structure
- Save processed files to the output folder, maintaining the input folder structure

#### 6.1.4 Technical Implementation
The implementation must follow the approach used in the existing script:
- Use regex pattern matching to identify slide blocks
- Extract content before first slide and after last slide
- Modify first and last slides to incorporate external content
- Process files recursively through the folder structure
- Maintain original file encoding (UTF-8)
- Provide detailed processing logs
- Display progress using Streamlit's progress bar

### 6.2 Page 02: Rename
#### 6.2.1 Purpose
To fix incorrectly named files according to standard naming conventions.

#### 6.2.2 User Interface Components
1. **Rename Button**
   - Initiates the file renaming analysis process
   
2. **Collapsible Course Sections**
   - One collapsible section per course
   - Collapsed by default
   - Only one course section can be expanded at a time
   - Courses must be displayed in ascending numerical order (Course 1, Course 2, etc.)

3. **Results Table (Per Course)**
   - Six columns:
     - Transcript Current | Transcript Corrected
     - Slide Current | Slide Corrected
     - Presentation Current | Presentation Corrected
   - Rows represent individual lectures within the course
   - Rows must be displayed in ascending numerical order by lecture number

4. **Progress Bar**
   - Must display processing progress during renaming operations

#### 6.2.3 Functionality
1. **File Discovery**
   - Traverse the input folder structure to locate all lecture sets
   - Handle variable folder structures as specified in the main requirements
   
2. **Renaming Analysis**
   - Analyze current file names
   - Apply renaming rules:
     - Convert single-digit lecture numbers to two-digit format (1 → 01, 2 → 02, etc.)
     - Convert "lec1" → "01", "lecture1" → "01"
     - Standardize "slides" naming:
       - "slide", "s" → "slides"
       - "lecX-slide.*", "lectureX-slide.*", "lecX-s.*" → "X-slides.*"
       - "lecX-slides.*", "lectureX-slides.*" → "X-slides.*"
       - "lectureX-slide-content.*" → "X-slides.*"
     - Standardize "transcript" naming:
       - "lectureX-transcript.*", "lectureX-video-transcript.*" → "Lecture X.*"
       - Example: "lecture-19-transcript.md" → "Lecture 19.md"
     - General Lecture Naming:
       - "lectureX.*", "lecX.*", "X.*" (where X is a number) → "Lecture X.*"
   - Generate proposed corrected names
   - Display both current and proposed names for comparison
   - Ensure all corresponding files (transcript, slide, presentation) for the same lecture appear in the same row

3. **Renaming Execution**
   - Additional functionality (likely a button) to apply the proposed renaming
   - Save renamed files to the output folder, maintaining the input folder structure

#### 6.2.4 User Interactions
1. User clicks the "Rename" button
2. System traverses input folder and analyzes all files
3. System displays progress bar during analysis
4. System generates collapsible sections for each course, sorted in ascending order
5. User clicks on a course name to expand its section
6. System displays detailed renaming table for that course with rows sorted by lecture number
7. User reviews proposed name changes
8. User initiates actual renaming (via additional control)
9. System displays progress bar during renaming execution

### 6.3 Page 03: Count
#### 6.3.1 Purpose
To verify alignment between transcript sections, slide descriptions, and presentation slides for each lecture by comparing counts and highlighting discrepancies.

#### 6.3.2 User Interface Components
1. **Count Button**
   - Initiates the counting process across all courses in the input folder
   
2. **Status Dashboard**
   - Displays summary metrics:
     - Total number of lecture sets checked
     - Total number of discrepancies found

3. **Collapsible Course Sections**
   - One collapsible section per course 
   - Collapsed by default
   - Only one course section can be expanded at a time
   - Courses must be displayed in ascending numerical order (Course 1, Course 2, etc.)

4. **Results Table (Per Course)**
   - Six columns:
     - Transcript Name | Transcript Count
     - Slide Name | Slide Count
     - Presentation Name | Presentation Count
   - Rows represent individual lectures within the course
   - Rows with count discrepancies are highlighted for quick identification
   - Rows must be displayed in ascending numerical order by lecture number
   - All three files for the same lecture (transcript, slide, presentation) must appear in the same row

5. **Progress Bar**
   - Must display processing progress during counting operations

#### 6.3.3 Functionality
1. **File Discovery**
   - Traverse the input folder structure to locate all lecture sets
   - Handle variable folder structures as specified in the main requirements
   
2. **Counting Logic**
   - For transcript files: Count the number of content sections
   - For slide files: Count the number of slide descriptions
   - For presentation files: Count the number of actual slides
   - Ensure proper matching of files across the three types for each lecture

3. **Discrepancy Detection**
   - Compare counts across the three file types for each lecture
   - Flag any lecture where counts do not match
   - Generate summary statistics
   - Save results to the output folder, maintaining the input folder structure

#### 6.3.4 User Interactions
1. User clicks the "Count" button
2. System traverses input folder and processes all files
3. System displays progress bar during processing
4. System displays summary dashboard with metrics
5. System generates collapsible sections for each course, sorted in ascending order
6. User clicks on a course name to expand its section
7. System displays detailed results table for that course with rows sorted by lecture number
8. User can identify problematic lectures through highlighting

### 6.4 Page 04: Save Text
#### 6.4.1 Purpose
To break transcript files into individual sections for TTS processing, extracting each slide's content into separate text files.

#### 6.4.2 User Interface Components
- Input selection controls
- Section separation parameters
- Output location controls
- Batch processing options
- Progress indicators with Streamlit progress bar integration
- File count statistics display

#### 6.4.3 Functionality
- Parse transcript files to identify section boundaries based on "[Slide X - Start/End]" markers
- Extract individual slide sections as separate files
- Apply naming conventions (e.g., "01.txt", "02.txt") using zero-padded numbering
- Create organized folder structures for processed files
- Move processed transcript files to an "all_transcripts" folder
- Move slide files to an "all_slides" folder
- Generate summary statistics of total slides extracted
- Display progress through visual progress bar
- Save all processed files to the output folder, maintaining the input folder structure

#### 6.4.4 Technical Implementation
The implementation must follow the approach used in the existing script:
- Use regex pattern matching to extract slide content: `\[Slide (\d+).*?Start\](.*?)\[Slide \d+.*?End\]`
- Process only files with specific naming conventions (starting with "Lecture" or containing "slide")
- Create appropriate output directory structure for each lecture
- Implement robust error handling for file I/O operations
- Maintain original file encoding (UTF-8)
- Create well-organized folders for future processing stages
- Display progress using Streamlit's progress bar

### 6.5 Page 05: TTS
#### 6.5.1 Purpose
To convert transcript sections to MP3 audio files using OpenAI's text-to-speech technology.

#### 6.5.2 User Interface Components
- TTS model selection dropdown (standard vs. HD)
- Voice selection dropdown with all available OpenAI voices:
  - Standard voices: alloy, echo, fable, onyx, nova, shimmer
  - HD voices: alloy-hd, echo-hd, fable-hd, onyx-hd, nova-hd, shimmer-hd
- Cost estimation display showing:
  - Estimated cost for each course
  - Total estimated cost
- Confirmation button to start processing
- Progress indicator with Streamlit progress bar
- Processing statistics display
- Error log display for failed conversions

#### 6.5.3 Functionality
- Process individual transcript section files
- Split long text into manageable chunks (max 4000 characters)
- Apply OpenAI's TTS API to generate audio
- Calculate and display cost estimates before processing
- Allow user to confirm before proceeding
- Implement retry logic with exponential backoff for API failures
- Skip files that have already been processed
- Save audio outputs as MP3 files
- Properly combine audio chunks for longer texts
- Display detailed statistics after completion:
  - Number of successful conversions
  - Number of skipped files
  - Actual cost
  - Failed conversions with error details
- Save all generated audio files to the output folder, maintaining the input folder structure
- Display processing progress through Streamlit progress bar

#### 6.5.4 Technical Implementation
The implementation must follow the approach used in the existing script:
- Use OpenAI's API for text-to-speech conversion
- Implement robust error handling for API failures
- Use exponential backoff strategy for retries
- Properly handle long texts by splitting into chunks
- Efficiently combine audio parts for final output
- Track and display cost information
- Display progress using Streamlit's progress bar

#### 6.5.5 Reference Code Snippets
```python
# Key constants
PRICE_PER_1K_CHARS_STANDARD = 0.015  # $15 per 1M characters
PRICE_PER_1K_CHARS_HD = 0.030  # $30 per 1M characters
MAX_RETRIES = 3
VOICE_OPTIONS = ["alloy", "echo", "fable", "onyx", "nova", "shimmer", 
                 "alloy-hd", "echo-hd", "fable-hd", "onyx-hd", "nova-hd", "shimmer-hd"]

# Text splitting function for long texts
def split_text(text, max_length=4000):
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind('.', 0, max_length)
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    chunks.append(text)
    return chunks

# Cost estimation function
def estimate_cost(text_files, voice):
    course_costs = {}
    for file in text_files:
        course_name = file.split(os.sep)[1]
        if course_name not in course_costs:
            course_costs[course_name] = 0
        output_file = os.path.join(os.path.dirname(file), os.path.splitext(os.path.basename(file))[0] + '.mp3')
        if not mp3_exists(output_file):
            with open(file, 'r', encoding='utf-8') as f:
                chars = len(f.read())
                cost_per_1k = PRICE_PER_1K_CHARS_HD if voice.endswith('-hd') else PRICE_PER_1K_CHARS_STANDARD
                course_costs[course_name] += (chars / 1000) * cost_per_1k
    return course_costs
```

### 6.6 Page 06: 4K Image
#### 6.6.1 Purpose
To generate high-resolution 4K (3840x2160) images from presentation slides for video production, with capability to upscale images, apply branding elements including company logo and copyright information.

#### 6.6.2 User Interface Components
- Presentation file selection
- Image quality parameters
- Output format options
- Batch processing controls
- Progress indicators with Streamlit progress bar
- Resolution settings (default: 3840x2160)
- Branding options for applying logo and copyright information
- User preference controls for handling already processed files

#### 6.6.3 Functionality
1. **PPTX to PNG Conversion**
   - Process PPTX presentation files
   - Extract individual slides and embedded images
   - Upscale images to 4K resolution using high-quality interpolation
   - Create organized folder structure for output images
   - Apply consistent naming convention (zero-padded numbering)
   - Move processed presentation files to an "all_pptx" folder
   - Maintain synchronization with audio sections
   - Save all processed files to the output folder, maintaining the input folder structure

2. **Image Personalization**
   - Add company logo from root-level logo.png file
   - Add copyright text from root-level copyright.txt file
   - Create "without_logo_png" folders to preserve original images
   - Configurable logo size, position, and padding
   - Configurable copyright text position, font size, and padding
   - User preference options for handling already processed files:
     1. Skip all already-processed files
     2. Process all already-processed files
     3. Ask for each file
   - Maintain image quality when saving processed files
   - Support various image formats (PNG, JPEG)
   - Save all personalized images to the output folder, maintaining the input folder structure

3. **Progress Tracking**
   - Display processing progress through Streamlit progress bar
   - Show statistics about processed and skipped files

#### 6.6.4 Technical Implementation
**PPTX to PNG Conversion:**
- Use python-pptx library for PPTX file processing
- Use OpenCV (cv2) for image manipulation and upscaling
- Implement Lanczos interpolation for high-quality upscaling
- Create folder with same name as PPTX file for organized output
- Calculate appropriate scaling factors to reach target 4K resolution
- Only upscale images smaller than target resolution
- Process files recursively through folder structure
- Display progress using Streamlit's progress bar

**Image Personalization:**
- Use PIL (Python Imaging Library/Pillow) for image manipulation
- Implement font fallback mechanism for text rendering
- Support configurable positioning (top-left, top-right, bottom-left, bottom-right, bottom-center)
- Preserve image quality with optimized saving
- Maintain original aspect ratio during upscaling
- Create alpha-composite images for proper logo transparency
- Handle various image formats consistently
- Display progress using Streamlit's progress bar

### 6.7 Page 07: MP4
#### 6.7.1 Purpose
To combine audio files and slide images to create final educational videos with properly timed slide transitions.

#### 6.7.2 User Interface Components
- Input selection for audio files
- Input selection for image files
- Video output parameters
- Video format options
- Frame rate control (default: 3 fps)
- Batch processing controls
- Progress indicators with Streamlit progress bar
- Processing statistics display

#### 6.7.3 Functionality
- Match audio sections with corresponding slide images in correct order
- Calculate appropriate slide duration based on corresponding audio length
- Use a frame rate of 3 fps for smooth transitions while maintaining static slides
- Combine audio and images into video segments
- Generate complete MP4 video files with proper encoding
- Create temporary files for processing stages
- Clean up temporary files after successful processing
- Support high-resolution 4K output (3840x2160)
- Save all generated video files to the output folder, maintaining the input folder structure
- Display processing progress through Streamlit progress bar

#### 6.7.4 Technical Implementation
The implementation must follow the approach used in the existing script:
- Use OpenCV for image processing
- Use ffmpeg for audio/video encoding and composition
- Process images at 4K resolution (3840x2160)
- Maintain timing synchronization between audio and slides
- Handle multiple audio and image files
- Create temporary files as needed for the workflow
- Implement proper cleanup of temporary files
- Use H.264 video codec and AAC audio codec for compatibility

#### 6.7.5 Reference Code Snippets
```python
# Define constants
OUTPUT_DIR = 'output'
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'output_video_temp.mp4')
FINAL_OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, 'final_output_video.mp4')
TEMP_AUDIO = os.path.join(OUTPUT_DIR, 'temp_audio.wav')

# Create video from images with proper timing based on audio duration
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

# Add audio to the video
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
        # Clean up temporary files
        os.remove(TEMP_AUDIO)
        os.remove(OUTPUT_VIDEO)
    except ffmpeg.Error as e:
        print(f"Error adding audio to video: {e.stderr.decode()}")
        raise
    return f"Added audio to video: {FINAL_OUTPUT_VIDEO}"
```

### 6.8 Page 08: Multilingual Text
#### 6.8.1 Purpose
To handle multilingual text processing for international educational content.

#### 6.8.2 User Interface Components
- Language selection
- Translation controls
- Text input/output options
- Batch processing controls
- Progress indicators with Streamlit progress bar
- Processing statistics display

#### 6.8.3 Functionality
- Process transcript files for translation
- Apply language-specific formatting
- Generate multilingual text outputs
- Maintain synchronization with original content
- Save all generated multilingual text files to the output folder, maintaining the input folder structure
- Display processing progress through Streamlit progress bar

### 6.9 Page 09: Multilingual TTS
#### 6.9.1 Purpose
To handle multilingual text-to-speech processing for international educational content.

#### 6.9.2 User Interface Components
- Language selection
- Voice selection options
- TTS model selection for various languages
- Audio output parameters
- Batch processing controls
- Progress indicators with Streamlit progress bar
- Processing statistics display

#### 6.9.3 Functionality
- Process multilingual transcript sections
- Apply language-specific TTS processing
- Generate multilingual audio outputs
- Maintain synchronization with visual content
- Save all generated multilingual audio files to the output folder, maintaining the input folder structure
- Display processing progress through Streamlit progress bar

## 7. Technical Requirements

### 7.1 Performance Requirements
- The system shall process files efficiently, with appropriate progress indicators for longer operations
- The system shall use Streamlit progress bars for visual progress tracking during batch operations
- The system shall handle large folder structures with minimal latency
- The system shall implement caching where appropriate to improve performance
- The system shall efficiently handle image upscaling to 4K resolution
- The system shall optimize for memory usage when processing large presentation files

### 7.2 Security Requirements
- The system shall protect content from unauthorized access
- The system shall maintain integrity of original files
- The system shall create backups before performing destructive operations

### 7.3 Usability Requirements
- The system shall provide a consistent and intuitive user interface using Streamlit components
- The system shall implement clear visual indicators for important information
- The system shall provide helpful error messages and guidance
- The system shall display progress bars for all long-running operations

### 7.4 Reliability Requirements
- The system shall handle errors gracefully
- The system shall provide recovery mechanisms for interrupted operations
- The system shall validate inputs and outputs at each processing stage

## 8. Common Components

### 8.1 User Interface Components
- Input folder selection mechanism with directory browser
- Navigation system between pages
- Progress indicators for longer operations using Streamlit progress bars
- Consistent header and footer elements
- Error notification system
- Collapsible sections for course-specific data display
- Data visualization components for displaying statistics

### 8.2 Backend Components
- File system interaction module
- Structure analyzer to determine folder hierarchy
- File format conversion utilities
- Audio processing utilities
- Image processing utilities (utilizing OpenCV)
- Video processing utilities
- Regular expression processing for text parsing
- Folder organization utilities
- Logging and reporting system
- Output folder creation and mirroring input structure

### 8.3 Required Assets
- **copyright.txt** - Text file containing copyright information to be applied to output files
  - Located in the root folder of the project directory
  - Contains plain text copyright statement
  - Used by the image personalization process

- **logo.png** - Logo image to be applied to output images
  - Located in the root folder of the project directory
  - Must have transparency (RGBA format)
  - Will be resized to configurable dimensions (default: 250x250 pixels)
  - Used by the image personalization process

### 8.4 Configuration Parameters
- **Logo Customization**
  - LOGO_SIZE: Size of the logo in pixels (default: 250)
  - LOGO_PADDING: Padding from the edge in pixels (default: 0)
  - LOGO_POSITION: Position on the image (default: 'top-right', options: 'top-left', 'top-right', 'bottom-left', 'bottom-right')

- **Copyright Customization**
  - COPYRIGHT_PADDING: Padding from the edge in pixels (default: 35)
  - COPYRIGHT_POSITION: Position on the image (default: 'bottom-center', options: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'bottom-center')
  - FONT_SIZE: Size of the copyright text (default: 65)
  - FONT_COLOR: Color of the copyright text (default: black)

## 9. Integration Requirements

### 9.1 External Dependencies
- **Streamlit** as the primary development framework
- **python-pptx** library for PPTX processing and slide extraction
- **OpenCV (cv2)** for image processing and upscaling in the PPTX to PNG conversion
- **PIL/Pillow** for image processing and adding logo/copyright in the personalization step
- **tqdm** library for progress visualization in background processing
- **NumPy** for efficient array operations and image processing
- **Regular expression (re)** module for text pattern matching
- **OpenAI API** for text-to-speech conversion
- **ffmpeg-python** for video and audio processing
- **ffmpeg** executable dependency for multimedia operations

### 9.2 API Requirements
- **OpenAI API** for TTS services
  - Requires API key configuration
  - Supports both standard and HD voice models
  - Rate limiting and retry handling required
- **ffmpeg** command-line interface for multimedia processing
- Python wrappers for external command-line tools

## 10. Testing Requirements

### 10.1 Unit Testing
- Each functional component shall have comprehensive unit tests
- Input validation shall be thoroughly tested
- Edge cases shall be identified and tested

### 10.2 Integration Testing
- End-to-end workflows shall be tested
- Performance under load shall be verified
- Error handling shall be verified

### 10.3 User Acceptance Testing
- Representative test cases shall be developed
- User experience shall be evaluated
- Feedback mechanisms shall be implemented

## 11. Deployment Requirements

### 11.1 Installation
- The system shall be installable with minimal configuration
- Dependencies shall be clearly documented
- System requirements shall be specified

### 11.2 Updates
- The system shall support version updates
- Update mechanisms shall be documented
- Backward compatibility shall be maintained where possible

## 12. Documentation Requirements

### 12.1 User Documentation
- User manuals shall be provided
- Quick-start guides shall be developed
- Context-sensitive help shall be implemented

### 12.2 Technical Documentation
- API documentation shall be maintained
- Code documentation shall be comprehensive
- System architecture shall be documented

## 13. Future Considerations

### 13.1 Scalability
- The system shall be designed to accommodate increasing content volumes
- Performance optimizations shall be identified for future implementation
- Resource utilization shall be monitored

### 13.2 Additional Features
- Additional file formats may be supported in future versions
- Enhanced analytics may be implemented
- Automation of additional workflow steps may be considered

## Appendix A: Glossary

- **Transcript File**: Text file containing the spoken content for an educational video
- **Slide File**: Text file describing the visual content for each slide
- **Presentation File**: PPTX file containing the actual slides for the video
- **TTS**: Text-to-Speech, a technology for converting text to spoken audio
- **Dreamlet**: The development platform for this application
- **Streamlit**: The web application framework used for development
