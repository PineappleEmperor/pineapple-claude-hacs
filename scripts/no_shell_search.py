#!/usr/bin/env python3
# skill-audit: local-tool
"""PreToolUse hook: refuse shell search tools, wherever they are buried.

Searching is not verifying. An empty result is not evidence a thing is fixed — that mistake
shipped a defect as resolved in this repo twice. The Grep TOOL locates candidate files; reading
them is what settles anything.

WHY EVERY TOKEN, NOT JUST THE COMMAND WORD. The point is to catch a search buried inside another
command: `xargs grep`, `sudo grep`, `find . -exec grep {} ;`, a pipeline stage, a subshell. An
earlier version of this hook only inspected the first word of each segment, which let every one
of those through — precisely the cases worth catching.

WHY TOKENISE AT ALL. The version before that matched the bare word anywhere in the command
string and misfired three times in one session: on the identifier `ack_key` (contains `ack`), on
the word appearing in prose being written into a docstring, and on a quoted argument containing
a pipe. Each was legitimate work refused, and a guard that cries wolf gets switched off.

`shlex` resolves both: a quoted string collapses to ONE token, so `echo 'mentions grep'` yields
`grep` nowhere, while `xargs grep foo` yields it plainly. Heredoc bodies are stripped first,
because their contents are document text rather than shell words.

Known and accepted misses: `a|grep` written with no spaces, and a search invoked through a
variable. Both require deliberately routing around the guard rather than drifting into it, which
is the failure this addresses.
"""

import json
import re
import shlex
import sys

BANNED = {"grep", "rg", "egrep", "fgrep", "ag", "ack"}

# Heredoc bodies are prose, not shell words: strip <<EOF ... EOF before tokenising.
_HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*(?P=tag)\s*$",
    re.DOTALL | re.MULTILINE,
)

REASON = (
    "[read-dont-search] Blocked {tool}. A search LOCATES; it does not VERIFY, and an empty "
    "result is not evidence a thing is fixed — that mistake shipped a defect as resolved in "
    "this repo twice. This fires wherever the search is, including buried in a pipeline, "
    "xargs, sudo or find -exec. To find candidate files use the governance gate's `locate` "
    "(regex, paths only) or `find_files` (glob), or the Grep tool where the session has "
    "one; then READ each candidate in full before concluding anything. To filter "
    "structured DATA use jq or python; to understand SOURCE, open it."
)


def banned_tool(command: str) -> str | None:
    """First banned search tool appearing as a shell token, or None."""
    stripped = _HEREDOC.sub(" ", command)
    try:
        tokens = shlex.split(stripped, comments=True)
    except ValueError:
        # Unbalanced quotes: fall back to whitespace splitting rather than allowing blindly.
        tokens = stripped.split()
    for token in tokens:
        if token.split("/")[-1] in BANNED:
            return token.split("/")[-1]
    return None


def main() -> int:
    """Read the hook payload on stdin and deny the call when it carries a search."""
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # Unparseable input is the harness's problem, not grounds to block.
    found = banned_tool((payload.get("tool_input") or {}).get("command", ""))
    if not found:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": REASON.format(tool=found),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
