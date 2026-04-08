# Machine-Aware 4K Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 4K Images page detect the active computer from config, apply optimized defaults per machine, and allow a safe manual override.

**Architecture:** Keep the page self-contained, but replace hardcoded machine profiles with config-driven profile loading from `config/computers.txt`. Detection will use explicit override first, then hostname/system matching, then fallback, and the chosen profile will drive runtime optimization settings and UI defaults.

**Tech Stack:** Python, Streamlit, pytest, stdlib `configparser`

---

### Task 1: Lock machine-profile behavior in tests

**Files:**
- Create: `01 dreamlet-edu-video latest/tests/test_4k_machine_profiles.py`
- Modify: `01 dreamlet-edu-video latest/tests/test_page_startup.py`

- [ ] Add tests for parsing structured machine profiles from `config/computers.txt`.
- [ ] Add tests for automatic profile selection and manual override behavior.
- [ ] Run the new targeted tests and confirm they fail before implementation.

### Task 2: Convert the machine config into a real source of truth

**Files:**
- Modify: `01 dreamlet-edu-video latest/config/computers.txt`
- Modify: `01 dreamlet-edu-video latest/pages/06 Generate 4K Images.py`

- [ ] Replace the free-form notes file with a machine-readable profile format while keeping it human-readable.
- [ ] Refactor the page to load profile definitions, normalize profile ids, and derive effective runtime settings from config.

### Task 3: Apply machine-aware runtime behavior in the UI and processing path

**Files:**
- Modify: `01 dreamlet-edu-video latest/pages/06 Generate 4K Images.py`

- [ ] Add profile-match reasoning to the UI.
- [ ] Add a manual override selector with `Auto` plus known machines and fallback.
- [ ] Apply profile defaults to batch size, threads, preferred image processing, and default conversion method.

### Task 4: Verify the page and app surface

**Files:**
- Modify as needed: `01 dreamlet-edu-video latest/pages/06 Generate 4K Images.py`

- [ ] Run targeted tests for the new profile logic.
- [ ] Run `uv run pytest` in `01 dreamlet-edu-video latest`.
- [ ] Confirm the 4K page still starts without import/name errors.
