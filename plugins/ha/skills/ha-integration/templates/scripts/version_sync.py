#!/usr/bin/env python3
"""Check that every copy of the Python version agrees.

The Python version an integration targets is written in several places, each read by a
different tool: every workflow that sets up Python, ruff, pyright, and (indirectly) the
pinned `pytest-homeassistant-custom-component`, which hard-pins the Home Assistant release
the suite runs against. Nothing compared them, so a bump in one place left the others
behind and CI stayed green while linting a version nobody runs; later, one workflow lagging
a bump ran the shipped scripts on an interpreter that rejected their syntax.

`requirements.test.txt` is the source: it names the HA release. Everything else derives
from it, and every declaration is compared with every other.
"""

import argparse
import json
import pathlib
import re
import sys

PHCC = re.compile(
    r"^\s*pytest-homeassistant-custom-component\s*==\s*(?P<version>\S+)", re.MULTILINE
)
RUFF_TARGET = re.compile(r'target-version\s*=\s*"py(?P<major>\d)(?P<minor>\d+)"')
PY_VERSION = re.compile(r'python-version:\s*["\']?(?P<version>\d+\.\d+)')


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def collect(root: pathlib.Path) -> dict[str, str | None]:
    """Every declared Python version, keyed by the file that declares it."""
    found: dict[str, str | None] = {}

    # Every workflow that sets up Python, not just the one that runs pytest: the ones
    # running scripts/ declare the version too, and one lagging a bump ran the scripts
    # on an interpreter that rejected their syntax while this said the versions agreed.
    found["python_validate.yml"] = None
    workflows = root / ".github/workflows"
    for wf in sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []:
        m = PY_VERSION.search(_read(wf))
        if m:
            found[wf.name] = m.group("version")

    pyproject = _read(root / "pyproject.toml")
    m = RUFF_TARGET.search(pyproject)
    found["pyproject.toml ruff target-version"] = (
        f"{m.group('major')}.{m.group('minor')}" if m else None
    )

    pyright = _read(root / "pyrightconfig.json")
    if pyright:
        try:
            found["pyrightconfig.json"] = json.loads(pyright).get("pythonVersion")
        except json.JSONDecodeError:
            found["pyrightconfig.json"] = None
    else:
        found["pyrightconfig.json"] = None

    return found


def problems(root: pathlib.Path) -> list[str]:
    """Disagreements between the declared versions; empty means they line up."""
    found = collect(root)
    declared = {k: v for k, v in found.items() if v is not None}
    out: list[str] = []

    distinct = set(declared.values())
    if len(distinct) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(declared.items()))
        out.append(f"python version disagrees across {len(declared)} files: {detail}")

    # The pin is what fixes the HA release under test; without it the suite silently
    # follows whatever HA published today.
    reqs = _read(root / "requirements.test.txt")
    if reqs and not PHCC.search(reqs):
        out.append(
            "requirements.test.txt does not pin pytest-homeassistant-custom-component "
            "(the suite would test against whichever HA release is current)"
        )
    return out


def thin(root: pathlib.Path) -> list[str]:
    """Warnings: the check ran but had little or nothing to compare.

    A single declaration cannot disagree with anything, so printing "versions agree" is a
    green tick for work not done. An integration is expected to declare it in every
    workflow that sets up Python, in ruff and in pyright; a repo that only runs pytest
    legitimately declares one, so this warns rather than fails.
    """
    found = collect(root)
    missing = [k for k, v in found.items() if v is None]
    declared = {k: v for k, v in found.items() if v is not None}
    if len(declared) < 2:
        return [
            (
                f"only {len(declared)} python version declared; nothing to compare "
                f"(absent: {', '.join(missing)})"
            )
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    """Report disagreements and thin coverage; exit 1 on a disagreement."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root to inspect")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    found = problems(root)
    for w in thin(root):
        print(f"⚠️  WARN: {w}")
    for p in found:
        print(f"❌ FAIL: {p}")
    if not found:
        print("✅ declared python versions agree")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
