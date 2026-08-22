"""Implementation of repo scaffolding (``stratadb.init()`` / ``python -m stratadb.init``).

Plants the breadcrumbs a coding agent discovers a library through — the files in
the repo it's working in — so the *next* agent knows Strata before its first tool
call, instead of web-searching and probing (#21):

- ``.claude/skills/strata-python/SKILL.md`` — the ``strata-python`` agent skill
  (vendored from strata-agent-skills; ``npx skills add stratalab/strata-agent-skills``
  installs the rest of the set).
- an ``AGENTS.md`` stanza — the cross-tool convention (Cursor, Copilot, Codex, …).
- optionally a ``CLAUDE.md`` pointer stanza.

Idempotent: stanzas are delimited by HTML-comment markers so re-running refreshes
them in place rather than duplicating. The runnable ``python -m stratadb.init``
entry point is the thin :mod:`stratadb.init` shim; this private module holds the
logic so ``stratadb.init`` stays a callable.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

# Actions reported per file.
CREATED = "created"
UPDATED = "updated"
UNCHANGED = "unchanged"
REMOVED = "removed"

_BEGIN = "<!-- strata:begin (managed by stratadb.init — edits inside are overwritten) -->"
_END = "<!-- strata:end -->"


def _agents_stanza() -> str:
    return f"""{_BEGIN}
## Strata (`stratadb`)

This repo uses [Strata](https://stratadb.org) via the `stratadb` Python SDK — an
**embedded** multi-model database (key-value, JSON, vectors, an event log, and a
graph) over one branch-aware, time-travelling store.

- **Start here:** call `stratadb.agents_guide()` for the complete offline Python
  usage guide — every namespace, runnable snippets, and error codes.
- **Open:** `import stratadb; db = stratadb.open("./app-data")` (durable) or
  `stratadb.open(cache=True)` (ephemeral, in-memory).
- **Tour it:** `python -m stratadb.demo` prints every primitive's real output.
- **Skills:** `.claude/skills/strata-python/SKILL.md` (installed by this scaffold);
  `npx skills add stratalab/strata-agent-skills` adds `strata`, `strata-branching`,
  and `strata-time-travel`.
- **MCP:** `strata ./app-data mcp serve` (config via `stratadb.mcp_config(path)`;
  the `strata` binary is a separate strata-core install).
{_END}"""


def _claude_stanza() -> str:
    return f"""{_BEGIN}
## Strata

This repo uses the `stratadb` Python SDK. For the full API, call
`stratadb.agents_guide()` (or read `.claude/skills/strata-python/SKILL.md`). Tour the
surface with `python -m stratadb.demo`.
{_END}"""


def _write_file(path: Path, content: str) -> str:
    """Create or overwrite ``path`` with ``content``; report the action taken."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return UNCHANGED
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return UPDATED if existed else CREATED


def _upsert_stanza(path: Path, stanza: str) -> str:
    """Insert or refresh a marker-delimited stanza in ``path`` (idempotent)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(stanza + "\n", encoding="utf-8")
        return CREATED

    text = path.read_text(encoding="utf-8")
    if _BEGIN in text and _END in text:
        head, _, rest = text.partition(_BEGIN)
        _, _, tail = rest.partition(_END)
        updated = head + stanza + tail
        if updated == text:
            return UNCHANGED
        path.write_text(updated, encoding="utf-8")
        return UPDATED

    # Present but unmanaged: append our stanza, leaving existing content intact.
    separator = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + separator + stanza + "\n", encoding="utf-8")
    return UPDATED


def _is_legacy_sdk_skill(text: str) -> bool:
    """The pre-1.0.4 SDK/CLI skill: named ``strata``, version-stamped, no provenance.

    The canonical ``strata`` skill from strata-agent-skills carries a pinned
    ``strata-core-rev`` in its frontmatter; ours never did.
    """
    return (
        text.startswith("---\nname: strata\n")
        and "strata-core-rev" not in text
        and "This skill matches strata" in text
    )


def init(repo_path: str = ".", *, include_claude_md: bool = True) -> List[Tuple[str, str]]:
    """Scaffold Strata's agent breadcrumbs into ``repo_path`` (idempotent).

    Writes ``.claude/skills/strata-python/SKILL.md`` (the ``strata-python`` skill)
    and an ``AGENTS.md`` stanza, and — unless ``include_claude_md=False`` — a
    ``CLAUDE.md`` pointer stanza. Stanzas are marker-delimited, so re-running
    refreshes them in place instead of duplicating. A ``strata`` skill written by
    a pre-1.0.4 SDK or CLI is retired (that path belongs to the canonical
    strata-agent-skills ``strata`` skill, which is left untouched).

    Returns a list of ``(relative_path, action)`` where ``action`` is ``"created"``,
    ``"updated"``, ``"unchanged"``, or ``"removed"`` — safe to call repeatedly.
    """
    import stratadb

    root = Path(repo_path)
    results: List[Tuple[str, str]] = []

    skill_path = root / ".claude" / "skills" / "strata-python" / "SKILL.md"
    results.append((str(skill_path.relative_to(root)), _write_file(skill_path, stratadb.agents_skill())))

    # Earlier releases wrote a Python-first skill named `strata` to the path the
    # canonical strata-agent-skills `strata` skill now owns (strata-core #2893).
    # Retire only our own copy so the two never fight.
    legacy = root / ".claude" / "skills" / "strata" / "SKILL.md"
    if legacy.exists() and _is_legacy_sdk_skill(legacy.read_text(encoding="utf-8")):
        legacy.unlink()
        try:
            legacy.parent.rmdir()  # only when nothing else lives there
        except OSError:
            pass
        results.append((str(legacy.relative_to(root)), REMOVED))

    agents_path = root / "AGENTS.md"
    results.append(("AGENTS.md", _upsert_stanza(agents_path, _agents_stanza())))

    if include_claude_md:
        claude_path = root / "CLAUDE.md"
        results.append(("CLAUDE.md", _upsert_stanza(claude_path, _claude_stanza())))

    return results
