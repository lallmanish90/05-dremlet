from __future__ import annotations

import runpy
import sys
from pathlib import Path


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
        "Prepare Course Files",
        "Generate Core Assets",
        "Validate & Render Video",
        "Optional Translation & Multilingual",
        "Alternative Audio Providers",
        "Maintenance & Recovery",
        "Legacy & Fallback Tools",
    ]
    assert fake_st.navigation_kwargs == {"position": "sidebar", "expanded": True}

    prepare_titles = [page.title for page in fake_st.navigation_pages["Prepare Course Files"]]
    core_asset_titles = [page.title for page in fake_st.navigation_pages["Generate Core Assets"]]
    video_titles = [page.title for page in fake_st.navigation_pages["Validate & Render Video"]]
    translation_titles = [page.title for page in fake_st.navigation_pages["Optional Translation & Multilingual"]]
    alternative_audio_titles = [page.title for page in fake_st.navigation_pages["Alternative Audio Providers"]]
    legacy_titles = [page.title for page in fake_st.navigation_pages["Legacy & Fallback Tools"]]

    assert prepare_titles == [
        "01 Prepare AAA EEE",
        "02 Rename Lecture Files",
        "03 Split Text Sections",
        "04 Clean Unwanted Files",
        "05 Move Slide Files",
    ]
    assert core_asset_titles == [
        "06 Generate 4K Images",
        "07 Generate Audio with Kokoro",
    ]
    assert video_titles == [
        "08 Validate File Counts",
        "09 Repair MP4 Inputs",
        "10 Render MP4 Videos",
        "11 Verify MP4 Output",
    ]
    assert translation_titles == [
        "08 Translate with Ollama",
        "08 Translate with LM Studio",
        "52 Create Multilingual Folder Structure",
        "53 Convert Text to Multiple Languages",
        "54 Generate Multilingual Audio",
    ]
    assert alternative_audio_titles == [
        "55 Generate Audio with OpenAI",
        "15 Generate Audio with Inworld",
    ]
    assert legacy_titles == [
        "06 Legacy 4K Image",
        "06 Legacy 4K Image PPTX ZIP",
        "09 Legacy Count",
        "10 Legacy MP4 GPU",
        "58 Legacy Translator Lecto",
        "60 Legacy MP4 CPU",
    ]
    for section, pages in fake_st.navigation_pages.items():
        for page in pages:
            if page.title == "Home":
                continue
            assert Path(page.page).name == f"{page.title}.py", (
                f"{section} item {page.title!r} should map to the matching filename"
            )
    assert fake_st.selected_page is not None and fake_st.selected_page.ran is True
