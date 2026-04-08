from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

from dreamlet_cli.catalog import PageEntry, sorted_pages, load_catalog
from dreamlet_cli.compat import RunContext, st


def _parse_param(values: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"invalid --param value: {item!r}; expected NAME=VALUE")
        key, value = item.split("=", 1)
        params[key.strip()] = value.strip()
    return params


def _build_page_parser(page: PageEntry) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"dreamlet run {page.page_id}",
        description=f"{page.title}: {page.purpose}",
    )
    parser.add_argument("--all", action="store_true", help="auto-select repeated lecture/language checkboxes")
    parser.add_argument("--confirm", action="store_true", help="auto-enable confirmation checkboxes")
    parser.add_argument("--param", action="append", default=[], metavar="NAME=VALUE", help="set a widget value by normalized name")
    reserved_flags = {"all", "confirm", "param"}
    added_flags: set[str] = set()
    for widget in page.widgets:
        if not widget.generated_flag:
            continue
        if widget.generated_flag in reserved_flags:
            continue
        flag = f"--{widget.generated_flag}"
        if flag in added_flags:
            continue
        if widget.value_type == "bool":
            parser.add_argument(flag, dest=widget.name, action="store_true", help=f"set {widget.label}")
            parser.add_argument(f"--no-{widget.generated_flag}", dest=widget.name, action="store_false")
        elif widget.value_type == "list":
            parser.add_argument(flag, dest=widget.name, action="append", help=f"set {widget.label}")
        else:
            parser.add_argument(flag, dest=widget.name, help=f"set {widget.label}")
        added_flags.add(flag)
    return parser


def _run_page(page: PageEntry, args: argparse.Namespace) -> int:
    params = _parse_param(args.param)
    for key, value in vars(args).items():
        if key in {"all", "confirm", "param"} or value is None:
            continue
        params[key] = value

    st.set_context(
        RunContext(
            page_id=page.page_id,
            all_selected=args.all,
            confirm=args.confirm,
            raw_params=params,
        )
    )

    module = importlib.import_module(f"dreamlet_cli.pages.{page.module_name}")
    if hasattr(module, "main"):
        module.main()
    return 0


def _cmd_list_pages() -> int:
    for page in sorted_pages():
        status = page.status.lower()
        compile_note = "" if page.source_compiles else " [patched]"
        print(f"{page.page_id:<35} {status:<12} {page.title}{compile_note}")
    return 0


def _cmd_run(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: dreamlet run <page-id> [options]\n")
        print("available page ids:")
        for page in sorted_pages():
            print(f"  {page.page_id}")
        return 0

    page_id = argv[0]
    catalog = load_catalog()
    if page_id not in catalog:
        print(f"unknown page id: {page_id}", file=sys.stderr)
        return 2

    parser = _build_page_parser(catalog[page_id])
    args = parser.parse_args(argv[1:])
    return _run_page(catalog[page_id], args)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: dreamlet <command> [args]\n")
        print("commands:")
        print("  list-pages")
        print("  run <page-id>")
        return 0

    command = argv[0]
    if command == "list-pages":
        return _cmd_list_pages()
    if command == "run":
        return _cmd_run(argv[1:])

    print(f"unknown command: {command}", file=sys.stderr)
    return 2
