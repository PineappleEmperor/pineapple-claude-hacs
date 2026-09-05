#!/usr/bin/env python3
"""Authoring audit for the skills in THIS repository.

`skill_audit.py` answers "was the ha-integration skill followed in this integration"
and ships to every scaffolded repo. These checks answer "are the skills in this
repository well built" — frontmatter the spec requires, a router whose links resolve,
docs that describe workflows the templates actually ship, prose a reader can act on.
None of it can fire in a consuming repo, which has no `plugins/*/skills/`, so shipping
it there would be dead weight in a file people are asked to read.

Exit 1 on any FAIL. Runs locally and in `quality_audit.yml`.
"""

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import tempfile

import yaml

Result = tuple[list[str], list[str]]


class Repo:
    """Just enough of skill_audit's Repo for these checks."""

    def __init__(self, root: pathlib.Path) -> None:
        """Remember the repository root; every check globs from it."""
        self.root = root


def _template_dir(repo: Repo) -> pathlib.Path | None:
    found = sorted(repo.root.glob("plugins/*/skills/*/templates"))
    return found[0] if found else None


# A workflow or job named in the docs but absent from templates/. The
# `commit-summary` job was deleted from pr-checks.yml, and six passages went on
# describing it as the thing that writes the PR body — including the table a
# reader consults first. Documenting a job the scaffold does not ship is worse than
# documenting nothing: it gets followed.
DOCS_EXCUSED = re.compile(
    r"supersede|do not reinstate|removed|deleted|replaced by|historical", re.IGNORECASE
)
# Described on purpose without being shipped: the floor-bumper is an opt-in add-on
# the reader builds when a manifest carries `>=` requirements, so the skill explains
# it rather than scaffolding it into every repo.
DOCS_OPTIONAL = {"update_manifest_floors.yml"}


def check_docs_match_templates(repo: Repo) -> Result:
    """Every workflow and job the skill's docs name must exist in templates/."""
    tmpl = _template_dir(repo)
    if not tmpl or not (tmpl / ".github/workflows").is_dir():
        return [], []
    shipped = {p.name for p in (tmpl / ".github").rglob("*.yml")}
    jobs: set[str] = set()
    for wf in (tmpl / ".github/workflows").glob("*.yml"):
        try:
            data = yaml.safe_load(wf.read_text()) or {}
        except OSError, yaml.YAMLError:
            continue
        jobs |= set((data.get("jobs") or {}).keys())

    fails = []
    for doc in sorted((tmpl.parent).glob("SKILL.md")) + sorted(
        (tmpl.parent / "reference").glob("*.md")
    ):
        section = ""
        for n, line in enumerate(doc.read_text().splitlines(), 1):
            if line.startswith("#"):
                section = line
            # An excuse applies to its whole section, not just the line carrying the word.
            # Giving wall-of-text paragraphs real headings moved "Superseded — do not
            # reinstate" into a heading, and a line-only check then flagged the section it
            # was excusing.
            if DOCS_EXCUSED.search(line) or DOCS_EXCUSED.search(section):
                continue
            fails += [
                f"{doc.name}:{n} names a workflow that is not shipped: {name}"
                for name in re.findall(r"`([a-z0-9_.-]+\.yml)`", line)
                if name not in shipped and name not in DOCS_OPTIONAL
            ]
            # The job table in the workflow reference, identified by its `needs:`
            # column so that a settings table elsewhere is not read as job names.
            if (
                doc.name == "github-actions.md"
                and (
                    m := re.match(
                        r"\|\s*`([a-z0-9-]+)`\s*\|\s*(?:—|`[a-z0-9-]+`)\s*\|", line
                    )
                )
                and m.group(1) not in jobs
            ):
                fails.append(
                    f"{doc.name}:{n} documents a job that no workflow defines: {m.group(1)}"
                )
    return fails, []


def check_skill_frontmatter(repo: Repo) -> Result:
    """Each SKILL.md must carry the frontmatter the skill spec requires.

    `name` and `description` are the two required fields, the block is capped at 1024
    characters, and the description states WHEN to reach for the skill. ha-panel-design
    shipped seven releases with no `name` at all, and a description that summarised what
    the skill does — which is the documented way to get an agent to act on the summary
    instead of reading the skill.
    """
    fails, warns = [], []
    for skill in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
        text = skill.read_text()
        parts = text.split("---", 2)
        if len(parts) < 3 or parts[0].strip():
            fails.append(f"{skill.parent.name}/SKILL.md has no frontmatter block")
            continue
        fm = parts[1]
        fields = dict(re.findall(r"^([a-z-]+):\s*(.*)$", fm, re.MULTILINE))
        if "name" not in fields:
            fails.append(f"{skill.parent.name}/SKILL.md frontmatter has no name field")
        elif fields["name"].strip() != skill.parent.name:
            fails.append(
                f"{skill.parent.name}/SKILL.md name field is {fields['name'].strip()!r}"
            )
        if "description" not in fields:
            fails.append(
                f"{skill.parent.name}/SKILL.md frontmatter has no description field"
            )
        elif not fields["description"].lstrip().startswith("Use when"):
            fails.append(
                f"{skill.parent.name}/SKILL.md description must start with 'Use when' "
                "and state triggers, not what the skill does"
            )
        if len(fm) > 1024:
            fails.append(
                f"{skill.parent.name}/SKILL.md frontmatter is {len(fm)} chars (max 1024)"
            )
        # Token budget: a skill loads in full once triggered. Past a few thousand words the
        # heavy sections belong in reference/ files, loaded only when the mode needs them.
        words = len(parts[2].split())
        if words > 5000:
            warns.append(
                f"{skill.parent.name}/SKILL.md is {words} words — move heavy sections "
                "to reference/ files and leave pointers"
            )
    return fails, warns


def check_reference_links(repo: Repo) -> Result:
    """A SKILL.md that routes to reference files must link every one, and only real ones.

    Splitting a skill into on-demand files trades one big document for a router. The
    router rots in two directions: a link to a file that was renamed sends the agent
    nowhere, and a reference file nothing links to is never read again.
    """
    fails = []
    for skill in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
        ref_dir = skill.parent / "reference"
        text = skill.read_text()
        linked = set(re.findall(r"\]\((reference/[A-Za-z0-9._-]+\.md)\)", text))
        linked |= set(re.findall(r"`(reference/[A-Za-z0-9._-]+\.md)`", text))
        fails += [
            f"{skill.parent.name}/SKILL.md links {target}, which does not exist"
            for target in sorted(linked)
            if not (skill.parent / target).is_file()
        ]
        if ref_dir.is_dir():
            fails += [
                f"{skill.parent.name}/reference/{f.name} is linked from nothing"
                for f in sorted(ref_dir.glob("*.md"))
                if f"reference/{f.name}" not in linked
            ]
    return fails, []


def check_named_sections(repo: Repo) -> Result:
    """A pointer to a *section* by name is invisible to a link check.

    Three of this skill's worst defects were cross-references of the form
    "*Merge discipline* in `SKILL.md`" pointing at a heading that had moved. The link
    check passed throughout, because the file existed — only the section did not.
    """
    fails = []
    ref = re.compile(
        r"\*([A-Z][^*\n]{3,60}?)\* in [`\[]+(?:reference/)?([A-Za-z0-9._-]+\.md)"
    )
    for manifest in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
        skill = manifest.parent
        for doc in sorted(skill.rglob("*.md")):
            if "evals" in doc.parts or "templates" in doc.parts:
                continue
            for section, target in ref.findall(doc.read_text()):
                path = (
                    skill / "reference" / target if target != "SKILL.md" else manifest
                )
                if not path.is_file():
                    fails.append(f"{doc.name} points at {target}, which does not exist")
                    continue
                headings = [
                    line.lstrip("# ").strip().lower()
                    for line in path.read_text().splitlines()
                    if line.startswith("#")
                ]
                if not any(section.strip().lower() in h for h in headings):
                    fails.append(
                        f"{doc.name} points at '{section}' in {target}, "
                        "which has no such heading"
                    )
    return fails, []


def check_required_contexts_documented(repo: Repo) -> Result:
    """The prose list of required checks and `ruleset.json` must agree, both ways.

    The docs named a context the ruleset omits (`Version validation`) and omitted one it
    requires (`Dependency review`), while a nearby sentence claimed a different count.
    A reader reconciling them adds a check that can never report.
    """
    tmpl = _template_dir(repo)
    if not tmpl or not (tmpl / "ruleset.json").is_file():
        return [], []
    data = json.loads((tmpl / "ruleset.json").read_text())
    contexts = [
        c["context"]
        for r in data.get("rules", [])
        if r.get("type") == "required_status_checks"
        for c in r["parameters"]["required_status_checks"]
    ]
    prose = "".join(
        p.read_text() for p in sorted((tmpl.parent / "reference").glob("*.md"))
    )
    fails = [
        f"required context {c!r} is in ruleset.json but named in no reference file"
        for c in contexts
        if f"`{c}`" not in prose
    ]
    for count in re.findall(r"the (\w+) job-name contexts", prose):
        words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        n = words.get(count.lower(), None if not count.isdigit() else int(count))
        if n is not None and n != len(contexts):
            fails.append(
                f"the docs claim {count} required contexts; ruleset.json has {len(contexts)}"
            )
    return fails, []


def check_shipped_workflows_documented(repo: Repo) -> Result:
    """Every workflow the scaffold ships must be described somewhere a reader will look.

    The workflow reference claimed to enumerate the templates and named six of twelve —
    so half the shipped stack had no documented contract to review against.
    """
    tmpl = _template_dir(repo)
    if not tmpl or not (tmpl / ".github/workflows").is_dir():
        return [], []
    prose = "".join(
        p.read_text() for p in sorted((tmpl.parent / "reference").glob("*.md"))
    )
    missing = [
        w.name
        for w in sorted((tmpl / ".github/workflows").glob("*.yml"))
        if w.name not in prose
    ]
    return [
        f"shipped workflow {m} is documented nowhere in reference/" for m in missing
    ], []


def check_document_integrity(repo: Repo) -> Result:
    """Catch the damage a careless bulk edit leaves behind.

    Five transforms during one session cut sentences in half, orphaned index entries and
    once emptied every section of a file while leaving its index intact — 663 words to 212,
    with four other files pointing at it. Reading the result catches this; so does asking
    the document whether it is still internally consistent.

    Not a word-count threshold: a legitimate consolidation loses words and a gutting can
    stay under any percentage. These are the shapes the damage actually takes.
    """
    fails = []
    for manifest in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
        for doc in sorted(manifest.parent.rglob("*.md")):
            if "evals" in doc.parts or "templates" in doc.parts:
                continue
            rel = doc.relative_to(manifest.parent.parent)
            lines = doc.read_text().splitlines()
            # An emptied file has no structure left to judge, so every check below it
            # finds nothing and the audit passes a gutted document. Partial gutting was
            # caught; total gutting was the boundary case that slipped. No legitimate
            # consolidation ends at zero bytes — delete the file, or keep its content.
            if not any(line.strip() for line in lines):
                fails.append(f"{rel}: file is empty — delete it or restore its content")
                continue
            heads = [
                line.lstrip("# ").strip()
                for line in lines
                if re.match(r"^#{2,3} ", line)
            ]
            # The index is the bullet run BEFORE the first heading. Bullets after one are
            # content, and treating them as index entries flags every checklist in the set.
            first_head = next(
                (i for i, line in enumerate(lines) if re.match(r"^#{2,3} ", line)),
                len(lines),
            )
            index = [
                line.lstrip("- ").strip()
                for line in lines[:first_head]
                if line.startswith("- ")
            ]
            fenced = False
            code: set[int] = set()
            for i, line in enumerate(lines):
                if line.lstrip().startswith("```"):
                    fenced = not fenced
                    continue
                if fenced:
                    code.add(i)
                    continue
                # a heading whose section has no body
                if re.match(r"^#{2,3} ", line):
                    nxt = next((rest for rest in lines[i + 1 :] if rest.strip()), "")
                    if nxt.startswith("#") or not nxt:
                        fails.append(
                            f"{rel}:{i + 1} heading {line.strip('# ')!r} has no body"
                        )
                    # A heading is a label, not the first half of a sentence its body
                    # finishes. Both halves then read wrong on their own, and the index
                    # inherits the fragment.
                    elif (
                        line.rstrip().endswith(":")
                        or nxt.lstrip()[:1] in ("—", "(")
                        or (nxt[:1].isalpha() and nxt[:1].islower())
                    ):
                        fails.append(
                            f"{rel}:{i + 1} heading {line.strip('# ')!r} runs on "
                            f"into its body: …{nxt.lstrip()[:40]!r}"
                        )
                # prose cut mid-sentence before a list or heading
                if (
                    line.strip()
                    and not line.startswith(("#", "-", "*", ">", "|", " "))
                    and line.rstrip()[-1:] not in '.:;)`"'
                ):
                    nxt = next((rest for rest in lines[i + 1 :] if rest.strip()), "")
                    if nxt.startswith(("- ", "#")):
                        fails.append(
                            f"{rel}:{i + 1} sentence ends mid-clause: …{line.rstrip()[-40:]!r}"
                        )
            # Only judge a bullet run that IS an index: most of its entries match headings.
            # A run of reference links or definitions matches none, and flagging those buries
            # the real finding — a stale entry left behind when a heading was renamed.
            matched = [e for e in index if e in heads]
            if index and len(matched) >= max(2, len(index) // 2):
                fails += [
                    f"{rel}: index lists {entry!r} but no such heading exists"
                    for entry in index
                    if entry not in heads
                ]
                # The other direction: a heading added later and never indexed. A reader who
                # navigates by the index never learns the section is there.
                fails += [
                    f"{rel}: heading {head!r} is missing from the index"
                    for head in heads
                    if head not in index
                ]
            # One blank line separates blocks; two is always debris — usually where a block
            # was deleted. The old threshold was four, which let every real case through.
            # Inside a code fence the rule is the formatter's, not this one's: ruff puts
            # two blank lines between top-level definitions, and the examples are formatted.
            fails += [
                f"{rel}:{j + 1} blank run"
                for j in range(len(lines) - 1)
                if j not in code
                and not lines[j].strip()
                and not lines[j + 1].strip()
                and (j == 0 or lines[j - 1].strip())
            ]
    return fails, []


def check_paragraph_length(repo: Repo) -> Result:
    """A 400-word paragraph is a wall, and a reader skims walls.

    Measured across this skill: the longest paragraph was 491 words, and two reference
    files carried nine and eleven paragraphs over 120. Prose that long is where a
    conditional rule hides in the middle and gets applied unconditionally — which is
    exactly how the manual-bump instruction survived the move to tag-driven releases.
    """
    warns = []
    # A skill is a directory holding a SKILL.md. Globbing `skills/*/` also matched
    # `skills/.claude/`, a sibling that is not a skill at all, and the crash that caused
    # was fixed once by skipping dot-directories — which would have hidden a real skill
    # whose reference file happened to sit under one. Identify skills by their manifest
    # instead, and let anything unreadable inside one be reported rather than skipped.
    for manifest in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
        for doc in sorted(manifest.parent.rglob("*.md")):
            if "evals" in doc.parts or "templates" in doc.parts:
                continue
            try:
                text = doc.read_text()
            except OSError as exc:
                warns.append(
                    f"{doc}: unreadable ({exc.strerror}) — an audit cannot "
                    "vouch for a file it could not open"
                )
                continue
            # Measure the longest run of PROSE, not of any block. A bullet list has no
            # blank lines between items, so counting blocks flagged well-structured lists
            # and code fences — 12 warnings, of which 8 were lists. What actually costs a
            # reader is an unbroken wall of sentences, which is where a conditional rule
            # hides mid-paragraph and gets applied unconditionally.
            fenced = False
            run: list[str] = []

            def flush(run=run, doc=doc):
                if not run:
                    return
                words = sum(len(line.split()) for line in run)
                if words > 200:
                    first = " ".join(" ".join(run).split())[:60]
                    warns.append(
                        f"{doc.relative_to(repo.root)}: {words}-word prose run — "
                        f"break it up ({first}...)"
                    )
                run.clear()

            for line in text.splitlines():
                if line.lstrip().startswith("```"):
                    fenced = not fenced
                    flush()
                    continue
                if fenced or not line.strip() or line.lstrip()[:1] in "-*>|#":
                    flush()
                    continue
                run.append(line)
            flush()
    return [], warns


# A fenced Python block, at any indentation (list items indent theirs), with its body.
_EXAMPLE = re.compile(r"^( *)```python\n(.*?)^\1```", re.MULTILINE | re.DOTALL)
# What a fragment cannot supply and is not judged on: the names its surrounding file
# defines, a module docstring, and imports shown for their own sake.
_FRAGMENT_RULES = ("F821", "D100", "F401")


def check_doc_examples(repo: Repo) -> Result:
    """Every fenced Python example in the skill docs must pass the shipped ruff rules.

    Two examples shipped for months with syntax errors — a positional argument after a
    keyword, an `...` declared as a parameter — and every one contradicted the docstring
    rule the same docs state. ruff never reads Markdown, so nothing saw. Each block is
    written out beside a copy of `templates/pyproject.toml` and linted under the rules a
    scaffold runs; the formatter already covers Markdown on its own. Findings carry the
    doc's line, not the block's.
    """
    tmpl = _template_dir(repo)
    config = tmpl / "pyproject.toml" if tmpl else None
    if config is None or not config.is_file():
        return [], []
    ruff = shutil.which("ruff")
    if ruff is None:
        return [], ["ruff is not installed — doc examples NOT CHECKED, not passed"]
    fails: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        work = pathlib.Path(scratch)
        (work / "pyproject.toml").write_bytes(config.read_bytes())
        origin: dict[str, tuple[str, int]] = {}
        for manifest in sorted(repo.root.glob("plugins/*/skills/*/SKILL.md")):
            for doc in sorted(manifest.parent.rglob("*.md")):
                if "evals" in doc.parts or "templates" in doc.parts:
                    continue
                text = doc.read_text()
                for n, m in enumerate(_EXAMPLE.finditer(text), 1):
                    indent, body = m.group(1), m.group(2)
                    lines = [line.removeprefix(indent) for line in body.splitlines()]
                    name = f"{doc.stem}_{n}.py"
                    (work / name).write_text("\n".join(lines) + "\n")
                    # The block's first code line is the line after the opening fence.
                    origin[name] = (
                        str(doc.relative_to(repo.root)),
                        text.count("\n", 0, m.start()) + 2,
                    )
        if not origin:
            return [], []
        ignores = [arg for rule in _FRAGMENT_RULES for arg in ("--ignore", rule)]
        out = subprocess.run(
            [ruff, "check", "--no-cache", "--output-format", "concise", *ignores, "."],
            cwd=work,
            capture_output=True,
            text=True,
            check=False,
        )
        for line in out.stdout.splitlines():
            name, _, rest = line.partition(":")
            if name not in origin:
                continue
            doc, start = origin[name]
            row, _, rest = rest.partition(":")
            _col, _, verdict = rest.partition(":")
            at = start + int(row) - 1 if row.isdigit() else start
            fails.append(f"{doc}:{at} example fails ruff: {verdict.strip()}")
    return fails, []


CHECKS = (
    check_docs_match_templates,
    check_skill_frontmatter,
    check_reference_links,
    check_named_sections,
    check_required_contexts_documented,
    check_shipped_workflows_documented,
    check_document_integrity,
    check_paragraph_length,
    check_doc_examples,
)


def audit(root: pathlib.Path) -> Result:
    """Run every authoring check against one repository."""
    repo = Repo(root)
    fails: list[str] = []
    warns: list[str] = []
    for check in CHECKS:
        f, w = check(repo)
        fails += f
        warns += w
    return fails, warns


def main(argv: list[str] | None = None) -> int:
    """Run the authoring audit against --root, or list the checks; exit 1 on any failure."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--list", action="store_true", help="print the checks and exit")
    args = ap.parse_args(argv)

    if args.list:
        for check in CHECKS:
            print(
                f"{check.__name__[len('check_') :]:26} {(check.__doc__ or '').strip().splitlines()[0]}"
            )
        return 0

    fails, warns = audit(pathlib.Path(args.root))
    for w in warns:
        print(f"⚠️  WARN: {w}")
    for f in fails:
        print(f"❌ FAIL: {f}")
    print(
        "skill authoring audit FAILED" if fails else "✅ skill authoring audit passed"
    )
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
