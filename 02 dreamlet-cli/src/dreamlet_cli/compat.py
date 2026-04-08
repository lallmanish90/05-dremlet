from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import pprint
import re
from typing import Any


def _slug(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "value"


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coerce_number(value: Any, default: Any) -> Any:
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


@dataclass
class RunContext:
    page_id: str
    all_selected: bool = False
    confirm: bool = False
    raw_params: dict[str, Any] = field(default_factory=dict)


class SessionState(dict):
    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


class _Block:
    def __init__(self, root: "StreamlitCompat", label: str | None = None):
        self.root = root
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __getattr__(self, name: str):
        return getattr(self.root, name)


class _Progress:
    def __init__(self, root: "StreamlitCompat", value: float = 0.0):
        self.root = root
        self.value = value

    def progress(self, value: float):
        self.value = value
        return self

    def empty(self):
        return None


class StreamlitCompat:
    def __init__(self):
        self.session_state = SessionState()
        self._ctx = RunContext(page_id="unknown")
        self.sidebar = _Block(self, label="sidebar")

    def set_context(self, ctx: RunContext) -> None:
        self._ctx = ctx
        self.session_state = SessionState()
        self.sidebar = _Block(self, label="sidebar")

    def _resolve_name(self, label: str | None, key: str | None = None) -> str:
        return _slug(key or label)

    def _lookup(self, label: str | None, key: str | None = None) -> Any:
        widget_name = self._resolve_name(label, key)
        if widget_name in self._ctx.raw_params:
            return self._ctx.raw_params[widget_name]
        raw_key = key if isinstance(key, str) else None
        if raw_key and raw_key in self._ctx.raw_params:
            return self._ctx.raw_params[raw_key]
        return None

    def _selection_default(self, label: str | None, default: bool) -> bool:
        text = (label or "").lower()
        destructive = any(token in text for token in ["delete", "permanently", "cannot be undone"])
        confirmation = any(token in text for token in ["confirm", "understand", "ready to proceed", "estimated cost"])
        bulk_select = any(token in text for token in ["select all", "translate ", "process ", "prepare ", "restore "])
        if confirmation:
            return self._ctx.confirm
        if bulk_select and not destructive:
            return self._ctx.all_selected or default
        return default

    def set_page_config(self, *args, **kwargs):
        return None

    def title(self, value: Any, *args, **kwargs):
        print(f"# {value}")

    def header(self, value: Any, *args, **kwargs):
        print(f"\n## {value}")

    def subheader(self, value: Any, *args, **kwargs):
        print(f"\n### {value}")

    def caption(self, value: Any, *args, **kwargs):
        print(value)

    def markdown(self, value: Any, *args, **kwargs):
        print(value)

    def text(self, value: Any, *args, **kwargs):
        print(value)

    def write(self, *args, **kwargs):
        if args:
            print(" ".join(str(arg) for arg in args))

    def info(self, value: Any, *args, **kwargs):
        print(f"[info] {value}")

    def success(self, value: Any, *args, **kwargs):
        print(f"[ok] {value}")

    def warning(self, value: Any, *args, **kwargs):
        print(f"[warn] {value}")

    def error(self, value: Any, *args, **kwargs):
        print(f"[error] {value}")

    def exception(self, value: Any, *args, **kwargs):
        print(f"[exception] {value}")

    def code(self, value: Any, *args, **kwargs):
        print(value)

    def json(self, value: Any, *args, **kwargs):
        print(pprint.pformat(value))

    def table(self, value: Any, *args, **kwargs):
        print(value)

    def dataframe(self, value: Any, *args, **kwargs):
        print(value)

    def metric(self, label: str, value: Any, delta: Any = None, *args, **kwargs):
        suffix = f" ({delta})" if delta is not None else ""
        print(f"{label}: {value}{suffix}")

    def checkbox(self, label: str, value: bool = False, key: str | None = None, **kwargs):
        resolved = self._lookup(label, key)
        if resolved is not None:
            result = _coerce_bool(resolved)
        else:
            result = self._selection_default(label, value)
        if key:
            self.session_state[key] = result
        return result

    def selectbox(self, label: str, options, index: int = 0, key: str | None = None, format_func=None, **kwargs):
        options = list(options)
        resolved = self._lookup(label, key)
        if resolved is not None:
            for option in options:
                rendered = format_func(option) if format_func else str(option)
                if str(resolved) == str(option) or str(resolved) == str(rendered):
                    if key:
                        self.session_state[key] = option
                    return option
        result = options[index] if options else None
        if key:
            self.session_state[key] = result
        return result

    def radio(self, label: str, options, index: int = 0, key: str | None = None, **kwargs):
        return self.selectbox(label, options, index=index, key=key, **kwargs)

    def multiselect(self, label: str, options, default=None, key: str | None = None, **kwargs):
        options = list(options)
        resolved = self._lookup(label, key)
        if resolved is not None:
            if isinstance(resolved, str):
                values = [item.strip() for item in resolved.split(",") if item.strip()]
            else:
                values = list(resolved)
            selected = [item for item in options if str(item) in {str(v) for v in values}]
        elif self._ctx.all_selected and default in (None, [], ()):
            selected = options
        else:
            selected = list(default or [])
        if key:
            self.session_state[key] = selected
        return selected

    def text_input(self, label: str, value: str = "", key: str | None = None, **kwargs):
        resolved = self._lookup(label, key)
        result = value if resolved is None else str(resolved)
        if key:
            self.session_state[key] = result
        return result

    def text_area(self, label: str, value: str = "", key: str | None = None, **kwargs):
        return self.text_input(label, value=value, key=key, **kwargs)

    def number_input(self, label: str, value: Any = 0, key: str | None = None, **kwargs):
        resolved = self._lookup(label, key)
        result = value if resolved is None else _coerce_number(resolved, value)
        if key:
            self.session_state[key] = result
        return result

    def slider(self, label: str, min_value=None, max_value=None, value=None, key: str | None = None, **kwargs):
        resolved = self._lookup(label, key)
        default = value if value is not None else min_value
        result = default if resolved is None else _coerce_number(resolved, default)
        if key:
            self.session_state[key] = result
        return result

    def button(self, label: str, disabled: bool = False, key: str | None = None, **kwargs):
        if disabled:
            return False
        resolved = self._lookup(label, key)
        if resolved is not None:
            return _coerce_bool(resolved)
        text = label.lower()
        if any(token in text for token in ["clear results", "load template", "view previous results", "reset to default", "restore all processed files", "select all languages", "deselect"]):
            return False
        return True

    def columns(self, spec, **kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            count = len(spec)
        return [_Block(self) for _ in range(count)]

    def tabs(self, labels):
        return [_Block(self, label=str(label)) for label in labels]

    def container(self):
        return _Block(self)

    def expander(self, label: str, **kwargs):
        print(f"\n[expander] {label}")
        return _Block(self, label=label)

    def empty(self):
        return _Block(self)

    @contextmanager
    def spinner(self, text: str = ""):
        if text:
            print(f"[spinner] {text}")
        yield _Block(self, label=text)

    def progress(self, value: float = 0.0):
        return _Progress(self, value)

    def download_button(self, *args, **kwargs):
        return False

    def rerun(self):
        return None

    def experimental_rerun(self):
        return None


st = StreamlitCompat()
