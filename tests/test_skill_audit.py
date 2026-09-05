"""Unit tests for scripts/skill_audit.py.

The shell version could only be tested by running the whole script against a fixture
repo and grepping its output, which is why several of its checks silently did nothing
for weeks. Each check here is a function, so each gets its own case.
"""

import importlib.util
import json
import pathlib
import subprocess

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "skill_audit", _SCRIPTS / "skill_audit.py"
)
audit = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(audit)


@pytest.fixture
def repo(tmp_path):
    """A repo with the workflow directory present and nothing else."""
    (tmp_path / ".github/workflows").mkdir(parents=True)
    return tmp_path


def _wf(repo, name, body):
    (repo / ".github/workflows" / name).write_text(body)


def test_missing_canonical_workflows_are_listed(repo) -> None:
    """Every absent canonical file is named, not just the first."""
    fails, _ = audit.check_canonical_files(audit.Repo(repo))
    assert any("pr-checks.yml" in f for f in fails)
    assert any(".gitignore" in f for f in fails)


def test_a_panel_repo_must_carry_the_panel_workflow(repo) -> None:
    """`frontend/` without `panel_bundle.yml` leaves the panel's TypeScript unchecked.

    The workflow was never required, so the two real panel repos sat on its superseded
    predecessor with nothing objecting.
    """
    (repo / "frontend").mkdir()
    (repo / "frontend/package.json").write_text("{}")
    fails, _ = audit.check_canonical_files(audit.Repo(repo))
    assert any("panel_bundle.yml" in f and "frontend/" in f for f in fails)


def test_a_repo_without_a_panel_is_not_asked_for_the_panel_workflow(repo) -> None:
    """On a repo with no `frontend/` the workflow's own first run fails; never demand it."""
    fails, _ = audit.check_canonical_files(audit.Repo(repo))
    assert not any("panel_bundle.yml" in f for f in fails)


def test_the_superseded_frontend_workflow_is_refused(repo) -> None:
    """`frontend_build.yml` gated merges on a build artefact; `panel_bundle.yml` replaced it."""
    (repo / ".github/workflows/frontend_build.yml").write_text("name: old\n")
    fails, _ = audit.check_canonical_files(audit.Repo(repo))
    assert any("frontend_build.yml" in f and "panel_bundle.yml" in f for f in fails)


def test_bare_tag_pins_fail(repo) -> None:
    """A tag can be repointed at new code that runs with the workflow's token."""
    _wf(repo, "a.yml", "jobs:\n  x:\n    steps:\n      - uses: actions/checkout@v7\n")
    fails, _ = audit.check_action_pins(audit.Repo(repo))
    assert len(fails) == 1 and "not pinned to a commit SHA" in fails[0]


def test_sha_without_a_version_comment_fails(repo) -> None:
    """A 40-character hex string tells a reader nothing on its own."""
    _wf(
        repo,
        "a.yml",
        f"jobs:\n  x:\n    steps:\n      - uses: actions/checkout@{'a' * 40}\n",
    )
    fails, _ = audit.check_action_pins(audit.Repo(repo))
    assert len(fails) == 1 and "no version comment" in fails[0]


def test_documented_mutable_refs_are_exempt(repo) -> None:
    """HACS and hassfest each document a mutable ref; pinning stops tracking them."""
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - uses: hacs/action@main\n"
        "      - uses: home-assistant/actions/hassfest@master\n",
    )
    assert audit.check_action_pins(audit.Repo(repo)) == ([], [])


def test_two_release_body_writers_fail(repo) -> None:
    """Two writers race, and the loser's output is what users read."""
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - run: gh release edit v1 --notes-file n.md\n",
    )
    _wf(
        repo,
        "b.yml",
        "jobs:\n  y:\n    steps:\n      - uses: softprops/action-gh-release@v3\n"
        "        with:\n          generate_release_notes: true\n",
    )
    fails, _ = audit.check_single_body_writer(audit.Repo(repo))
    assert (
        len(fails) == 1
        and "more than one workflow step writes the release body" in fails[0]
    )


def test_v6_drafter_categories_fail(repo) -> None:
    """The v6 shape parses, matches nothing, and resolves every release as a patch."""
    (repo / ".github/release-drafter.yml").write_text(
        "categories:\n  - title: Features\n    semver-increment: minor\n    labels:\n      - feature\n"
    )
    fails, _ = audit.check_drafter_categories(audit.Repo(repo))
    assert len(fails) == 1 and "v6 top-level" in fails[0]


def test_when_shaped_categories_pass(repo) -> None:
    """The v7 `when:` shape is the one that matches."""
    (repo / ".github/release-drafter.yml").write_text(
        "categories:\n  - title: Features\n    semver-increment: minor\n    when:\n"
        "      labels:\n        - feature\n"
    )
    assert audit.check_drafter_categories(audit.Repo(repo)) == ([], [])


def test_pr_opener_must_be_draft_and_actor_gated(repo) -> None:
    """A PR opened with a shared token otherwise appears to be written by its owner."""
    _wf(
        repo,
        "auto_draft_pr.yml",
        "jobs:\n  draft:\n    steps:\n      - run: gh pr create --title x\n",
    )
    fails, _ = audit.check_pr_openers(audit.Repo(repo))
    assert any("gate on the actor" in f for f in fails)
    assert any("must open the PR as a draft" in f for f in fails)


def test_multiline_docstrings_in_integration_code_fail(tmp_path) -> None:
    """Module docstrings are exempt; functions and classes are not."""
    cc = tmp_path / "custom_components/demo"
    cc.mkdir(parents=True)
    (cc / "__init__.py").write_text(
        '"""Module docstring.\n\nStill fine, multiple lines.\n"""\n\n\n'
        'def f():\n    """One line."""\n\n\n'
        'def g():\n    """First.\n\n    Second.\n    """\n'
    )
    fails, _ = audit.check_docstrings(audit.Repo(tmp_path))
    assert len(fails) == 1 and "g" in fails[0]


def test_done_rules_without_tests_fail(tmp_path) -> None:
    """A `done` with no test is a claim, not evidence."""
    cc = tmp_path / "custom_components/demo"
    cc.mkdir(parents=True)
    (cc / "quality_scale.yaml").write_text(
        "rules:\n  config-flow: done\n  diagnostics: todo\n"
    )
    fails, _ = audit.check_claims_have_tests(audit.Repo(tmp_path))
    assert any("no tests/ directory" in f for f in fails)


def test_hook_without_the_subject_guards_fails(tmp_path) -> None:
    """A hook that only measures length lets a well-formed empty subject through."""
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    hook = hooks / "commit-msg"
    hook.write_text("#!/usr/bin/env bash\n[ ${#1} -gt 72 ] && exit 1\nexit 0\n")
    hook.chmod(0o755)

    fails, _ = audit.check_commit_hook(audit.Repo(tmp_path))
    assert any("Conventional Commit subject shape" in f for f in fails)
    assert any("editorialising" in f for f in fails)

    hook.write_text(
        "case x in feat|fix|docs) ;; esac\n# editorialising subjects rejected\n"
    )
    hook.chmod(0o755)
    fails, _ = audit.check_commit_hook(audit.Repo(tmp_path))
    assert fails == []


def test_shipped_scripts_must_match_the_ones_this_repo_runs(tmp_path) -> None:
    """The shipped copy is what integrations get, and it drifted from the repo's own.

    Two fixes landed in `scripts/` and never reached `templates/scripts/`, while the docs
    described the fixed behaviour. Nothing compared them: `check_self_diff` walks workflows
    only. A silent no-op here would restore exactly that blind spot, so assert both that it
    catches a difference and that it clears once the copies agree.
    """
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / "scripts").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmpl / "scripts/tool.py").write_text("VALUE = 1\n")
    (tmp_path / "scripts/tool.py").write_text("VALUE = 2\n")

    fails, _ = audit.check_template_scripts_match(audit.Repo(tmp_path))
    assert any("scripts/tool.py" in f for f in fails)

    (tmp_path / "scripts/tool.py").write_text("VALUE = 1\n")
    assert audit.check_template_scripts_match(audit.Repo(tmp_path)) == ([], [])


def test_shipped_script_absent_from_this_repo_is_not_drift(tmp_path) -> None:
    """Not every shipped file is one the skill repo runs; a missing counterpart is fine."""
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / "scripts").mkdir(parents=True)
    (tmpl / "scripts/only_shipped.py").write_text("VALUE = 1\n")
    assert audit.check_template_scripts_match(audit.Repo(tmp_path)) == ([], [])


def test_a_shipped_workflow_this_repo_lacks_is_named_as_unexercised(tmp_path) -> None:
    """A template with no counterpart here is run by nothing, and the audit must say so.

    `panel_bundle.yml` was edited eight times over three weeks without one execution:
    this repo carries no copy, so its CI never ran it, and the silent skip here meant
    no run ever mentioned that. Its first run anywhere failed.
    """
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / ".github/workflows").mkdir(parents=True)
    (tmpl / ".github/workflows/only_shipped.yml").write_text("name: x\n")
    (tmpl / ".github/workflows/both.yml").write_text("name: y\n")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/both.yml").write_text("name: y\n")
    fails, warns = audit.check_self_diff(audit.Repo(tmp_path))
    assert fails == []
    assert len(warns) == 1
    assert "only_shipped.yml" in warns[0] and "both.yml" not in warns[0]
    assert "runs it" in warns[0]


def test_list_mode_names_every_check(capsys) -> None:
    """The skill points readers at --list instead of enumerating rules that go stale."""
    assert audit.main(["--list"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == len(audit.CHECKS)
    assert all(line.split()[0] for line in out)


def test_a_third_pr_opener_is_still_refused(repo) -> None:
    """The sanctioned list is short on purpose: a workflow opening a PR acts as an author."""
    _wf(
        repo,
        "helpful.yml",
        "jobs:\n  x:\n    steps:\n      - run: gh pr create --title hi\n",
    )
    fails, _ = audit.check_pr_openers(audit.Repo(repo))
    assert any("helpful.yml opens PRs" in f for f in fails)


def test_a_marked_opener_states_its_own_reason(repo) -> None:
    """A repo with a different delivery model declares its exception in its own file.

    The shipped audit should not carry the filenames of repos it never runs in.
    """
    _wf(
        repo,
        "sync_plugin_version.yml",
        "# skill-audit: sanctioned-opener — the version lives in a committed file\n"
        "jobs:\n  x:\n    steps:\n      - run: gh pr create --title v\n",
    )
    fails, _ = audit.check_pr_openers(audit.Repo(repo))
    assert fails == []


def test_unverifiable_checks_warn_rather_than_passing(repo, monkeypatch) -> None:
    """A check that cannot run must say NOT CHECKED, not stay silent.

    Observed on a live run: `Skill Audit` passed in CI while the same script failed
    locally, because CI could not query GitHub and the check returned nothing. A check
    that only fails where nobody looks is worse than no check.
    """

    class _Missing:
        def __call__(self, *a, **k):
            raise OSError("gh not found")

    monkeypatch.setattr(audit.subprocess, "run", _Missing())

    _, warns = audit.check_required_status_checks(audit.Repo(repo))
    assert any("NOT CHECKED" in w for w in warns)

    _wf(repo, "dependency_review.yml", "jobs:\n  review:\n    steps: []\n")
    _, warns = audit.check_dependency_graph(audit.Repo(repo))
    assert any("NOT CHECKED" in w for w in warns)


def test_dependency_graph_off_is_a_failure(repo, monkeypatch) -> None:
    """Seven workflows green and Dependency review red alone — the observed failure."""
    _wf(repo, "dependency_review.yml", "jobs:\n  review:\n    steps: []\n")

    class _Fake:
        def __init__(self, out, rc=0):
            self.stdout, self.returncode = out, rc

    calls = []

    def fake_run(cmd, **k):
        calls.append(cmd)
        if "repo" in cmd and "view" in cmd:
            return _Fake("owner/repo\n")
        return _Fake("", 1)  # sbom probe fails: graph disabled

    monkeypatch.setattr(audit.subprocess, "run", fake_run)

    fails, _ = audit.check_dependency_graph(audit.Repo(repo))
    assert any("dependency graph is off" in f for f in fails)


def test_no_dependency_review_workflow_means_nothing_to_check(
    repo, monkeypatch
) -> None:
    """A repo that does not ship the workflow has no prerequisite to satisfy."""
    monkeypatch.setattr(
        audit.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not query")),
    )
    assert audit.check_dependency_graph(audit.Repo(repo)) == ([], [])


def test_platforms_naming_a_missing_module_fails(repo) -> None:
    """The live defect: PLATFORMS = ["sensor"] with no sensor.py, inert until forwarded."""
    pkg = repo / "custom_components/acmedev"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"domain": "acmedev"}')
    (pkg / "const.py").write_text(
        'DOMAIN = "acmedev"\nPLATFORMS = ["sensor", "notify"]\n'
    )
    (pkg / "notify.py").write_text("")
    fails, _ = audit.check_platforms_have_modules(audit.Repo(repo))
    assert len(fails) == 1 and "sensor" in fails[0] and "notify" not in fails[0]


def test_platform_enum_form_is_understood(repo) -> None:
    """Both spellings appear in real integrations."""
    pkg = repo / "custom_components/acmedev"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"domain": "acmedev"}')
    (pkg / "const.py").write_text("PLATFORMS = [Platform.SENSOR, Platform.NOTIFY]\n")
    (pkg / "sensor.py").write_text("")
    fails, _ = audit.check_platforms_have_modules(audit.Repo(repo))
    assert len(fails) == 1 and "notify" in fails[0]


def test_matching_platforms_pass(repo) -> None:
    """A module beside every PLATFORMS entry is the wired state."""
    pkg = repo / "custom_components/acmedev"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"domain": "acmedev"}')
    (pkg / "const.py").write_text('PLATFORMS = ["notify"]\n')
    (pkg / "notify.py").write_text("")
    assert audit.check_platforms_have_modules(audit.Repo(repo)) == ([], [])


def _ruleset(repo, *contexts) -> None:
    (repo / "ruleset.json").write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [{"context": c} for c in contexts]
                        },
                    }
                ]
            }
        )
    )


def test_a_required_context_no_job_produces_fails(repo) -> None:
    """The observed defect, twice: a ruleset requiring a check nothing reports.

    Checking that workflow FILES exist cannot catch this — the failure is a name in the
    ruleset with no job on the other end. Every other check goes green and the PR is
    unmergeable with nothing to point at.
    """
    _wf(
        repo,
        "pr-checks.yml",
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n",
    )
    _ruleset(repo, "CC labelling", "Version validation")
    fails, _ = audit.check_required_contexts_have_producers(audit.Repo(repo))
    assert len(fails) == 1 and "Version validation" in fails[0]


def test_every_required_context_produced_passes(repo) -> None:
    """A ruleset whose every context has a producing job is the healthy state."""
    _wf(
        repo,
        "pr-checks.yml",
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n",
    )
    _ruleset(repo, "CC labelling")
    assert audit.check_required_contexts_have_producers(audit.Repo(repo)) == ([], [])


def test_a_job_without_a_name_is_known_by_its_id(repo) -> None:
    """GitHub names the check-run for the job id when the job declares no name."""
    _wf(repo, "a.yml", "jobs:\n  review:\n    steps: []\n")
    _ruleset(repo, "review")
    assert audit.check_required_contexts_have_producers(audit.Repo(repo)) == ([], [])


def test_the_shipped_ruleset_is_checked_against_the_shipped_workflows(tmp_path) -> None:
    """What ships is what scaffolds; an orphan here bricks every repo built from it."""
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / ".github/workflows").mkdir(parents=True)
    (tmpl / ".github/workflows/a.yml").write_text(
        "jobs:\n  x:\n    name: Real\n    steps: []\n"
    )
    (tmpl / "ruleset.json").write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [{"context": "Imaginary"}]
                        },
                    }
                ]
            }
        )
    )
    fails, _ = audit.check_required_contexts_have_producers(audit.Repo(tmp_path))
    assert len(fails) == 1 and "Imaginary" in fails[0]


def test_live_required_contexts_warn_when_gh_is_missing(repo, monkeypatch) -> None:
    """Unverifiable must say NOT CHECKED; a silent pass is how this survived before."""

    class _Missing:
        def __call__(self, *a, **k):
            raise OSError("gh not found")

    monkeypatch.setattr(audit.subprocess, "run", _Missing())
    _, warns = audit.check_live_required_contexts(audit.Repo(repo))
    assert any("NOT CHECKED" in w for w in warns)


def test_live_ruleset_orphan_fails(repo, monkeypatch) -> None:
    """A repo protected from the GitHub UI has no ruleset.json to compare against."""
    _wf(
        repo,
        "pr-checks.yml",
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n",
    )

    class _Fake:
        def __init__(self, out, rc=0):
            self.stdout, self.returncode = out, rc

    def fake_run(cmd, **k):
        if cmd[0] == "git":
            return _Fake(
                "", 128
            )  # no clone to consult: the working tree is the verdict
        if "view" in cmd:
            return _Fake("owner/repo\n")
        if cmd[-1] == ".default_branch":
            return _Fake("main\n")
        return _Fake('["CC labelling","Version validation"]')

    monkeypatch.setattr(audit.subprocess, "run", fake_run)

    fails, _ = audit.check_live_required_contexts(audit.Repo(repo))
    assert (
        len(fails) == 1
        and "Version validation" in fails[0]
        and "working tree" in fails[0]
    )


def test_a_placeholder_left_in_a_shipped_run_block_fails(tmp_path) -> None:
    """The observed defect: `<domain>` shipped in release.yml and bash read it as a redirect.

    The zip step died on `cd custom_components/<domain>` with a syntax error, no asset was
    attached, and HACS could not install the release. The one check that read the file only
    asked whether it mentioned manifest.json, which it did.
    """
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / ".github/workflows").mkdir(parents=True)
    (tmpl / ".github/workflows/release.yml").write_text(
        "jobs:\n  build:\n    steps:\n      - run: |\n"
        "          cd custom_components/<domain>\n          zip -r out.zip .\n"
    )
    fails, _ = audit.check_no_placeholders(audit.Repo(tmp_path))
    assert len(fails) == 1 and "release.yml" in fails[0] and "<domain>" in fails[0]


def test_a_placeholder_in_a_comment_is_documentation(tmp_path) -> None:
    """A comment saying what `<domain>` means is never seen by bash."""
    tmpl = tmp_path / "plugins/ha/skills/demo/templates"
    (tmpl / ".github/workflows").mkdir(parents=True)
    (tmpl / ".github/workflows/release.yml").write_text(
        "# zips custom_components/<domain>\njobs:\n  build:\n    steps:\n      - run: |\n"
        "          # the package is custom_components/<domain>\n          zip -r out.zip .\n"
    )
    assert audit.check_no_placeholders(audit.Repo(tmp_path)) == ([], [])


def test_a_placeholder_left_in_a_copied_workflow_fails(repo) -> None:
    """A scaffolded repo that copied the template and never substituted has the same defect."""
    _wf(
        repo,
        "release.yml",
        "jobs:\n  build:\n    steps:\n      - run: gh release upload v1 <domain>.zip\n",
    )
    fails, _ = audit.check_no_placeholders(audit.Repo(repo))
    assert len(fails) == 1 and "<domain>" in fails[0]


def test_a_placeholder_in_a_with_value_fails(repo) -> None:
    """An action input is not shell, but a placeholder there is just as unsubstituted."""
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - uses: actions/setup-node@abc # v1\n"
        "        with:\n          cache-dependency-path: <domain>/package-lock.json\n",
    )
    fails, _ = audit.check_no_placeholders(audit.Repo(repo))
    assert len(fails) == 1 and "<domain>" in fails[0]


def test_python_run_without_a_setup_step_fails(repo) -> None:
    """A step that runs Python before any setup-python step runs on the runner's own.

    Four shipped workflows did exactly this, and the runner's interpreter rejected the
    scripts' syntax. Comparing declared versions cannot see a job that declares none.
    """
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - uses: actions/checkout@abc # v1\n"
        "      - name: Gate\n        run: python3 scripts/manifest_gate.py --suggest\n",
    )
    fails, _ = audit.check_python_steps_have_a_setup(audit.Repo(repo))
    assert len(fails) == 1
    assert "a.yml" in fails[0] and "'Gate'" in fails[0] and "setup-python" in fails[0]


def test_python_run_after_a_setup_step_passes(repo) -> None:
    """The ordinary shape: setup-python, then the script."""
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - uses: actions/checkout@abc # v1\n"
        "      - uses: actions/setup-python@def # v7\n        with:\n"
        "          python-version: '3.14'\n"
        "      - run: |\n          python3 - <<'PY'\n          print(1)\n          PY\n",
    )
    assert audit.check_python_steps_have_a_setup(audit.Repo(repo)) == ([], [])


def test_a_setup_step_in_another_job_does_not_count(repo) -> None:
    """Jobs run on separate runners; a setup in one job leaves the other on the default."""
    _wf(
        repo,
        "a.yml",
        "jobs:\n  x:\n    steps:\n      - uses: actions/setup-python@def # v7\n"
        "  y:\n    steps:\n      - run: python -m pytest\n",
    )
    fails, _ = audit.check_python_steps_have_a_setup(audit.Repo(repo))
    assert len(fails) == 1 and "job 'y'" in fails[0]


def _pr_checks(ref: str) -> str:
    """A pr-checks.yml carrying every string the shape check requires, checking out `ref`."""
    return (
        "on:\n  pull_request_target:\n    types: [opened]\n"
        "jobs:\n  label:\n    steps:\n      - run: echo 'Remove superseded'\n"
        "  title-check:\n    needs: label\n    if: github.event.pull_request.user.type != 'Bot'\n"
        "    steps:\n      - uses: actions/checkout@abc # v1\n"
        f"        with:\n          ref: ${{{{ github.event.pull_request.{ref} }}}}\n"
        "      - run: python3 scripts/commit_summary.py --mode label\n"
    )


def test_title_check_pinned_to_the_base_sha_fails(repo) -> None:
    """base.sha is frozen at PR creation while the workflow runs from the base branch head.

    A PR opened before a scripts/ change merged ran the NEW workflow against the OLD script:
    on ha-ci-testing #9 the gate died with `--mode: invalid choice: 'label'` instead of
    reporting the label mismatch it exists to report. base.ref keeps the tree and the
    workflow consistent and is equally base-side.
    """
    _wf(repo, "pr-checks.yml", _pr_checks("base.sha"))
    fails, _ = audit.check_pr_checks_shape(audit.Repo(repo))
    assert len(fails) == 1 and "base.ref" in fails[0] and "frozen" in fails[0]


def test_title_check_on_the_base_ref_passes(repo) -> None:
    """base.ref is the base branch head, the same ref the workflow itself is loaded from."""
    _wf(repo, "pr-checks.yml", _pr_checks("base.ref"))
    assert audit.check_pr_checks_shape(audit.Repo(repo)) == ([], [])


def _cloned_repo(tmp_path, workflow: str) -> pathlib.Path:
    """A working clone whose origin/main carries `workflow` as pr-checks.yml."""
    src = tmp_path / "src"
    (src / ".github/workflows").mkdir(parents=True)
    (src / ".github/workflows/pr-checks.yml").write_text(workflow)
    git = [
        "git",
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
    ]
    subprocess.run([*git, "init", "-q", "-b", "main"], cwd=src, check=True)
    subprocess.run([*git, "add", "."], cwd=src, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "chore: init"], cwd=src, check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(src), str(work)], check=True)
    return work


def test_a_job_the_base_branch_defines_is_not_an_orphan(tmp_path) -> None:
    """The misreading that cost a working gate.

    Under pull_request_target the producing workflow comes from the BASE branch, so a
    branch that deletes a job main still defines does not orphan the context. `Version
    validation` was called an orphan on exactly this evidence and removed from the ruleset
    while origin/main still defined `version-gate`, which was correctly failing PR #65.
    """
    work = _cloned_repo(
        tmp_path, "jobs:\n  gate:\n    name: Version validation\n    steps: []\n"
    )
    (work / ".github/workflows/pr-checks.yml").write_text(
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n"
    )
    _ruleset(work, "CC labelling", "Version validation")
    assert audit.check_required_contexts_have_producers(audit.Repo(work)) == ([], [])


def test_an_orphan_report_names_the_refs_it_judged(tmp_path) -> None:
    """A verdict without its evidence is what got misread; say which ref was consulted."""
    work = _cloned_repo(
        tmp_path, "jobs:\n  label:\n    name: CC labelling\n    steps: []\n"
    )
    _ruleset(work, "CC labelling", "Version validation")
    fails, _ = audit.check_required_contexts_have_producers(audit.Repo(work))
    assert (
        len(fails) == 1
        and "Version validation" in fails[0]
        and "origin/main" in fails[0]
    )


def test_without_a_remote_the_verdict_says_working_tree(repo) -> None:
    """No base branch to consult is a weaker verdict, and it must say so."""
    _wf(
        repo,
        "pr-checks.yml",
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n",
    )
    _ruleset(repo, "CC labelling", "Version validation")
    fails, _ = audit.check_required_contexts_have_producers(audit.Repo(repo))
    assert len(fails) == 1 and "working tree" in fails[0]


def test_live_check_counts_jobs_the_base_branch_defines(tmp_path, monkeypatch) -> None:
    """The live ruleset is judged the same way: producers on the base branch count."""
    work = _cloned_repo(
        tmp_path, "jobs:\n  gate:\n    name: Version validation\n    steps: []\n"
    )
    (work / ".github/workflows/pr-checks.yml").write_text(
        "jobs:\n  label:\n    name: CC labelling\n    steps: []\n"
    )
    real_run = audit.subprocess.run

    class _Fake:
        def __init__(self, out, rc=0):
            self.stdout, self.returncode = out, rc

    def fake_run(cmd, **k):
        if cmd[0] == "git":
            return real_run(cmd, **k)
        if "view" in cmd:
            return _Fake("owner/repo\n")
        if cmd[-1] == ".default_branch":
            return _Fake("main\n")
        return _Fake('["CC labelling","Version validation"]')

    monkeypatch.setattr(audit.subprocess, "run", fake_run)

    assert audit.check_live_required_contexts(audit.Repo(work)) == ([], [])


def test_the_future_import_is_not_demanded(repo) -> None:
    """Python 3.14 defers annotations itself; the shipped ruff config bans the import."""
    pkg = repo / "custom_components/acmedev"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"domain": "acmedev"}')
    (pkg / "__init__.py").write_text('DOMAIN = "acmedev"\n')
    assert audit.check_antipatterns(audit.Repo(repo)) == ([], [])
