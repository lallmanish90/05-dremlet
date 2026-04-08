from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(PYTHONPATH=str(ROOT / "src"))
    return subprocess.run(
        [sys.executable, "-m", "dreamlet_cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_list_pages_shows_collision_safe_ids():
    result = run_cli("list-pages")

    assert result.returncode == 0
    assert "01" in result.stdout
    assert "06-4k-image" in result.stdout
    assert "06-4k-image-pptx-zip" in result.stdout
    assert "08-ollama" in result.stdout
    assert "11-workflow-manager" in result.stdout
    assert "99-03-save-text-backup" in result.stdout


def test_help_has_no_side_effects():
    before = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if ".pytest_cache" not in path.parts and "__pycache__" not in path.parts
    )

    result = run_cli("run", "01", "--help")

    after = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if ".pytest_cache" not in path.parts and "__pycache__" not in path.parts
    )

    assert result.returncode == 0
    assert before == after


def test_header_only_page_runs_without_browser_layer():
    result = run_cli("run", "50")

    assert result.returncode == 0
    assert "Legacy" in result.stdout
