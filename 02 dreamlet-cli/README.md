# Dreamlet CLI

`02 dreamlet-cli` is a CLI-only clone of `01 dreamlet-edu-video latest`.

- Source of truth: `../01 dreamlet-edu-video latest`
- Runtime dependency on `01`: none
- Interface style: numbered page commands plus collision-safe page IDs

## Install

```bash
uv sync
```

System tools still required where the copied page logic expects them, including `ffmpeg`, `poppler`, and `libreoffice`.

## Usage

```bash
python -m dreamlet_cli list-pages
python -m dreamlet_cli run 01
python -m dreamlet_cli run 06-4k-image-pptx-zip --all
python -m dreamlet_cli run 11-workflow-manager --template-name "Full Pipeline"
```

Common flags:

- `--all`: auto-select repeated lecture/language checkboxes
- `--confirm`: auto-enable confirmation checkboxes
- `--param NAME=VALUE`: set a widget value by normalized key

Per-page literal Streamlit controls are also exposed as CLI flags when they can be derived statically from the copied source.
