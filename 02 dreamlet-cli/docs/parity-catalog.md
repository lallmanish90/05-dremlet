# Parity Catalog

| Page ID | Source File | Status | Source Compiles | Purpose |
| --- | --- | --- | --- | --- |
| `01` | `01 Prepare AAA EEE.py` | CURRENT | yes | Split and normalize AAA / EEE source content into the expected lecture-level text structure. |
| `02` | `02 Rename Lecture Files.py` | CURRENT | yes | Standardize lecture file names into the naming scheme expected by the rest of the pipeline. |
| `03` | `03 Split Text Sections.py` | CURRENT | yes | Break transcript and summary material into section files for downstream TTS processing. |
| `04` | `04 Clean Unwanted Files.py` | CURRENT | yes | Remove unwanted or low-value files from lecture folders before later processing steps. |
| `05` | `05 Move Slide Files.py` | CURRENT | yes | Move slide files into the folder structure expected by the image-generation and verification steps. |
| `06` | `06 Generate 4K Images.py` | CURRENT | yes | Generate branded 4K images from PPTX presentations or ZIP image archives. |
| `06-4k-image` | `06 Legacy 4K Image.py` | LEGACY | yes | Older 4K image generation page for PPTX-based lecture assets. |
| `06-4k-image-pptx-zip` | `06 Legacy 4K Image PPTX ZIP.py` | LEGACY | yes | Older combined PPTX and ZIP 4K image generation page. |
| `07` | `07 Generate Audio with Kokoro.py` | CURRENT | yes | Generate lecture audio from section text using the local Kokoro TTS service. |
| `08-ollama` | `08 Translate with Ollama.py` | CURRENT | yes | Translate lecture content using a local Ollama model backend. |
| `08-translator-lm-studio` | `08 Translate with LM Studio.py` | CURRENT | yes | Translate lecture content using an LM Studio-compatible local OpenAI API endpoint. |
| `09-count` | `09 Legacy Count.py` | LEGACY | yes | Older lecture artifact verification and count page. |
| `09-count-new` | `08 Validate File Counts.py` | CURRENT | yes | Verify that lecture artifacts, text sections, and presentation outputs are aligned before video generation. |
| `09-fix-for-mp4` | `09 Repair MP4 Inputs.py` | CURRENT | yes | Repair lecture folders so they satisfy the prerequisites required by MP4 generation. |
| `10` | `10 Render MP4 Videos.py` | CURRENT | yes | Generate final MP4 lecture videos from image/audio pairs with machine-aware acceleration. |
| `10-mp4-gpu` | `10 Legacy MP4 GPU.py` | LEGACY | yes | Older GPU-focused MP4 generation page for lecture videos. |
| `11-verify-mp4` | `11 Verify MP4 Output.py` | CURRENT | yes | Verify generated MP4 files and surface mismatches, missing outputs, or duration problems. |
| `11-workflow-manager` | `11_Workflow_Manager.py` | CURRENT | yes | Create, save, and run workflow templates for batch execution of the current page pipeline. |
| `12` | `12 Delete Files.py` | CURRENT | yes | Delete selected lecture files as a maintenance and recovery utility. |
| `13` | `13 Delete Folders.py` | CURRENT | yes | Delete selected folder types across lecture trees as a maintenance and recovery utility. |
| `14` | `14 Restore PPTX Files.py` | CURRENT | yes | Restore PPTX files back into lecture folders after earlier reorganization or cleanup steps. |
| `15` | `15 Generate Audio with Inworld.py` | CURRENT | yes | Generate lecture audio using the Inworld cloud TTS service as an alternative narration backend. |
| `50` | `50_Legacy_Files_Header.py` | LEGACY | yes | Sidebar grouping page that introduces older, superseded pages retained for reference. |
| `51` | `51_Adjust_Slide_Files_Only.py` | EXPERIMENTAL | yes | Narrow slide-file-only adjustment variant retained for experimentation and reference. |
| `52` | `52 Create Multilingual Folder Structure.py` | LEGACY | no | 52 multilingual folder structure |
| `53` | `53 Convert Text to Multiple Languages.py` | UNSPECIFIED | no | 53 Convert Text to multiple languages |
| `54` | `54 Generate Multilingual Audio.py` | UNSPECIFIED | no | 54 Multilingual TTS |
| `55` | `55 Generate Audio with OpenAI.py` | UNSPECIFIED | no | 55 TTS Open AI |
| `56` | `56_TTS_Kokoro_old.py` | LEGACY | yes | Older Kokoro TTS page retained for reference and backward compatibility. |
| `57` | `57_TTS_Kokoro_GPU_old.py` | LEGACY | yes | Older advanced Kokoro GPU-oriented TTS page retained for reference. |
| `58` | `58 Legacy Translator Lecto.py` | LEGACY | yes | Older Lecto-based translation page retained as an alternate legacy backend. |
| `59` | `59_count_old.py` | LEGACY | yes | Older lecture count and discrepancy page retained for reference. |
| `60` | `60 Legacy MP4 CPU.py` | LEGACY | yes | Older CPU-only MP4 generation page retained as a fallback reference path. |
| `61` | `61_Adjust_Transcript_Only.py` | LEGACY | yes | Narrow transcript-only adjustment page retained as a legacy variant. |
| `99-01-rename-backup` | `99_01_Rename_BACKUP.py` | BACKUP | yes | Backup copy of the rename page retained for rollback and reference. |
| `99-02-adjust-aaa-eee-backup` | `99_02_Adjust_AAA_EEE_BACKUP.py` | BACKUP | yes | Backup copy of the main AAA / EEE adjustment page retained for rollback and reference. |
| `99-03-save-text-backup` | `99_03_Save_Text_BACKUP.py` | BACKUP | yes | Backup copy of the save-text page retained for rollback and reference. |
