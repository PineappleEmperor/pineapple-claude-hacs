#!/usr/bin/env python3
# skill-audit: local-tool
"""MCP transport for the governed-edit gate.

Thin on purpose: every decision lives in governance_gate.py, which has no dependencies and is
what the test suite imports. This file only speaks MCP, using the official SDK rather than a
hand-rolled JSON-RPC loop — protocol framing, capability negotiation and error semantics are
the SDK's job to keep current, not ours. (Point in evidence: the SDK is 2.x, where FastMCP was
renamed MCPServer; a hand-rolled loop would have drifted silently instead of failing loudly.)

The tools are one workflow, in order, and the order is the point:
    get_docs(tier)                     -> ReceiptKey. The rules.
    get_file(path, Receipt)            -> the WHOLE file, plus an EditKey bound to its bytes.
    get_function(path, name, Receipt)  -> one function with everything it uses, plus an
                                          EditKey bound to that text alone.
    patch_file(path, old, new, Edit)   -> one exact replacement, reported as a diff, plus the
                                          EditKey for the next patch.

Named the way ha-mcp names its tools: a plain verb and noun, get/patch pairs, no adjective
about governance in the name because the docs the first tool returns are where that lives.

Thin does not mean transparent: this file must be kept in step with the gate's signatures. It
once lagged them — the server still published a whole-file patch tool taking `content` after
the gate had moved to patching, so every live call raised an argument error. The live tool
schema is the contract callers see; a stale one is a broken gate that looks installed.

Run via the repo venv, which carries the SDK:
    .venv/bin/python scripts/governance_server.py
"""

import importlib.util
import pathlib

from mcp.server.mcpserver import MCPServer

_GATE = pathlib.Path(__file__).resolve().parent / "governance_gate.py"
_spec = importlib.util.spec_from_file_location("governance_gate", _GATE)
gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gate)

mcp = MCPServer("governance")


@mcp.tool()
def get_docs(tier: str) -> str:
    """Emit the ReceiptKey for a tier, then the docs that govern it.

    The only source of that key. Step one of three: read this before touching anything under
    the tier.
    """
    try:
        return gate.get_docs(tier)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"


@mcp.tool()
def get_file(path: str, ReceiptKey: str | None = None) -> str:
    """Emit a governed file in full, plus the EditKey required to patch it.

    Step two of three. Requires the tier's ReceiptKey, so the rules are read before the file
    rather than instead of it. The EditKey is bound to the bytes returned here, so it dies the
    moment the file changes.
    """
    try:
        return gate.get_file(path, ReceiptKey)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"


@mcp.tool()
def get_function(path: str, name: str, ReceiptKey: str | None = None) -> str:
    """Emit one function with everything it uses, plus an EditKey that unlocks only that text.

    The cheaper read for a file that is a list of functions. The parser picks the slice: the
    function, every module-level name it reaches, the imports, and the registry that lists it.
    A patch outside that text is refused; a change to any of it kills the key. Serves every
    governed Python file, tests included, where the fixtures a test names come along with it.
    """
    try:
        return gate.get_function(path, name, ReceiptKey)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"


@mcp.tool()
def patch_file(
    path: str, old_string: str, new_string: str, EditKey: str | None = None
) -> str:
    """Replace one exact, unique occurrence of old_string, returning the resulting diff.

    Last step. Requires the EditKey from get_file or get_function, which is only obtainable
    by reading that text — patching cheaply is fine, patching something unread is the failure
    this exists to prevent. Refuses when old_string is absent or appears more than once rather
    than choosing for you. The reply ends with the EditKey for the next patch, so one read
    serves many patches.
    """
    try:
        return gate.patch_file(path, old_string, new_string, EditKey)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"


@mcp.tool()
def patch_twins(
    path: str, old_string: str, new_string: str, EditKey: str | None = None
) -> str:
    """Apply one patch to a script or test and to its shipped copy under templates/.

    Same key, same rules as patch_file, applied to both copies, which must already be
    byte-identical — twins that have drifted are refused so the drift is fixed rather than
    buried. Saves the second read, and makes a fix that reaches only one copy impossible.
    """
    try:
        return gate.patch_twins(path, old_string, new_string, EditKey)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"


@mcp.tool()
def locate(pattern: str, under: str = "") -> str:
    """Name the files whose text matches a regex. Paths only, never a matching line.

    The sanctioned search: it can tell you where to read and nothing else, so its output
    cannot be quoted as evidence and an empty result cannot be read as "fixed". Skips .git,
    .tmp, caches and environments; `under` narrows the walk to one repo-relative prefix.
    Read every path it returns, in full, before concluding anything.
    """
    try:
        hits = gate.locate(pattern, under)
    except gate.GateError as exc:
        return f"REFUSED: {exc}"
    return (
        "\n".join(hits) if hits else "no file matches; that is not evidence of anything"
    )


@mcp.tool()
def find_files(glob: str) -> str:
    """Name the files matching a glob by path, e.g. `scripts/*.py` or `**/*.md`."""
    hits = gate.find_files(glob)
    return "\n".join(hits) if hits else "no file matches"


if __name__ == "__main__":
    mcp.run()
