import os
import re
from tqdm import tqdm

def extract_slides(file_path, output_dir):
    # Read the content of the input file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        print(f"File content:\n{content}\n")
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return 0

    # Define the regex pattern to match slide content
    slide_pattern = r'\[Slide (\d+).*?Start\](.*?)\[Slide \d+.*?End\]'
    # Extract all slides using the pattern
    slides = re.findall(slide_pattern, content, re.DOTALL)
    print(f"Number of slides found: {len(slides)}")
    
    # Process each slide
    for slide_num, slide_content in slides:
        # Create output file name (e.g., "01.txt", "02.txt", etc.)
        output_file = os.path.join(output_dir, f"{slide_num.zfill(2)}.txt")
        try:
            # Write slide content to individual file
            with open(output_file, 'w', encoding='utf-8') as out_file:
                out_file.write(slide_content.strip())
            print(f"Created slide file: {output_file}")
            print(f"Slide content:\n{slide_content.strip()}\n")
        except IOError as e:
            print(f"Error writing file {output_file}: {e}")

    return len(slides)

def process_directory(root_dir):
    total_slides = 0
    all_files = []
    
    # First, collect all files to process
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if dirpath == root_dir:
            continue  # Skip the root directory itself
        
        dirnames[:] = [d for d in dirnames if d not in ['all_transcripts', 'all_slides']]
        
        all_files.extend([
            (dirpath, f) for f in filenames
            if (f.startswith('Lecture') or 'slide' in f.lower() or 'slides' in f.lower())
            and (f.endswith('.txt') or f.endswith('.md'))
        ])
    
    # Process files with a single progress bar
    for dirpath, file in tqdm(all_files, desc="Processing files"):
        file_path = os.path.join(dirpath, file)
        
        if file.startswith('Lecture'):
            # Process transcript files
            all_transcripts_folder = os.path.join(dirpath, 'all_transcripts')
            os.makedirs(all_transcripts_folder, exist_ok=True)
            
            lecture_folder = os.path.join(dirpath, os.path.splitext(file)[0])
            if not os.path.exists(lecture_folder):
                os.makedirs(lecture_folder)
            
            total_slides += extract_slides(file_path, lecture_folder)
            
            new_file_path = os.path.join(all_transcripts_folder, file)
            os.rename(file_path, new_file_path)
        
        elif 'slide' in file.lower() or 'slides' in file.lower():
            # Process slide files
            all_slides_folder = os.path.join(dirpath, 'all_slides')
            os.makedirs(all_slides_folder, exist_ok=True)
            
            new_file_path = os.path.join(all_slides_folder, file)
            os.rename(file_path, new_file_path)
    
    print(f"Total slides extracted: {total_slides}")
    print("All transcripts and slides processed and moved.")

if __name__ == "__main__":
    # Process files in 'input' directory
    root_directory = os.path.join(os.getcwd(), 'input')
    print(f"Starting slide extraction in directory: {root_directory}")
    process_directory(root_directory)
    
    print("Slide extraction completed.")
