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


def test_workflow_manager_smoke_run():
    result = run_cli("run", "11-workflow-manager")
    assert result.returncode == 0


def test_multilingual_page_smoke_run():
    result = run_cli("run", "52")
    assert result.returncode == 0


def test_backup_page_smoke_run():
    result = run_cli("run", "99-01-rename-backup")
    assert result.returncode == 0


def test_remove_unwanted_smoke_run():
    result = run_cli("run", "04")
    assert result.returncode == 0


def test_count_legacy_smoke_run():
    result = run_cli("run", "09-count")
    assert result.returncode == 0


def test_count_new_smoke_run():
    result = run_cli("run", "09-count-new")
    assert result.returncode == 0


def test_delete_smoke_run():
    result = run_cli("run", "12")
    assert result.returncode == 0


def test_experimental_51_smoke_run():
    result = run_cli("run", "51")
    assert result.returncode == 0


def test_legacy_mp4_cpu_smoke_run():
    result = run_cli("run", "60")
    assert result.returncode == 0
