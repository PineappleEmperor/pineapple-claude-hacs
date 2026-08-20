# CI contract

What the `ha-integration` CI stack is *for*, what it guarantees, and where it currently
falls short. Written after two days of fixing the release path forward and discovering
each gap by tripping over it.

The recurring failure has one shape: **a fact written in two places, changed in one.**
The matrix name and the ruleset context. The gather step's output name and the gate's
input name. The release trigger and the previous-tag lookup. The manifest patcher and
the version gate. Every guard below exists because two halves disagreed and nothing read
both.

## Two repo shapes

| | Integration repo | This marketplace repo |
|---|---|---|
| Who reads the version | HACS and manual installers, from the release **zip** | Claude Code, from the **committed** file |
| Version source | the release tag | a bump commit in a PR |
| Version gate | none — nothing to gate | required |
| Manifest between releases | stale placeholder, accepted | always accurate |

## Principles

1. **One writer per artefact.** One thing writes the release body; one thing sets the
   version. Two writers race, and the loser's output is what users read.
2. **Every claim has a check that reads both halves.** A guard that reads one side is a
   comment with a shell prompt.
3. **A gate that cannot block is decoration.** Required contexts, `bypass_actors` empty.
4. **The default token triggers nothing.** Anything that must wake another workflow uses
   `RELEASE_TOKEN`; anything that doesn't, uses `GITHUB_TOKEN`.
5. **Fail loudly, never half-produce.** A missing secret stops the job; it does not
   publish a release with no notes.

## Release flow

A rolling **full draft** always exists, recreated on every push to `main`, versioned from
the merged PRs' labels — highest increment since the last full release wins.

- **Cut an rc**: run `Cut Release Candidate`. It publishes `vX.Y.ZrcN` from the draft's
  version, auto-incrementing N, and leaves the draft standing.
- **Ship the final**: publish the draft. Its notes already read cumulatively, because the
  previous release is resolved as the last **non-prerelease**.
- **Override**: edit the tag before publishing.

An rc is **recommended, not enforced** — a new integration finding its feet should not be
forced through one. It *is* expected whenever the change's first real execution is the
publish itself: release-body writers, tag-triggered workflows, the zip patcher.

Any maintainer may release. Attribution is protected by `auto_draft_pr.yml` gating on
the actor, not by restricting who can publish.

## Required checks

Eight on a scaffolded integration, with strict mode (branches up to date):

```
Label from title · Title is labellable · Commit summary in PR body · Validate PR title
hassfest · hacs · lint-and-type · audit
```

`Manifest version bumped vs last release` is **not** among them: the tag sets the version.
This repo keeps it, because its committed file is what consumers read.

## Current state

Working and proven on a real publish: grouped notes by commit type, the single-writer
rule, notes measured from the last full release, the first-release range, the manifest
patcher, the audit's static guards.

Built but unproven — no rc has been cut yet: `cut_rc.yml`, `auto_draft_pr.yml`, and the
`RELEASE_TOKEN` failure paths.

## Gaps

- [ ] Cut a real rc on the testbed; prove the cutter, patcher and notes range end to end
- [ ] Remove `version-gate` from the integration template and `ruleset.json`
- [ ] Tag-vs-resolved-version check at publish, replacing the gate's guidance role
- [ ] Reusable workflows so fixes propagate by Dependabot bump, not re-copying
- [ ] `bootstrap_repo.sh`: secret, ruleset, description, topics, licence, hooks path
- [ ] uv with an HA-version-keyed cache in `python_validate`
- [ ] One source of truth for the HA version, with the other five derived and checked
- [ ] SHA-pinned actions
- [ ] `dependency-review` on PRs
- [ ] Nudge-only `stale`
- [ ] Skill prose still describing the old model outside `reference/` — Mode 1 scaffolding,
      quality-scale advice, the Freshness table's consumers
