#!/usr/bin/env python3
"""Generate stratadb's typed core from the vendored IDL.

Reads ``idl/v1/command-index.json`` + ``idl/v1/schemas/<id>.json`` and emits
``python/stratadb/_generated/{models.py, commands.py, catalog.py, __init__.py}``.

Design:
- Concrete leaf DTOs (``CommitReceipt``, ``VersionedValue``, enums, …) are
  byte-identical across every schema, so each becomes one shared dataclass/enum.
- Structural envelopes that specialize per command (``Maybe`` value type,
  ``BatchItemResult``) are resolved *here*, at generation time, and emitted as
  explicit inline decode — there is no runtime schema-walking.

Determinism: identical inputs produce byte-identical output (the CI drift guard
re-runs this and diffs). Data-plane only: the ``inference`` family and the two
``hub`` admin commands are excluded (the wheel is built without those features)
and recorded in the uncovered-command allowlist for the coverage guard.
"""

from __future__ import annotations

import json
import keyword
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDL = ROOT / "idl" / "v1"
OUT = ROOT / "python" / "stratadb" / "_generated"

EXCLUDED_FAMILIES = {"inference"}
EXCLUDED_IDS = {"admin.hub_clone", "admin.remote"}
EXCLUDED_REASON = "out of the V1 data-plane surface (requires the inference/hub executor features)"

HEADER = '''"""Generated from the Strata IDL — do not edit by hand.

Regenerate with ``python tools/generate.py``. The CI drift guard fails if this
file is stale.
"""
'''


# --------------------------------------------------------------------------
# Schema helpers
# --------------------------------------------------------------------------


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def ref_name(schema: dict) -> str:
    return schema["$ref"].rsplit("/", 1)[-1]


def is_bytes(defn: dict) -> bool:
    return defn.get("contentEncoding") == "base64"


def is_enum(defn: dict) -> bool:
    if "enum" in defn:
        return True
    one_of = defn.get("oneOf")
    return bool(one_of) and all("const" in v for v in one_of)


def enum_values(defn: dict) -> list[str]:
    if "enum" in defn:
        return list(defn["enum"])
    return [v["const"] for v in defn["oneOf"]]


def is_object(defn: dict) -> bool:
    return defn.get("type") == "object" and "properties" in defn


def non_null_variant(schema) -> tuple:
    """Returns (non-null schema, nullable?) for anyOf/typed-null shapes."""
    if isinstance(schema, bool):
        return schema, False
    if "anyOf" in schema:
        variants = [v for v in schema["anyOf"] if v.get("type") != "null"]
        nullable = any(v.get("type") == "null" for v in schema["anyOf"])
        inner = variants[0] if len(variants) == 1 else {"anyOf": variants}
        return inner, nullable
    t = schema.get("type")
    if isinstance(t, list):
        nn = [x for x in t if x != "null"]
        base = {k: v for k, v in schema.items() if k != "type"}
        base["type"] = nn[0] if len(nn) == 1 else nn
        return base, ("null" in t)
    return schema, False


# --------------------------------------------------------------------------
# Load + classify defs across all data-plane commands
# --------------------------------------------------------------------------


def load_commands() -> list[dict]:
    index = json.loads((IDL / "command-index.json").read_text())
    out = []
    for cmd in index["commands"]:
        if cmd["family"] in EXCLUDED_FAMILIES or cmd["id"] in EXCLUDED_IDS:
            continue
        schema = json.loads((IDL / "schemas" / f"{cmd['id']}.json").read_text())
        out.append({**cmd, "schema": schema})
    return sorted(out, key=lambda c: c["id"])


def classify(commands: list[dict]):
    """Returns (defs, model_names, bytes_names).

    ``defs`` maps a def name to its canonical content (for convergent names).
    ``model_names`` are the convergent enum/object defs safe to share as a
    single generated class; ``bytes_names`` are the base64 scalar defs.
    """
    hashes: dict[str, set[str]] = {}
    content: dict[str, dict] = {}
    for cmd in commands:
        for name, defn in cmd["schema"].get("$defs", {}).items():
            hashes.setdefault(name, set()).add(canon(defn))
            content.setdefault(name, defn)

    convergent = {n for n, hs in hashes.items() if len(hs) == 1}
    bytes_names = {n for n in convergent if is_bytes(content[n])}
    enum_names = {n for n in convergent if is_enum(content[n])}
    object_names = {n for n in convergent if is_object(content[n])}

    # An object is shareable only if every def it references is itself
    # shareable (or a scalar/bytes/enum). Iterate to a fixpoint.
    shareable = set(enum_names) | set(object_names)

    def refs_of(defn) -> set[str]:
        found: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                if "$ref" in node:
                    found.add(ref_name(node))
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(defn)
        return found

    changed = True
    while changed:
        changed = False
        for name in list(shareable):
            if name not in object_names:
                continue
            for r in refs_of(content[name]):
                blocked = (
                    r not in convergent
                    or (r not in shareable and r not in bytes_names)
                )
                if blocked:
                    shareable.discard(name)
                    changed = True
                    break

    model_names = {n for n in shareable}
    return content, model_names, bytes_names, enum_names, object_names


# --------------------------------------------------------------------------
# Code emitters
# --------------------------------------------------------------------------


class Emitter:
    def __init__(self, defs, model_names, bytes_names, enum_names, prefix="models."):
        self.defs = defs
        self.model_names = model_names
        self.bytes_names = bytes_names
        self.enum_names = enum_names
        self.prefix = prefix  # "" inside models.py, "models." inside commands.py

    def decode(self, expr: str, schema) -> str:
        if not schema or schema is True or isinstance(schema, bool):
            return expr
        if "$ref" in schema:
            name = ref_name(schema)
            if name in self.bytes_names:
                return f"_wire.b64d({expr})"
            if name in self.enum_names and name in self.model_names:
                return f"{self.prefix}{name}({expr})"
            if name in self.model_names:
                return f"{self.prefix}{name}.from_wire({expr})"
            return self.decode(expr, self.defs[name])  # inline-expand
        if "anyOf" in schema:
            inner, _ = non_null_variant(schema)
            return f"(None if {expr} is None else {self.decode(expr, inner)})"
        t = schema.get("type")
        if isinstance(t, list):
            base, nullable = non_null_variant(schema)
            if nullable:
                return f"(None if {expr} is None else {self.decode(expr, base)})"
            return self.decode(expr, base)
        if t == "array":
            return f"[{self.decode('_x', schema.get('items', {}))} for _x in ({expr} or [])]"
        if t == "object" and "properties" in schema:
            req = set(schema.get("required", []))
            parts = []
            for k in sorted(schema["properties"]):
                ks = schema["properties"][k]
                if k in req:
                    parts.append(f"{k!r}: {self.decode(f'{expr}[{k!r}]', ks)}")
                else:
                    nn, _ = non_null_variant(ks)
                    parts.append(
                        f"{k!r}: (None if {expr}.get({k!r}) is None "
                        f"else {self.decode(f'{expr}[{k!r}]', nn)})"
                    )
            return f"_wire.Record({{{', '.join(parts)}}})"
        return expr

    def encode(self, expr: str, schema) -> str:
        if not schema or schema is True or isinstance(schema, bool):
            return expr
        if "$ref" in schema:
            name = ref_name(schema)
            if name in self.bytes_names:
                return f"_wire.b64e({expr})"
            return self.encode(expr, self.defs[name])  # inline-expand
        if "anyOf" in schema:
            inner, _ = non_null_variant(schema)
            return f"(None if {expr} is None else {self.encode(expr, inner)})"
        t = schema.get("type")
        if isinstance(t, list):
            base, nullable = non_null_variant(schema)
            if nullable:
                return f"(None if {expr} is None else {self.encode(expr, base)})"
            return self.encode(expr, base)
        if t == "array":
            return f"[{self.encode('_x', schema.get('items', {}))} for _x in ({expr} or [])]"
        if t == "object" and "properties" in schema:
            req = set(schema.get("required", []))
            parts = []
            for k in sorted(schema["properties"]):
                ks = schema["properties"][k]
                acc = f"{expr}[{k!r}]"
                if k in req:
                    parts.append(f"{k!r}: {self.encode(acc, ks)}")
                else:
                    nn, _ = non_null_variant(ks)
                    parts.append(
                        f"{k!r}: (None if {expr}.get({k!r}) is None "
                        f"else {self.encode(acc, nn)})"
                    )
            return f"{{{', '.join(parts)}}}"
        return expr

    def annotate(self, schema: dict, optional: bool = False) -> str:
        ann = self._ann(schema)
        return f"Optional[{ann}]" if optional and not ann.startswith("Optional") else ann

    def _ann(self, schema) -> str:
        if not schema or isinstance(schema, bool):
            return "Any"
        if "$ref" in schema:
            name = ref_name(schema)
            if name in self.bytes_names:
                return "bytes"
            if name in self.model_names:
                return f'"{name}"'
            return "_wire.Record"
        if "anyOf" in schema:
            inner, nullable = non_null_variant(schema)
            base = self._ann(inner)
            return f"Optional[{base}]" if nullable else base
        t = schema.get("type")
        if isinstance(t, list):
            base_schema, nullable = non_null_variant(schema)
            base = self._ann(base_schema)
            return f"Optional[{base}]" if nullable else base
        if t == "array":
            return f"List[{self._ann(schema.get('items', {}))}]"
        if t == "object":
            return "_wire.Record"
        return {"integer": "int", "number": "float", "boolean": "bool", "string": "str"}.get(t, "Any")


# --------------------------------------------------------------------------
# models.py
# --------------------------------------------------------------------------


def enum_member(value: str) -> str:
    name = value.upper().replace(".", "_").replace("-", "_")
    if not name or name[0].isdigit():
        name = "V_" + name
    if keyword.iskeyword(name):
        name += "_"
    return name


def gen_models(defs, model_names, bytes_names, enum_names, object_names, emitter) -> str:
    lines = [
        HEADER,
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from enum import Enum",
        "from typing import Any, List, Optional",
        "",
        "from .. import _wire",
        "",
    ]

    for name in sorted(model_names):
        defn = defs[name]
        if name in enum_names:
            lines.append(f"class {name}(str, Enum):")
            doc = defn.get("description")
            if doc:
                lines.append(f'    """{doc.splitlines()[0]}"""')
            for value in enum_values(defn):
                lines.append(f'    {enum_member(value)} = {value!r}')
            lines.append("")
            lines.append("")
        else:  # object
            props = defn["properties"]
            req = list(defn.get("required", []))
            required = sorted(k for k in props if k in req)
            optional = sorted(k for k in props if k not in req)
            lines.append("@dataclass")
            lines.append(f"class {name}:")
            doc = defn.get("description")
            if doc:
                lines.append(f'    """{doc.splitlines()[0]}"""')
            if not required and not optional:
                lines.append("    pass")
            for k in required:
                lines.append(f"    {safe_field(k)}: {emitter.annotate(props[k])}")
            for k in optional:
                lines.append(f"    {safe_field(k)}: {emitter.annotate(props[k], optional=True)} = None")
            lines.append("")
            lines.append("    @classmethod")
            lines.append("    def from_wire(cls, d: dict) -> \"%s\":" % name)
            lines.append("        return cls(")
            for k in required:
                lines.append(f"            {safe_field(k)}={emitter.decode(f'd[{k!r}]', props[k])},")
            for k in optional:
                nn, _ = non_null_variant(props[k])
                lines.append(
                    f"            {safe_field(k)}=(None if d.get({k!r}) is None "
                    f"else {emitter.decode(f'd[{k!r}]', nn)}),"
                )
            lines.append("        )")
            lines.append("")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def safe_field(name: str) -> str:
    return name + "_" if keyword.iskeyword(name) else name


# --------------------------------------------------------------------------
# commands.py
# --------------------------------------------------------------------------


def gen_commands(commands, emitter) -> str:
    lines = [
        HEADER,
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "from .. import _wire",
        "from . import models",
        "",
        "",
        "class Commands:",
        '    """One typed method per data-plane command, over the core wire."""',
        "",
        "    __slots__ = (\"_core\",)",
        "",
        "    def __init__(self, core: Any):",
        "        self._core = core",
        "",
    ]

    for cmd in commands:
        req_schema = cmd["schema"]["request"]
        resp_data = cmd["schema"]["response"]["properties"]["data"]
        props = req_schema["properties"]
        required = [k for k in req_schema.get("required", []) if k != "type"]
        wire_tag = props["type"]["const"]
        method = cmd["id"].replace(".", "_")

        # branch/space are session scope only when optional; when required they
        # are real operands (branch.create's `branch` is the name to create).
        scope = [k for k in ("branch", "space") if k in props and k not in required]
        optional = sorted(k for k in props if k not in required and k != "type" and k not in scope)

        # signature: required positional, then keyword-only optionals + scope
        sig = ["self"]
        for k in required:
            sig.append(safe_field(k))
        kw = optional + scope
        if kw:
            sig.append("*")
            for k in kw:
                sig.append(f"{safe_field(k)}=None")
        lines.append(f"    def {method}({', '.join(sig)}):")

        summary = cmd.get("summary") or cmd.get("title") or ""
        errs = ", ".join(e["code"] for e in cmd.get("errors", []))
        doc = f'        """{summary}'
        if errs:
            doc += f"\n\n        Errors: {errs}"
        doc += '\n        """'
        lines.append(doc)

        lines.append(f"        cmd = {{'type': {wire_tag!r}}}")
        for k in required:
            lines.append(f"        cmd[{k!r}] = {emitter.encode(safe_field(k), props[k])}")
        for k in optional:
            nn, _ = non_null_variant(props[k])
            lines.append(f"        if {safe_field(k)} is not None:")
            lines.append(f"            cmd[{k!r}] = {emitter.encode(safe_field(k), nn)}")
        for k in scope:
            lines.append(f"        if {safe_field(k)} is not None:")
            lines.append(f"            cmd[{k!r}] = {safe_field(k)}")
        lines.append("        data = self._core.data(cmd)")
        lines.append(f"        return {emitter.decode('data', resp_data)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# catalog.py + __init__.py
# --------------------------------------------------------------------------


def gen_catalog(commands, all_ids) -> str:
    generated = sorted(c["id"] for c in commands)
    uncovered = sorted(set(all_ids) - set(generated))
    lines = [
        HEADER,
        "from __future__ import annotations",
        "",
        "# Every data-plane command with a generated typed method.",
        "GENERATED_COMMANDS = [",
    ]
    lines += [f"    {i!r}," for i in generated]
    lines += [
        "]",
        "",
        "# Commands intentionally not surfaced (coverage guard allowlist).",
        f"UNCOVERED_REASON = {EXCLUDED_REASON!r}",
        "UNCOVERED_COMMANDS = [",
    ]
    lines += [f"    {i!r}," for i in uncovered]
    lines += ["]", ""]
    lines.append("METHOD_BY_ID = {i: i.replace('.', '_') for i in GENERATED_COMMANDS}")
    lines.append("")
    return "\n".join(lines)


def gen_init() -> str:
    return (
        HEADER
        + "\nfrom . import catalog, models\n"
        + "from .commands import Commands\n\n"
        + '__all__ = ["Commands", "models", "catalog"]\n'
    )


def main() -> None:
    index = json.loads((IDL / "command-index.json").read_text())
    all_ids = [c["id"] for c in index["commands"]]
    commands = load_commands()
    defs, model_names, bytes_names, enum_names, object_names = classify(commands)
    # Inside models.py, model refs are bare names; inside commands.py they are
    # qualified `models.Name`.
    models_emitter = Emitter(defs, model_names, bytes_names, enum_names, prefix="")
    cmds_emitter = Emitter(defs, model_names, bytes_names, enum_names, prefix="models.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "models.py").write_text(
        gen_models(defs, model_names, bytes_names, enum_names, object_names, models_emitter)
    )
    (OUT / "commands.py").write_text(gen_commands(commands, cmds_emitter))
    (OUT / "catalog.py").write_text(gen_catalog(commands, all_ids))
    (OUT / "__init__.py").write_text(gen_init())

    print(
        f"generated {len(commands)} commands, {len(model_names)} models "
        f"({len(enum_names & model_names)} enums, {len(object_names & model_names)} objects), "
        f"{len(all_ids) - len(commands)} uncovered"
    )


if __name__ == "__main__":
    main()
