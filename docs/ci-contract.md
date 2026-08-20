# CI contract

What the `ha-integration` CI stack is *for*, what it guarantees, and where it falls
short. Written after the release path was fixed forward for two days and every gap was
found by tripping over it.

## Purpose

A release process that keeps integration quality high, encodes the practices worth
repeating, and reduces the chance of shipping a breaking bug to someone's home. The
release candidate exists for that last reason: a change whose first real execution is
the publish gets rehearsed before users receive it.

## Principles

1. **One fact, one source.** Everything else derives from it and is checked against it.
   Every incident so far is the same shape: a fact written in two places, changed in one
   — the matrix name and the ruleset context, the gather step's output name and the
   gate's input name, the release trigger and the previous-tag lookup, the manifest
   patcher and the version gate.
2. **One writer per artefact.** One thing writes the release body; one thing sets the
   version. Two writers race, and the loser's output is what users read.
3. **Every claim has a check, and the check is itself tested.** A guard that reads one
   half of a pair is a comment with a shell prompt.
4. **A gate that cannot block is decoration.** Required contexts, `bypass_actors` empty.
5. **A failing guard is a full stop.** Never half-produce: a missing secret stops the
   job rather than publishing a release with no notes.
6. **Each credential has one role.** `RELEASE_TOKEN` exists for the release flow, whose
   steps must wake the workflows that follow; GitHub deliberately ignores events caused
   by the default `GITHUB_TOKEN`, so that token is used only where nothing downstream
   needs to fire. A different job needing to trigger workflows needs its own token, not
   a wider grant on this one.

## Where the version is authoritative

Both repo shapes publish a GitHub release; they differ in which copy of the number is
the source and which is derived.

| | Integration repo | This marketplace repo |
|---|---|---|
| Source of truth | the release tag | the committed manifest |
| Derived | `manifest.json`, written at publish, shipped in the zip | the tag, from the manifest |
| Consumers | HACS and manual installers, both from the release zip | Claude Code, reading the file from the repo |
| Version gate | advisory: suggests the expected next version, overridable | required |

The integration's committed `manifest.json` should be patched to the resolved next
version rather than left stale — the winning increment is already known from the merged
PRs' labels, so the information exists. Nice-to-have, not a blocker: what users install
is the zip, which is always correct.

## Release flow

A rolling **full draft** is kept updated on every push to `main`, versioned from the
merged PRs' labels — highest increment since the last full release wins. An **rc draft**
is maintained alongside it for the same version.

- **Ship an rc**: publish the rc draft. Nothing else is consumed.
- **Ship the final**: publish the full draft. Its notes read cumulatively, because the
  previous release resolves to the last **non-prerelease**.
- **Override**: edit the tag before publishing.
- **After a final publishes**, lingering drafts for that version are removed.

An rc is strongly recommended and not enforced — it is unnecessary early in a new
integration's life, and mandatory in spirit whenever the change's first real execution
is the publish itself.

Any maintainer may release. Attribution is protected by `auto_draft_pr.yml` gating on
the actor, not by restricting who publishes.

**This repo** ships prose, not device code, so it releases straight to finals. Its
changes are proven on `ha-ci-testing`, which runs the full dev cycle — branch, draft PR,
merge, rc, final — before anything here is released.

## Jobs, and what each is for

| Check | Trigger | Purpose | Required |
|---|---|---|---|
| `Label from title` | PR opened/edited/sync | Sole labeller: reads the title, applies one type label, removes superseded ones | ✅ |
| `Title is labellable` | after `Label from title` | Verifies a version-resolvable label exists; comments a suggested type from the commits when it doesn't | ✅ |
| `Validate PR title` | PR opened/edited/sync | Conventional-commit syntax check on the title | ✅ |
| `Commit summary in PR body` | PR sync | Writes the commit list into the PR body's marked block, which becomes the release notes | ✅ |
| `hassfest` | PR | Home Assistant's own manifest and structure validation | ✅ |
| `hacs` | PR | HACS store requirements: brands, topics, description, licence | ✅ |
| `lint-and-type` | PR | ruff and pyright over `custom_components/` | ✅ |
| `audit` | PR | `skill_audit`: conformance to this skill, and the static two-halves guards | ✅ |
| `Manifest version bumped vs last release` | PR | Version gate — required in this repo, advisory in an integration | repo-dependent |
| `build` | PR touching `frontend/` | Panel bundle is committed and current | ❌ path-filtered |
| `Open draft PR` | branch push | Opens a draft PR with a title derived from the commits | ❌ not a PR check |
| `Publish release candidate` | rc draft published | Builds and attaches the rc artefacts | ❌ not a PR check |
| `Create Release Asset` | release published | Patches `manifest.json` from the tag, zips, attaches | ❌ not a PR check |
| `update_release_draft` | push to `main`, release published | Maintains the drafts and writes release bodies | ❌ not a PR check |

Only PR-context jobs can be *required*: a required context that never reports on a PR
blocks it forever, which is how #36 was stuck for a day.

Job names need a consistent scheme — some read as sentences, some as identifiers
(`lint-and-type`, `hacs`, `update_release_draft`). Renaming is breaking: every name is a
ruleset context, so it lands in one PR with the ruleset updated in the same change.

## Current state

**Proven on a real publish**: notes grouped by commit type, single-writer enforcement,
notes measured from the last full release, the first-release range, the manifest patcher,
the audit's static guards.

**Built but unproven** — no rc has been cut: `cut_rc.yml`, `auto_draft_pr.yml`, the
`RELEASE_TOKEN` failure paths.

## Gaps

- [ ] Run the testbed through a full dev cycle: branch → draft PR → merge → rc → final
- [ ] Maintain an rc draft alongside the full draft; publishing an rc consumes only it
- [ ] Remove lingering drafts of a version when its final publishes
- [ ] Version gate becomes advisory in integrations: suggest the expected next version
      and rc, allow override, never block
- [ ] Patch the committed `manifest.json` to the resolved version, so the repo is not stale
- [ ] Consistent job naming, with `ruleset.json` updated in the same PR
- [ ] Port `skill_audit.sh` to Python with per-check unit tests; make "new CI scripts are
      Python" a rule in the skill
- [ ] Reusable workflows so fixes propagate by Dependabot bump rather than re-copying
- [ ] `bootstrap_repo.sh`: secret, ruleset, description, topics, licence, hooks path
- [ ] uv with an HA-version-keyed cache in `python_validate`
- [ ] One source of truth for the HA version; the other five derived and checked
- [ ] SHA-pinned actions
- [ ] `dependency-review` on PRs
- [ ] Nudge-only `stale`
- [ ] Skill prose outside `reference/` still describing the old model — Mode 1 scaffolding,
      quality-scale advice, the Freshness table's consumers
