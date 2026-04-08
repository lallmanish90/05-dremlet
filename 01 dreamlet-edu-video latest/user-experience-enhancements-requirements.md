# User Experience Enhancements Requirements


## Goal

Improve the usability of the existing educational video workflow without changing the core architecture:
- Streamlit multipage app
- file-system based workflow
- standalone page files in `pages/`
- no shared internal utilities across pages

## Current Scope

These requirements are meant for the current page structure, especially:
- `pages/01 Prepare AAA EEE.py`
- `pages/02 Rename Lecture Files.py`
- `pages/03 Split Text Sections.py`
- `pages/04 Clean Unwanted Files.py`
- `pages/05 Move Slide Files.py`
- `pages/06 Generate 4K Images.py`
- `pages/07 Generate Audio with Kokoro.py`
- `pages/08 Translate with Ollama.py`
- `pages/08 Translate with LM Studio.py`
- `pages/08 Validate File Counts.py`
- `pages/09 Repair MP4 Inputs.py`
- `pages/10 Render MP4 Videos.py`
- `pages/11 Verify MP4 Output.py`
- `pages/11_Workflow_Manager.py`

## Requirements Worth Implementing

### 1. Workflow Management

Keep and improve workflow management in `pages/11_Workflow_Manager.py`.

Useful requirements:
- allow users to select multiple current workflow steps and run them in sequence
- support workflow templates based on the real current page set
- store workflow state on disk so interrupted workflows can be resumed
- support checkpoints for long-running workflows
- let users skip already completed steps when re-running a workflow
- validate workflow templates before saving or executing them

### 2. Error Handling And Recovery

Useful requirements:
- show clear, actionable error messages
- classify common failures in a simple way: user error, system error, external service error
- retry transient external failures where safe, especially network or API failures
- allow safe recovery options when a step fails:
  - retry the step
  - resume from a checkpoint
  - restart the workflow
- validate outputs before moving to the next step in a workflow

### 3. Progress Tracking

Useful requirements:
- show progress bars and detailed status messages during long-running work
- show step-level progress for workflows
- show estimated time remaining where practical
- keep batch result summaries easy to scan
- preserve enough state to resume long-running work after interruption

### 4. Usability Improvements

Useful requirements:
- add contextual help inside pages
- explain expected inputs and outputs clearly on each page
- keep page-level guidance simple and task-focused
- preserve lightweight user preferences only where they directly improve workflow usability

### 5. Feedback And Logging

Useful requirements:
- provide immediate visual feedback for actions
- show success, warning, and error states consistently
- maintain workflow logs and checkpoint history on disk
- keep logs detailed enough to diagnose failures in batch processing

## Delivery Principles

These requirements must respect the current coding rule:
- each page remains self-contained
- no cross-page imports
- duplicated helper logic is acceptable when required by the page isolation rule
- workflow coordination should happen through file-system state, not shared Python modules

## Explicitly Out Of Scope

These items were removed from the old JSON because they do not fit the current project state well enough:
- adding `pages/00_Dashboard.py`
- adding `pages/12_System_Monitor.py`
- adding `pages/13_User_Settings.py`
- WebSocket-based real-time infrastructure
- browser or email notification systems
- keyboard shortcut systems
- behavior-based recommendation engines
- usage analytics and machine-learning style suggestions
- multi-user scalability requirements
- broad success metrics that depend on survey, analytics, or support-ticket infrastructure
- page references that no longer match the current page names

## Implementation Standard

If these UX improvements are implemented later, they should:
- use the current page names and current workflow
- favor small, practical improvements over new product layers
- avoid introducing infrastructure that the rest of the app does not already support
- keep the app understandable for a single-user, file-based workflow
