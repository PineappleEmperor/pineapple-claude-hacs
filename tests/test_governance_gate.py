"""Unit tests for scripts/governance_gate.py.

The gate's whole value is that it refuses. Every test asserting a refusal has a matching test
asserting the allow, because a gate stuck shut and a gate stuck open are both failures and only
the pair distinguishes them.

Fixtures rebind REPO and TIERS onto a tmp tree so the suite never depends on — or mutates — the
real governing docs. The gate module is imported rather than the server, so CI, which installs
only pytest and pyyaml, never needs the MCP SDK.
"""

import importlib.util
import pathlib

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "governance_gate", _SCRIPTS / "governance_gate.py"
)
gs = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(gs)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A tiny repo: one governing doc, one governed file, one ungoverned file."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/rules.md").write_text("the rules\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/t.py").write_text("a = 1\nb = 2\nc = 3\nb = 2\n")
    (tmp_path / "README.md").write_text("ungoverned\n")
    monkeypatch.setattr(gs, "REPO", tmp_path)
    monkeypatch.setattr(gs, "TIERS", {"scripts/": ("docs/rules.md",)})
    return tmp_path


def _keys(rel="scripts/t.py"):
    """Docs receipt, then the file receipt it unlocks — the intended two-step."""
    docs_key = gs.current_receipt_key("scripts/")
    gs.get_file(rel, docs_key)
    return docs_key, gs.current_edit_key(rel)


# --------------------------------------------------------------------- tiers


def test_governed_and_ungoverned_paths_resolve(repo) -> None:
    """A path under a tier prefix resolves to it; anything else is ungoverned."""
    assert gs.resolve_tier("scripts/t.py") == "scripts/"
    assert gs.resolve_tier("README.md") is None


def test_specific_tier_wins_over_general(monkeypatch, repo) -> None:
    """Ordering matters: a file with its own tier must not fall into the broader one."""
    monkeypatch.setattr(
        gs,
        "TIERS",
        {"scripts/special.py": ("docs/rules.md",), "scripts/": ("docs/rules.md",)},
    )
    assert gs.resolve_tier("scripts/special.py") == "scripts/special.py"
    assert gs.resolve_tier("scripts/other.py") == "scripts/"


# ------------------------------------------------------------ key derivation


def test_key_is_stable_within_a_window_and_rotates_across(repo) -> None:
    """The clock enters the key by bucket, so it holds for the window and then turns."""
    now = 10_000.0
    assert gs.current_receipt_key("scripts/", now) == gs.current_receipt_key(
        "scripts/", now + 1
    )
    assert gs.current_receipt_key("scripts/", now) != gs.current_receipt_key(
        "scripts/", now + gs.ROTATION_SECONDS
    )


def test_previous_window_is_honoured_as_grace(repo) -> None:
    """A read just before rotation must not strand the write that follows it."""
    now = 10_000.0
    previous = gs.current_receipt_key("scripts/", now - gs.ROTATION_SECONDS)
    assert previous in gs.valid_receipt_keys("scripts/", now)


def test_editing_a_governing_doc_invalidates_outstanding_keys(repo) -> None:
    """The divergence from ha-mcp: change the rules and every outstanding key dies."""
    docs_key, edit_key = _keys()
    (repo / "docs/rules.md").write_text("the rules, amended\n")
    assert docs_key not in gs.valid_receipt_keys("scripts/")
    assert edit_key not in gs.valid_edit_keys("scripts/t.py")


def test_the_two_key_kinds_are_not_interchangeable(repo) -> None:
    """A docs receipt proves the rules were read, not the file; it unlocks no patch."""
    docs_key, _ = _keys()
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/t.py", "a = 1", "a = 9", docs_key)


# ------------------------------------------------------- reading before writing


def test_reading_a_governed_file_requires_the_docs_receipt(repo) -> None:
    """The rules are read before the file, never instead of it."""
    with pytest.raises(gs.GateError):
        gs.get_file("scripts/t.py", None)
    out = gs.get_file("scripts/t.py", gs.current_receipt_key("scripts/"))
    assert "c = 3" in out, "the whole file must be emitted, not a fragment"
    assert gs.current_edit_key("scripts/t.py") in out


def test_patch_is_refused_without_a_file_receipt_and_allowed_with_one(repo) -> None:
    """Patching cheaply is fine; patching something unread is the failure being prevented."""
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/t.py", "a = 1", "a = 9", None)
    assert (repo / "scripts/t.py").read_text().startswith("a = 1")

    _, edit_key = _keys()
    gs.patch_file("scripts/t.py", "a = 1", "a = 9", edit_key)
    assert (repo / "scripts/t.py").read_text().startswith("a = 9")


def test_a_file_receipt_dies_when_the_file_changes(repo) -> None:
    """Bound to content, so a stale key means the file moved under the reader."""
    _, edit_key = _keys()
    gs.patch_file("scripts/t.py", "a = 1", "a = 9", edit_key)
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/t.py", "c = 3", "c = 9", edit_key)


def test_a_receipt_for_one_file_does_not_unlock_another(repo) -> None:
    """The path is part of the key, so reading one file buys no write to its neighbour."""
    (repo / "scripts/other.py").write_text("z = 0\n")
    _, edit_key = _keys("scripts/t.py")
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/other.py", "z = 0", "z = 1", edit_key)


# ------------------------------------------------------------------ patching


def test_an_ambiguous_old_string_is_refused(repo) -> None:
    """Two matches means the gate would be choosing; that is the caller's job."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError) as excinfo:
        gs.patch_file("scripts/t.py", "b = 2", "b = 9", edit_key)
    assert "2 times" in str(excinfo.value)
    assert (repo / "scripts/t.py").read_text().count("b = 2") == 2


def test_a_new_file_can_be_created_through_the_gate(repo) -> None:
    """Otherwise a governed directory becomes unextendable once other writers are denied."""
    docs_key = gs.current_receipt_key("scripts/")
    gs.get_file("scripts/new.py", docs_key)
    gs.patch_file(
        "scripts/new.py", "", "fresh = 1\n", gs.current_edit_key("scripts/new.py")
    )
    assert (repo / "scripts/new.py").read_text() == "fresh = 1\n"


def test_an_empty_old_string_will_not_clobber_an_existing_file(repo) -> None:
    """Creation is the only empty-old_string case; anything else is a whole-file overwrite."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/t.py", "", "clobbered\n", edit_key)
    assert (repo / "scripts/t.py").read_text().startswith("a = 1")


def test_an_absent_old_string_is_refused(repo) -> None:
    """No match means the caller's picture of the file is wrong; nothing is written."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError):
        gs.patch_file("scripts/t.py", "nowhere", "somewhere", edit_key)


def test_the_report_shows_the_actual_diff(repo) -> None:
    """Counts prove volume, not correctness: the changed lines themselves are the evidence."""
    _, edit_key = _keys()
    out = gs.patch_file("scripts/t.py", "a = 1", "a = 9\nextra = 1", edit_key)
    assert "+2 -1" in out
    assert "-a = 1" in out and "+a = 9" in out and "+extra = 1" in out
    assert "b = 2" in out, (
        "surrounding context must be shown, not just the changed lines"
    )


def test_the_report_says_so_when_nothing_changed(repo) -> None:
    """A replacement identical to the original must not read as a successful edit."""
    _, edit_key = _keys()
    out = gs.patch_file("scripts/t.py", "a = 1", "a = 1", edit_key)
    assert "no textual change" in out


# ------------------------------------------------------------------- refusals


def test_refusal_never_contains_a_key(repo) -> None:
    """A refusal that leaks the key hands over exactly what the gate withholds."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError) as excinfo:
        gs.patch_file("scripts/t.py", "a = 1", "a = 9", "wrong")
    assert edit_key not in str(excinfo.value)
    assert gs.current_receipt_key("scripts/") not in str(excinfo.value)


def test_paths_outside_the_repo_are_refused(repo) -> None:
    """Every spelling of an escape resolves outside the repo and is refused."""
    for attempt in ("../escape.txt", "/etc/passwd", "scripts/../../escape.txt"):
        with pytest.raises(gs.GateError):
            gs.safe_relpath(attempt)


def test_a_symlink_out_of_the_repo_is_refused(repo) -> None:
    """resolve() follows the link, so the escape is caught rather than written through."""
    outside = repo.parent / "outside.txt"
    outside.write_text("original\n")
    (repo / "scripts/link.txt").symlink_to(outside)
    with pytest.raises(gs.GateError):
        gs.safe_relpath("scripts/link.txt")
    assert outside.read_text() == "original\n"


def test_ungoverned_files_are_not_writable_through_the_gate(repo) -> None:
    """The gate is not a general-purpose writer; ungoverned edits use the ordinary tools."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError):
        gs.patch_file("README.md", "ungoverned", "clobbered", edit_key)
    assert (repo / "README.md").read_text() == "ungoverned\n"


def test_unknown_tier_is_refused(repo) -> None:
    """A tier nothing governs has no docs to receipt; asking for one is refused."""
    with pytest.raises(gs.GateError):
        gs.get_docs("nope/")


# ----------------------------------------------------------------- fail open


def test_unreadable_governing_doc_fails_open(repo) -> None:
    """A broken doc makes the key unobtainable; bricking every edit would be worse."""
    (repo / "docs/rules.md").unlink()
    assert gs.current_receipt_key("scripts/") is None
    assert gs.valid_receipt_keys("scripts/") == set()
    result = gs.patch_file("scripts/t.py", "a = 1", "a = 9", None)
    assert "OPEN" in result
    assert (repo / "scripts/t.py").read_text().startswith("a = 9")


def test_emitted_docs_carry_the_key_and_the_content(repo) -> None:
    """One reply holds both the receipt and the rules it receipts."""
    out = gs.get_docs("scripts/")
    assert gs.current_receipt_key("scripts/") in out
    assert "the rules" in out


def test_the_old_tool_names_are_gone(repo) -> None:
    """A renamed tool that keeps its old alias is two names for one gate, and docs drift."""
    for old in ("get_governing_docs", "get_governed_file", "governed_edit"):
        assert not hasattr(gs, old), old


# --------------------------------------------------------------- rolling key


def test_a_patch_hands_back_the_key_for_the_file_it_just_wrote(repo) -> None:
    """Read once, patch many times: the reply carries the next key, so no re-read is needed.

    Eleven of thirteen reads of one file in a session were re-reads forced by a key that died
    on every patch. The server holds the bytes it just wrote and the caller saw the diff, so
    handing the next key back keeps the guarantee and drops the cost.
    """
    _, edit_key = _keys()
    out = gs.patch_file("scripts/t.py", "a = 1", "a = 9", edit_key)
    fresh = gs.current_edit_key("scripts/t.py")
    assert fresh in out and fresh != edit_key
    gs.patch_file("scripts/t.py", "c = 3", "c = 9", fresh)
    assert (repo / "scripts/t.py").read_text() == "a = 9\nb = 2\nc = 9\nb = 2\n"


# ------------------------------------------------------------ one function


_MODULE = '''\
"""A file shaped like the audit: independent checks, shared helpers, one registry."""
import re

LIMIT = 3


def _helper(x):
    return x * LIMIT


def check_one(repo):
    """First check."""
    return _helper(repo)


def check_two(repo):
    """Second check."""
    return re.sub("a", "b", repo)


CHECKS = (check_one, check_two)
'''


@pytest.fixture
def module(repo):
    """The audit-shaped module written into the governed tree, as its relative path."""
    (repo / "scripts/mod.py").write_text(_MODULE)
    return "scripts/mod.py"


def test_a_function_read_returns_it_with_everything_it_uses(module) -> None:
    """The server decides what the slice is, from the code, so it is never incomplete.

    Reading one check out of a thousand-line file is the cheap read the whole-file rule was
    written to forbid, because a hand-picked slice omits the context that made the line wrong.
    A slice the parser picks is different: the function, every module-level name it reaches,
    the imports, and the registry that lists it. Nothing the edit can touch is out of view.
    """
    docs_key = gs.current_receipt_key("scripts/")
    out = gs.get_function(module, "check_one", docs_key)
    for needed in (
        "def check_one",
        "def _helper",
        "LIMIT = 3",
        "import re",
        "CHECKS = (",
    ):
        assert needed in out, needed
    assert "def check_two" not in out, (
        "an unrelated function is not part of the closure"
    )
    assert gs.current_function_key(module, "check_one") in out


def test_a_function_key_unlocks_a_patch_inside_it_and_refuses_one_outside(
    module,
) -> None:
    """The key covers exactly the text returned; the rest of the file stays locked."""
    docs_key = gs.current_receipt_key("scripts/")
    gs.get_function(module, "check_one", docs_key)
    key = gs.current_function_key(module, "check_one")
    with pytest.raises(gs.GateError) as excinfo:
        gs.patch_file(module, 're.sub("a", "b", repo)', "repo", key)
    assert "outside" in str(excinfo.value)
    gs.patch_file(module, "return _helper(repo)", "return _helper(repo) + 1", key)
    assert "return _helper(repo) + 1" in (gs.REPO / module).read_text()


def test_a_function_key_dies_with_its_closure_and_survives_unrelated_edits(
    module,
) -> None:
    """Bound to the closure, not the file: an edit elsewhere must not force a re-read."""
    key = gs.current_function_key(module, "check_one")
    text = (gs.REPO / module).read_text()
    (gs.REPO / module).write_text(text.replace('"b", repo', '"c", repo'))
    assert gs.current_function_key(module, "check_one") == key
    (gs.REPO / module).write_text(text.replace("x * LIMIT", "x + LIMIT"))
    assert gs.current_function_key(module, "check_one") != key


def test_a_patch_with_a_function_key_hands_back_a_function_key(module) -> None:
    """The rolling key keeps the kind it was given: a function read stays function-scoped."""
    docs_key = gs.current_receipt_key("scripts/")
    gs.get_function(module, "check_one", docs_key)
    out = gs.patch_file(
        module,
        "return _helper(repo)",
        "return _helper(repo) + 1",
        gs.current_function_key(module, "check_one"),
    )
    fresh = gs.current_function_key(module, "check_one")
    assert fresh in out
    gs.patch_file(module, "return _helper(repo) + 1", "return _helper(repo) + 2", fresh)


def test_a_fixture_named_as_a_parameter_is_part_of_the_closure(repo) -> None:
    """A test reaches its fixtures by parameter name, never by a call, so names count too."""
    (repo / "scripts/test_x.py").write_text(
        "import pytest\n\n\n"
        "@pytest.fixture\ndef thing():\n    return 1\n\n\n"
        "def test_it(thing):\n    assert thing == 1\n"
    )
    out = gs.get_function(
        "scripts/test_x.py", "test_it", gs.current_receipt_key("scripts/")
    )
    assert "def thing" in out


def test_an_unknown_function_and_an_unparseable_file_are_refused(module) -> None:
    """No closure can be taken from a missing name or a file that does not parse."""
    docs_key = gs.current_receipt_key("scripts/")
    with pytest.raises(gs.GateError):
        gs.get_function(module, "check_nine", docs_key)
    (gs.REPO / module).write_text("def (\n")
    with pytest.raises(gs.GateError) as excinfo:
        gs.get_function(module, "check_one", docs_key)
    assert "get_file" in str(excinfo.value)


# --------------------------------------------------------------------- twins


@pytest.fixture
def twins(repo, monkeypatch):
    """A script and its shipped copy, byte-identical, both governed."""
    (repo / "tmpl/scripts").mkdir(parents=True)
    (repo / "tmpl/scripts/t.py").write_text((repo / "scripts/t.py").read_text())
    monkeypatch.setattr(gs, "TWIN_ROOT", "tmpl/")
    monkeypatch.setattr(
        gs, "TIERS", {"tmpl/": ("docs/rules.md",), "scripts/": ("docs/rules.md",)}
    )
    return repo


def test_a_twin_patch_lands_on_both_copies(twins) -> None:
    """The shipped copy is what integrations get; a fix that reaches only one is drift.

    Two fixes once landed in scripts/ and never reached templates/scripts/. The audit now
    catches that after the fact; this makes it impossible in the first place, and halves the
    reads, since the twin never has to be read separately.
    """
    _, edit_key = _keys()
    out = gs.patch_twins("scripts/t.py", "a = 1", "a = 9", edit_key)
    assert (twins / "scripts/t.py").read_text().startswith("a = 9")
    assert (twins / "scripts/t.py").read_text() == (
        twins / "tmpl/scripts/t.py"
    ).read_text()
    assert "tmpl/scripts/t.py" in out


def test_a_twin_patch_works_from_the_shipped_side(twins) -> None:
    """Either copy may be the one read; the patch reaches both regardless."""
    docs_key = gs.current_receipt_key("tmpl/")
    gs.get_file("tmpl/scripts/t.py", docs_key)
    gs.patch_twins(
        "tmpl/scripts/t.py", "a = 1", "a = 9", gs.current_edit_key("tmpl/scripts/t.py")
    )
    assert (twins / "scripts/t.py").read_text().startswith("a = 9")


def test_twins_that_already_differ_are_refused(twins) -> None:
    """Mirroring a patch onto a copy that has drifted would bury the drift, not fix it."""
    (twins / "tmpl/scripts/t.py").write_text("drifted\n")
    _, edit_key = _keys()
    with pytest.raises(gs.GateError) as excinfo:
        gs.patch_twins("scripts/t.py", "a = 1", "a = 9", edit_key)
    assert "differ" in str(excinfo.value)
    assert (twins / "scripts/t.py").read_text().startswith("a = 1")


def test_a_file_without_a_twin_is_refused(repo) -> None:
    """A file that ships nowhere has nothing to mirror to; patch_file is the right tool."""
    _, edit_key = _keys()
    with pytest.raises(gs.GateError):
        gs.patch_twins("scripts/t.py", "a = 1", "a = 9", edit_key)
    assert (repo / "scripts/t.py").read_text().startswith("a = 1")


# ------------------------------------------------------------------- gate id


def test_every_key_carries_the_gate_id(module) -> None:
    """A restart mints a new salt and a new id together, so the id says which gate spoke.

    Keys minutes old, docs and file unchanged, well inside the grace window, were all refused
    after the harness restarted the server, and the refusal read exactly like a stale read.
    The id in the key is what lets the two be told apart.
    """
    docs_key = gs.current_receipt_key("scripts/")
    _, edit_key = _keys()
    fn_key = gs.current_function_key(module, "check_one")
    for key in (docs_key, edit_key, fn_key):
        assert f"-{gs.GATE_ID}-" in key, key


def test_a_key_from_another_gate_is_refused_and_the_restart_is_named(
    monkeypatch, module
) -> None:
    """All four key checks name the restart when the key's id is not this gate's."""
    docs_key, edit_key = _keys()
    fn_key = gs.current_function_key(module, "check_one")
    born_as = gs.GATE_ID
    monkeypatch.setattr(gs, "GATE_ID", "dead")
    for call in (
        lambda: gs.patch_file("scripts/t.py", "a = 1", "a = 9", edit_key),
        lambda: gs.patch_file(module, "return _helper(repo)", "return 0", fn_key),
        lambda: gs.get_file("scripts/t.py", docs_key),
        lambda: gs.get_function(module, "check_one", docs_key),
    ):
        with pytest.raises(gs.GateError) as excinfo:
            call()
        assert f"minted by gate {born_as}" in str(excinfo.value)
        assert "restarted since" in str(excinfo.value)
    assert (gs.REPO / "scripts/t.py").read_text().startswith("a = 1")
    assert "return _helper(repo)" in (gs.REPO / module).read_text()


def test_a_stale_key_from_this_gate_is_not_blamed_on_a_restart(repo) -> None:
    """The other cause must not be misnamed either: same id means the content moved."""
    _, edit_key = _keys()
    (repo / "scripts/t.py").write_text("moved\n")
    with pytest.raises(gs.GateError) as excinfo:
        gs.patch_file("scripts/t.py", "moved", "back", edit_key)
    assert "has not restarted" in str(excinfo.value)
    assert "restarted since" not in str(excinfo.value)
    assert gs.GATE_ID in str(excinfo.value)


def test_a_missing_key_still_names_the_gate(repo) -> None:
    """Even with nothing to diagnose, the refusal says which gate is speaking."""
    with pytest.raises(gs.GateError) as excinfo:
        gs.get_file("scripts/t.py", None)
    assert gs.GATE_ID in str(excinfo.value)


def test_locate_returns_paths_and_never_a_line(repo) -> None:
    """A locate names the files a pattern occurs in and nothing of their content.

    A search that returns lines gets quoted as evidence; one that returns only paths
    cannot be, so the file has to be read. That is the whole difference between this and
    the shell grep the hook refuses.
    """
    (repo / "docs/other.md").write_text("no match here\n")
    out = gs.locate(r"b = 2")
    assert out == ["scripts/t.py"]
    assert "b = 2" not in "\n".join(out)


def test_locate_skips_scratch_and_git(repo) -> None:
    """`.tmp/`, `.git/` and caches are never candidates."""
    for d in (".tmp", ".git", "__pycache__"):
        (repo / d).mkdir()
        (repo / d / "x.py").write_text("b = 2\n")
    assert gs.locate(r"b = 2") == ["scripts/t.py"]


def test_locate_can_be_narrowed_to_a_prefix(repo) -> None:
    """`under` limits the walk to one subtree, so a broad pattern stays cheap."""
    (repo / "docs/rules.md").write_text("the rules\nb = 2\n")
    assert gs.locate(r"b = 2", under="docs/") == ["docs/rules.md"]


def test_locate_refuses_a_prefix_outside_the_repo(repo) -> None:
    """The walk never leaves the repository, like every other gate operation."""
    with pytest.raises(gs.GateError):
        gs.locate("x", under="../")


def test_find_files_matches_a_glob_by_name(repo) -> None:
    """Name search is the other half of locating: which files exist at all."""
    (repo / "scripts/u.py").write_text("")
    assert gs.find_files("scripts/*.py") == ["scripts/t.py", "scripts/u.py"]
    assert gs.find_files("**/*.md") == ["README.md", "docs/rules.md"]


def test_find_files_refuses_a_glob_that_leaves_the_repo(repo) -> None:
    """`../*` reached the home directory on first review; a glob is a path too."""
    (repo.parent / "outside.md").write_text("")
    with pytest.raises(gs.GateError):
        gs.find_files("../*.md")
    with pytest.raises(gs.GateError):
        gs.find_files("scripts/../../*.md")


def test_every_skipped_directory_is_skipped_by_both_tools(repo) -> None:
    """All six never-candidate directories, for the name search and the content search."""
    for d in sorted(gs._SKIPPED_DIRS):
        (repo / d).mkdir()
        (repo / d / "x.py").write_text("b = 2\n")
    assert gs.locate(r"b = 2") == ["scripts/t.py"]
    assert gs.find_files("**/*.py") == ["scripts/t.py"]
