#!/usr/bin/env python3
"""Generate the Python doctest ``Examples:`` in the curated namespaces from the
vendored canonical example specs (``idl/v1/examples/<id>.yaml``).

One spec per command drives the strata-core reference docs (CLI + wire tabs)
*and* these SDK docstring examples — single source, no drift. The example
scenario (which calls, which args, the expected result) is authored once in
strata-core; here it is rendered to the curated ``db.<ns>.<method>(...)`` form,
with the expected result formatted from the curated method's return annotation
(``Optional[bytes]`` -> ``b'...'``, ``bool`` -> ``True``/``False``, ...).

Usage:
  python tools/generate_examples.py --check   # fail if any block is stale
  python tools/generate_examples.py --write   # rewrite the bound docstrings

The rendered examples remain plain doctests, so ``tests/test_doctests.py`` still
executes them against a fresh ``Strata(cache=True)`` — that is where the exact
value (``b'hello'``) is asserted.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "idl" / "v1" / "examples"
NS_DIR = ROOT / "python" / "stratadb" / "namespaces"

# command id -> (namespace module, curated method) whose docstring shows it.
# Grows as example specs land; every command referenced by a bound spec's
# steps must itself be bound (so the call form is known).
BINDINGS = {
    "kv.put": ("kv", "put"),
    "kv.get": ("kv", "get"),
    "kv.exists": ("kv", "exists"),
    "kv.delete": ("kv", "delete"),
    "kv.count": ("kv", "count"),
}

DOCSTRING_INDENT = " " * 8  # method docstrings sit at 8 spaces
EXAMPLE_INDENT = " " * 12  # >>> lines sit at 12


def load_spec(command_id: str) -> dict:
    return yaml.safe_load((EXAMPLES / f"{command_id}.yaml").read_text())


def namespace_methods(ns: str) -> dict:
    """Reads each method's positional params, keyword-only params, and return
    annotation from the namespace source (no import of the built extension)."""
    tree = ast.parse((NS_DIR / f"{ns}.py").read_text())
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            methods[node.name] = {
                "pos": [a.arg for a in node.args.args if a.arg != "self"],
                "kwonly": [a.arg for a in node.args.kwonlyargs],
                "returns": ast.unparse(node.returns) if node.returns else "Any",
            }
    return methods


def py_lit(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    return json.dumps(value)  # strings render double-quoted; numbers as-is


def render_call(step: dict, methods: dict) -> str:
    ns, method = BINDINGS[step["call"]]
    sig = methods[ns][method]
    args = step.get("args") or {}
    parts = [py_lit(args[p]) for p in sig["pos"] if p in args]
    parts += [f"{k}={py_lit(args[k])}" for k in sig["kwonly"] if k in args]
    return f"db.{ns}.{method}({', '.join(parts)})"


def render_result(value, return_annotation: str) -> str:
    if "bytes" in return_annotation and isinstance(value, str):
        return f"b{json.dumps(value)}".replace('"', "'")  # b'hello'
    if isinstance(value, bool):
        return "True" if value else "False"
    return json.dumps(value)


def render_step(step: dict, methods: dict) -> list[str]:
    call = render_call(step, methods)
    note = f"  # {step['note']}" if step.get("note") else ""
    if "returns" not in step:
        return [f">>> _ = {call}{note}"]
    value = step["returns"]
    if value is None:  # returns: null -> a miss
        return [f">>> {call} is None", "True"]
    ns, method = BINDINGS[step["call"]]
    return [f">>> {call}", render_result(value, methods[ns][method]["returns"])]


def render_block(command_id: str, methods: dict) -> list[str]:
    """The dedented doctest lines (>>> / continuations / results) for a spec."""
    spec = load_spec(command_id)
    lines: list[str] = []
    for step in spec["steps"]:
        lines += render_step(step, methods)
    return lines


# --------------------------------------------------------------------------
# Docstring surgery
# --------------------------------------------------------------------------


def split_prose(docstring: str) -> str:
    """The docstring content up to (not including) its ``Examples:`` block."""
    marker = docstring.find(f"\n{DOCSTRING_INDENT}Examples:")
    return (docstring[:marker] if marker != -1 else docstring).rstrip()


def existing_block(docstring: str) -> list[str] | None:
    """The dedented doctest lines currently in a docstring, or None."""
    marker = docstring.find(f"\n{DOCSTRING_INDENT}Examples:")
    if marker == -1:
        return None
    lines = []
    for raw in docstring[marker:].splitlines():
        stripped = raw.strip()
        if not stripped or stripped == "Examples:":
            continue
        lines.append(stripped)
    return lines


def build_docstring(prose: str, block: list[str]) -> str:
    body = f"{DOCSTRING_INDENT}Examples:\n" + "\n".join(
        f"{EXAMPLE_INDENT}{line}" for line in block
    )
    return f"{prose}\n\n{body}\n{DOCSTRING_INDENT}"


def method_docstring_nodes(source: str):
    """Yields (method_name, docstring_constant_node) for each method."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                yield node.name, first.value


def process(write: bool) -> int:
    by_file: dict[str, list[str]] = {}
    for command_id, (ns, _method) in BINDINGS.items():
        by_file.setdefault(ns, []).append(command_id)

    methods = {ns: namespace_methods(ns) for ns in by_file}
    stale = []
    for ns, command_ids in by_file.items():
        path = NS_DIR / f"{ns}.py"
        source = path.read_text()
        # Map bound method -> command id for this namespace.
        method_to_cmd = {BINDINGS[c][1]: c for c in command_ids}

        edits = []  # (node, new_docstring_value)
        for method_name, const in method_docstring_nodes(source):
            command_id = method_to_cmd.get(method_name)
            if command_id is None:
                continue
            block = render_block(command_id, methods)
            if existing_block(const.value) == block:
                continue
            stale.append(f"{ns}.{method_name} ({command_id})")
            edits.append((const, build_docstring(split_prose(const.value), block)))

        if write and edits:
            source = apply_edits(source, edits)
            path.write_text(source)

    if stale and not write:
        print("stale example docstrings (run tools/generate_examples.py --write):")
        for item in stale:
            print(f"  - {item}")
        return 1
    if write:
        print(f"synced {len(stale)} example docstring(s)")
    return 0


def apply_edits(source: str, edits: list) -> str:
    """Replaces each docstring literal's source span, bottom-up so earlier
    line numbers stay valid."""
    lines = source.splitlines(keepends=True)
    for const, new_value in sorted(edits, key=lambda e: e[0].lineno, reverse=True):
        start = const.lineno - 1  # 0-indexed first line of the literal
        end = const.end_lineno - 1  # 0-indexed last line
        literal = f'{DOCSTRING_INDENT}"""{new_value}"""\n'
        lines[start : end + 1] = [literal]
    return "".join(lines)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--check", "--write"):
        print("usage: generate_examples.py <--check|--write>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(process(write=(mode == "--write")))


if __name__ == "__main__":
    main()
