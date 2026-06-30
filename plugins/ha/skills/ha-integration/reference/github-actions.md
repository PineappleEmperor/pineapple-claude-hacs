# GitHub CI stack — rationale & required behaviours

The **file bodies** live in the skill's `templates/` dir (mirrors the target repo: `templates/.github/workflows/*.yml`, `templates/.github/*.yml`, `templates/scripts/*`, `templates/tests/*`, `templates/hooks/*`). Copy them as-is — they are self-contained, no external repo. This file is the **why**: the behaviours each workflow must preserve. Read it before changing any workflow.

#### create-dev-pr.yml template (canonical — copy this, no external repo)

Self-contained; embodies every rule above (title from commits, grouped `$BODY` sub-heads, `xargs` title trim, no label step, concurrency guard, skip when 0 ahead). Pin actions to current majors and let Dependabot bump them.

#### Remaining workflow + config templates (canonical — copy these, no external repo)

All paths assume one integration per repo: `custom_components/<domain>/manifest.json` is resolved with `ls custom_components/*/manifest.json | head -1`. Action majors are current as of 2026-06; Dependabot (`github-actions`) keeps them bumped. The full release path is: `release_drafter.yml` drafts notes on `main`, `semantic_release.yml` cuts the release on the tag, and **`release.yml` (*Create Release ZIP*) attaches the `<domain>.zip` asset on publish** — the last is mandatory whenever `hacs.json` sets `zip_release: true` (omit it only on a repo that deliberately uses no `zip_release`).

**`.github/workflows/lint_pr.yml`** — semantic PR-title gate.

**`.github/workflows/pr-labeler.yml`** — the **sole** labeler: autolabeler adds, removal-only step subtracts superseded type labels (can't flap).

**`.github/workflows/release_drafter.yml`** — drafts release notes on `main` only (labelling lives in `pr-labeler.yml`, so no autolabeler job here). Reads the release version from the manifest.

**`.github/release-drafter.yml`** (config) — title-only autolabeler rules (breaking `!` first), `$BODY` kept with bounded Dependabot `replacers`, label→semver `version-resolver`.

**`.github/workflows/semantic_release.yml`** — cuts the GitHub release on a `v*.*.*` tag; `rc/alpha/beta` tags marked prerelease.

**`.github/workflows/release.yml`** — *Create Release ZIP*. Required when `hacs.json` has `zip_release: true`: builds `<domain>.zip` (integration files at the **zip root**) and attaches it to the published release, so HACS has the asset to download. `cd` into the package before zipping so paths are root-relative (not `custom_components/<domain>/…`). Uses the `gh` CLI to upload (the old `actions/upload-release-asset@v1` is archived — don't reinstate it).

**`.github/workflows/hassfest_validate.yml`** — HA manifest/services/quality-scale validation.

**`.github/workflows/hacs_validate.yml`** — HACS 8-check validation. **No `ignore:` input** — ignoring any check disqualifies the repo from the default store.

**`.github/workflows/python_validate.yml`** — ruff + pyright on HA's floor Python (keep the matrix in lockstep with `pyproject.toml` / `pyrightconfig.json`).

**`.github/workflows/check-manifest-version.yml`** + **`scripts/manifest_gate.py`** + **`tests/test_manifest_gate.py`** — version gate **against the last published release** (not `main` HEAD). ⚠️ **The decision logic lives in a unit-tested Python script, NOT inline bash.** A real bug shipped from inline-bash logic: it used strict equality (`suggested == manifest`), so a `chore` PR sitting at `1.2.0` (riding a minor already merged this cycle) was rejected with "expected v1.1.1" — even though `1.2.0` is a perfectly valid in-cycle version. Inline gate logic is untested and regresses silently; extract it so it has a test suite. The gate must enforce a **floor** (≥ the label's minimum bump from the last release — catches under-bumps) **and** a **ceiling** (≤ the in-cycle version on `main`, or this PR's own label bump if it escalates the tier — catches over-bumps), with prerelease versions only needing to differ and `dependabot[bot]` exempt.

The workflow just gathers inputs and shells out:

`scripts/manifest_gate.py` — pure `evaluate()` + thin CLI (add `"scripts/*" = ["T20", "INP001"]` to ruff `per-file-ignores`):

`tests/test_manifest_gate.py` — load the standalone script by path (it isn't an importable package) and cover the matrix, **including the regression that shipped** (chore riding an in-cycle minor) and the over-bump it must still catch:

**`.github/dependabot.yml`** — `github-actions` is the real value; `pip` covers `requirements.test.txt` when pinned. `chore` prefix → autolabeler maps to patch.

#### Optional: per-turn reminder hooks (personal `~/.claude`)

The repo `CLAUDE.md` rule is the **canonical, shareable** enforcement (it ships with the repo, applies to everyone). These two personal hooks are a *convenience* layer on top — they live in your own `~/.claude/` and re-arm the rules every session/turn so they don't drift down-context in a long session. **Marker-file gated** so each only fires where it applies: the skill anchor on an integration repo (`custom_components/*/manifest.json`), the CI-convention anchor on any repo using this workflow stack (`.github/workflows/create-dev-pr.yml`) — which includes this skill's own repo, not just scaffolded integrations.

`~/.claude/settings.json` (merge into existing `hooks`):

`~/.claude/hooks/ha-skill-reinvoke.sh` — re-arms the skill rule at session start (compaction drops the skill's guidance; stdout is injected as session context):

`~/.claude/hooks/ha-resources-reminder.sh` — per-turn anchors; stdout is injected as prompt context, so keep each line terse:

`chmod +x` both scripts. Editing a hook *script* takes effect immediately (the hook re-execs it each turn); editing `settings.json` to add/remove a hook needs a `/hooks` open or restart to re-register.

---
