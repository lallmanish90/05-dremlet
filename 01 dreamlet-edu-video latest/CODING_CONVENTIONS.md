# Coding Conventions

## NO SHARED CODE POLICY

**CRITICAL RULE**: All code in the `pages/` folder must be completely self-contained.

### Requirements:
- **Each page file contains ALL code it needs** - never import from other page files
- **No shared utilities or modules** - copy any needed functions directly into each page file
- **Complete independence** - each page must work without any dependencies on other page files
- **No cross-file references** - never create utils, helpers, or shared modules

### Implementation Guidelines:
- If you need a function that exists in another page, copy it entirely into your current page
- Each page should be able to run independently without any other page files
- All imports should only be from standard libraries or external packages, never from other page files
- When creating new pages, include all necessary utility functions within that single file

### Why This Convention:
- Ensures complete modularity and independence of each page
- Prevents breaking changes when modifying one page affecting others
- Makes debugging and maintenance easier
- Allows pages to be moved or copied without dependencies

**Remember: Each page is a complete, standalone application within the larger project.**

## CORE RULES

- Every file in `pages/` must be able to run as a standalone page without importing code from another page
- No shared internal helper modules, utility files, or cross-page abstractions
- If logic is reused, copy it into the page that needs it and keep the copied version explicit
- Files may use standard library modules and external packages only

## REQUIRED PAGE HEADER

Every page should begin with a short comment block that states:
- page status: `CURRENT`, `LEGACY`, `BACKUP`, or `EXPERIMENTAL`
- purpose
- main inputs
- main outputs
- required config files or assets
- external services used, if any
- hardware assumptions, if any
- replacement page, if the file is legacy or backup

## PAGE STATUS AND NAMING

- Prefer one active page per workflow step
- If an alternate page must exist, name it clearly with a suffix such as:
  - `_legacy`
  - `_backup`
  - `_old`
  - `_experimental`
  - `_gpu`
  - `_cpu`
- Legacy and backup pages must say what replaced them
- Backup pages should never look like the primary workflow by accident

## STANDARD FILE LAYOUT

Keep the internal structure of standalone pages consistent:

1. Header comment block
2. Imports
3. Constants and path definitions
4. Small path and file helper functions
5. Validation functions
6. Core processing functions
7. Progress and status helpers
8. Streamlit UI rendering
9. `main()`

Large pages are acceptable. Large disorganized pages are not.

## STANDARD PATH CONSTANTS

When a page uses common folders or assets, define them near the top of the file with consistent names:
- `INPUT_DIR`
- `OUTPUT_DIR`
- `CONFIG_DIR`
- `LOGO_PATH`
- `COPYRIGHT_PATH`
- `PROMPT_PATH`

Rules:
- Do not scatter raw path strings throughout the file
- Keep config assets under `config/` unless there is a strong reason not to
- If a page depends on a config file or asset, make that dependency explicit near the top

## DUPLICATION DISCIPLINE

Because duplication is required, duplication must be controlled.

- When copying logic from one page to another, keep the same function name when the concept is the same
- Keep the same function signature when the behavior is the same
- Copy the whole function block, not partial fragments
- Add a short sync note above copied blocks when helpful, for example:
  - `Copied from page 06 on 2026-04-07`
- For major repeated blocks, add a simple version marker, for example:
  - `# FILE_DISCOVERY_BLOCK v2`
  - `# MP4_ENCODER_BLOCK v3`

## FUNCTION AND CODE STYLE

- Prefer small, focused functions over one giant processing body
- Use descriptive, stable names for the same concept across pages
- If two pages do the same kind of work, use the same helper names where practical
- Keep comments short and useful
- Delete dead code instead of leaving commented-out blocks

## VALIDATION BEFORE PROCESSING

Every page should validate inputs before starting expensive work.

Check for:
- required folders
- required files
- expected counts
- required binaries such as `ffmpeg` or `libreoffice`
- required config files and assets
- required API credentials when external services are used

Fail early with a clear message instead of starting long work and failing late.

## ERROR HANDLING

User-facing errors should consistently say:
- what failed
- why it failed, if known
- what the user should check next

Use clear categories where helpful:
- missing input
- invalid input
- count mismatch
- missing config
- missing external dependency
- external API or network failure

## PROGRESS AND UI CONVENTIONS

Long-running pages should show:
- current action
- progress bar
- count processed
- time estimate when practical

Keep section order predictable where possible:
- overview
- requirements
- options
- discovery
- selection
- execution
- results

## DESTRUCTIVE ACTIONS

Pages that delete, overwrite, or restore files must:
- clearly state scope before execution
- require explicit user action
- avoid silent destructive behavior

## MACHINE-AWARE PAGES

If a page contains hardware-specific logic:
- keep the machine profiles inside that page
- use consistent machine profile names across pages
- keep hardware detection explicit and readable
- keep fallback behavior obvious when acceleration is unavailable

## SECRETS AND EXTERNAL SERVICES

- Do not hardcode secrets, API keys, passwords, or tokens in page files
- Prefer environment variables or explicit config inputs
- If a credential is missing, fail clearly and tell the user what is required

## LEGACY AND BACKUP PAGE RULES

Legacy and backup pages must be clearly marked at the top of the file.

They should state:
- why they still exist
- whether they are safe to use
- which page is the preferred current version

## DOCUMENTATION RULES

- The README should document the current workflow pages
- Legacy or backup pages should not be presented as primary pages
- If assets move, update both the page constants and the README

## MAINTENANCE PRACTICES

When a repeated logic block is updated:
- identify every page that contains the same logic
- update all copies intentionally
- keep names and signatures aligned
- use a checklist if the same change must be applied in multiple files
