#!/usr/bin/env python3
"""Vendor the ``strata-python`` skill from a sibling strata-agent-skills checkout.

The wheel ships that skill as ``stratadb.agents_skill()`` and ``stratadb.init()``
installs it, so a pip-only project gets the canonical skill offline. The skill is
authored in stratalab/strata-agent-skills — the one agent-facing surface
(strata-core #2893) — so this copies it verbatim at the checkout's HEAD and
records the rev in ``STRATA_AGENT_SKILLS_REV``.

  python tools/vendor_skill.py                   # copy + pin from ../strata-agent-skills
  python tools/vendor_skill.py --check           # fail if the bundled copy differs
  python tools/vendor_skill.py --source <dir>    # another checkout
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "python" / "stratadb" / "_data" / "skill.md"
PIN = ROOT / "STRATA_AGENT_SKILLS_REV"
SKILL_REL = Path("skills") / "strata-python" / "SKILL.md"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    source = ROOT.parent / "strata-agent-skills"
    if "--source" in argv:
        source = Path(argv[argv.index("--source") + 1])
    skill = source / SKILL_REL
    if not skill.exists():
        print(
            f"error: {skill} not found (pass --source <strata-agent-skills checkout>)",
            file=sys.stderr,
        )
        return 2
    git = ["git", "-C", str(source)]
    rev = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(
        [*git, "status", "--porcelain", "--", str(SKILL_REL)], text=True
    ).strip()
    if dirty:
        print(
            f"warning: {SKILL_REL} is modified in {source}; the pin names HEAD, not those edits",
            file=sys.stderr,
        )
    content = skill.read_text(encoding="utf-8")

    if check:
        stale = []
        if not BUNDLED.exists() or BUNDLED.read_text(encoding="utf-8") != content:
            stale.append(str(BUNDLED.relative_to(ROOT)))
        if not PIN.exists() or PIN.read_text(encoding="utf-8").strip() != rev:
            stale.append(str(PIN.relative_to(ROOT)))
        if stale:
            print(
                f"stale against strata-agent-skills @ {rev[:8]}: {', '.join(stale)} "
                "(run tools/vendor_skill.py)",
                file=sys.stderr,
            )
            return 1
        print(f"skill is fresh at strata-agent-skills {rev[:8]}")
        return 0

    BUNDLED.write_text(content, encoding="utf-8")
    PIN.write_text(rev + "\n", encoding="utf-8")
    print(f"vendored {SKILL_REL} from strata-agent-skills {rev[:8]} -> {BUNDLED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
