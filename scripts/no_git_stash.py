#!/usr/bin/env python3
# skill-audit: local-tool
"""PreToolUse hook: refuse a `git stash` that would move files, wherever it is buried.

The sandbox cannot write the governed directories, so a stash there half-applies: the
ungoverned files revert, the governed ones keep their edits, and the pop aborts with the
entry kept. That lost an edit once, mid-task, while the tree looked clean. A stash is
never the right tool here anyway — comparing against HEAD is `git show HEAD:<path>` into
`.tmp/`, or `git diff`.

Same tokeniser as no_shell_search.py, for the same reasons: a quoted string collapses to
one token, so `git commit -m 'stash it'` passes and `xargs git stash` does not; heredoc
bodies are prose and are stripped first. `git` is found by its last path segment, then
the first token that is neither an option nor an option's argument is the subcommand.

`list`, `drop` and `show` are allowed: they read or discard an entry without touching the
working tree, and drop is how a half-applied stash is cleaned up.
"""

import json
import re
import shlex
import sys

# Global git options that consume the next token, so it is not the subcommand.
_TAKES_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_HARMLESS = {"list", "drop", "show"}

# Heredoc bodies are prose, not shell words: strip <<EOF ... EOF before tokenising.
_HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*(?P=tag)\s*$",
    re.DOTALL | re.MULTILINE,
)

REASON = (
    "[no-git-stash] Blocked git stash. The sandbox cannot write the governed directories, "
    "so a stash half-applies: ungoverned files revert, governed ones keep their edits, and "
    "the pop aborts — an edit was lost that way once. To compare against HEAD use "
    "`git show HEAD:<path>` into .tmp/, or `git diff`. If an entry already exists, recover "
    "with `git checkout stash@{0} -- <file>` and then `git stash drop`, which is allowed."
)


def stashes(command: str) -> bool:
    """Whether the command runs a git stash subcommand that writes the working tree."""
    stripped = _HEREDOC.sub(" ", command)
    try:
        tokens = shlex.split(stripped, comments=True)
    except ValueError:
        # Unbalanced quotes: fall back to whitespace splitting rather than allowing blindly.
        tokens = stripped.split()
    in_git = False
    skip = False
    for i, token in enumerate(tokens):
        if skip:
            skip = False
            continue
        if token.split("/")[-1] == "git":
            in_git = True
            continue
        if not in_git:
            continue
        if token in _TAKES_ARG:
            skip = True
            continue
        if token.startswith("-"):
            continue
        in_git = False
        if token == "stash":
            action = tokens[i + 1] if i + 1 < len(tokens) else ""
            if action not in _HARMLESS:
                return True
    return False


def main() -> int:
    """Read the hook payload on stdin and deny the call when it carries a stash."""
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # Unparseable input is the harness's problem, not grounds to block.
    if not stashes((payload.get("tool_input") or {}).get("command", "")):
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": REASON,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
