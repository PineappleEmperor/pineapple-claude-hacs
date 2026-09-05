# 06 — Router selection, post-fix run

- **Date:** 2026-08-26
- **Skill state:** `feat/reference-link-check`, after the second backlog was cleared
- **Arm:** treatment (fresh subagent, no skill preloaded, told only where the three skills live)
- **Verdict:** PASS, 5/5

| Request | Expected | Answered | By |
|---|---|---|---|
| A log triage | `ha-triage`, no reference file | same | `ha-integration/SKILL.md` negative-routing block, then `ha-triage/SKILL.md` line 8 |
| B reconfigure flow | `ha-integration` → `patterns.md` | same | Modify row of the mode table |
| C panel dark mode | `ha-panel-design`, no reference file | same | negative-routing block, then `ha-panel-design/SKILL.md` line 8 |
| D release process | `ha-integration` → `github-setup.md` | same | Release / repo setup row |
| E setup-entry test | `ha-integration` → `testing.md` | same | Test row |

**Reference files opened to decide: zero.** All five were answerable from the router layer —
three `SKILL.md` files and nothing else. None was reached by elimination, which the scenario
counts as a failure even when the destination is right.

## ⚠️ The oracle was edited before the run — weigh the result accordingly

Two changes were made to the scenario *before* this run, which makes it weaker evidence than
a blind run:

- **E's expected answer was changed** from `patterns.md` (testing sections) to `testing.md`.
  The key predated the split that created `testing.md`, and `docs/skill-file-hierarchy.md`
  assigns test-harness rules to `testing.md`, so the new key is the correct one — but a test
  whose answer is edited to match current behaviour proves less than one that was not. E is
  now documented in the scenario as the deliberate edge case it tests.
- **A and C were answered from a line that has since been removed.** Earlier in the session
  *"This skill is self-contained…"* was deleted from both single-file skills as
  meta-commentary, then restored as *"Work from this file alone — there is no `reference/`
  directory to load"*, which is what the run cited. That wording was wrong: both skills name
  authoritative external sources (Material 3, HA frontend theming, the companion-app docs)
  that a task still has to consult, and "work from this file alone" tells an agent not to.
  The line is gone again, and the scenario now states the distinction instead.

**A and C should be re-run against the current wording.** B, D and E stand.

## Findings not planted by the scenario

- **B is near-ambiguous.** The Modify row names `quality-scale.md` as its only alternative,
  scoped to *adding a platform*. A reconfigure flow wins `patterns.md` by that scope
  qualifier rather than by anything in the row naming flows. The confirming line
  (`Add reconfigure flow`) sits ~64 lines below the table.
- **D is ordered, not ambiguous.** The row names four files and sequences them with "Then…",
  which is what stops a reader starting in the wrong one.
- **`ha-triage` did not appear in the session's skill registry**, though the directory exists
  and both other routers name it. Registration is directory-based with no explicit skill
  list, so this is stale session state after the `ha-log-triage` → `ha-triage` rename, not a
  repo defect. Confirm in a fresh session before trusting A end to end.
