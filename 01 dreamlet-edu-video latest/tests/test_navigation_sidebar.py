from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


class FakePage:
    def __init__(self, page, title=None, icon=None, default=False):
        self.page = page
        self.title = title
        self.icon = icon
        self.default = default
        self.ran = False

    def run(self):
        self.ran = True


class FakeStreamlit:
    def __init__(self):
        self.navigation_pages = None
        self.navigation_kwargs = None
        self.selected_page = None

    def set_page_config(self, *args, **kwargs):
        return None

    def Page(self, page, title=None, icon=None, default=False):
        return FakePage(page=page, title=title, icon=icon, default=default)

    def navigation(self, pages, **kwargs):
        self.navigation_pages = pages
        self.navigation_kwargs = kwargs
        for section_pages in pages.values():
            for page in section_pages:
                if page.default:
                    self.selected_page = page
                    return page
        self.selected_page = next(iter(next(iter(pages.values()))))
        return self.selected_page

    def title(self, *args, **kwargs):
        return None

    def subheader(self, *args, **kwargs):
        return None

    def markdown(self, *args, **kwargs):
        return None

    def header(self, *args, **kwargs):
        return None

    def success(self, *args, **kwargs):
        return None


def test_app_uses_categorized_navigation(monkeypatch, tmp_path: Path):
    fake_st = FakeStreamlit()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    runpy.run_path(str(ROOT / "app.py"), run_name="__main__")

    assert fake_st.navigation_pages is not None
    assert list(fake_st.navigation_pages.keys()) == [
        "Overview",
        "Core Workflow",
        "Translation & Multilingual",
        "Validation & Video",
        "Maintenance & Recovery",
        "Legacy & Alternate",
    ]
    assert fake_st.navigation_kwargs == {"position": "sidebar", "expanded": True}

    core_titles = [page.title for page in fake_st.navigation_pages["Core Workflow"]]
    legacy_titles = [page.title for page in fake_st.navigation_pages["Legacy & Alternate"]]

    assert "Adjust AAA EEE" in core_titles
    assert "Rename" in core_titles
    assert "Count New" in [page.title for page in fake_st.navigation_pages["Validation & Video"]]
    assert "Multilingual TTS" in [page.title for page in fake_st.navigation_pages["Translation & Multilingual"]]
    assert "4K Image" in legacy_titles
    assert fake_st.selected_page is not None and fake_st.selected_page.ran is True
