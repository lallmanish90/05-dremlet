# Lecture Slide Converter

A comprehensive utility for processing lecture slide notes from various input formats into a clean, standardized format by removing timestamps, cleaning unwanted content, and handling formatting issues.

## Overview

This tool meticulously processes lecture slide files that contain timestamps, formatting markers, and various artifacts, converting them to a clean, standardized format suitable for review and distribution.

### What it Does:

1. Processes all `.md` and `.txt` files in the specified directory
2. Creates backups of original files before processing
3. Removes timestamp information from slide markers
4. Cleans unwanted content and formatting artifacts
5. Handles duplicate slide markers intelligently
6. Standardizes slide formatting and structure
7. Overwrites original files in-place with cleaned content
8. Cleans up all backup files after successful processing

## Usage

### Basic Usage

Simply run the script without any arguments:

```
python slide_processor.py
```

The script will automatically:
1. Look for an `input` directory and process all `.md` and `.txt` files there
2. If no `input` directory exists, it will process all `.md` and `.txt` files in the current directory

### Advanced Usage

You can specify a specific directory to process:

```
python slide_processor.py path/to/directory
```

Or process a single file:

```
python slide_processor.py path/to/file.md
```

## Comprehensive Processing Logic

### 1. Slide Marker Detection and Handling

The script handles a wide variety of slide marker formats:

- **Complete Timestamped Format**: 
  - `[Slide N - Start: MM:SS]` → `[Slide N - Start]`
  - `[Slide N - End: MM:SS]` → `[Slide N - End]`

- **Partially Timestamped Format**:
  - `[Slide N - Start: MM:SS]` + `[Slide N - End]`
  - `[Slide N - Start]` + `[Slide N - End: MM:SS]`

- **Clean Format**:
  - `[Slide N - Start]` + `[Slide N - End]`

- **Incomplete Format Correction**:
  - Fixes incomplete slide markers with missing closing brackets
  - Example: `[Slide N - End: MM:SS` → `[Slide N - End: MM:SS]`

### 2. Duplicate Slide Processing

- **First Occurrence Priority**: When multiple instances of the same slide number exist, only the first occurrence is processed
- **Multiple Sequence Handling**: When a file contains multiple complete slide sequences (multiple sets starting from Slide 1), only the first complete sequence is processed
- **Verification**: The script verifies the final output to ensure no duplicate slide markers remain

### 3. Fallback Extraction Methods

When standard pattern matching fails, the script employs fallback extraction methods:

- **Manual Extraction**: Directly extracts content between start and end markers 
- **Position-Based Extraction**: Uses marker positions to determine slide boundaries
- **Multiple Pattern Attempts**: Tries various regex patterns to handle different formatting variations

### 4. Content Cleaning and Standardization

The script performs extensive cleaning operations:

- **Timestamp Removal**:
  - Removes all timestamp information (MM:SS) from slide markers
  - Standardizes to `[Slide N - Start]` and `[Slide N - End]` format

- **Content Cleanup**:
  - Removes lines containing "transcript" or "duration" (case-insensitive)
  - Removes Markdown headers (e.g., `# Header`, `## Subheader`, etc.)
  - Removes music cue notations (e.g., `[Music fades in]`, `[Background music]`)
  - Removes empty lines and excessive whitespace
  - Removes Word Count lines that appear after slide markers

- **Formatting Cleanup**:
  - Removes Markdown formatting (bold `**text**` → `text`, italic `*text*` → `text`)
  - Removes lines that are purely metadata (e.g., `_Duration: 20 minutes (1200 words)_`)
  - Replaces placeholder text (`[Name]` → `Professor`)

### 5. Slide Content Formatting

- **Proper Spacing**:
  - Adds empty line after the first slide start tag only
  - Adds empty line after each slide for better readability

- **Slide Organization**:
  - Sorts slides numerically by slide number
  - Ensures proper nesting of start and end markers

### 6. File Handling and Backup Management

- **Backup Creation**:
  - Creates `.bak` backups of all files before processing them
  - Logs backup creation or failures

- **Backup Cleanup**:
  - Automatically removes all backup files (`.bak`, `.ba`, `.md.ba`) after successful processing
  - Logs cleanup operations for transparency

- **Error Handling**:
  - Gracefully handles file access errors
  - Provides detailed logging of processing steps and issues

## Input File Format Variations

The script handles a wide array of input formats:

1. **Standard Timestamped Format**:
   ```
   [Slide 1 - Start: 00:15]
   Content for slide 1
   [Slide 1 - End: 01:20]
   ```

2. **Mixed Format** (start timestamp only):
   ```
   [Slide 1 - Start: 00:15]
   Content for slide 1
   [Slide 1 - End]
   ```

3. **Mixed Format** (end timestamp only):
   ```
   [Slide 1 - Start]
   Content for slide 1
   [Slide 1 - End: 01:20]
   ```

4. **Clean Format**:
   ```
   [Slide 1 - Start]
   Content for slide 1
   [Slide 1 - End]
   ```

5. **Incomplete Bracket Format** (automatically fixed):
   ```
   [Slide 1 - Start: 00:15]
   Content for slide 1
   [Slide 1 - End: 01:20
   ```

6. **With Word Count** (automatically removed):
   ```
   [Slide 1 - Start: 00:15]
   Content for slide 1
   [Slide 1 - End: 01:20]
   Word Count: 150
   ```

7. **With Formatting and Placeholders** (automatically cleaned):
   ```
   [Slide 1 - Start: 00:15]
   # Introduction
   Hello, my name is [Name]. Today we'll be discussing:
   - **Important** concept one
   - *Secondary* concept two
   [Music fades in]
   [Slide 1 - End: 01:20]
   ```

## Output Format

The script produces a consistent, clean output format:

```
[Slide 1 - Start]

Content for slide 1 with all formatting removed 
and unnecessary elements cleaned up
[Slide 1 - End]

[Slide 2 - Start]
Content for slide 2
[Slide 2 - End]

...
```

## Corner Cases and Special Handling

### 1. Malformed and Edge Cases

- **Incomplete Markers**: The script repairs incomplete slide markers missing closing brackets
- **Missing End Markers**: The script attempts to extract content even when end markers are missing
- **Slide Number Mismatch**: The script correctly pairs start and end markers with matching slide numbers
- **Zero Slides Found**: The script provides clear error logging if no valid slides are found

### 2. Content Transformation

- **Placeholder Replacement**: `[Name]` is automatically replaced with `Professor`
- **Markdown Cleaning**: Both bold (`**text**`) and italic (`*text*`) formatting are removed
- **Metadata Removal**: Lines that are purely metadata (surrounded by underscores) are removed

### 3. Error Recovery Strategies

- **Multiple Extraction Attempts**: The script tries multiple regex patterns to extract slide content
- **Manual Position-Based Extraction**: As a last resort, the script attempts manual extraction based on marker positions
- **Graceful Failure**: If all extraction methods fail, the script provides clear error messages

## Requirements

- Python 3.6 or higher
- Standard libraries only (no external dependencies required):
  - os
  - re
  - glob
  - logging

## Logging and Diagnostics

The script provides detailed logging at various levels:

- **INFO**: General processing updates, file operations, and successful conversions
- **WARNING**: Non-critical issues like missing slide markers or backup creation failures
- **ERROR**: Critical failures like file access issues or no slides found

## Notes for Future Development

When making changes to this utility, consider:

1. The script prioritizes robustness over efficiency, employing multiple extraction methods to handle edge cases
2. The backup mechanism ensures original content is preserved before processing
3. The modular design allows for easy extension of cleaning rules and extraction patterns
4. Error handling is comprehensive to prevent data loss in edge cases
5. The script attempts to repair malformed content where possible