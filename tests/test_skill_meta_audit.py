"""Unit tests for scripts/skill_meta_audit.py — the authoring checks.

These live apart from test_skill_audit.py for the same reason the scripts do: nothing
here can fire in a scaffolded integration, so nothing here ships to one.
"""

import importlib.util
import json
import pathlib
import shutil

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "skill_meta_audit", _SCRIPTS / "skill_meta_audit.py"
)
audit = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(audit)


def _skill(root, name, frontmatter, body="body\n"):
    d = root / "plugins/ha/skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n{body}")


def test_docs_naming_a_dead_job_fails(tmp_path) -> None:
    """`commit-summary` was deleted from pr-checks.yml; six passages still described it."""
    skill = tmp_path / "plugins/ha/skills/ha-integration"
    wfs = skill / "templates/.github/workflows"
    wfs.mkdir(parents=True)
    (wfs / "pr-checks.yml").write_text("jobs:\n  label:\n    steps: []\n")
    (skill / "reference").mkdir()
    (skill / "SKILL.md").write_text("the `pr-checks.yml` workflow runs on every PR\n")
    (skill / "reference/github-actions.md").write_text(
        "| Job | `needs:` | Does |\n|---|---|---|\n"
        "| `label` | — | labels |\n| `commit-summary` | — | writes the body |\n"
    )

    fails, _ = audit.check_docs_match_templates(audit.Repo(tmp_path))
    assert any("commit-summary" in f for f in fails)
    assert not any("`label`" in f or ": label" in f for f in fails)

    # A workflow the docs name but the scaffold does not ship.
    (skill / "SKILL.md").write_text("run `cut_rc.yml` to mint a candidate\n")
    fails, _ = audit.check_docs_match_templates(audit.Repo(tmp_path))
    assert any("cut_rc.yml" in f for f in fails)


def test_docs_may_name_a_workflow_that_is_gone(tmp_path) -> None:
    """History and opt-in add-ons are documented on purpose, not drift."""
    skill = tmp_path / "plugins/ha/skills/ha-integration"
    (skill / "templates/.github/workflows").mkdir(parents=True)
    (skill / "reference").mkdir()
    (skill / "SKILL.md").write_text(
        "Superseded: `pr-labeler.yml` is folded into pr-checks.\n"
        "Historical note: `create-dev-pr.yml` raced the labeler.\n"
        "Add `update_manifest_floors.yml` when the manifest carries `>=` floors.\n"
    )
    (skill / "reference/github-actions.md").write_text("")
    assert audit.check_docs_match_templates(audit.Repo(tmp_path)) == ([], [])


def test_skill_without_a_name_field_fails(tmp_path) -> None:
    """ha-panel-design shipped seven releases with no name in its frontmatter."""
    _skill(tmp_path, "ha-panel-design", "description: Use when changing a panel")
    fails, _ = audit.check_skill_frontmatter(audit.Repo(tmp_path))
    assert any("no name field" in f for f in fails)


def test_description_summarising_the_skill_fails(tmp_path) -> None:
    """A description that says what the skill does gets followed instead of the skill."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Material 3 type scale and tokens",
    )
    fails, _ = audit.check_skill_frontmatter(audit.Repo(tmp_path))
    assert any("must start with 'Use when'" in f for f in fails)


def test_name_must_match_its_directory(tmp_path) -> None:
    """The name field is how a skill is invoked, so it must be the directory's name."""
    _skill(tmp_path, "ha-thing", "name: ha-other\ndescription: Use when doing a thing")
    fails, _ = audit.check_skill_frontmatter(audit.Repo(tmp_path))
    assert any("name field is 'ha-other'" in f for f in fails)


def test_valid_frontmatter_passes_and_size_only_warns(tmp_path) -> None:
    """Well-formed frontmatter passes; an oversized body is advice, not a failure."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="word " * 5001,
    )
    fails, warns = audit.check_skill_frontmatter(audit.Repo(tmp_path))
    assert fails == []
    assert any("move heavy sections" in w for w in warns)


def test_reference_link_to_a_missing_file_fails(tmp_path) -> None:
    """A renamed reference file leaves the router pointing at nothing."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="Read [scaffold](reference/scaffold.md) first.\n",
    )
    fails, _ = audit.check_reference_links(audit.Repo(tmp_path))
    assert any("links reference/scaffold.md" in f for f in fails)


def test_orphan_reference_file_fails(tmp_path) -> None:
    """A reference file nothing links to is never read again."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="No links here.\n",
    )
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir()
    (ref / "orphan.md").write_text("content\n")
    fails, _ = audit.check_reference_links(audit.Repo(tmp_path))
    assert any("orphan.md is linked from nothing" in f for f in fails)


def test_backticked_reference_counts_as_a_link(tmp_path) -> None:
    """The skill cites some references in backticks rather than as markdown links."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="See `reference/patterns.md` for the rules.\n",
    )
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir()
    (ref / "patterns.md").write_text("content\n")
    assert audit.check_reference_links(audit.Repo(tmp_path)) == ([], [])


def test_a_non_skill_sibling_directory_is_not_audited(tmp_path) -> None:
    """A sibling directory with no SKILL.md is not a skill and is not judged.

    Skipping dot-paths by name would instead hide a real skill's reference file that
    happened to live under one. A skill is a directory with a SKILL.md.
    """
    skills = tmp_path / "plugins/ha/skills"
    (skills / ".claude").mkdir(parents=True)
    (skills / ".claude/loop.md").write_text("word " * 300)
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    fails, warns = audit.check_paragraph_length(audit.Repo(tmp_path))
    assert fails == []
    assert not any("loop.md" in w for w in warns)


def test_an_unreadable_file_inside_a_skill_is_reported(tmp_path) -> None:
    """An audit that cannot open a file must say so, not pass over it."""
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    doc = tmp_path / "plugins/ha/skills/ha-thing/reference"
    doc.mkdir()
    f = doc / "locked.md"
    f.write_text("content\n")
    f.chmod(0o000)
    try:
        _, warns = audit.check_paragraph_length(audit.Repo(tmp_path))
        assert any("locked.md" in w and "unreadable" in w for w in warns)
    finally:
        f.chmod(0o644)


def _templates(root, ruleset_contexts=(), workflows=()):
    t = root / "plugins/ha/skills/ha-thing/templates"
    (t / ".github/workflows").mkdir(parents=True)
    for w in workflows:
        (t / ".github/workflows" / w).write_text("jobs: {}\n")
    (t / "ruleset.json").write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {"context": c} for c in ruleset_contexts
                            ]
                        },
                    }
                ]
            }
        )
    )
    (root / "plugins/ha/skills/ha-thing/reference").mkdir(parents=True, exist_ok=True)
    return t


def test_a_pointer_to_a_moved_section_fails(tmp_path) -> None:
    """The exact defect: "*Merge discipline* in `SKILL.md`" after it moved to discipline.md."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="The full rule is *Merge discipline* in `reference/discipline.md`.\n",
    )
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir(exist_ok=True)
    (ref / "discipline.md").write_text("# Something else\n\ntext\n")
    fails, _ = audit.check_named_sections(audit.Repo(tmp_path))
    assert any("no such heading" in f for f in fails)

    (ref / "discipline.md").write_text("# Discipline\n\n## Merge discipline\n\ntext\n")
    assert audit.check_named_sections(audit.Repo(tmp_path)) == ([], [])


def test_a_required_context_documented_nowhere_fails(tmp_path) -> None:
    """`Dependency review` was required by the ruleset and named in no reference file."""
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    _templates(tmp_path, ruleset_contexts=("CC labelling", "Dependency review"))
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    (ref / "github-setup.md").write_text("Required: `CC labelling`.\n")
    fails, _ = audit.check_required_contexts_documented(audit.Repo(tmp_path))
    assert any("Dependency review" in f for f in fails)


def test_a_wrong_context_count_fails(tmp_path) -> None:
    """The docs said "nine job-name contexts"; the ruleset had eight."""
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    _templates(tmp_path, ruleset_contexts=("A", "B"))
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    (ref / "github-setup.md").write_text(
        "`A` and `B`. It requires the nine job-name contexts.\n"
    )
    fails, _ = audit.check_required_contexts_documented(audit.Repo(tmp_path))
    assert any("claim nine required contexts" in f for f in fails)


def test_an_undocumented_shipped_workflow_fails(tmp_path) -> None:
    """The workflow reference named six of twelve shipped workflows."""
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    _templates(tmp_path, workflows=("pr-checks.yml", "stale.yml"))
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    (ref / "github-actions.md").write_text("We ship `pr-checks.yml`.\n")
    fails, _ = audit.check_shipped_workflows_documented(audit.Repo(tmp_path))
    assert any("stale.yml" in f for f in fails)
    assert not any("pr-checks.yml" in f for f in fails)


def test_an_emptied_document_fails(tmp_path) -> None:
    """Total gutting was the boundary case that slipped past every structural check.

    `check_document_integrity` was written for the partial kind — sentences cut in half,
    an index left pointing at deleted headings. On a fully empty file there are no lines,
    so no headings, no index and no loop bodies: it returned nothing and the audit passed
    a document with its content removed. Found by emptying each governing doc in turn and
    watching which ones the audit noticed; `audit.md` was the one it did not.
    """
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="See `reference/gutted.md`.\n",
    )
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir(exist_ok=True)

    (ref / "gutted.md").write_text("")
    fails, _ = audit.check_document_integrity(audit.Repo(tmp_path))
    assert any("gutted.md" in f and "is empty" in f for f in fails)

    # Whitespace-only is the same damage with the evidence hidden.
    (ref / "gutted.md").write_text("\n\n   \n")
    fails, _ = audit.check_document_integrity(audit.Repo(tmp_path))
    assert any("gutted.md" in f and "is empty" in f for f in fails)

    # And a file with real content must not be flagged by it.
    (ref / "gutted.md").write_text("# Heading\n\nA sentence that says something.\n")
    fails, _ = audit.check_document_integrity(audit.Repo(tmp_path))
    assert not any("is empty" in f for f in fails)


def test_blank_runs_inside_a_code_fence_are_code(tmp_path) -> None:
    """The formatter puts two blank lines between top-level defs; in a fence that is code."""
    _skill(
        tmp_path,
        "ha-thing",
        "name: ha-thing\ndescription: Use when doing a thing",
        body="See `reference/code.md`.\n",
    )
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir(exist_ok=True)

    (ref / "code.md").write_text(
        "# C\n\n```python\nimport re\n\n\ndef f():\n    return re\n```\n"
    )
    fails, _ = audit.check_document_integrity(audit.Repo(tmp_path))
    assert not any("blank run" in f for f in fails)

    # Outside a fence the same two blank lines are still debris.
    (ref / "code.md").write_text("# C\n\ntext\n\n\nmore\n")
    fails, _ = audit.check_document_integrity(audit.Repo(tmp_path))
    assert any("blank run" in f for f in fails)


def test_a_wall_of_prose_is_flagged_but_a_long_list_is_not(tmp_path) -> None:
    """The first version counted blocks, so a 60-item bullet list read as one paragraph.

    Eight of its twelve warnings were well-structured lists and code fences. What costs a
    reader is an unbroken run of sentences — that is where a conditional rule hides in the
    middle and gets applied unconditionally.
    """
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    ref.mkdir(exist_ok=True)

    (ref / "wall.md").write_text(
        "# W\n\n" + "sentence words here about a rule " * 45 + "\n"
    )
    _, warns = audit.check_paragraph_length(audit.Repo(tmp_path))
    assert any("prose run" in w for w in warns)

    (ref / "wall.md").write_text(
        "# W\n\n"
        + "\n".join(f"- item {i} with several words in it" for i in range(60))
        + "\n"
    )
    _, warns = audit.check_paragraph_length(audit.Repo(tmp_path))
    assert not any("prose run" in w for w in warns)

    (ref / "wall.md").write_text(
        "# W\n\n```python\n" + "x = 1  # a comment with words\n" * 60 + "```\n"
    )
    _, warns = audit.check_paragraph_length(audit.Repo(tmp_path))
    assert not any("prose run" in w for w in warns)


def _doc_with_example(tmp_path, code: str) -> None:
    """A skill whose one reference doc carries `code` as a fenced Python example."""
    _skill(tmp_path, "ha-thing", "name: ha-thing\ndescription: Use when doing a thing")
    tmpl = _templates(tmp_path)
    (tmpl / "pyproject.toml").write_text('[tool.ruff]\ntarget-version = "py314"\n')
    ref = tmp_path / "plugins/ha/skills/ha-thing/reference"
    (ref / "code.md").write_text(f"# C\n\n```python\n{code}```\n")


def test_a_doc_example_that_fails_ruff_is_named(tmp_path) -> None:
    """Two examples shipped with syntax errors; ruff never reads Markdown, so nothing saw.

    The finding carries the doc's own line number, not the line inside the block, so the
    reader lands on the fence rather than counting from it.
    """
    if not shutil.which("ruff"):
        pytest.skip("ruff is not installed")
    _doc_with_example(tmp_path, "def f(a, ...):\n    return a\n")
    fails, _ = audit.check_doc_examples(audit.Repo(tmp_path))
    assert fails and all("invalid-syntax" in f for f in fails)
    assert fails[0].startswith("plugins/ha/skills/ha-thing/reference/code.md:4 ")


def test_a_fragment_is_not_blamed_for_what_its_file_would_supply(tmp_path) -> None:
    """Names defined elsewhere in the file and a module docstring are not the example's."""
    if not shutil.which("ruff"):
        pytest.skip("ruff is not installed")
    _doc_with_example(
        tmp_path,
        "async def setup(hass: HomeAssistant) -> None:\n"
        '    """Use names the surrounding file defines."""\n'
        "    hass.data[DOMAIN] = True\n",
    )
    assert audit.check_doc_examples(audit.Repo(tmp_path)) == ([], [])


def test_without_ruff_the_examples_are_not_checked_rather_than_passed(
    tmp_path, monkeypatch
) -> None:
    """A check that cannot run says so; silence here would read as a pass."""
    monkeypatch.setattr(audit.shutil, "which", lambda _name: None)
    _doc_with_example(tmp_path, "def f(a, ...):\n    return a\n")
    fails, warns = audit.check_doc_examples(audit.Repo(tmp_path))
    assert fails == []
    assert any("NOT CHECKED" in w for w in warns)
