# Page Rename Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the Streamlit page filenames and sidebar menu labels to one shared naming scheme without changing behavior.

**Architecture:** Rename only the `01 dreamlet-edu-video latest/pages` files, then update all hardcoded filename references in the Streamlit app, tests, docs, and CLI source metadata. Keep the CLI module filenames unchanged while updating its mirrored `source_file` records to match the renamed Streamlit pages.

**Tech Stack:** Python, Streamlit, pytest, JSON metadata

---

### Task 1: Lock the approved naming scheme in tests

**Files:**
- Modify: `01 dreamlet-edu-video latest/tests/test_navigation_sidebar.py`
- Modify: `01 dreamlet-edu-video latest/tests/test_homepage_dashboard.py`
- Modify: `01 dreamlet-edu-video latest/tests/test_page_startup.py`

- [ ] Update navigation and homepage tests to expect the shared filename/menu labels.
- [ ] Update startup-path tests to reference the renamed page files.
- [ ] Run the affected tests to confirm they fail against the old names.

### Task 2: Rename the Streamlit page files

**Files:**
- Rename under: `01 dreamlet-edu-video latest/pages/`

- [ ] Rename current and legacy page files to the approved shared label scheme.
- [ ] Preserve page contents and behavior.

### Task 3: Update application references

**Files:**
- Modify: `01 dreamlet-edu-video latest/app.py`

- [ ] Update `build_navigation()` to point at the renamed files and use identical menu labels.
- [ ] Update homepage recommended-step labels to use the same shared titles.

### Task 4: Update docs and mirrored metadata

**Files:**
- Modify: `01 dreamlet-edu-video latest/README.md`
- Modify: `01 dreamlet-edu-video latest/user-experience-enhancements-requirements.md`
- Modify: `02 dreamlet-cli/src/dreamlet_cli/page_catalog.json`
- Modify: `02 dreamlet-cli/docs/parity-catalog.md`

- [ ] Replace old source filenames with the renamed page filenames.
- [ ] Keep CLI page IDs and module names unchanged.

### Task 5: Remove stale inline references and verify

**Files:**
- Modify as needed: page docstrings/comments that mention old page filenames

- [ ] Update stale inline references where they directly mention renamed page files.
- [ ] Run `uv run pytest` in `01 dreamlet-edu-video latest`.
- [ ] Run `uv run pytest` in `02 dreamlet-cli`.
- [ ] Launch the Streamlit app and confirm the renamed pages still load from the sidebar.
