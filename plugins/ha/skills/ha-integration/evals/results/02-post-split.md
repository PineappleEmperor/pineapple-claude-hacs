# 02 — Mode 4 audit — run against the split skill

**Date:** 2026-08-23 · **Verdict:** PASS (behaviour) · **4 skill defects found**

## Result

Correct verdict on a fixture with empty `.github/`, `scripts/` and `tests/`: the skill
was not followed. The agent ran the mechanical gate (exit 1, 26 FAIL) *and* the judgement
checklist, ran the `diff -ru` commands verbatim from `reference/audit.md`, and — the item
that matters — reported `RELEASE_TOKEN` and required-status-checks as **NOT CHECKED**
rather than passed, because the fixture has no remote. That distinction is the one the
checklist exists to enforce.

## Routing

Opened 4 of 10 reference files: `audit.md` (which carries the whole procedure),
`freshness.md` (required by the checklist's last item), and one grep into
`github-setup.md`. It skipped `patterns.md`, `versioning.md`, `scaffold.md` and the rest
on the grounds that every item they elaborate fails at the antecedent — correct, and only
possible because the router let it choose.

## Defects found (all fixed)

1. `reference/audit.md` pointed at *Where `templates/` lives* "in Mode 1" — the split moved
   that section to `github-setup.md`, so the cross-reference resolved to nothing.
2. `reference/github-actions.md` carried the same stale pointer.
3. `SKILL.md` gave `scripts/skill_audit.py` as the Mode 4 entry point. In a repo that never
   copied the templates — the case where an audit matters most — that path does not exist.
   SKILL.md now says which copy to run in which situation.
4. (From the router KAT, same session) testing was reachable only by elimination.

Defects 1-3 were introduced by the restructure itself. The scenario found them on its
first run, which is the argument for running these before merging a restructure rather
than after.
