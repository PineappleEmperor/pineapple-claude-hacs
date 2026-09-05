#!/usr/bin/env python3
# skill-audit: local-tool
"""Read-receipt gate over this repo's own governing docs — pure logic, no dependencies.

Transport lives in governance_server.py so this module stays importable by the test suite in
CI, which installs only pytest and pyyaml.

Modelled on ha-mcp's strict best-practices gate (`src/ha_mcp/strict_bps.py`). The shape is
theirs; four things differ because our situation differs.

WHY A SEPARATE PROCESS AT ALL. A gate whose secret lives anywhere the gated party can read is
theatre. ha-mcp puts the salt in a server on another host. We cannot, so the equivalent boundary
is this process: spawned by the harness, outside the agent's sandbox and PID namespace, so its
memory is unreachable and its salt unguessable. Measured, not assumed — a harness child writes
paths the agent's shell gets `Read-only file system` on, and sees 116 PIDs against the agent's 5.

WHAT DIFFERS FROM ha-mcp:
  * The key mixes the governing docs' CONTENT hash alongside salt and clock. Theirs need not:
    their guide ships with their server. Ours change under us, so editing a governing doc must
    invalidate outstanding keys for the tiers it governs.
  * Keys are per-TIER. The corpus is ~2,000 lines; emitting all of it on every gate would be
    unusable, so each governed path maps to the docs that govern it. Same idea as their
    STRICT_BPS_GATED_TOOLS mapping a tool to one reference file.
  * The gated operation is a file write rather than an HA config write.
  * TWO receipts, not one. The docs receipt proves the rules were read; a second receipt, bound
    to the target file's own bytes, proves the WHOLE FILE was read before it was patched.
    Whole-file rewrites forced that reading implicitly and were the original design here.
    Patching is cheaper and avoids transcription slips across hundreds of untouched lines, but
    on its own it would restore the exact failure this repo already suffered: locate a line,
    replace it in isolation, never see the context that made it wrong. The file receipt buys
    the cheapness back without buying the failure.

WHAT IS COPIED DELIBERATELY:
  * Plain-English key prefixes. An opaque token made an agent read the round-trip as prompt
    injection and talk its user into disabling the gate (ha-mcp #1924).
  * One emitter, one validator per key. A refusal that leaks the key defeats the gate.
  * Fail OPEN where the key is unobtainable (a governing doc unreadable) so a broken doc cannot
    brick every edit. Fail CLOSED where intent is unclear (path outside the repo, unknown tier,
    ambiguous match): wrongly refusing costs one confusing error, wrongly allowing costs the gate.
"""

import ast
import difflib
import hashlib
import hmac
import os
import pathlib
import re
import secrets
import time

REPO = pathlib.Path(__file__).resolve().parents[1]

RECEIPT_PREFIX = "I-HAVE-READ-THE-GOVERNING-DOCS"
EDIT_PREFIX = "I-HAVE-READ-THE-WHOLE-FILE"
_SALT = secrets.token_hex(8)
# Four hex characters carried by every key and named in every key refusal. The salt dies with
# the process, so a restart kills every outstanding key at once — and without this the refusal
# read exactly like a stale read or an hour rollover. Observed: keys minutes old, nothing
# changed, all refused, cause unguessable. Now a key from another gate says so.
GATE_ID = secrets.token_hex(2)
ROTATION_SECONDS = int(os.environ.get("GOVERNANCE_ROTATION_SECONDS", "3600"))

# Governed path prefix -> the docs that govern it. FIRST match wins, so specific before general.
TIERS: dict[str, tuple[str, ...]] = {
    # The governing docs govern THEMSELVES, via the doc about how changes are made. Without
    # this the gate is trivially defeated: the docs were writable by ordinary means, and since
    # an unreadable governing doc fails the gate OPEN, deleting one bought a keyless write.
    # Demonstrated end-to-end — a governing doc moved aside, then the search guard disarmed
    # through the live server with no key at all.
    "docs/workflow-map.md": (
        "plugins/ha/skills/ha-integration/reference/discipline.md",
    ),
    "plugins/ha/skills/ha-integration/reference/": (
        "plugins/ha/skills/ha-integration/reference/discipline.md",
    ),
    "docs/backlog.md": ("plugins/ha/skills/ha-integration/reference/discipline.md",),
    ".github/workflows/": (
        "docs/workflow-map.md",
        "plugins/ha/skills/ha-integration/reference/github-actions.md",
    ),
    "plugins/ha/skills/ha-integration/templates/.github/workflows/": (
        "docs/workflow-map.md",
        "plugins/ha/skills/ha-integration/reference/github-actions.md",
    ),
    "plugins/ha/skills/ha-integration/templates/": (
        "plugins/ha/skills/ha-integration/reference/scaffold.md",
    ),
    "scripts/": (
        "plugins/ha/skills/ha-integration/reference/audit.md",
        "plugins/ha/skills/ha-integration/reference/testing.md",
    ),
    "tests/": (
        "plugins/ha/skills/ha-integration/reference/audit.md",
        "plugins/ha/skills/ha-integration/reference/testing.md",
    ),
}


class GateError(Exception):
    """Refusal that reaches the caller as a tool error, never as a crash."""


def resolve_tier(rel: str) -> str | None:
    """First matching tier for a repo-relative path, or None when ungoverned."""
    for prefix in TIERS:
        if rel == prefix or rel.startswith(prefix):
            return prefix
    return None


def _docs_hash(tier: str) -> str | None:
    """Hash of the tier's governing docs, or None if any is unreadable (fail-open signal)."""
    h = hashlib.sha256()
    for rel in TIERS[tier]:
        try:
            h.update((REPO / rel).read_bytes())
        except OSError:
            return None
    return h.hexdigest()


def _file_hash(rel: str) -> str:
    """Hash of the target's current bytes; a missing file counts as empty so it can be created."""
    try:
        return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
    except OSError:
        return hashlib.sha256(b"").hexdigest()


def _key_for(tier: str, bucket: int, docs: str) -> str:
    mac = hmac.new(_SALT.encode(), f"{bucket}:{tier}:{docs}".encode(), hashlib.sha256)
    return f"{RECEIPT_PREFIX}-{GATE_ID}-{mac.hexdigest()[:8]}"


def _edit_key_for(tier: str, rel: str, bucket: int, docs: str, body: str) -> str:
    mac = hmac.new(
        _SALT.encode(), f"{bucket}:{tier}:{docs}:{rel}:{body}".encode(), hashlib.sha256
    )
    return f"{EDIT_PREFIX}-{GATE_ID}-{mac.hexdigest()[:8]}"


def _minted_by(key: str | None) -> str:
    """The gate id a key carries — the segment before the MAC — or '' when it carries none."""
    parts = (key or "").split("-")
    minted = parts[-2] if len(parts) >= 3 else ""
    return minted if len(minted) == 4 and set(minted) <= set("0123456789abcdef") else ""


def _cause(key: str | None) -> str:
    """Why a key failed, as far as the gate can tell. A restart names itself; nothing else may.

    Appended to every key refusal. Without it the three causes — never read, read before a
    restart, read before the content moved — produced one message, and the caller could only
    guess which re-read would help.
    """
    minted = _minted_by(key)
    if minted and minted != GATE_ID:
        return (
            f" That key was minted by gate {minted}; this is gate {GATE_ID}, so the server has "
            f"restarted since and every key issued before it is dead. Re-read to mint new ones."
        )
    if minted:
        return (
            f" This is gate {GATE_ID}, the one that minted the key, so the process has not "
            f"restarted: the content the key was bound to has changed."
        )
    return f" This is gate {GATE_ID}."


def current_receipt_key(tier: str, now: float | None = None) -> str | None:
    """The tier's docs key for this rotation window, or None when a doc is unreadable."""
    docs = _docs_hash(tier)
    if docs is None:
        return None
    bucket = int((time.time() if now is None else now) // ROTATION_SECONDS)
    return _key_for(tier, bucket, docs)


def valid_receipt_keys(tier: str, now: float | None = None) -> set[str]:
    """Current key plus the previous rotation's, so a read just before rotation still counts."""
    docs = _docs_hash(tier)
    if docs is None:
        return set()
    t = time.time() if now is None else now
    return {
        _key_for(tier, int(t // ROTATION_SECONDS), docs),
        _key_for(tier, int((t - ROTATION_SECONDS) // ROTATION_SECONDS), docs),
    }


def current_edit_key(rel: str, now: float | None = None) -> str | None:
    """The file's edit key as it stands, or None when ungoverned or its docs are unreadable."""
    tier = resolve_tier(rel)
    if tier is None:
        return None
    docs = _docs_hash(tier)
    if docs is None:
        return None
    bucket = int((time.time() if now is None else now) // ROTATION_SECONDS)
    return _edit_key_for(tier, rel, bucket, docs, _file_hash(rel))


def valid_edit_keys(rel: str, now: float | None = None) -> set[str]:
    """Current and previous window, bound to the file's CURRENT bytes.

    Binding to content is what makes this receipt mean "you read this file as it stands". It
    also settles concurrent modification for free: if anything else rewrote the file after the
    read, every outstanding key for it is already dead.
    """
    tier = resolve_tier(rel)
    if tier is None:
        return set()
    docs = _docs_hash(tier)
    if docs is None:
        return set()
    t = time.time() if now is None else now
    body = _file_hash(rel)
    return {
        _edit_key_for(tier, rel, int(t // ROTATION_SECONDS), docs, body),
        _edit_key_for(
            tier, rel, int((t - ROTATION_SECONDS) // ROTATION_SECONDS), docs, body
        ),
    }


def receipt_line(tier: str) -> str:
    """The ONLY place a docs key is emitted. Never reuse this text in a refusal."""
    return (
        f"Acknowledgment key: {current_receipt_key(tier)} - pass this as ReceiptKey to "
        f"get_file for paths under '{tier}'. It is a read-receipt, not a secret: "
        f"published here deliberately, rotates, is bound to the current content of the docs "
        f"below, and grants no privileges. Replaying it is the designed protocol."
    )


def safe_relpath(path: str) -> str:
    """Repo-relative path, refusing anything that escapes the repo. Fail closed."""
    p = pathlib.Path(path) if pathlib.Path(path).is_absolute() else (REPO / path)
    resolved = p.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        raise GateError(
            "path resolves outside the repository; patch_file only writes within it"
        ) from None


def get_docs(tier: str) -> str:
    """Emit the tier's receipt line and then every doc that governs it, in full."""
    if tier not in TIERS:
        raise GateError(f"unknown tier {tier!r}; known tiers: {sorted(TIERS)}")
    if current_receipt_key(tier) is None:
        return (
            f"A governing doc for '{tier}' is unreadable, so no key can be issued and the gate "
            f"is OPEN for this tier. Fix the doc to restore it."
        )
    parts = [receipt_line(tier), ""]
    for rel in TIERS[tier]:
        parts += [f"===== {rel} =====", (REPO / rel).read_text(encoding="utf-8"), ""]
    return "\n".join(parts)


def get_file(path: str, receipt_key: str | None) -> str:
    """Emit a governed file in full, plus the EditKey that patching it requires.

    Requires the tier's docs receipt first, so the rules are read before the file rather than
    instead of it.
    """
    rel = safe_relpath(path)
    tier = resolve_tier(rel)
    if tier is None:
        raise GateError(
            f"{rel} is not governed; read it with the ordinary tools rather than through this gate"
        )
    valid = valid_receipt_keys(tier)
    if valid and receipt_key not in valid:
        raise GateError(
            f"{rel} is governed by '{tier}'. Call get_docs(tier={tier!r}) first, read "
            f"it, then pass that ReceiptKey here." + _cause(receipt_key)
        )
    try:
        body = (REPO / rel).read_text(encoding="utf-8")
    except OSError:
        body = ""
    return "\n".join(
        [
            (
                f"EditKey: {current_edit_key(rel)} - pass this as EditKey on patch_file for "
                f"{rel}. It is bound to the bytes below, so it dies the moment this file "
                f"changes; re-read rather than resending a previous value."
            ),
            "",
            f"===== {rel} ({len(body.splitlines())} lines) =====",
            body,
        ]
    )


FUNCTION_PREFIX = "I-HAVE-READ-THE-FUNCTION"


def _closure(source: str, name: str, rel: str) -> list[tuple[int, int, str]]:
    """The segments of `source` a patch to `name` may touch, as (start, end, label), 1-based.

    The function itself; every module-level function, class or constant it reaches, taken
    transitively so a helper's own helpers come too; every import; and any module-level
    statement that names the function, which is how the registry tuple listing a check is
    brought in. Parameter names count as references, because a test reaches its fixtures
    that way and never by a call.

    This is the one slice of a file the whole-file rule allows. A hand-picked slice omits the
    context that made a line wrong, which is how this repo shipped a defect as fixed, twice.
    A slice the parser picks cannot omit anything the patch can reach.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise GateError(
            f"{rel} does not parse ({exc.msg} at line {exc.lineno}); read it with get_file"
        ) from None
    defs: dict[str, ast.stmt] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs[target.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs[node.target.id] = node
    if not isinstance(defs.get(name), (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise GateError(f"{rel} defines no function named {name!r}")

    wanted = {name}
    queue = [name]
    while queue:
        node = defs[queue.pop()]
        refs = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            refs |= {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
        for ref in sorted(refs):
            if ref in defs and ref not in wanted:
                wanted.add(ref)
                queue.append(ref)
    chosen_nodes = {id(defs[n]) for n in wanted}

    segments: list[tuple[int, int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            label = "imports"
        elif id(node) in chosen_nodes:
            label = getattr(node, "name", None) or "assignment"
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
            isinstance(n, ast.Name) and n.id == name for n in ast.walk(node)
        ):
            label = "registry"
        else:
            continue
        decorators = getattr(node, "decorator_list", [])
        start = min([node.lineno] + [d.lineno for d in decorators])
        segments.append((start, node.end_lineno or start, label))
    return segments


def _closure_text(source: str, segments: list[tuple[int, int, str]]) -> str:
    lines = source.splitlines()
    return "\n\n".join("\n".join(lines[s - 1 : e]) for s, e, _ in segments)


def _closure_hash(rel: str, name: str) -> str | None:
    """Hash of the function's closure as the file stands; None when it cannot be taken."""
    try:
        source = (REPO / rel).read_text(encoding="utf-8")
        segments = _closure(source, name, rel)
    except OSError, GateError:
        return None
    return hashlib.sha256(_closure_text(source, segments).encode()).hexdigest()


def _function_key_for(
    tier: str, rel: str, name: str, bucket: int, docs: str, body: str
) -> str:
    mac = hmac.new(
        _SALT.encode(),
        f"{bucket}:{tier}:{docs}:{rel}:fn:{name}:{body}".encode(),
        hashlib.sha256,
    )
    return f"{FUNCTION_PREFIX}-{name}-{GATE_ID}-{mac.hexdigest()[:8]}"


def current_function_key(rel: str, name: str, now: float | None = None) -> str | None:
    """The function's key over its closure as it stands, or None when it cannot be taken."""
    tier = resolve_tier(rel)
    if tier is None:
        return None
    docs = _docs_hash(tier)
    body = _closure_hash(rel, name)
    if docs is None or body is None:
        return None
    bucket = int((time.time() if now is None else now) // ROTATION_SECONDS)
    return _function_key_for(tier, rel, name, bucket, docs, body)


def valid_function_keys(rel: str, name: str, now: float | None = None) -> set[str]:
    """Current and previous window, bound to the closure's CURRENT text, not the file's.

    An edit elsewhere in the file leaves the key alive; that is the saving. An edit to anything
    the function reaches kills it; that is the guarantee.
    """
    tier = resolve_tier(rel)
    if tier is None:
        return set()
    docs = _docs_hash(tier)
    body = _closure_hash(rel, name)
    if docs is None or body is None:
        return set()
    t = time.time() if now is None else now
    return {
        _function_key_for(tier, rel, name, int(t // ROTATION_SECONDS), docs, body),
        _function_key_for(
            tier, rel, name, int((t - ROTATION_SECONDS) // ROTATION_SECONDS), docs, body
        ),
    }


def get_function(path: str, name: str, receipt_key: str | None) -> str:
    """Emit one function with everything it uses, plus an EditKey that unlocks only that text."""
    rel = safe_relpath(path)
    tier = resolve_tier(rel)
    if tier is None:
        raise GateError(
            f"{rel} is not governed; read it with the ordinary tools rather than through this gate"
        )
    valid = valid_receipt_keys(tier)
    if valid and receipt_key not in valid:
        raise GateError(
            f"{rel} is governed by '{tier}'. Call get_docs(tier={tier!r}) first, read "
            f"it, then pass that ReceiptKey here." + _cause(receipt_key)
        )
    try:
        source = (REPO / rel).read_text(encoding="utf-8")
    except OSError:
        raise GateError(
            f"{rel} does not exist; a new file is made with get_file then patch_file"
        ) from None
    segments = _closure(source, name, rel)
    lines = source.splitlines()
    spans = ", ".join(f"{s}-{e}" for s, e, _ in segments)
    parts = [
        (
            f"EditKey: {current_function_key(rel, name)} - pass this as EditKey on patch_file "
            f"for {rel}. It unlocks only the text below (lines {spans} of {len(lines)}): a "
            f"patch outside them is refused, and a change to any of them kills the key."
        ),
        "",
    ]
    for s, e, label in segments:
        parts += [f"===== {rel}:{s}-{e} {label} =====", "\n".join(lines[s - 1 : e]), ""]
    return "\n".join(parts)


def _inside(before: str, old_string: str, segments: list[tuple[int, int, str]]) -> bool:
    """Whether the unique match of old_string lies wholly within one returned segment."""
    idx = before.index(old_string)
    first = before.count("\n", 0, idx) + 1
    last = before.count("\n", 0, idx + len(old_string.rstrip("\n"))) + 1
    return any(s <= first and last <= e for s, e, _ in segments)


def _apply(before: str, old_string: str, new_string: str, rel: str) -> str:
    """Exact, unique replacement. Absence and ambiguity are refusals, never guesses.

    One special case: an empty old_string against an empty file CREATES it. Without this, a
    governed directory becomes unextendable the moment writes are denied elsewhere — every new
    script or test would be impossible to add through the only writer allowed to add it. An
    empty old_string against a file with content stays a refusal, because that is a whole-file
    clobber wearing a patch's clothes.
    """
    if not old_string:
        if before == "":
            return new_string
        raise GateError(
            f"old_string is empty but {rel} is not; pass the exact text to replace rather than "
            f"clobbering the file"
        )
    hits = before.count(old_string)
    if hits == 0:
        raise GateError(
            f"old_string does not appear in {rel}; re-read the file, because it is not what you "
            f"think it is"
        )
    if hits > 1:
        raise GateError(
            f"old_string appears {hits} times in {rel}; include enough surrounding lines to make "
            f"it unique rather than letting the gate choose one"
        )
    return before.replace(old_string, new_string)


def _report(before: str, after: str, rel: str) -> str:
    """The actual diff, so an unintended edit is visible the moment it lands.

    Counts alone prove volume, not correctness: "+1 -1" reads identically whether the right
    line changed or the wrong one did. The diff is the evidence, so it is returned in full —
    context included, never truncated. A change large enough to be unwieldy here is itself
    worth seeing, and a silent cap would hide exactly the case this exists to catch.
    """
    diff = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
            n=3,
        )
    )
    if not diff:
        return "  no textual change"
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    hunks = sum(1 for d in diff if d.startswith("@@"))
    return f"  {hunks} hunk(s), +{added} -{removed} lines\n" + "\n".join(diff)


def patch_file(
    path: str, old_string: str, new_string: str, edit_key: str | None
) -> str:
    """Replace one exact, unique occurrence of old_string, reporting what actually changed."""
    rel = safe_relpath(path)
    tier = resolve_tier(rel)
    if tier is None:
        raise GateError(
            f"{rel} is not governed; edit it with the ordinary tools rather than through this gate"
        )
    try:
        before = (REPO / rel).read_text(encoding="utf-8")
    except OSError:
        # A missing file is empty, not an error: creating one is a legitimate governed edit,
        # and its receipt is issued over the same empty-bytes hash get_file used.
        before = ""

    if not valid_receipt_keys(tier):
        # Fail open, as ha-mcp does when its skill content is missing: a broken governing doc
        # makes the key unobtainable, and bricking every edit is the worse failure.
        after = _apply(before, old_string, new_string, rel)
        (REPO / rel).write_text(after, encoding="utf-8")
        return (
            f"wrote {rel} (gate OPEN: a governing doc for '{tier}' is unreadable)\n"
            + _report(before, after, rel)
        )

    # A function key names its function in plain English; the name is what lets the gate
    # recompute the closure it was issued over and confine the patch to it.
    scope: str | None = None
    if (edit_key or "").startswith(FUNCTION_PREFIX + "-"):
        scope = edit_key[len(FUNCTION_PREFIX) + 1 :].rsplit("-", 2)[0]
        if edit_key not in valid_function_keys(rel, scope):
            raise GateError(
                f"{rel} is governed by '{tier}'. That function key is stale: {scope!r} or "
                f"something it uses has changed, or the file no longer parses. Call "
                f"get_function(path={rel!r}, name={scope!r}) again, or get_file for the whole "
                f"file, then retry with the EditKey it returns." + _cause(edit_key)
            )
    elif edit_key not in valid_edit_keys(rel):
        raise GateError(
            f"{rel} is governed by '{tier}'. Call get_docs(tier={tier!r}), then "
            f"get_file(path={rel!r}) and READ IT IN FULL, then retry with the EditKey "
            f"it returns. That key is bound to this file's current bytes, so a stale one means "
            f"the file moved under you - re-read rather than resending a previous value."
            + _cause(edit_key)
        )

    after = _apply(before, old_string, new_string, rel)
    if scope is not None and not _inside(
        before, old_string, _closure(before, scope, rel)
    ):
        raise GateError(
            f"old_string lies outside the text get_function returned for {scope!r} in {rel}; "
            f"read the function that contains it, or the whole file with get_file"
        )
    (REPO / rel).write_text(after, encoding="utf-8")
    # The key rolls forward: the caller read the file (or the function's closure) and has
    # just seen this diff, so it has read that text as it now stands. Without this every
    # second patch cost a re-read of the whole file — eleven of thirteen reads of one file in
    # a session were that.
    next_key = current_function_key(rel, scope) if scope else current_edit_key(rel)
    if next_key is None:
        tail = (
            f"\n{rel} no longer parses, or {scope!r} is gone; read it again with get_file "
            f"before patching further."
        )
    else:
        tail = (
            f"\nEditKey: {next_key} - for the next patch to {rel}; it is bound to the text as "
            f"now written, so it dies if anything else touches it."
        )
    return f"wrote {rel}\n" + _report(before, after, rel) + tail


# The shipped copies of scripts/ and tests/ live here; the audit's check_template_scripts_match
# fails the repo when a pair differs by a byte.
TWIN_ROOT = "plugins/ha/skills/ha-integration/templates/"


def twin_of(rel: str) -> str | None:
    """The shipped copy of a repo script or test, or the repo copy of a shipped one."""
    for sub in ("scripts/", "tests/"):
        if rel.startswith(TWIN_ROOT + sub):
            return rel[len(TWIN_ROOT) :]
        if rel.startswith(sub):
            return TWIN_ROOT + rel
    return None


# Never candidates for a locate: version control, scratch, caches, environments.
_SKIPPED_DIRS = {
    ".git",
    ".tmp",
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
}
_LOCATE_CAP = 200


def _walk(under: str) -> list[pathlib.Path]:
    """Every file under a repo-relative prefix, skipping what is never a candidate."""
    start = REPO / safe_relpath(under) if under else REPO
    found: list[pathlib.Path] = []
    for path in sorted(start.rglob("*")):
        if not path.is_file():
            continue
        if _SKIPPED_DIRS & set(path.relative_to(REPO).parts[:-1]):
            continue
        found.append(path)
    return found


def locate(pattern: str, under: str = "") -> list[str]:
    """Repo-relative paths of files whose text matches the regex. Paths only, never a line.

    The one search this gate offers. A search that returns matching lines gets quoted as
    evidence, and an empty result gets read as "fixed"; one that returns only paths can be
    neither, so the file still has to be read. Capped, so a broad pattern reports that it
    was broad instead of flooding the caller.
    """
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise GateError(f"pattern does not compile: {exc}") from None
    hits: list[str] = []
    for path in _walk(under):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        if rx.search(text):
            hits.append(str(path.relative_to(REPO)))
            if len(hits) > _LOCATE_CAP:
                raise GateError(
                    f"more than {_LOCATE_CAP} files match; narrow the pattern or the prefix"
                )
    return hits


def find_files(glob: str) -> list[str]:
    """Repo-relative paths matching a glob by name, skipping what is never a candidate.

    A glob is a path, and `..` in one walks out of the repository: `../*` returned the
    home directory's dotfiles on first review. Refused up front, and every hit is resolved
    and re-checked, so a symlink cannot do the same thing quietly.
    """
    if (
        ".." in pathlib.PurePosixPath(glob).parts
        or pathlib.PurePosixPath(glob).is_absolute()
    ):
        raise GateError(
            "glob must stay inside the repository; `..` and absolute paths are refused"
        )
    hits: list[str] = []
    for p in sorted(REPO.glob(glob)):
        if not p.is_file() or _SKIPPED_DIRS & set(p.relative_to(REPO).parts[:-1]):
            continue
        try:
            p.resolve().relative_to(REPO)
        except ValueError:
            continue
        hits.append(str(p.relative_to(REPO)))
    return hits


def patch_twins(
    path: str, old_string: str, new_string: str, edit_key: str | None
) -> str:
    """Apply one patch to a script or test and to its shipped copy, which must already match.

    A fix that reaches one copy and not the other is the drift the audit exists to catch;
    this makes it unreachable rather than merely detected, and spares the second read. Twins
    that already differ are refused, because mirroring a patch onto a drifted copy would
    bury the drift instead of fixing it.
    """
    rel = safe_relpath(path)
    twin = twin_of(rel)
    if twin is None or not (REPO / twin).is_file():
        raise GateError(f"{rel} has no shipped twin; patch it alone with patch_file")
    if (REPO / rel).read_bytes() != (REPO / twin).read_bytes():
        raise GateError(
            f"{rel} and {twin} already differ; align them first (the audit's "
            f"check_template_scripts_match names the drift), then patch both"
        )
    out = patch_file(rel, old_string, new_string, edit_key)
    (REPO / twin).write_bytes((REPO / rel).read_bytes())
    return out + f"\nmirrored to {twin}: byte-identical to {rel}"
