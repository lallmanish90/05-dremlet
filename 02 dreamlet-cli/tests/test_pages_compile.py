from pathlib import Path
import py_compile


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "src" / "dreamlet_cli" / "pages"


def test_all_copied_page_modules_compile():
    failures = []
    for path in sorted(PAGES.glob("page_*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")

    assert failures == []
