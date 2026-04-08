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

    def run(self):
        return None


class _Block:
    def __init__(self, root):
        self.root = root

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __getattr__(self, name):
        return getattr(self.root, name)


class FakeStreamlit:
    def __init__(self):
        self.calls = []

    def set_page_config(self, *args, **kwargs):
        return None

    def Page(self, page, title=None, icon=None, default=False):
        return FakePage(page=page, title=title, icon=icon, default=default)

    def navigation(self, pages, **kwargs):
        for section_pages in pages.values():
            for page in section_pages:
                if page.default:
                    return page
        return next(iter(next(iter(pages.values()))))

    def title(self, value, *args, **kwargs):
        self.calls.append(("title", value))

    def subheader(self, value, *args, **kwargs):
        self.calls.append(("subheader", value))

    def header(self, value, *args, **kwargs):
        self.calls.append(("header", value))

    def caption(self, value, *args, **kwargs):
        self.calls.append(("caption", value))

    def markdown(self, value, *args, **kwargs):
        self.calls.append(("markdown", value))

    def write(self, value="", *args, **kwargs):
        self.calls.append(("write", value))

    def info(self, value, *args, **kwargs):
        self.calls.append(("info", value))

    def warning(self, value, *args, **kwargs):
        self.calls.append(("warning", value))

    def success(self, value, *args, **kwargs):
        self.calls.append(("success", value))

    def metric(self, label, value, *args, **kwargs):
        self.calls.append(("metric", label, value))

    def columns(self, spec, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Block(self) for _ in range(count)]

    def expander(self, label, **kwargs):
        self.calls.append(("expander", label))
        return _Block(self)

    def divider(self):
        self.calls.append(("divider", None))


def _seed_runtime_tree(base: Path) -> None:
    input_dir = base / "input"
    output_dir = base / "output"
    course = input_dir / "Course 01"
    lecture = course / "Lecture 01"
    english_text = lecture / "English text"
    english_audio = lecture / "English audio"
    english_image = lecture / "English image"

    english_text.mkdir(parents=True)
    english_audio.mkdir(parents=True)
    english_image.mkdir(parents=True)
    output_dir.mkdir()

    (course / "01-AAA.md").write_text("aaa", encoding="utf-8")
    (course / "01-EEE.md").write_text("eee", encoding="utf-8")
    (course / "Lecture 01.md").write_text("transcript", encoding="utf-8")
    (course / "01-slides.md").write_text("slides", encoding="utf-8")
    (course / "01.pptx").write_text("pptx", encoding="utf-8")
    (english_text / "01.txt").write_text("section", encoding="utf-8")
    (english_audio / "01.mp3").write_text("audio", encoding="utf-8")
    (english_image / "01.png").write_text("image", encoding="utf-8")
    (output_dir / "English").mkdir()
    (output_dir / "English" / "Lecture 01.mp4").write_text("mp4", encoding="utf-8")


def test_homepage_dashboard_logic_and_sections(monkeypatch, tmp_path: Path):
    fake_st = FakeStreamlit()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    globals_dict = runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
    _seed_runtime_tree(tmp_path)

    context = globals_dict["build_homepage_context"]()
    assert context["input"]["courses"] == 1
    assert context["input"]["lectures"] == 1
    assert context["input"]["aaa_files"] == 1
    assert context["input"]["eee_files"] == 1
    assert context["generated"]["audio_folders"] == 1
    assert context["generated"]["image_folders"] == 1
    assert context["generated"]["mp4_files"] == 1

    next_step = globals_dict["get_recommended_next_step"](context)
    assert next_step["title"] == "Adjust AAA EEE"

    fake_st.calls.clear()
    globals_dict["render_homepage"]()
    headers = [call[1] for call in fake_st.calls if call[0] in {"header", "subheader"}]

    assert "Input Status" in headers
    assert "Current Blockers" in headers
    assert "Recommended Next Step" in headers
    assert "Workflow Status" in headers
    assert "Generated Assets" in headers
