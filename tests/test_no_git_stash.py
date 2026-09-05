"""Unit tests for scripts/no_git_stash.py, the hook that refuses a stash in the sandbox.

Load the standalone script by path; it is not an importable package.
"""

import importlib.util
import io
import json
import pathlib

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "no_git_stash", _SCRIPTS / "no_git_stash.py"
)
ngs = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(ngs)


@pytest.mark.parametrize(
    "command",
    [
        "git stash",
        "git stash pop",
        "git stash push -m wip",
        "git stash apply stash@{0}",
        "git -C /home/x/repo stash",
        "git --git-dir=.git stash save",
        "cd repo && git stash -q && pytest",
        "sudo git stash",
        "/usr/bin/git stash",
    ],
)
def test_a_stash_that_moves_files_is_refused(command) -> None:
    """Every form that writes the working tree, wherever git sits in the command."""
    assert ngs.stashes(command)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git stash list",
        "git stash drop",
        "git stash show -p stash@{0}",
        "git commit -m 'stash the old notes'",
        "echo 'never git stash here'",
        "git show HEAD:scripts/x.py > .tmp/x.py",
        "python3 - <<'EOF'\nprint('git stash')\nEOF",
    ],
)
def test_ordinary_git_and_prose_are_allowed(command) -> None:
    """Reading a stash, dropping one, and the word inside a string or heredoc pass.

    Drop and list are how a half-applied stash is cleaned up, so blocking them would
    leave the recovery to the user; neither touches the working tree.
    """
    assert not ngs.stashes(command)


def _run(monkeypatch, capsys, payload: dict) -> dict | None:
    """Feed one hook payload through main and return what it printed, parsed."""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert ngs.main() == 0
    out = capsys.readouterr().out
    return json.loads(out) if out else None


def test_the_hook_denies_with_the_recovery_in_the_reason(monkeypatch, capsys) -> None:
    """The refusal says what to do instead, because the agent reads nothing else."""
    out = _run(monkeypatch, capsys, {"tool_input": {"command": "git stash"}})
    assert out is not None
    decision = out["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "git show HEAD:" in decision["permissionDecisionReason"]
    assert "stash drop" in decision["permissionDecisionReason"]


def test_the_hook_stays_silent_for_anything_else(monkeypatch, capsys) -> None:
    """No output means allow; a hook that prints on the happy path is noise."""
    assert _run(monkeypatch, capsys, {"tool_input": {"command": "git status"}}) is None
    assert _run(monkeypatch, capsys, {"tool_input": {}}) is None
