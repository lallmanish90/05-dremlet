# Dreamlet CLI

`02 dreamlet-cli` is a standalone, file-first CLI clone of these three `01` pages:

- `src/06 Generate 4K Images.py`
- `src/07 Generate Audio with Kokoro.py`
- `src/10 Render MP4 Videos.py`

Each script is standalone. No processing code is shared between the three files in `src/`.

Each script has its own same-named TOML:

- `config/06 Generate 4K Images.toml`
- `config/07 Generate Audio with Kokoro.toml`
- `config/10 Render MP4 Videos.toml`

## Install

```powershell
python -m pip install -e .
```

## Run

```powershell
python "src/06 Generate 4K Images.py"
python "src/07 Generate Audio with Kokoro.py"
python "src/10 Render MP4 Videos.py"
```

Each script accepts an optional explicit config path:

```powershell
python "src/06 Generate 4K Images.py" --config "config/06 Generate 4K Images.toml"
python "src/07 Generate Audio with Kokoro.py" --config "config/07 Generate Audio with Kokoro.toml"
python "src/10 Render MP4 Videos.py" --config "config/10 Render MP4 Videos.toml"
```

## Notes

- The sample TOMLs are configured for this folder's local `input`, `output`, and `config` paths.
- `06 Generate 4K Images.py` expects `config/logo.png` and `config/copyright.txt`.
- `07 Generate Audio with Kokoro.py` expects a Kokoro service at `http://localhost:8880`.
- `10 Render MP4 Videos.py` writes MP4 output under `output/`.
