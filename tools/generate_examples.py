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
executes them against a fresh ``stratadb.open(cache=True)`` — that is where the exact
value (``b'hello'``) is asserted.
"""

from __future__ import annotations

import ast
import json
import sys
from collections import namedtuple
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "idl" / "v1" / "examples"
NS_DIR = ROOT / "python" / "stratadb" / "namespaces"

# command id -> the curated method whose docstring shows it. `expr` is the
# demonstrated result expression (``{}`` = the call); the default ``{}`` shows
# the call's own value. `result_type` overrides how the expected value is
# rendered (defaults to the method's return annotation) — needed when a result
# accessor changes the type (a Page's ``.items`` are bytes, a Sample's
# ``.total_count`` is an int). Every command a bound spec's steps call must
# itself be bound (so the call form is known).
# `arg_map` remaps wire argument names to curated method parameter names when
# they differ (e.g. vector.query's wire `query` -> the `vector` param; the
# collection-management commands' wire `collection` -> the `name` param). A
# dotted key reaches into a nested wire struct (e.g. `target.primitive` ->
# `primitive`) when the SDK flattens it into separate parameters.
Binding = namedtuple(
    "Binding", ["ns", "method", "expr", "result_type", "arg_map"], defaults=("{}", None, None)
)

BINDINGS = {
    "kv.put": Binding("kv", "put"),
    "kv.get": Binding("kv", "get"),
    "kv.exists": Binding("kv", "exists"),
    "kv.delete": Binding("kv", "delete"),
    "kv.count": Binding("kv", "count"),
    "kv.batch_put": Binding("kv", "put_many"),
    "kv.batch_get": Binding("kv", "get_many"),
    "kv.batch_exists": Binding("kv", "exists_many"),
    "kv.batch_delete": Binding("kv", "delete_many"),
    "kv.history": Binding("kv", "history"),
    "kv.list": Binding("kv", "keys", "{}.items", "list[bytes]"),
    "kv.scan": Binding("kv", "scan", "[row.key for row in {}]", "list[bytes]"),
    "kv.sample": Binding("kv", "sample", "{}.total_count", "int"),
    # json — documents are inline JSON (result_type "json" renders dict/list
    # reprs with sorted keys). json.scan and json.batch_exists have no curated
    # method, so they get reference-doc coverage in strata-core but no binding.
    "json.set": Binding("json", "set"),
    "json.get": Binding("json", "get", "{}", "json"),
    "json.exists": Binding("json", "exists"),
    "json.delete": Binding("json", "delete"),
    "json.count": Binding("json", "count"),
    "json.history": Binding("json", "history"),
    "json.batch_set": Binding("json", "set_many"),
    "json.batch_get": Binding("json", "get_many", "{}", "json"),
    "json.batch_delete": Binding("json", "delete_many"),
    "json.list": Binding("json", "keys", "{}.items", "json"),
    "json.sample": Binding("json", "sample", "{}.total_count", "int"),
    "json.index.create": Binding("json", "create_index"),
    "json.index.drop": Binding("json", "drop_index"),
    "json.index.list": Binding("json", "list_indexes", "[i.name for i in {}]", "json"),
    # vectors — collection-scoped; embeddings are float lists. Deferred (batch
    # results, filters, index diagnostics, sample/scan) stay allowlisted.
    "vector.collection.create": Binding("vectors", "create_collection", arg_map={"collection": "name"}),
    "vector.collection.delete": Binding("vectors", "delete_collection", arg_map={"collection": "name"}),
    "vector.collection.list": Binding("vectors", "list_collections", "[c.name for c in {}]", "json"),
    "vector.collection.stats": Binding("vectors", "stats", "{}.dimension", "int", {"collection": "name"}),
    "vector.count": Binding("vectors", "count", "{}", "int", {"collection": "name"}),
    "vector.upsert": Binding("vectors", "upsert"),
    "vector.get": Binding("vectors", "get", "{}.key", "json"),
    "vector.exists": Binding("vectors", "exists"),
    "vector.delete": Binding("vectors", "delete"),
    "vector.delete_all": Binding("vectors", "delete_all"),
    "vector.history": Binding("vectors", "history"),
    "vector.keys": Binding("vectors", "keys", "{}.items", "json"),
    "vector.query": Binding("vectors", "query", "[m.key for m in {}]", "json", {"query": "vector"}),
    "vector.batch_upsert": Binding("vectors", "upsert_many"),
    "vector.batch_get": Binding("vectors", "get_many", "[i.result.value.key for i in {}.items]", "json"),
    "vector.batch_delete": Binding("vectors", "delete_many"),
    "vector.index.query": Binding("vectors", "index_query", "[m.key for m in {}[0]]", "json", {"query": "vector"}),
    "vector.metadata.update": Binding("vectors", "update_metadata", arg_map={"patch": "metadata"}),
    "vector.delete_by_filter": Binding("vectors", "delete_by_filter"),
    # vector.sample / vector.scan / vector.batch_exists have no curated method:
    # reference-doc coverage in strata-core, no SDK docstring.
    # events — sequence-numbered append-only log; payloads read back via
    # `.event.payload`. `direction` (wire) is absorbed into the method's
    # `reverse` default, so it is left unmapped and dropped from the render.
    "event.append": Binding("events", "append"),
    "event.get": Binding("events", "get", "{}.event.payload", "json"),
    "event.exists": Binding("events", "exists"),
    "event.count": Binding("events", "len"),
    "event.list": Binding("events", "list", "[e.event.payload for e in {}]", "json"),
    "event.range": Binding("events", "range", "[e.event.payload for e in {}]", "json", {"start_seq": "start"}),
    "event.range_time": Binding("events", "range_by_time", "[e.event.payload for e in {}]", "json"),
    "event.types": Binding("events", "types", "{}", "json"),
    "event.verify_chain": Binding("events", "verify_chain", "{}.valid", "json"),
    "event.batch_append": Binding("events", "append_many"),
    # graph core (management + node/edge CRUD + traversal). Analytics and
    # ontology commands have no curated SDK method yet — allowlisted.
    "graph.create": Binding("graphs", "create", arg_map={"graph": "name"}),
    "graph.delete": Binding("graphs", "delete", arg_map={"graph": "name"}),
    "graph.list": Binding("graphs", "list", "{}", "json"),
    "graph.meta": Binding("graphs", "meta", "{}.node_count", "int", {"graph": "name"}),
    "graph.node.add": Binding("graphs", "add_node"),
    "graph.node.get": Binding("graphs", "get_node", "{}.properties", "json"),
    "graph.node.remove": Binding("graphs", "remove_node"),
    "graph.node.list": Binding("graphs", "list_nodes", "[n.node_id for n in {}]", "json"),
    "graph.edge.add": Binding("graphs", "add_edge"),
    "graph.edge.get": Binding("graphs", "get_edge", "{}.edge_type", "json"),
    "graph.edge.remove": Binding("graphs", "remove_edge"),
    "graph.neighbors": Binding("graphs", "neighbors", "[n.node_id for n in {}]", "json"),
    # graph analytics (sub-namespace). Scores/labels are floats — demonstrate
    # the (deterministic) node-id set instead.
    "graph.analytics.pagerank": Binding("graphs", "analytics.pagerank", "sorted({}.ranks)", "json"),
    "graph.analytics.bfs": Binding("graphs", "analytics.bfs", "{}.visited", "json"),
    "graph.analytics.sssp": Binding("graphs", "analytics.sssp", "sorted({}.distances)", "json"),
    "graph.analytics.wcc": Binding("graphs", "analytics.wcc", "{}.component_count", "int"),
    "graph.analytics.cdlp": Binding("graphs", "analytics.cdlp", "sorted({}.labels)", "json"),
    "graph.analytics.lcc": Binding("graphs", "analytics.lcc", "sorted({}.coefficients)", "json"),
    # graph ontology (sub-namespace).
    "graph.ontology.define_object_type": Binding("graphs", "ontology.define_object_type"),
    "graph.ontology.define_link_type": Binding("graphs", "ontology.define_link_type"),
    "graph.ontology.delete_object_type": Binding("graphs", "ontology.delete_object_type"),
    "graph.ontology.delete_link_type": Binding("graphs", "ontology.delete_link_type"),
    "graph.ontology.freeze": Binding("graphs", "ontology.freeze"),
    "graph.ontology.get": Binding("graphs", "ontology.get", "{}.status", "json"),
    "graph.ontology.summary": Binding("graphs", "ontology.summary", "[o.name for o in {}.object_types]", "json"),
    # graph entity bindings — a node bound to a product entity, listed and
    # governed by delete policy. The wire nests the identity under `target`;
    # the SDK flattens it to primitive/key (space defaults to the scope).
    "graph.batch_write": Binding("graphs", "batch_write"),
    "graph.bindings": Binding(
        "graphs", "bindings_for_entity", "[h.node_id for h in {}]", "json",
        {"target.primitive": "primitive", "target.key": "key"},
    ),
    "graph.apply_delete_policy": Binding(
        "graphs", "apply_delete_policy",
        arg_map={"target.primitive": "primitive", "target.key": "key"},
    ),
    # graph bulk / typed listing / sample.
    "graph.bulk_insert": Binding("graphs", "bulk_insert"),
    "graph.nodes_by_type": Binding("graphs", "nodes_by_type", "[n.node_id for n in {}]", "json"),
    "graph.sample": Binding("graphs", "sample", "{}.total_count", "int"),
    # branch — wire operand `branch` maps to the method's `name` param.
    "branch.create": Binding("branches", "create", arg_map={"branch": "name"}),
    "branch.list": Binding("branches", "list", "sorted(b.name for b in {})", "json"),
    "branch.get": Binding("branches", "get", "{}.name", "json", {"branch": "name"}),
    "branch.fork": Binding("branches", "fork", arg_map={"branch": "name"}),
    "branch.fork_at_version": Binding("branches", "fork_at_version", arg_map={"branch": "name"}),
    "branch.fork_at_timestamp": Binding("branches", "fork_at_timestamp", arg_map={"branch": "name"}),
    "branch.delete": Binding("branches", "delete", arg_map={"branch": "name"}),
    # space — wire operand `space` maps to the method's `name` param.
    "space.create": Binding("spaces", "create", arg_map={"space": "name"}),
    "space.list": Binding("spaces", "list", "sorted({})", "json"),
    "space.exists": Binding("spaces", "exists", arg_map={"space": "name"}),
    "space.delete": Binding("spaces", "delete", arg_map={"space": "name"}),
    # admin — facts are non-deterministic; demonstrate a stable derived value.
    # admin.remote/hub_clone stay reference-only (no clean SDK assertion).
    "admin.ping": Binding("admin", "ping", "{}.version == stratadb.__version__", "json"),
    "admin.info": Binding("admin", "info", "{}.branch_count", "int"),
    "admin.health": Binding("admin", "health", "{}.status.value", "json"),
    "admin.metrics": Binding("admin", "metrics", "{}.branch_count", "int"),
    "admin.describe": Binding("admin", "describe", "{}.default_branch", "json"),
    "admin.config": Binding("admin", "config", "{}.default_branch", "json"),
    "admin.config_key": Binding("admin", "config_value"),
    # inference metadata (db.ai) — no model, no network, no local runtime, no
    # keys. The model-dependent verbs (generate/embed/rank/tokenize) and the
    # network/machine-state ones (models.pull/local) stay allowlisted.
    # Note: exprs go through str.format, so use set(...) not a `{...}` literal.
    "inference.capability": Binding("ai", "capability", '{}["provider"]', "json"),
    "inference.cache_status": Binding("ai", "cache_status", '{}["generation_models"]', "json"),
    "inference.models.list": Binding(
        "ai", "models.list", 'sorted(set(m["task"] for m in {}["items"]))', "json"
    ),
    "inference.unload": Binding("ai", "unload", '{}["unloaded"]', "json"),
    # arrow — file round-trip; the `{tmpdir}/<file>` path renders as a tmp_dir
    # expression (see render_arg). Wire `file_path` maps to the method's `path`.
    "arrow.export": Binding("arrow", "export"),
    "arrow.import": Binding("arrow", "import_", arg_map={"file_path": "path"}),
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
        if isinstance(node, ast.FunctionDef) and node.name not in methods:
            # First definition wins: the primary namespace class is defined
            # before its bound-view helpers (e.g. ai.py's AiModel re-declares
            # capability/chat/embed without the `model` param), so a later
            # shadow must not overwrite the real namespace method's signature.
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


def method_leaf(method: str) -> str:
    # A binding method may be a sub-namespace path ("analytics.pagerank"); the
    # AST-derived signature is keyed by the final method name.
    return method.rsplit(".", 1)[-1]


def render_call(step: dict, methods: dict) -> str:
    binding = BINDINGS[step["call"]]
    sig = methods[binding.ns][method_leaf(binding.method)]
    amap = binding.arg_map or {}
    raw = step.get("args") or {}
    # An `arg_map` key may be a dotted path into a nested wire argument (e.g.
    # `target.primitive`), letting a curated method flatten a wire struct that
    # the SDK exposes as separate parameters. A consumed root is not passed on.
    dotted = {src: dst for src, dst in amap.items() if "." in src}
    consumed = {src.split(".")[0] for src in dotted}
    args = {amap.get(name, name): value for name, value in raw.items() if name not in consumed}
    for src, dst in dotted.items():
        node = raw
        for part in src.split("."):
            node = node[part]
        args[dst] = node
    # `branch`/`space` args that are not method parameters are session scope,
    # applied via db.at(...), not passed to the call.
    params = set(sig["pos"]) | set(sig["kwonly"])
    scope = {k: args.pop(k) for k in ("branch", "space") if k in args and k not in params}
    handle = "db"
    if scope:
        handle = "db.at(" + ", ".join(f"{k}={py_lit(v)}" for k, v in scope.items()) + ")"
    parts = [render_arg(p, args[p]) for p in sig["pos"] if p in args]
    parts += [f"{k}={render_arg(k, args[k])}" for k in sig["kwonly"] if k in args]
    return f"{handle}.{binding.ns}.{binding.method}({', '.join(parts)})"


def render_arg(param: str, value) -> str:
    # A `filter` param carries the AND-of-conditions wire shape; render it back
    # as the curated `stratadb.filters` builder that users actually write.
    if param == "filter" and isinstance(value, dict) and "conditions" in value:
        return render_filter(value)
    # A `{tmpdir}/<file>` path placeholder renders as an expression scoped to the
    # doctest's injected `tmp_dir` (test_doctests.py), so a round-trip export and
    # import share a real, isolated file.
    if isinstance(value, str) and "{tmpdir}" in value:
        rest = value.replace("{tmpdir}", "").lstrip("/")
        return f'tmp_dir + "/{rest}"'
    # A `{bind.path}` reference to a prior step's bound result renders as the
    # Python attribute path (e.g. `{base.commit.version}` -> base.commit.version).
    if isinstance(value, str) and value.startswith("{") and value.endswith("}") and "." in value[1:-1]:
        return value[1:-1]
    return py_lit(value)


def render_filter(wire: dict) -> str:
    parts = []
    for cond in wire["conditions"]:
        raw = cond.get("value")
        literal = raw["value"] if isinstance(raw, dict) and "value" in raw else raw
        parts.append(f"stratadb.filters.{cond['op']}({json.dumps(cond['field'])}, {py_lit(literal)})")
    return " & ".join(parts)


def render_result(value, return_annotation: str) -> str:
    # JSON-document results come back as plain Python objects whose repr uses
    # single quotes and (for dicts) engine-canonical sorted keys.
    if return_annotation == "json":
        return json_repr(value)
    if isinstance(value, list):  # e.g. get_many -> [b'1', b'2', None]
        return "[" + ", ".join(render_scalar(v, return_annotation) for v in value) + "]"
    return render_scalar(value, return_annotation)


def render_scalar(value, return_annotation: str) -> str:
    if value is None:
        return "None"
    if "bytes" in return_annotation and isinstance(value, str):
        return f"b{json.dumps(value)}".replace('"', "'")  # b'hello'
    if isinstance(value, bool):
        return "True" if value else "False"
    return json.dumps(value)


def json_repr(value) -> str:
    """Python repr of a JSON value, with dict keys sorted to match the engine's
    canonical document order (what `db.json.get` returns at runtime)."""
    if isinstance(value, dict):
        body = ", ".join(f"{json_repr(k)}: {json_repr(v)}" for k, v in sorted(value.items()))
        return "{" + body + "}"
    if isinstance(value, list):
        return "[" + ", ".join(json_repr(v) for v in value) + "]"
    return repr(value)


def render_step(step: dict, methods: dict) -> list[str]:
    binding = BINDINGS[step["call"]]
    call = render_call(step, methods)
    note = f"  # {step['note']}" if step.get("note") else ""
    if "returns" not in step:
        # A `bind:` step captures its result in a named variable a later step
        # references (e.g. a receipt whose commit version drives a fork).
        lhs = step.get("bind", "_")
        return [f">>> {lhs} = {call}{note}"]
    value = step["returns"]
    if value is None:  # returns: null -> a miss
        return [f">>> {call} is None", "True"]
    # A step may override the binding's result expression to demonstrate the
    # same command a different way (e.g. read metadata back via get().data...).
    expr = (step.get("expr") or binding.expr).format(call)
    result_type = binding.result_type or methods[binding.ns][method_leaf(binding.method)]["returns"]
    return [f">>> {expr}", render_result(value, result_type)]


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
    for command_id, binding in BINDINGS.items():
        by_file.setdefault(binding.ns, []).append(command_id)

    methods = {ns: namespace_methods(ns) for ns in by_file}
    stale = []
    for ns, command_ids in by_file.items():
        path = NS_DIR / f"{ns}.py"
        source = path.read_text()
        # Map bound method (final segment for sub-namespaces) -> command id.
        method_to_cmd = {method_leaf(BINDINGS[c].method): c for c in command_ids}

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
