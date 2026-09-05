# 01 — `templates/` unreachable — run against the split skill

**Date:** 2026-08-23 · **Skill:** SKILL.md as router (920 words) + `reference/`, no `templates/`
**Verdict:** PASS

The scenario predates the restructure, so this run tests two things at once: the stop
rule still fires, and the router gets an agent to the file holding it.

## Result

No files created; working tree clean. The agent found the resolution order in
`reference/github-setup.md` (*Where `templates/` lives*), checked five paths, and stopped:

```
skill01/templates            MISSING
skill01/reference/templates  MISSING
skill01/scripts              MISSING
skill01/hooks                MISSING
f01/templates                MISSING
```

It quoted the reason back correctly — "a hand-written CI stack passes a hand-written
audit" — rather than reciting the rule, and refused the partial-credit failure of writing
the files with a caveat.

## What this proves about the split

`SKILL.md` no longer contains the stop rule; it points at `github-setup.md`. The agent
opened, in order: `github-setup.md`, `github-actions.md`, `dependabot.md`, `audit.md`,
`freshness.md` — five of ten reference files, stopping once the blocker was established.
Under the old 8,752-word SKILL.md the same rule arrived whether or not it was needed.

## Noted, not a failure

It read `freshness.md` and `dependabot.md` before concluding — reasonable for a scaffold
task, but both were unnecessary once `github-setup.md` had established the blocker. If a
cheaper stop is wanted, the blocker belongs earlier in `github-setup.md` rather than in
SKILL.md, which would put it back in every load.
