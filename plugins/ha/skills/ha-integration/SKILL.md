---
description: Create, modify, lint, and triage Home Assistant custom integrations — custom_components packages, manifest.json, config/options/reauth/reconfigure flows, coordinator + entity platforms, services, diagnostics, quality_scale.yaml — targeting Platinum quality scale. Also triages HA logs (Mode 5). Use before writing or modifying any HA integration code or reading a HA log; re-invoke after /compact.
---

# Home Assistant Integration Assistant

Help create, modify, and lint Home Assistant custom integrations targeting **platinum quality scale**.

**Always fetch before coding** — these are the authoritative sources:
- Creating integrations: https://developers.home-assistant.io/docs/creating_integration_index/
- Config entries: https://developers.home-assistant.io/docs/config_entries_index/
- Config flows: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
- Data fetching + coordinator: https://developers.home-assistant.io/docs/integration_fetching_data/
- Setup failures: https://developers.home-assistant.io/docs/integration_setup_failures/
- Quality scale: https://developers.home-assistant.io/docs/integration_quality_scale_index/
- Real examples: https://github.com/home-assistant/core/tree/dev/homeassistant/components

---

## Step 1 — Detect mode

Check the current working directory:
- No `custom_components/` → default to **Scaffold**
- `custom_components/` exists → ask: **Scaffold** new integration / **Modify** existing / **Lint & quality check** / **Audit** (verify the skill was actually followed — see Mode 4)?
- The task is reading/triaging a **HA log** (a `home-assistant.log`, a Settings → System → Logs download, or a copied log dump) → **Log triage** (Mode 5) — regardless of `custom_components/` presence.

---

## Mode 1 — Scaffold new integration

### Gather requirements (ask all at once)

1. **Domain** — snake_case, e.g. `my_device`. Must be stable; can't change later.
2. **Friendly name** — e.g. "My Device"
3. **Description** — one sentence
4. **IoT class** — `local_polling` / `local_push` / `cloud_polling` / `cloud_push` / `calculated`
5. **Data model** — polling (use `DataUpdateCoordinator`) or push (subscription)
6. **Auth model** — none / API key / OAuth / username+password
7. **Platforms** — button, sensor, binary_sensor, switch, light, number, select, text, notify, cover, climate, fan, lock, media_player, vacuum (pick any)
8. **MicroPython firmware?** (yes/no) — adds `firmware/` exclusion to pyrightconfig.json
9. **Version** — default `0.1.0`

### Files to generate

**Integration package** (`custom_components/{domain}/`):
- `__init__.py`
- `config_flow.py`
- `const.py`
- `manifest.json`
- `strings.json`
- `translations/en.json`
- `services.yaml` (only if custom services are genuinely needed; prefer standard services first)
- `icons.json` (action/service icons for UI display — `{"services": {"my_action": {"service": "mdi:icon"}}}`)
- `quality_scale.yaml`
- `diagnostics.py` (Gold requirement — see patterns section)
- One file per selected platform (e.g. `button.py`, `sensor.py`)
- Additional files as needed: `api.py`, `coordinator.py`, `models.py`, `entity.py`, `helpers.py` (see file structure conventions section)

**Repo root:**
- `CLAUDE.md` — project instructions. **Always include a rule telling future AI sessions to invoke this `ha-integration` skill before writing/modifying integration code, and to re-invoke after `/compact`** (compaction drops the skill's guidance). Keep this enforcement **per-repo, not global** — a project file is the right scope; do not push a user's global config on others. Suggested snippet:
  ```markdown
  ## AI sessions
  Before writing or modifying integration code (config flow, platforms, manifest,
  websocket, services…), invoke the `ha-integration` skill. Re-invoke it after any
  `/compact`, since compaction can drop the skill's guidance from context.
  ```
  (A user may *additionally* wire personal `SessionStart` + `UserPromptSubmit` hooks in their own `~/.claude/settings.json` to re-arm the rule and anchor the CI conventions per-turn — see the *Optional: per-turn reminder hooks* appendix below for the full recipe. That's a personal convenience; the canonical, shareable enforcement still lives in the repo's `CLAUDE.md`.)
- `hacs.json` — `name` is the only strict requirement, but the canonical setup ships a **zip release**: `{"name": "My Integration", "content_in_root": false, "zip_release": true, "filename": "<domain>.zip"}` (add `"homeassistant": "2024.1.0"` for a minimum HA version). `zip_release` makes HACS download a release **asset** named `<filename>` instead of the tag source archive — so it **requires** the `release.yml` *Create Release ZIP* workflow (below) to build and attach that asset on every published release. **Without that workflow, HACS install fails with `Could not download`** (the symptom of a `zip_release` repo whose release has no attached zip). Drop `zip_release`/`filename` only if you deliberately want HACS to pull the whole tagged repo archive instead.
- `pyproject.toml`
- `pyrightconfig.json`
- `README.md` — **include the AI-assistance disclaimer** as a GitHub `> [!NOTE]` admonition box. Link the skill name to its public repo. Template:
  ```markdown
  > [!NOTE]
  > **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/pineapple-claude-hacs) skill. Architecture and final review are mine; every change is human-reviewed before it merges.
  ```
- `.gitignore`
- `.githooks/commit-msg` — terse-commit + AI-trailer-rejection hook (see the Conventional Commits section); enable once per clone with `git config core.hooksPath .githooks` (document this in `CLAUDE.md`)
- `custom_components/{domain}/brand/icon.png` — **256×256**, required by HACS brands validation
- `custom_components/{domain}/brand/icon@2x.png` — **512×512** (see HiDPI note below)
- `custom_components/{domain}/brand/logo.png` — landscape, shortest side **128–256**
- `custom_components/{domain}/brand/logo@2x.png` — landscape, shortest side **256–512**

> **Brand assets are served from the integration's own `brand/` folder since HA 2026.3.0** (via the Brands Proxy API). The `home-assistant/brands` CDN `custom_integrations/` folder is **legacy** — do not rely on it for new work. Files are PNG, lossless; transparent background for wordmark/logo art (an LED-screen/device screenshot keeps its black background — that's the device, not a missing alpha).
>
> ⚠️ **The HACS store/search dashboard still reads the legacy `data-v2.hacs.xyz` (which mirrors the old brands CDN), NOT the inline `brand/` folder.** So an integration that ships *only* inline brand images — i.e. one that never got a `home-assistant/brands` entry, and now **can't** (brands auto-closes `custom_integrations/*` PRs) — renders **blank in the HACS dashboard** even though HA's own UI shows the icon correctly via the proxy. Integrations with a *legacy* brands entry (added before the Feb-2026 cutoff) keep showing in HACS. This is a HACS-side gap, not a repo defect — nothing to fix in the integration; it resolves when HACS points its dashboard at the proxy (tracked in hacs/integration #5171 and #5223). Don't try to "fix" it by PR-ing `home-assistant/brands` (auto-closed).
>
> ⚠️ **Ship the `@2x` variants or the icon flickers/fails on HiDPI.** The most common "icon shows only sometimes" bug is a present `icon.png` with **no `icon@2x.png`**: a Retina/zoomed client requests `@2x`, 404s, and falls back inconsistently. `icon@2x.png` (512²) and `logo@2x.png` are not optional. Exact, square sizes matter — an off-spec `icon.png` (e.g. 384²) also misbehaves.
>
> **Sources:** a placeholder may start as an SVG rasterised with `cairosvg` (ImageMagick's MSVG renderer botches text) or `convert -background none -density 144 in.svg out.png`. But the asset can equally be a **crisp nearest-neighbour upscale of a real device render** — for a pixel display this is the strongest branding. Pick by where HA shows it: the **logo** renders large (integration page / HACS) so a busy/detailed screen reads well; the **icon** renders small (~48px in the integrations list) so use a **simple, low-detail** screen (fewer, fatter pixels survive the shrink) — a full text-heavy screen turns to mush. Generate the PNG straight from the byte-faithful preview (`render_layout_png(..., scale=N)`), not a photo.

> HACS `check-brands` fails if `custom_components/{domain}/brand/icon.png` is absent and the integration is not listed in the HA brands repo.

**HACS validation — 8 checks**

⚠️ All checks must pass without ignoring any — the `ignore:` input in `hacs_validate.yml` exists for debugging only. Ignoring checks disqualifies the repo from the HACS default store.

| Check | What's needed | Where to fix |
|-------|--------------|--------------|
| `archived` | Repo not archived | GitHub repo settings |
| `brands` | `brand/icon.png` present | File in repo |
| `description` | Repo has a description | GitHub repo settings → About |
| `hacsjson` | `hacs.json` exists | File in repo |
| `images` | README contains at least one image | Add screenshot to README |
| `information` | README.md exists | File in repo |
| `issues` | Issues tab enabled | GitHub repo settings → Features |
| `topics` | Repo has at least one topic | GitHub repo settings → About |

The `description`, `issues`, and `topics` checks fail silently until the first `hacs_validate` run — they're GitHub settings, not files.

**GitHub workflows** — look for existing workflow files in the current project first and replicate the same patterns. If none exist, use standard HA integration CI:
- `.github/workflows/semantic_release.yml` — triggers on `v*.*.*` tag push; uses `softprops/action-gh-release@v3` with `generate_release_notes: true`. Tags containing `beta` auto-marked as prerelease. No npm, no semantic-release tooling needed.
- `.github/workflows/release.yml` — **Create Release ZIP.** Triggers on `release: published`; zips the contents of `custom_components/<domain>/` (files at the **zip root**, not nested) and attaches it as the `<filename>` asset declared in `hacs.json`. **Required whenever `hacs.json` sets `zip_release: true`** — HACS downloads that asset, so a missing zip = `Could not download` on install. Full canonical YAML in the templates appendix below. (The `release: published` trigger fires when a human publishes the drafted release; a release *created* by `GITHUB_TOKEN` would be suppressed by the anti-recursion rule, so publish from the draft, don't auto-create via token.)
- `.github/workflows/create-dev-pr.yml` — triggers on every push to non-main branches; auto-creates a draft PR with **title from commits** (`feat:` wins over `fix:` wins over last commit). Updates PR body with commit list on subsequent pushes. **Full canonical YAML in the *create-dev-pr.yml template* appendix below** — this skill is the source of truth; do not copy from any other repo. ⚠️ After computing `TITLE`, always add `TITLE=$(echo "$TITLE" | xargs)` before `echo "title=$TITLE" >> $GITHUB_OUTPUT` — GitHub Actions env var interpolation can add surrounding whitespace that breaks `lint_pr.yml` semantic title validation. **Do NOT add a label step here** — labelling is the autolabeler's job (below). Since this sets the title to the winning commit type, autolabelling off the title is effectively commit-driven; a second labeler here just causes flapping.
- `.github/workflows/release_drafter.yml` — owns the draft release notes (categories + `version-resolver` + `$BODY`); `push` (main) trigger only; `pull-requests: write`. Labelling lives in `pr-labeler.yml` (the sole labeler), so this carries no autolabeler job.
- `.github/workflows/pr-labeler.yml` — runs `release-drafter/release-drafter/autolabeler@v7` on `pull_request` (opened/reopened/synchronize). The **sole labeler.**
- `.github/workflows/lint_pr.yml`
- `.github/workflows/hacs_validate.yml`
- `.github/workflows/hassfest_validate.yml`
- `.github/workflows/python_validate.yml` — **pin the matrix to HA's current minimum Python** (as of 2026-06, `["3.14"]` — HA dev requires 3.14.2+; `pip install homeassistant` refuses older). Test the *floor* HA supports, and re-check it at developers.home-assistant.io/docs/development_environment when HA bumps. Keep this in lockstep with `pyproject.toml` ruff `target-version = "py314"` and pylint `py-version = "3.14"`, and `pyrightconfig.json`.
- `.github/workflows/check-manifest-version.yml`
- `.github/workflows/quality_audit.yml` — runs `scripts/skill_audit.sh` on every PR to mechanically enforce skill conformance (workflows present, action pins current, antipatterns absent). See **Mode 4 — Audit**.
- `scripts/skill_audit.sh` — the mechanical conformance check (run locally before claiming done; CI runs it too).
- `.github/pr-labeler.yml`
- `.github/release-drafter.yml` — autolabeler rules are **title-only** (no `branch:` rules). The release-drafter autolabeler can only match title/body/branch/files (never commit subjects), so label off the **title** — which `create-dev-pr` already derives from the commits. Keep it the one-and-only labeler; don't also label in `create-dev-pr.yml`.
- `.github/dependabot.yml` — see the **Dependabot** section below.

#### create-dev-pr.yml template (canonical — copy this, no external repo)

Self-contained; embodies every rule above (title from commits, grouped `$BODY` sub-heads, `xargs` title trim, no label step, concurrency guard, skip when 0 ahead). Pin actions to current majors and let Dependabot bump them.

```yaml
name: Create/Update Dev PR

on:
  push:
    branches-ignore:
      - main

permissions:
  contents: read
  pull-requests: write

concurrency:
  group: dev-pr-${{ github.ref }}
  cancel-in-progress: true

jobs:
  create-or-update-pr:
    runs-on: ubuntu-latest
    outputs:
      pr_number: ${{ steps.pr.outputs.pr_number }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Generate PR body and title type from commits
        id: commits
        run: |
          AHEAD=$(git rev-list --count origin/main..HEAD)
          echo "ahead=$AHEAD" >> $GITHUB_OUTPUT

          SUBJECTS=$(git log origin/main..HEAD --pretty=format:"%s" --reverse)

          # Group the body by commit type so release-drafter's $BODY reads as a
          # sorted mini-changelog under the PR's category (bold emoji sub-heads).
          classify() {
            printf '%s' "$1" | grep -qiE '^[a-z]+(\([^)]*\))?!:' && { echo breaking; return; }
            printf '%s' "$1" | grep -qiE '^feat(\([^)]*\))?:'    && { echo feat; return; }
            printf '%s' "$1" | grep -qiE '^fix(\([^)]*\))?:'     && { echo fix; return; }
            printf '%s' "$1" | grep -qiE '^(chore|docs|refactor|perf|test|build|ci|style)(\([^)]*\))?:' && { echo maint; return; }
            echo other
          }
          desc() { printf '%s' "$1" | sed -E 's/^[a-zA-Z]+(\([^)]*\))?!?:[[:space:]]*//'; }

          # The manifest/plugin version-bump commit is release plumbing, not a changelog
          # entry. Skip it: as a lone 'chore' it would otherwise spawn a 🧰 Maintenance
          # section and, by adding a second commit type, trip the >1-type sub-head guard.
          is_version_bump() {
            printf '%s' "$1" | grep -qiE '^[a-z]+(\([^)]*\))?:[[:space:]]*bump\b.*(\bversion\b|\bmanifest\b|\bto v?[0-9]+\.[0-9]+)'
          }

          BREAKING=""; FEAT=""; FIX=""; MAINT=""; OTHER=""
          while IFS= read -r s; do
            [ -z "$s" ] && continue
            is_version_bump "$s" && continue
            d=$(desc "$s")
            case "$(classify "$s")" in
              breaking) BREAKING="${BREAKING}  - ${d}"$'\n' ;;
              feat)     FEAT="${FEAT}  - ${d}"$'\n' ;;
              fix)      FIX="${FIX}  - ${d}"$'\n' ;;
              maint)    MAINT="${MAINT}  - ${d}"$'\n' ;;
              *)        OTHER="${OTHER}  - ${d}"$'\n' ;;
            esac
          done <<< "$SUBJECTS"

          # Emit the emoji sub-heads ONLY when the PR spans >1 commit type. release-drafter
          # already files the PR under one category heading (🚀/🔧/🧰…), so for a single-type
          # PR (every Dependabot chore, most human PRs) a matching sub-head just duplicates it.
          groups=0
          for g in "$BREAKING" "$FEAT" "$FIX" "$MAINT" "$OTHER"; do
            [ -n "$g" ] && groups=$((groups + 1))
          done
          BODY=""
          if [ "$groups" -le 1 ]; then
            BODY="${BREAKING}${FEAT}${FIX}${MAINT}${OTHER}"
          else
            [ -n "$BREAKING" ] && BODY="${BODY}  **🚨 Breaking**"$'\n'"${BREAKING}"
            [ -n "$FEAT" ]     && BODY="${BODY}  **🚀 Features**"$'\n'"${FEAT}"
            [ -n "$FIX" ]      && BODY="${BODY}  **🔧 Fixes**"$'\n'"${FIX}"
            [ -n "$MAINT" ]    && BODY="${BODY}  **🧰 Maintenance**"$'\n'"${MAINT}"
            [ -n "$OTHER" ]    && BODY="${BODY}  **📦 Other**"$'\n'"${OTHER}"
          fi
          [ -z "$BODY" ] && BODY="  - (no commits ahead of main)"
          echo "body<<EOF" >> $GITHUB_OUTPUT
          printf '%s' "$BODY" >> $GITHUB_OUTPUT
          printf '\n' >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

          TITLE=$(echo "$SUBJECTS" | grep -iE "^feat(\(.+\))?!?:" | tail -1)
          if [ -z "$TITLE" ]; then
            TITLE=$(echo "$SUBJECTS" | grep -iE "^fix(\(.+\))?!?:" | tail -1)
          fi
          if [ -z "$TITLE" ]; then
            TITLE=$(echo "$SUBJECTS" | tail -1)
          fi
          TITLE=$(echo "$TITLE" | xargs)
          echo "title=$TITLE" >> $GITHUB_OUTPUT

      - name: Create or update draft PR
        id: pr
        if: steps.commits.outputs.ahead != '0'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BRANCH: ${{ github.ref_name }}
          BODY: ${{ steps.commits.outputs.body }}
          TITLE: ${{ steps.commits.outputs.title }}
        run: |
          PR_NUMBER=$(gh pr list --head "$BRANCH" --base main --state open --json number --jq '.[0].number')
          if [ -z "$PR_NUMBER" ]; then
            gh pr create \
              --draft \
              --title "$TITLE" \
              --body "$BODY" \
              --base main \
              --head "$BRANCH"
            PR_NUMBER=$(gh pr list --head "$BRANCH" --base main --state open --json number --jq '.[0].number')
          else
            gh pr edit "$PR_NUMBER" --title "$TITLE" --body "$BODY"
          fi
          echo "pr_number=$PR_NUMBER" >> $GITHUB_OUTPUT
```

#### Remaining workflow + config templates (canonical — copy these, no external repo)

All paths assume one integration per repo: `custom_components/<domain>/manifest.json` is resolved with `ls custom_components/*/manifest.json | head -1`. Action majors are current as of 2026-06; Dependabot (`github-actions`) keeps them bumped. The full release path is: `release_drafter.yml` drafts notes on `main`, `semantic_release.yml` cuts the release on the tag, and **`release.yml` (*Create Release ZIP*) attaches the `<domain>.zip` asset on publish** — the last is mandatory whenever `hacs.json` sets `zip_release: true` (omit it only on a repo that deliberately uses no `zip_release`).

**`.github/workflows/lint_pr.yml`** — semantic PR-title gate.
```yaml
name: Lint PR

on:
  pull_request_target:
    types: [opened, edited, synchronize, reopened]

jobs:
  main:
    name: Validate PR title
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: amannn/action-semantic-pull-request@v6
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**`.github/workflows/pr-labeler.yml`** — the **sole** labeler: autolabeler adds, removal-only step subtracts superseded type labels (can't flap).
```yaml
name: PR Labeler

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  contents: read

jobs:
  pr-labeler:
    permissions:
      pull-requests: write
    runs-on: ubuntu-latest
    steps:
      - uses: release-drafter/release-drafter/autolabeler@v7
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # The autolabeler only *adds*. When a PR's title flips type mid-life
      # (fix -> feat), the old label lingers and the PR lists under two
      # release-drafter categories. Remove superseded labels, keyed on the
      # same title the autolabeler reads (removal-only -> cannot flap).
      - name: Remove superseded type labels
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GH_REPO: ${{ github.repository }}  # job has no checkout
          TITLE: ${{ github.event.pull_request.title }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          if   printf '%s' "$TITLE" | grep -qiE '^[a-z]+(\([^)]*\))?!:';        then WIN=xfeat
          elif printf '%s' "$TITLE" | grep -qiE '^(chore|docs)(\([^)]*\))?:';   then WIN=chore
          elif printf '%s' "$TITLE" | grep -qiE '^fix(\([^)]*\))?:';            then WIN=fix
          elif printf '%s' "$TITLE" | grep -qiE '^(feat|feature)(\([^)]*\))?:'; then WIN=feature
          else exit 0  # title maps to no managed label; leave labels untouched
          fi
          CURRENT=$(gh pr view "$PR" --json labels --jq '.labels[].name')
          for L in xfeat feature fix chore; do
            [ "$L" = "$WIN" ] && continue
            # `if` (not `grep && gh`): a no-match grep as the step's last command
            # returns 1 under `bash -e`, failing the step even when nothing's wrong.
            if printf '%s\n' "$CURRENT" | grep -qx "$L"; then
              gh pr edit "$PR" --remove-label "$L"
            fi
          done
```

**`.github/workflows/release_drafter.yml`** — drafts release notes on `main` only (labelling lives in `pr-labeler.yml`, so no autolabeler job here). Reads the release version from the manifest.
```yaml
name: Release Drafter

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  update_release_draft:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - id: ver
        name: Read version from manifest
        run: |
          MANIFEST=$(ls custom_components/*/manifest.json | head -1)
          V=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$MANIFEST")
          echo "version=$V" >> "$GITHUB_OUTPUT"
          if echo "$V" | grep -Eiq '[0-9][-._]?(rc|alpha|beta|dev|a|b)'; then
            echo "prerelease=true" >> "$GITHUB_OUTPUT"
          else
            echo "prerelease=false" >> "$GITHUB_OUTPUT"
          fi
      - uses: release-drafter/release-drafter@v7
        with:
          version: ${{ steps.ver.outputs.version }}
          tag: v${{ steps.ver.outputs.version }}
          name: v${{ steps.ver.outputs.version }}
          prerelease: ${{ steps.ver.outputs.prerelease }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**`.github/release-drafter.yml`** (config) — title-only autolabeler rules (breaking `!` first), `$BODY` kept with bounded Dependabot `replacers`, label→semver `version-resolver`.
```yaml
name-template: 'v$RESOLVED_VERSION'
tag-template: 'v$RESOLVED_VERSION'
# Sole labeler keyed on the PR TITLE only — create-dev-pr.yml sets the title to the
# winning commit type, so this is effectively commit-driven. No branch rules (they
# flapped when branch name disagreed with commits). Breaking `!` must precede `feature`.
autolabeler:
  - label: "xfeat"
    title:
      - '/^\w+(\(.+\))?!:/'
  - label: "chore"
    title:
      - '/^(chore|docs|refactor|perf|test|build|ci|style)(\(.+\))?:/i'
  - label: "fix"
    title:
      - '/^fix(\(.+\))?:/i'
  - label: "feature"
    title:
      - '/^(feat|feature)(\(.+\))?:/i'
categories:
  - title: '🚨 Breaking Change'
    labels: ['xfeat', 'xfeature', 'major']
  - title: '🚀 Features'
    labels: ['feat', 'feature', 'enhancement']
  - title: '🔧 Fixes'
    labels: ['fix', 'bugfix', 'bug']
  - title: '🧰 Maintenance'
    label: 'chore'
change-template: |-
  - $TITLE @$AUTHOR (#$NUMBER)
  $BODY
change-title-escapes: '\<*_&'
# $BODY is global (no per-category change-template). Bounded replacers (no end-anchor,
# so they can't bleed across concatenated PR bodies) scrub Dependabot fluff while
# keeping human PRs' grouped mini-changelog.
replacers:
  - search: '/<details>[\s\S]*?<\/details>\s*/g'
    replace: ''
  - search: '/\[!\[Dependabot compatibility score\][^\n]*\n?/g'
    replace: ''
  - search: '/Dependabot will resolve[^\n]*\n?/g'
    replace: ''
  - search: '/\[\/\/\]: # \(dependabot-start\)[\s\S]*?\[\/\/\]: # \(dependabot-end\)\s*/g'
    replace: ''
  - search: '/<br\s*\/?>\s*/g'
    replace: ''
version-resolver:
  major:
    labels: ['major', 'xfeature', 'xfeat']
  minor:
    labels: ['feat', 'feature', 'minor']
  patch:
    labels: ['patch', 'fix', 'chore', 'bugfix', 'bug']
  default: patch
template: |
  ## Changes

  $CHANGES
```

**`.github/workflows/semantic_release.yml`** — cuts the GitHub release on a `v*.*.*` tag; `rc/alpha/beta` tags marked prerelease.
```yaml
name: Semantic Release

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - id: pre
        name: Mark prerelease for rc/beta/alpha tags
        run: |
          if echo "${GITHUB_REF_NAME}" | grep -Eiq '(rc|alpha|beta|dev|a|b)[0-9]*$'; then
            echo "prerelease=true" >> "$GITHUB_OUTPUT"
          else
            echo "prerelease=false" >> "$GITHUB_OUTPUT"
          fi
      - uses: softprops/action-gh-release@v3
        with:
          generate_release_notes: true
          prerelease: ${{ steps.pre.outputs.prerelease }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**`.github/workflows/release.yml`** — *Create Release ZIP*. Required when `hacs.json` has `zip_release: true`: builds `<domain>.zip` (integration files at the **zip root**) and attaches it to the published release, so HACS has the asset to download. `cd` into the package before zipping so paths are root-relative (not `custom_components/<domain>/…`). Uses the `gh` CLI to upload (the old `actions/upload-release-asset@v1` is archived — don't reinstate it).
```yaml
name: Create Release ZIP

on:
  release:
    types: [published]

permissions:
  contents: write

jobs:
  build:
    name: Create Release Asset
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Create ZIP file
        run: |
          cd custom_components/<domain>
          zip -r "$GITHUB_WORKSPACE/<domain>.zip" . -x '*/__pycache__/*' '*.pyc'

      - name: Upload release asset
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh release upload "${{ github.event.release.tag_name }}" "$GITHUB_WORKSPACE/<domain>.zip" --clobber
```

**`.github/workflows/hassfest_validate.yml`** — HA manifest/services/quality-scale validation.
```yaml
name: Hassfest

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: home-assistant/actions/hassfest@master
```

**`.github/workflows/hacs_validate.yml`** — HACS 8-check validation. **No `ignore:` input** — ignoring any check disqualifies the repo from the default store.
```yaml
name: HACS Validation

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration
```

**`.github/workflows/python_validate.yml`** — ruff + pyright on HA's floor Python (keep the matrix in lockstep with `pyproject.toml` / `pyrightconfig.json`).
```yaml
name: Python Validate

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint-and-type:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.14"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install homeassistant ruff pyright
          [ -f requirements.test.txt ] && pip install -r requirements.test.txt || true
      - name: Ruff
        run: ruff check custom_components/
      - name: Pyright
        run: python -m pyright custom_components/
```

**`.github/workflows/check-manifest-version.yml`** + **`scripts/manifest_gate.py`** + **`tests/test_manifest_gate.py`** — version gate **against the last published release** (not `main` HEAD). ⚠️ **The decision logic lives in a unit-tested Python script, NOT inline bash.** A real bug shipped from inline-bash logic: it used strict equality (`suggested == manifest`), so a `chore` PR sitting at `1.2.0` (riding a minor already merged this cycle) was rejected with "expected v1.1.1" — even though `1.2.0` is a perfectly valid in-cycle version. Inline gate logic is untested and regresses silently; extract it so it has a test suite. The gate must enforce a **floor** (≥ the label's minimum bump from the last release — catches under-bumps) **and** a **ceiling** (≤ the in-cycle version on `main`, or this PR's own label bump if it escalates the tier — catches over-bumps), with prerelease versions only needing to differ and `dependabot[bot]` exempt.

The workflow just gathers inputs and shells out:
```yaml
name: Check Manifest Version

on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
  push:
    branches-ignore:
      - main

permissions:
  contents: read
  pull-requests: read

jobs:
  check_version:
    name: Manifest version bumped vs last release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Gather versions and labels
        id: gather
        if: github.event_name == 'pull_request'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BASE_REF: ${{ github.event.pull_request.base.ref }}
        run: |
          MANIFEST=$(ls custom_components/*/manifest.json | head -1)
          echo "pr_version=$(jq -r '.version' "$MANIFEST")" >> "$GITHUB_OUTPUT"
          TAG=$(gh release list --exclude-drafts --limit 1 --json tagName --jq '.[0].tagName')
          echo "last_release=${TAG#v}" >> "$GITHUB_OUTPUT"
          git fetch origin "$BASE_REF" --depth=1 -q || true
          echo "main_version=$(git show "origin/$BASE_REF:$MANIFEST" 2>/dev/null | jq -r '.version' || echo '')" >> "$GITHUB_OUTPUT"
          echo "labels=$(gh pr view ${{ github.event.pull_request.number }} --json labels -q '[.labels[].name]|join(",")')" >> "$GITHUB_OUTPUT"

      # All decision logic lives in scripts/manifest_gate.py (unit-tested in
      # tests/test_manifest_gate.py) so the gate can't silently regress again.
      - name: Version gate
        if: github.event_name == 'pull_request' && github.event.pull_request.user.login != 'dependabot[bot]'
        run: |
          python3 scripts/manifest_gate.py \
            --last-release "${{ steps.gather.outputs.last_release }}" \
            --main-version "${{ steps.gather.outputs.main_version }}" \
            --pr-version "${{ steps.gather.outputs.pr_version }}" \
            --labels "${{ steps.gather.outputs.labels }}"
```

`scripts/manifest_gate.py` — pure `evaluate()` + thin CLI (add `"scripts/*" = ["T20", "INP001"]` to ruff `per-file-ignores`):
```python
"""Decide whether a PR's manifest version is a valid bump for its label."""
from __future__ import annotations

import argparse
import re
import sys

Version = tuple[int, int, int]
_PRERELEASE = re.compile(r"(rc|alpha|beta|a|b|dev)[0-9]*$", re.IGNORECASE)


def is_prerelease(version: str) -> bool:
    return _PRERELEASE.search(version) is not None


def parse_semver(version: str) -> Version:
    match = re.match(r"^([0-9]+)\.([0-9]+)\.([0-9]+)", version)  # de-anchored: tolerate rcN
    if not match:
        raise ValueError(f"cannot parse version: {version!r}")
    return int(match[1]), int(match[2]), int(match[3])


def label_bump(labels: list[str]) -> str | None:
    joined = " ".join(labels).lower()
    if re.search(r"xfeat|xfeature|major", joined):
        return "major"
    if re.search(r"feat|feature|minor", joined):
        return "minor"
    if re.search(r"fix|patch|chore|bugfix|bug", joined):
        return "patch"
    return None


def _bump(base: Version, tier: str) -> Version:
    major, minor, patch = base
    if tier == "major":
        return (major + 1, 0, 0)
    if tier == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _fmt(version: Version) -> str:
    return "v{}.{}.{}".format(*version)


def evaluate(last_release: str, main_version: str, pr_version: str,
             labels: list[str], *, dependabot: bool = False) -> tuple[bool, str]:
    if dependabot:
        return True, "dependabot exempt"
    base = parse_semver(last_release or "0.0.0")
    if is_prerelease(pr_version):
        if pr_version == last_release:
            return False, f"prerelease v{pr_version} must differ from last release"
        return True, "prerelease differs from last release"
    pr = parse_semver(pr_version)
    if pr == base:
        # Graduating an rc line to its same-number final (2.0.0rc19 -> 2.0.0): the
        # de-anchored parse makes both (x,y,z), but AwesomeVersion knows final > its
        # own prerelease, so allow it instead of demanding a label-derived bump.
        if is_prerelease(last_release):
            return True, f"final v{pr_version} graduates prerelease {last_release}"
        return False, f"manifest v{pr_version} == last release; bump it"
    tier = label_bump(labels)
    if tier is None:
        return True, "no managed label; version only needs to differ from last release"
    floor = _bump(base, tier)
    if pr < floor:
        return False, f"{tier} needs >= {_fmt(floor)}, got v{pr_version} (under-bumped)"
    main = parse_semver(main_version) if main_version else floor
    ceiling = max(floor, main)
    if pr > ceiling:
        return False, f"v{pr_version} exceeds the justified bump (expected <= {_fmt(ceiling)} for {tier})"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--last-release", required=True)
    parser.add_argument("--main-version", default="")
    parser.add_argument("--pr-version", required=True)
    parser.add_argument("--labels", default="", help="comma-separated label names")
    parser.add_argument("--dependabot", action="store_true")
    args = parser.parse_args(argv)
    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    ok, reason = evaluate(args.last_release, args.main_version, args.pr_version,
                          labels, dependabot=args.dependabot)
    print(("✅ " if ok else "❌ ") + reason)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

`tests/test_manifest_gate.py` — load the standalone script by path (it isn't an importable package) and cover the matrix, **including the regression that shipped** (chore riding an in-cycle minor) and the over-bump it must still catch:
```python
"""Unit tests for the manifest version gate decision logic."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "manifest_gate", Path(__file__).parents[1] / "scripts" / "manifest_gate.py"
)
assert _SPEC and _SPEC.loader
manifest_gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(manifest_gate)
evaluate = manifest_gate.evaluate


def ok(*args, **kwargs) -> bool:
    return evaluate(*args, **kwargs)[0]


def test_unchanged_vs_last_release_fails() -> None:
    assert not ok("1.1.0", "1.1.0", "1.1.0", ["fix"])

def test_feature_minor_bump_passes() -> None:
    assert ok("1.1.0", "1.1.0", "1.2.0", ["feature"])

def test_feature_only_patch_under_bumps() -> None:
    assert not ok("1.1.0", "1.1.0", "1.1.1", ["feature"])

def test_chore_rides_in_cycle_minor() -> None:  # the shipped regression
    assert ok("1.1.0", "1.2.0", "1.2.0", ["chore"])

def test_chore_overbump_beyond_cycle_fails() -> None:
    assert not ok("1.1.0", "1.2.0", "2.0.0", ["chore"])

def test_breaking_major_passes() -> None:
    assert ok("1.1.0", "1.2.0", "2.0.0", ["xfeat"])

def test_prerelease_only_needs_to_differ() -> None:
    assert ok("1.1.0", "1.1.0", "2.0.0rc1", ["feature"])
    assert not ok("2.0.0rc1", "2.0.0rc1", "2.0.0rc1", ["feature"])

def test_final_graduates_prerelease() -> None:  # 2.0.0rc19 -> 2.0.0, even feature-labelled
    assert ok("2.0.0rc19", "2.0.0rc20", "2.0.0", ["feature"])
    assert not ok("2.0.0", "2.0.0", "2.0.0", ["feature"])  # already final -> still must bump

def test_dependabot_exempt() -> None:
    assert ok("1.1.0", "1.1.0", "1.1.0", [], dependabot=True)

def test_no_managed_label_passes_when_changed() -> None:
    assert ok("1.1.0", "1.1.0", "1.1.5", [])
```

**`.github/dependabot.yml`** — `github-actions` is the real value; `pip` covers `requirements.test.txt` when pinned. `chore` prefix → autolabeler maps to patch.
```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    commit-message:
      prefix: chore
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    commit-message:
      prefix: chore
```

#### Optional: per-turn reminder hooks (personal `~/.claude`)

The repo `CLAUDE.md` rule is the **canonical, shareable** enforcement (it ships with the repo, applies to everyone). These two personal hooks are a *convenience* layer on top — they live in your own `~/.claude/` and re-arm the rules every session/turn so they don't drift down-context in a long session. **Marker-file gated** so each only fires where it applies: the skill anchor on an integration repo (`custom_components/*/manifest.json`), the CI-convention anchor on any repo using this workflow stack (`.github/workflows/create-dev-pr.yml`) — which includes this skill's own repo, not just scaffolded integrations.

`~/.claude/settings.json` (merge into existing `hooks`):
```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume|compact",
        "hooks": [{ "type": "command", "command": "bash \"$HOME/.claude/hooks/ha-skill-reinvoke.sh\"" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "bash \"$HOME/.claude/hooks/ha-resources-reminder.sh\"" }] }
    ]
  }
}
```

`~/.claude/hooks/ha-skill-reinvoke.sh` — re-arms the skill rule at session start (compaction drops the skill's guidance; stdout is injected as session context):
```bash
#!/usr/bin/env bash
# SessionStart: in an HA custom-integration repo, re-arm the ha-integration skill rule.
if ls custom_components/*/manifest.json >/dev/null 2>&1; then
  cat <<'MSG'
[ha-integration] This repo is a Home Assistant custom integration. Invoke the `ha-integration` skill via the Skill tool BEFORE modifying any integration code this session, and re-invoke after every /compact.
MSG
fi
```

`~/.claude/hooks/ha-resources-reminder.sh` — per-turn anchors; stdout is injected as prompt context, so keep each line terse:
```bash
#!/usr/bin/env bash
# UserPromptSubmit: per-turn anchors. Independent, each marker-gated.

# HA-integration repos: skill + quality anchors.
if ls custom_components/*/manifest.json >/dev/null 2>&1; then
  msg="[ha-integration] ha-integration skill active before integration edits · keep quality_scale.yaml honest · verify HA APIs at developers.home-assistant.io"
  [ -d firmware ] && msg="$msg · run scripts/sync_render.py after firmware/ edits"
  echo "$msg."
fi

# Any repo on this workflow stack (the skill repo AND scaffolded integrations):
# the commit/PR conventions that drift down-context mid-session.
if [ -f .github/workflows/create-dev-pr.yml ]; then
  echo "[ci-conventions] commit & PR subject = ONE tight imperative (lowercase after the colon, no trailing period, no comma-joined dual subject). create-dev-pr.yml OWNS the PR — never hand-create it with gh pr create; push the branch and let the action open/update it (PR title mirrors the winning commit subject). Branch off main; bump the manifest/plugin version once, as the last commit before merge."
fi
```

`chmod +x` both scripts. Editing a hook *script* takes effect immediately (the hook re-execs it each turn); editing `settings.json` to add/remove a hook needs a `/hooks` open or restart to re-register.

---

### manifest.json key order

Always `domain` first, `name` second, then remaining keys alphabetically:
```json
{
  "domain": "my_device",
  "name": "My Device",
  "codeowners": ["@username"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/username/repo",
  "integration_type": "device",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/username/repo/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

`integration_type` is **required** — choose: `device` / `hub` / `service` / `entity` / `hardware` / `helper` / `system` / `virtual`.

`issue_tracker` is **required by HACS validation** — omitting it fails the `integration_manifest` check.

---

### Implementation patterns

**`__init__.py`**
- Config-entry-based only — no new YAML integrations.
- `async_setup_entry`:
  - Store runtime state on `entry.runtime_data` (HA 2024.2+, preferred over `hass.data[DOMAIN][entry.entry_id]`)
  - Call `await coordinator.async_config_entry_first_refresh()`
  - Call `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`
  - Raise `ConfigEntryNotReady` for transient failures (device offline, timeout, network error)
  - Raise `ConfigEntryAuthFailed` for invalid/expired credentials
- `async_unload_entry`: call `async_unload_platforms`; `entry.runtime_data` cleaned up automatically. **Also `await coordinator.async_shutdown()` when the unload succeeds** — `async_unload_platforms` removes entities but does **not** stop the coordinator's `update_interval` timer or its request-refresh **debouncer**, which then linger across unload/reload (and fail pytest's `verify_cleanup` with "Lingering timer"). Shutting down is correct on reload too (a fresh coordinator is built in the next `async_setup_entry`).
- `async_remove_config_entry_device(hass, entry, device_entry) -> bool` — **implement it if the integration creates any device.** HA only shows the device **Delete** button when this handler exists; without it users are stuck with the device. Return `True` to allow deletion (or `False` to block while the device is still live). This is the Gold `stale-devices` rule — **do not `exempt` `stale-devices` just because there's a single static device**; a created device still needs a removal path, so it's `done` (via this handler), not `exempt`. Keep `quality_scale.yaml` honest: an optimistic `exempt` hides a real gap.
- Include `"notify"` in `PLATFORMS` — loaded via `async_forward_entry_setups` like any other platform

**Notify platform (modern pattern — HA 2023.8+)**
```python
# notify.py
from homeassistant.components.notify import NotifyEntity

class MyNotifyEntity(NotifyEntity):
    _attr_has_entity_name = True
    _attr_name = "Notify"
    _attr_unique_id = f"{device_id}_notify"

    async def async_send_message(self, message: str, title: str | None = None, **kwargs) -> None:
        data = kwargs.get("data") or {}
        ...

async def async_setup_entry(hass, entry, async_add_entities):
    opts = {**entry.data, **entry.options}
    async_add_entities([MyNotifyEntity(hass, opts[CONF_DEVICE_ID])])
```
⚠️ **Do NOT use** `discovery.async_load_platform` + `BaseNotificationService` — deprecated, silently fails in recent HA versions.
⚠️ `NotifyEntity` only supports `message` and `title` — `data` is **not in its service schema**. If you need custom payload fields (animations, sounds, colours, etc.), register the service directly instead:
```python
# notify.py
from homeassistant.components.notify.const import ATTR_DATA, ATTR_MESSAGE, ATTR_TITLE
from homeassistant.components.notify.const import DOMAIN as NOTIFY_DOMAIN

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE):   cv.string,
    vol.Optional(ATTR_DATA):    dict,
})

def make_notify_handler(hass: HomeAssistant, device_id: str):
    async def async_handle(call: ServiceCall) -> None:
        data = call.data.get(ATTR_DATA) or {}
        ...
    return async_handle

# __init__.py async_setup_entry:
if not hass.services.has_service(NOTIFY_DOMAIN, device_id):
    hass.services.async_register(
        NOTIFY_DOMAIN, device_id, make_notify_handler(hass, device_id), schema=SERVICE_SCHEMA
    )
# async_unload_entry:
if hass.services.has_service(NOTIFY_DOMAIN, device_id):
    hass.services.async_remove(NOTIFY_DOMAIN, device_id)
```
This creates `notify.{device_id}` (e.g. `notify.pimoroni_unicorn_studio`) with full data support.

**`config_flow.py`**
- `class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):` — `domain=` is a keyword arg, not a class attribute
- Include `OptionsFlow` (not `OptionsFlowHandler` — that name is deprecated) when the integration has configurable options
- Implement `async_step_reauth` for expired/invalid auth (Silver requirement)
- Implement `async_step_reconfigure` for changing connection settings (Gold requirement)
- `vol.Schema` — align into three columns: key | `default=` | type:
  ```python
  DATA_SCHEMA = vol.Schema({
      vol.Required(CONF_HOST,  default="192.168.1.1"): str,
      vol.Required(CONF_PORT,  default=8080):          int,
  })
  ```

**Entity platform files**
- Extend `CoordinatorEntity` (polling) or `Entity` (push)
- Access runtime state via `entry.runtime_data` not `hass.data[DOMAIN][entry.entry_id]`
- Use `DeviceInfo` TypedDict (from `homeassistant.helpers.device_registry`) — not a plain dict:
  ```python
  from homeassistant.helpers.device_registry import DeviceInfo
  @property
  def device_info(self) -> DeviceInfo:
      return DeviceInfo(identifiers={(DOMAIN, self._device_id)}, name="My Device", ...)
  ```
- Set `unique_id` on all entities
- **`_attr_has_entity_name = True` is mandatory for new integrations** — entity name identifies only the data point; main feature entity sets `_attr_name = None` so only device name shows
- Set `_attr_translation_key = "my_key"` for translated entity names/states (pairs with `strings.json` `entity` section)
- Use `_attr_entity_category = EntityCategory.DIAGNOSTIC` (read-only info like RSSI) or `EntityCategory.CONFIG` (settings that change device behaviour) for non-primary entities
- Prefer `_attr_*` class/instance attributes over property methods for static values — only use properties for dynamic/state-dependent values
- Implement `_attr_available` to reflect device reachability
- Read state from `self.coordinator.data` only — never do I/O in properties
- Don't pass `update_before_add=True` to `async_add_entities`. It papers over a real gap and schedules a refresh **debouncer timer** that lingers in tests and frozen-clock runs. The gap: `CoordinatorEntity` does **not** push initial state on add, so a push-style entity (one that sets `_attr_native_value` inside `_handle_coordinator_update`) reads `unknown` until the next poll. Fix it properly — either compute `native_value` as a **property** off `self.coordinator.data` (always current), or call `self._handle_coordinator_update()` at the end of `async_added_to_hass` (after `await super().async_added_to_hass()`) to populate from the already-loaded coordinator data. `first_refresh` runs before entities are added, so the data is there.
- **A list/collection sensor's state should be the `len()` count, with the items in an attribute** — not a timestamp or the raw list. (`last_updated`/`last_changed` are already built-in state attributes; don't re-add them.) Add `_attr_state_class = MEASUREMENT` so the count graphs.
- **A `device_class` constrains which `state_class` is legal — verify the pair against the authoritative source, never guess.** HA hard-codes the allowed combinations in `DEVICE_CLASS_STATE_CLASSES` (`homeassistant/components/sensor/const.py`); a disallowed pair logs *"is using state class X which is impossible considering device class Y"* and silently drops long-term statistics. The trap that bit hard: `SensorDeviceClass.MONETARY` permits **only `{SensorStateClass.TOTAL}`** — `MEASUREMENT` is invalid for monetary. Don't "fix" an invalid combo by **deleting** `state_class` (that kills LTS entirely, a worse regression than the warning) — switch to a *valid* one. So a fluctuating money **balance** (settle-up debt, account balance) is `device_class=MONETARY` + `state_class=TOTAL`, not `MEASUREMENT`. Before setting any `device_class`/`state_class` pair, check the current mapping at https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sensor/const.py (or the device-class table at developers.home-assistant.io/docs/core/entity/sensor) — the mapping changes between HA versions. Lock the chosen pair with an attribute test so a future rewrite can't silently drop it.

**`EntityDescription` pattern** — preferred when an integration exposes many similar entities:
```python
@dataclass(frozen=True, kw_only=True)
class MySensorDescription(SensorEntityDescription):
    value_fn: Callable[[MyData], float]

SENSORS: tuple[MySensorDescription, ...] = (
    MySensorDescription(key="temperature", translation_key="temperature", value_fn=lambda d: d.temp),
    MySensorDescription(key="humidity",    translation_key="humidity",    value_fn=lambda d: d.humidity),
)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(MySensor(coordinator, desc) for desc in SENSORS)
```

**`UpdateEntity` (firmware/OTA install)**
- `_attr_in_progress` only **greys out the dashboard install button** — it does **not** stop a programmatic re-entry. A service call, automation, or two near-simultaneous dashboard clicks can still re-enter `async_install` while an install is mid-flight, double-pushing the OTA. Add an **explicit re-entry guard** at the top of `async_install` (after any can't-install checks), windowed so a crashed/timed-out install can't wedge the entity forever:
  ```python
  async def async_install(self, version, backup, **kwargs) -> None:
      if self._reflash:
          raise HomeAssistantError("Layout change — reflash via USB, not OTA.")
      if self._installing and time.monotonic() - self._install_started < INSTALL_TIMEOUT:
          raise HomeAssistantError("An update is already in progress for this device.")
      self._installing = True
      self._install_started = time.monotonic()
      self._attr_in_progress = True
      self.async_write_ha_state()
      ...  # push the OTA
  ```
  Clear `_installing` when the new version lands (or the same window elapses) in whatever resyncs state from the device manifest. The `in_progress` flag is for the UI; the boolean+timestamp is the actual lock.

**`DataUpdateCoordinator` (polling)**
- `update_interval` minimum 5 s
- Set `always_update=False` when API responses support `__eq__` — avoids unnecessary state machine writes
- Raise `ConfigEntryAuthFailed` on auth errors inside `_async_update_data`
- Raise `UpdateFailed` on other errors; use `UpdateFailed(retry_after=60)` for rate-limited APIs
- For push APIs: use `coordinator.async_set_updated_data(data)` instead of adapting to polling

**Entity push subscriptions**
- Subscribe in `async_added_to_hass`, unsubscribe in `async_will_remove_from_hass` — prevents resource leaks
- Never subscribe in `__init__`

**`ConfigEntry` mutation**
- Never mutate `ConfigEntry` directly — always use `hass.config_entries.async_update_entry(entry, data=..., options=...)`

**Logging** (Silver `log-when-unavailable`; HA logging conventions)
- **The coordinator already gives you `log-when-unavailable` for free.** When `_async_update_data` raises `UpdateFailed`, `DataUpdateCoordinator` logs the *first* failure at **ERROR**, subsequent consecutive failures at **DEBUG** (no spam), and logs **recovery** automatically. So **do not** wrap the fetch in your own try/log — manual error logging there is double-logging and *fails* the rule. Same for `ConfigEntryNotReady`/`ConfigEntryAuthFailed`: HA logs the reason once; don't also `_LOGGER.exception(...)` in `async_setup_entry` (delete broad `try/except: log; raise` wrappers — they spam and add nothing).
- **Don't log-and-raise.** Raise the right exception and let HA log it: transient → `UpdateFailed`/`ConfigEntryNotReady`; auth → `ConfigEntryAuthFailed`; service/action errors → `HomeAssistantError`/`ServiceValidationError` (Silver `action-exceptions`). Logging *and* raising the same condition is noise.
- **Level discipline:** `INFO` is shown by default → use it almost never. **Setup / unload / teardown lifecycle = `DEBUG`, not `INFO`.** `WARNING` = recoverable thing the user should know; `ERROR` = unexpected, actionable bug (never for expected transient failures — those are exceptions HA handles). `DEBUG` = per-poll / developer detail.
- **Lazy `%` args, never f-strings:** `_LOGGER.debug("added %s", key)` not `f"added {key}"` — ruff `G004` / pylint `logging-fstring-interpolation` enforce. f-string args evaluate even when the level is disabled.
- **Never log secrets** — credentials, API keys, tokens, raw auth responses.
- Logger name (`logging.getLogger(__name__)`) already carries the module path — don't prefix messages with the integration name or "Home Assistant".
- Remove a module-level `_LOGGER` that ends up unused (e.g. after deleting lifecycle spam) — ruff won't flag an unused module global, so it lingers silently.

**Custom services**
- Register in `async_setup` (not `async_setup_entry`) to avoid duplicate registration across multiple config entries
- Use `async_register_platform_entity_service()` for entity-targeted actions
- Document in `services.yaml`; add icons in `icons.json`
- A `selector: config_entry` renders a field labelled "Integration" (hardcoded in the HA frontend). To present a device dropdown, use `selector: device` with `integration: {domain}`, then resolve the HA device → config entry in the handler via `device_registry.async_get(hass).async_get(id)`.

**`services.yaml` + `strings.json` (hassfest rules)**
- The modern convention: `services.yaml` carries only field **structure** (selectors, `required`, `default`, collapsible `sections`); names/descriptions live in `strings.json` under a top-level `services` key (`services.{svc}.name/description`, `.fields.{key}.name/description`, `.sections.{key}.name`). Field keys are flat in `strings.json` even when nested in a `sections` block in `services.yaml`. Keep `translations/en.json` a copy of `strings.json`.
- **hassfest forbids literal URLs in `strings.json` descriptions** — `the string should not contain URLs`. Use plain text, or a `{placeholder}` filled via `description_placeholders` in the flow step. A markdown image `![x]({url})` with a placeholder is fine (no literal `http`).
- Collapsible service form: `fields: { appearance: { collapsed: true, fields: {...} } }` — sections are UI-only; the call data stays flat, so the voluptuous schema is unaffected.

**Custom frontend panel** (sidebar UI beyond config/options)
- **Register integration-global resources in `async_setup`, not `async_setup_entry`.** The static-path serve and the `websocket_api` command registration are process-global, register-once resources — like services, they belong in `async_setup`, which HA calls **exactly once, before any entry, never in parallel.** Doing them per-entry *races*: with multiple devices, two entries set up concurrently and both pass a `hass.data` "already registered?" guard before either's `await` completes, so the second `async_register_static_paths` raises aiohttp `RuntimeError: Added route ... already registered` and fails that entry's setup. The **sidebar panel** is the one exception — it's gated on a per-entry option (`show_panel`) and toggled at runtime, so it stays entry-driven; guard it with a `hass.data` flag set **synchronously before** the `await` (claim-then-register) to close the same race, and `frontend.async_remove_panel` on last unload.
  ```python
  from homeassistant.components import frontend, panel_custom, websocket_api
  from homeassistant.components.http import StaticPathConfig

  async def async_setup(hass, config):  # once per process — no entry parallelism
      await hass.http.async_register_static_paths(
          [StaticPathConfig("/{domain}_panel/editor.js", str(Path(__file__).parent / "panel" / "editor.js"), False)])
      websocket_api.async_register_command(hass, ws_handler)  # all ws commands here too
      return True

  async def _refresh_panel(hass):  # from async_setup_entry — option-gated, toggleable
      if _panel_wanted(hass) and not hass.data.get(f"{DOMAIN}_panel"):
          hass.data[f"{DOMAIN}_panel"] = True  # claim BEFORE the await to close the parallel-setup race
          await panel_custom.async_register_panel(hass, frontend_url_path="{domain}",
              webcomponent_name="{domain}-panel", module_url="/{domain}_panel/editor.js",
              sidebar_title="...", sidebar_icon="mdi:view-grid", require_admin=True)
  # last unload: frontend.async_remove_panel(hass, "{domain}")
  ```
  Add `"http"`, `"panel_custom"`, `"websocket_api"` to manifest `dependencies`.
- Back the panel with `websocket_api` commands (`@websocket_api.websocket_command({...})` + `async_register_command`), not custom REST. The panel element gets `hass` injected and calls `hass.callWS({type: "..."})`.
- Pyright flags `websocket_api.websocket_command`/`async_response` as private — set `"reportPrivateImportUsage": false` in `pyrightconfig.json` (standard HA-integration usage).
- Frontend: a Lit + TS bundle built with esbuild to a **committed** `panel/editor.js` (HACS ships it, no build on the user's box). A CI job runs `npm ci && npm run build` and `git diff --exit-code` to prove the committed bundle matches source. The JS is not Python, so ruff/pyright skip it; keep render logic in the **backend** and send the browser finished pixels/data so the JS stays display-only.
- If the integration reuses MicroPython firmware render code under CPython (e.g. for a pixel-accurate preview), bundle a copy inside the package and add a CI sync check (hash/transform compare against `firmware/`) so the copies can't drift; exclude that copy from ruff (`extend-exclude`) and pyright (`exclude`).

**Diagnostics platform** (Gold requirement — add `diagnostics.py`):
```python
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_PASSWORD, CONF_API_KEY, "token"}

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    return async_redact_data({"entry": entry.as_dict(), "data": entry.runtime_data}, TO_REDACT)
```
No registration needed — HA discovers it automatically from the file name.

**Config entry migration** — implement in `__init__.py` when stored `entry.data` schema changes:
```python
# In config flow:
class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2        # bump for breaking changes (fails setup if no handler)
    MINOR_VERSION = 1  # bump for backwards-compatible changes (setup continues without handler)

# In __init__.py:
async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version == 1:
        new_data = {**entry.data, "new_field": "default"}
        hass.config_entries.async_update_entry(entry, data=new_data, version=2, minor_version=1)
    return True
```
Major version bump without `async_migrate_entry` = setup **fails** for existing users. Always implement the handler before shipping a major bump.

---

### File structure conventions

Split files by responsibility. Rule of thumb: if `__init__.py` exceeds ~100 lines of logic, extract.

| File | Purpose |
|------|---------|
| `__init__.py` | `async_setup_entry`, `async_unload_entry`, `async_migrate_entry` only — no business logic |
| `coordinator.py` | `DataUpdateCoordinator` subclass |
| `api.py` | All I/O to the device/service — no HA imports; makes it independently testable |
| `models.py` | Dataclasses and type aliases for device data |
| `entity.py` | Shared base entity class when multiple platforms extend the same base |
| `const.py` | Constants only — no imports from other local modules |
| `config_flow.py` | Config + options flows |
| `diagnostics.py` | `async_get_config_entry_diagnostics` |
| `services.py` | `async_setup_services(hass)` called from `async_setup`; keeps `__init__.py` clean |
| `migration.py` | `async_migrate_entry` logic if complex; import into `__init__.py` |
| `helpers.py` / `util.py` | Pure functions shared across platforms |
| `<platform>.py` | One per HA platform (`sensor.py`, `button.py`, etc.) |

`api.py` is the most important split — it decouples device logic from HA lifecycle and makes unit testing possible without a running HA instance.

---

### Typing

Complete, correct typing is a **Platinum requirement** — not cosmetic. It catches contract violations between platforms, coordinator data shapes, and config entry contents at development time rather than runtime. Every file must pass `python -m pyright custom_components/` with zero errors before a PR is ready. Suppressions are failures, not fixes.

**Always add at top of every file:**
```python
from __future__ import annotations
```
Enables deferred annotation evaluation — avoids forward-reference quoting and circular import issues.

**`TYPE_CHECKING` for expensive or circular imports:**
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
```

**Typed `ConfigEntry`** — avoids untyped `entry.runtime_data`:
```python
# In coordinator.py or models.py:
from homeassistant.config_entries import ConfigEntry
type MyConfigEntry = ConfigEntry[MyCoordinator]  # Python 3.12+ / HA 2024.x

# In platform files:
async def async_setup_entry(hass: HomeAssistant, entry: MyConfigEntry, ...) -> None:
    coordinator = entry.runtime_data  # typed as MyCoordinator, no cast needed
```

**Avoid `# type: ignore`** — at Platinum quality, type suppressions are a violation, not a shortcut. The common HA patterns that tempt `# type: ignore` all have proper solutions:
- `hass.data[DOMAIN]` is untyped → don't use it; use `entry.runtime_data` with typed `ConfigEntry` instead
- `entry.runtime_data` assignment errors → solved by the typed `ConfigEntry` alias above
- Third-party library missing stubs → contribute stubs or use `cast()` with a comment explaining why

Only acceptable suppression: `# type: ignore[import-untyped]` on a third-party import with no available stubs, where contributing stubs is out of scope.

**MicroPython firmware files** — exclude from Pyright entirely in `pyrightconfig.json`:
```json
{
  "exclude": ["firmware/"],
  "typeCheckingMode": "standard"
}
```

**HA itself is fully typed** — import its types directly rather than re-typing them:
```python
from homeassistant.helpers.typing import StateType, ConfigType, DiscoveryInfoType
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
```

---

### Testing — mock at the boundary, not your own code

The most dangerous test is the one that passes while the integration is broken. It happens when a test **patches the integration's own functions** instead of the external dependency.

**Mock only at the external boundary** — the third-party client, socket, or library (`imaplib.IMAP4_SSL`, `aiohttp` via `aioclient_mock`, the vendored device lib, `serial`). Then the integration's *own* wiring runs: reading `entry.data`/`entry.options` into attributes, building requests, parsing responses, populating the coordinator. **Never patch your own `_async_update_data`, `email_triage`, `api.fetch`, etc.** — doing so stubs out exactly the code a refactor is most likely to break, so the test stays green through the regression.

> **Real failure that motivated this rule:** a `runtime-data` refactor dropped the `entry.data → self.host/credential` reads from the coordinator's `__init__`. Every coordinator test passed because they patched the data-fetch function, so the missing attributes were never read. Setup then crashed at runtime with `AttributeError: object has no attribute 'host'`. A test that mocks the *transport* and runs the real fetch (or even just constructs the coordinator and asserts it read the config) fails loudly. The fix-forward is also the `api.py` split: pass config as explicit constructor args so pyright catches a missing field, instead of a helper reaching into `self.<attr>` set elsewhere (an untyped runtime contract that survives refactors silently).

**`test-before-setup` means a real config-entry setup.** Add a `MockConfigEntry`, call `hass.config_entries.async_setup(entry.entry_id)`, and assert `entry.state is ConfigEntryState.LOADED` plus that entities exist — with only the transport mocked. This exercises `async_setup_entry` end to end (credential reads, `async_config_entry_first_refresh`, `runtime_data`, platform forward, entity creation). A `async_setup_component(hass, DOMAIN, {})` test only proves the (unused) YAML path returns `True` and is near-worthless for a config-entry integration. **If you scaffold an `init_integration` fixture, actually use it** — an unused setup fixture is a tell that the highest-value test was skipped.

**If the integration allows multiple devices, test two entries set up in parallel.** A single-entry `LOADED` test can't catch integration-global registration done per-entry (static paths, websocket commands, the panel) — the clash only fires on the *second* concurrent entry. Add a test that `add_to_hass`es two `MockConfigEntry`s and `await asyncio.gather(hass.config_entries.async_setup(e1.entry_id), …(e2.entry_id))`, then asserts **both** `state is ConfigEntryState.LOADED`. On the buggy per-entry code the second entry goes `SETUP_ERROR` with aiohttp `RuntimeError: Added route ... already registered`; it passes once the registration moves to `async_setup`. Unload both entries at the end, and if a fixture starts a self-rescheduling timer (e.g. `mqtt_mock`'s periodic loop) override the `expected_lingering_timers` fixture to `True` **in that module only** so it tolerates the fixture's own timer without masking leaks elsewhere.

**Unit-test the pure logic directly** — regex parsers, date/format extraction, data transforms (`order_parse`, `voucher_parse`, `sort_orders`, …) take a string/object and return a value with no HA and no mocks. They carry the highest regression risk and are the cheapest to cover; a parser with zero tests is a standing liability.

**Minimum coverage before claiming a tier:** config-flow (happy path + each error + reauth/reconfigure), a real setup-entry `LOADED` test (plus a **two-entry parallel `LOADED`** test if multiple devices are allowed), coordinator success + auth-failure + the credential-read path against a mocked transport, unload, and a unit test per parser. Wire the regression test *first* on any bug fix: confirm it fails on the unpatched code, then fix. **For Gold specifically, each rule gets a behavioural test (hassfest proves none of these):** reconfigure-success + reconfigure-error flow; diagnostics shape **and** redaction; `stale-devices` removal handler (`False` live / `True` gone); and a `translation_key`-resolution test that scrapes the keys used in code and asserts each exists in `strings.json`. A `done` without such a test is an unproven claim — see the *Prove the rule* note in the quality-scale section.

**Prefer future-dated fixtures over freezing the clock.** For an end-to-end test that feeds a real captured payload (e.g. an `.eml`) through the mocked transport and asserts a sensor populates: if the payload has dates that must be "upcoming" for the integration to surface them, **shift the fixture's dates forward at runtime** (parse + rewrite, or template) rather than `freeze_time(...)`. Freezing the clock breaks anything that depends on the loop's time — most painfully it stops the **debouncer** that an `update_before_add` refresh relies on, so the entity never populates (state stays `unknown`), *and* it leaves a timer scheduled at the frozen wall-clock time that fails teardown. A live clock with future-dated data sidesteps both and keeps the fixture's real bytes/encoding.

**Push coordinator data to entities without scheduling timers.** In a setup test, after `async_setup` + `async_block_till_done`, the entities may still read defaults (the on-add refresh is debounced and won't fire within `block_till_done`). Call `coordinator.async_update_listeners()` to notify entities from the **already-loaded** `coordinator.data` synchronously — unlike `async_refresh()` it schedules no new timer, so teardown stays clean. (The real fix for production is the `async_added_to_hass` initial-state population above; the test then needs no nudge at all.)

**Standalone helper scripts** (e.g. a `scripts/foo.py` CI tool) trip `T201` (print) and `INP001` (implicit namespace package) — add `"scripts/*" = ["T20", "INP001"]` to ruff `per-file-ignores`. Tests legitimately reach into private members; HA core ignores `SLF001` under `tests/` — mirror that (`"tests/**" = [..., "SLF001"]`). And `result["type"]`/`["errors"]`/`["reason"]` on a flow `ConfigFlowResult` are `reportTypedDictNotRequiredAccess` under pyright — use `result.get("type")` etc. in tests.

---

### Quality scale — target Platinum

Generate `quality_scale.yaml` with each rule set to `todo` or `done` as appropriate.

| Tier | Key requirements |
|------|-----------------|
| 🥉 Bronze | UI setup, basic coding standards, automated tests for config, basic docs |
| 🥈 Silver | + code owners, auto-recovery from errors without log spam, reauth flow (`async_step_reauth`) |
| 🥇 Gold | + auto-discovery, full translations, reconfigure flow (`async_step_reconfigure`), diagnostics, full test coverage |
| 🏆 Platinum | + complete type annotations, fully async (no blocking I/O), `always_update=False` where applicable, all HA coding standards |

Note: `PlatformNotReady` is for legacy `async_setup_platform` only — config-entry integrations use `ConfigEntryNotReady` instead.

`quality_scale.yaml` format:
```yaml
rules:
  config_flow: done
  test_coverage: done
  diagnostics:
    status: exempt
    comment: Device exposes no sensitive runtime data worth redacting.
```
Valid statuses: `done`, `todo`, `exempt` (exempt requires a `comment`).

**Scaffold `quality_scale.yaml` from the start** (even in Mode 2 on an existing integration that lacks it) and treat it as the definition-of-done — don't discover rules by hitting them. **hassfest gotchas:** the file must list **every** canonical rule with a valid status, `exempt` **must** carry a `comment`, and **only add `"quality_scale": "<tier>"` to `manifest.json` once every rule up to that tier is `done`/`exempt`** — claiming a tier makes hassfest enforce it (a single `todo` at/below that tier fails CI). So: ship the yaml as a tracking ledger first, omit the manifest tier until a tier is fully met.

⚠️ **Prove the rule, don't just claim it — hassfest checks structure, not behaviour.** A green hassfest + a `done` in `quality_scale.yaml` only proves the file is well-formed and the manifest tier is a valid enum; hassfest **never runs the integration**, so it cannot tell you `diagnostics.py` actually redacts, the reconfigure flow works, `async_remove_config_entry_device` returns correctly, or that a `translation_key` used in code resolves in `strings.json`. (For HA core those rules are enforced by human reviewers; for a custom integration nothing enforces them.) So **every rule you mark `done` must have a test that exercises it** — marking `done` off code-presence alone is "claiming compliance" without showing it. Concretely, each of these needs its own test, not just the code: `reconfiguration-flow` (a reconfigure-success + reconfigure-error flow test), `diagnostics` (asserts the payload shape **and** that secrets are `**REDACTED**`), `stale-devices` (`async_remove_config_entry_device` → `False` while the device is live, `True` once it's gone), `exception-translations`/`entity-translations`/`icon-translations` (a test that scrapes the `translation_key`s used in code and asserts each exists in `strings.json` — catches a typo'd key that hassfest passes). If a rule is genuinely untestable, it should be `exempt` with a comment, not an unproven `done`.

**Canonical rule set (cached 2026-06; re-verify at developers.home-assistant.io/docs/core/integration-quality-scale/ — rules change).** All must appear in `quality_scale.yaml`:
- **Bronze:** `action-setup`, `appropriate-polling`, `brands`, `common-modules`, `config-flow-test-coverage`, `config-flow`, `dependency-transparency`, `docs-actions`, `docs-high-level-description`, `docs-installation-instructions`, `docs-removal-instructions`, `entity-event-setup`, `entity-unique-id`, `has-entity-name`, `runtime-data`, `test-before-configure`, `test-before-setup`, `unique-config-entry`
- **Silver:** `config-entry-unloading`, `log-when-unavailable`, `entity-unavailable`, `action-exceptions`, `reauthentication-flow`, `parallel-updates`, `test-coverage`, `integration-owner`, `docs-installation-parameters`, `docs-configuration-parameters`
- **Gold:** `entity-translations`, `entity-device-class`, `devices`, `entity-category`, `entity-disabled-by-default`, `discovery`, `stale-devices`, `diagnostics`, `exception-translations`, `icon-translations`, `reconfiguration-flow`, `dynamic-devices`, `discovery-update-info`, `repair-issues`, `docs-use-cases`, `docs-supported-devices`, `docs-supported-functions`, `docs-data-update`, `docs-known-limitations`, `docs-troubleshooting`, `docs-examples`
- **Platinum:** `async-dependency`, `inject-websession`, `strict-typing`

Common `exempt`s for a local-push MQTT device integration: `appropriate-polling` (push, no polling), `reauthentication-flow` (no integration-level auth), `inject-websession` (no cloud HTTP), `async-dependency` (only sync libs run in executor), `dynamic-devices` (one device per entry).

---

### Code style

- Module docstring on every file
- Short single-line docstrings on all public functions and classes
- No inline comments unless the WHY is genuinely non-obvious
- No trailing summaries after edits
- ruff + pylint compliant; pyright standard mode

---

### Conventional Commits & Semantic Versioning

**Commit format:**
```
<type>[(<scope>)][!]: <description>

[optional body — one blank line after description]

[optional footers — BREAKING CHANGE: <detail>]
```

**Keep messages short.** Tight imperative subject; **subject-only by default**. Add a body ONLY when the *why* is non-obvious, or for breaking changes / migration notes — never to restate what the diff already shows. Long bodies that narrate the change are noise. Subject in imperative mood, lowercase after the colon, no trailing period.

**No AI-attribution trailers.** Don't append `Co-Authored-By: Claude`, tool/session links, or any "generated with…" line to commits — keep the authorship history clean. (If a harness injects such trailers by default, strip them.) A `Co-Authored-By:` for a *real* human collaborator is fine.

⚠️ **Enforce the trailer ban with a `commit-msg` hook — prose alone isn't enough.** A coding harness can inject `Co-Authored-By: Claude` / `Claude-Session:` on *every* commit via a standing instruction, which fights this rule turn after turn; the agent keeps "remembering" the harness default over the skill and regresses. The fix is deterministic enforcement at the git layer, not memory. Ship `.githooks/commit-msg` (terse-subject + no-narrative-body + **AI-trailer rejection**), add it to the scaffold's repo-root files, and tell contributors to enable it once per clone in `CLAUDE.md`: `git config core.hooksPath .githooks`.
```bash
#!/usr/bin/env bash
# Enforce terse commits: subject <=72 chars, no narrative body, no AI-attribution trailers.
# Body lines allowed only as trailers (Key: value), Closes/Refs/Fixes #N, or any body when a
# BREAKING CHANGE footer is present. Enable once per clone: git config core.hooksPath .githooks
msg_file="$1"
subject="$(grep -v '^#' "$msg_file" | sed -n '1p')"

if [ "${#subject}" -gt 72 ]; then
  echo "commit-msg: subject is ${#subject} chars (>72). Keep it terse." >&2
  exit 1
fi
case "$subject" in "Merge "*|"Revert "*|"fixup! "*|"squash! "*) exit 0 ;; esac

# Reject harness-injected AI-attribution trailers (this skill bans them). A real human
# Co-Authored-By is still fine.
if grep -v '^#' "$msg_file" | grep -Eqi '^Co-authored-by:[[:space:]]*Claude|^Claude-Session:|Generated with .*(Claude|Anthropic)'; then
  echo "commit-msg: AI-attribution trailer not allowed (strip Co-Authored-By: Claude / Claude-Session)." >&2
  exit 1
fi

if grep -q 'BREAKING CHANGE' "$msg_file"; then
  exit 0
fi

bad=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in \#*) continue ;; esac
  printf '%s' "$line" | grep -Eq '^[A-Za-z][A-Za-z-]*: ' && continue
  printf '%s' "$line" | grep -Eq '^(Closes|Refs|Fixes|Resolves) #' && continue
  bad="$line"
  break
done < <(grep -v '^#' "$msg_file" | tail -n +2)

if [ -n "$bad" ]; then
  echo "commit-msg: narrative body line not allowed:" >&2
  echo "    $bad" >&2
  echo "Keep commits subject-only; put detail in the PR / release notes." >&2
  exit 1
fi
exit 0
```

**Put the narrative in the release, not the commit.** The human-readable "what changed and why it matters" belongs in the **PR description / release notes** (surfaced by release-drafter / `generate_release_notes`), which is where users actually read it. Keep commits terse; write the detail once, in the release description.

**Match release-drafter when writing the PR body.** If `change-template` includes `$BODY`, the PR description is inlined **under** its category heading (e.g. `### 🚀 Features`). So the body must nest cleanly: use **bold emoji sub-heads** (`**🧩 Engine**`), not `#`/`##` — top-level headings render bigger than the category and clash. Mirror the config's emoji category style, and label the PR so it lands in the intended category (e.g. a `major`/`xfeature` label → 🚨 Breaking Change). Note release-drafter draws the PR body via the GraphQL path; `gh pr edit` can fail on the Projects-classic deprecation — set title/body via `gh api -X PATCH repos/{o}/{r}/pulls/{n} -f title=… -F body=@file` instead.

> ✅ **Canonical release-notes pattern (Dependabot + `$BODY` + `replacers` scrub) — the standard for every repo.** Keep `$BODY` in `change-template` so **human** PRs surface their grouped mini-changelog (`create-dev-pr` builds it — see below), and scrub Dependabot's noise with release-drafter **`replacers`** (native regex find/replace over the *rendered* notes). This **supersedes the older "drop `$BODY` when Dependabot is on" advice** — that worked but threw away the human per-commit detail. release-drafter has **no per-category `change-template`** (verified), so `$BODY` is global (all PRs or none); `replacers` is the only way to keep human detail *and* strip bot fluff.
>
> - **Group the dev-PR body by commit type** in `create-dev-pr.yml`: classify each `origin/main..HEAD` subject (`breaking`/`feat`/`fix`/`maint`/`other`), emit bold emoji sub-heads (`  **🚀 Features**`, `  **🐛 Fixes**`, `  **🧰 Maintenance**`…) with the descriptions under each, written to `$GITHUB_OUTPUT` via a heredoc. release-drafter inlines `$BODY` verbatim under the PR's one category and does **no** intra-body sorting, so the grouping must happen at body-generation time.
> - **`change-template`** keeps the two-line `$BODY` form:
>   ```yaml
>   change-template: |-
>     - $TITLE @$AUTHOR (#$NUMBER)
>     $BODY
>   ```
> - **`replacers`** scrub Dependabot's fluff. All patterns must be **bounded** (no `$`/end-of-string anchor) — the changelog concatenates every PR's `$BODY`, so an end-anchored strip bleeds across PRs and eats later human entries:
>   ```yaml
>   replacers:
>     - search: '/<details>[\s\S]*?<\/details>\s*/g'                                  # release-note/commit folds
>       replace: ''
>     - search: '/\[!\[Dependabot compatibility score\][^\n]*\n?/g'                   # compat badge
>       replace: ''
>     - search: '/Dependabot will resolve[^\n]*\n?/g'                                 # rebase boilerplate line
>       replace: ''
>     - search: '/\[\/\/\]: # \(dependabot-start\)[\s\S]*?\[\/\/\]: # \(dependabot-end\)\s*/g' # command block — markers are `[//]: # (...)`, brackets included
>       replace: ''
>     - search: '/<br\s*\/?>\s*/g'
>       replace: ''
>   ```
>   Leaves Dependabot's clean opener (`Bumps [pkg] from a to b.`) as the body — a fine one-liner. Regex over bot output is inherently brittle: revisit if Dependabot changes its format. (The full `create-dev-pr.yml` that builds the grouped `$BODY` is inlined in the *create-dev-pr.yml template* appendix above — no external repo needed.)
>
> **Adopt this in every repo** — enable Dependabot (`github-actions` ecosystem at minimum) *and* the `$BODY`+grouping+`replacers` release-drafter, so release notes carry real per-PR detail without bot noise everywhere. (A repo on the old title-only template is behind, not "configured differently".)

**Types and semver mapping:**

| Type | Semver | Notes |
|------|--------|-------|
| `feat` | MINOR | New feature |
| `fix` | PATCH | Bug fix |
| `feat!` / `BREAKING CHANGE:` | MAJOR | Breaking change — any type with `!` or `BREAKING CHANGE` footer |
| `chore`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style` | PATCH | No user-facing change |

**How this flows through the repo workflows:**

1. `create-dev-pr.yml` sets the PR **title** from the winning commit type (`feat` > `fix` > last commit). It does **no** labelling.
2. `pr-labeler.yml` runs the **release-drafter autolabeler** — the sole labeler — keyed on the PR **title** (title-only rules; no `branch:`). Since the title is the winning commit type, the label tracks the commits: breaking `type!:` → `xfeat`, `feat|feature:` → `feature`, `fix:` → `fix`, `chore|docs:` → `chore`. The breaking `!` rule must precede `feature` (else `feat!` is swallowed as a minor `feature`).
3. `release-drafter.yml` config maps labels → semver bump: `feature` → minor, `fix`/`chore` → patch, `major`/`xfeat`/`xfeature` → major.
4. On tag push (`v*.*.*`), `semantic_release.yml` cuts the GitHub release

⚠️ **One labeler, title-only — don't hand-roll a second one.** The autolabeler can only match title/body/branch/files (never commit subjects). Label off the **title** (which `create-dev-pr` derives from commits) and keep it the *only* labeler. Pitfalls that bit hard: (a) a second label step in `create-dev-pr.yml` **fights** the autolabeler → labels flap (add/remove every push); (b) `branch:` rules flap when the branch name disagrees with the commits (e.g. branch `chore/…`, commits `feat:`) — so use **title-only** rules. Resist re-adding custom bash to "label from commit subjects"; the title already encodes the winning type.

⚠️ **Stale superseded labels — NOT rare in a squash + rc-cycle repo.** The autolabeler only *adds*, never removes. When a PR's title flips type mid-life (`fix:` → `feat:` as scope grows — routine on a long-lived `feat/rcN` branch), the **old type label lingers alongside the new one**. release-drafter is PR-granular and lists a PR under **every** matching label's category, so a double-labelled PR shows up under *two* headings (e.g. both `## 🚀 Features` and `## 🔧 Fixes`) with its full `$BODY` duplicated under each. The `version-resolver` still picks the highest for the bump, but the **release notes are wrong**. This is common — not "rare since a PR is usually one type"; rc-cycle PRs routinely accrue mixed types and a flipping title. Fix with a **removal-only** step after the autolabeler (removal-only can't flap — it only ever subtracts the non-winning labels, keyed on the same title the autolabeler reads):
```yaml
# pr-labeler.yml, step AFTER autolabeler@v7
- name: Remove superseded type labels
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GH_REPO: ${{ github.repository }}  # job has no checkout — gh would else fail "not a git repository"
    TITLE: ${{ github.event.pull_request.title }}
    PR: ${{ github.event.pull_request.number }}
  run: |
    if   printf '%s' "$TITLE" | grep -qiE '^[a-z]+(\([^)]*\))?!:';        then WIN=xfeat
    elif printf '%s' "$TITLE" | grep -qiE '^(chore|docs)(\([^)]*\))?:';   then WIN=chore
    elif printf '%s' "$TITLE" | grep -qiE '^fix(\([^)]*\))?:';            then WIN=fix
    elif printf '%s' "$TITLE" | grep -qiE '^(feat|feature)(\([^)]*\))?:'; then WIN=feature
    else exit 0  # title maps to no managed label; leave labels untouched
    fi
    CURRENT=$(gh pr view "$PR" --json labels --jq '.labels[].name')
    for L in xfeat feature fix chore; do
      [ "$L" = "$WIN" ] && continue
      # `if` (not `grep && gh`): a no-match grep as the step's last command
      # returns 1 under `bash -e`, failing the step even when nothing's wrong.
      if printf '%s\n' "$CURRENT" | grep -qx "$L"; then
        gh pr edit "$PR" --remove-label "$L"
      fi
    done
```
The `!`-breaking branch must come first (else `feat!` matches the `feat` arm). This is still **one source of truth** — the title — and removal-only, so it can't fight the autolabeler the way a second *adding* step does. Needs `pull-requests: write`. **Note this only fixes the *labels* (one PR → one category).** Within a single squash PR whose body lists mixed-type commits, the commits stay together under that PR's one category — sort *those* by grouping the PR body itself by commit type in `create-dev-pr.yml` (bold emoji sub-heads), since release-drafter inlines `$BODY` verbatim under the category and does no intra-body sorting.

⚠️ **Type-vocab gap:** the autolabeler title rules map only `feat|fix|chore|docs` (+ `!` → `xfeat`). A title typed `ci:`, `refactor:`, `build:`, `perf:`, `style:`, `revert:` matches **nothing** → no label → no release-drafter category. Since `create-dev-pr` picks the title as `feat` > `fix` > last commit, ensure at least one commit is a mapped type (e.g. `chore:` not `ci:` for a workflow-only PR) so the title lands on something labellable. Don't hand-patch the label (clobbered next push).

**HA `manifest.json` version** must be bumped manually to match the intended release version before merging — `check-manifest-version.yml` enforces that it's been updated.

⚠️ **Bump discipline (learned the hard way):** the manifest bump is the **single, last commit of a PR before it merges** — not a per-push act. **Before even suggesting a bump, check whether the same PR is still being iterated; if so, don't bump.** A red `check-manifest-version` while a PR is in progress is expected and fine — it goes green when you add the one bump commit at the end. The bump **value is the version the PR will be published as** (the next release), and it gets set **once**; don't re-bump it on later pushes to the same PR. When you do set it: `git fetch origin` **first** (the local `origin/main` ref goes stale as PRs merge), compare to `origin/main`'s version, and match the level to the PR's type label (the gate keys its expected version off the label): `feat`→minor, `fix`/`chore`/`test`→patch, breaking→major. The exception that *does* re-bump mid-PR: the PR's type escalates (`fix`→`feat`→`feat!`), changing the label-derived expected version.

**Prerelease (rc) cycle:** release candidates are published via the GitHub **prerelease flag** + a `v…-rcN` tag; the manifest carries a matching **PEP440 prerelease** (`2.0.0rc1`) which `AwesomeVersion`/hassfest/HACS accept (`2.0.0 > 2.0.0rc1`). Two rules that bit hard:
- **rc numbers track *published* candidates, not PRs.** You only increment `rc1`→`rc2` when you actually cut a new published rc; you do **not** invent `rc2`/`rc3` per-PR to satisfy the gate. The version stays frozen at the current rc across iteration; it changes only as the pre-merge bump to the version being published.
- **A prerelease deliberately changes gate behaviour:** a prerelease version only needs to *differ from base* — so the gate must **skip** the label-derived "incorrect version" suggestion when the PR version matches `(rc|alpha|beta|a|b|dev)[0-9]*$` (otherwise a `feature`-labelled `2.0.0rc1` PR fails, demanding `v2.1.0`). Also de-anchor the base parse (`^([0-9]+)\.([0-9]+)\.([0-9]+)` without `$`) so a base that already carries `rcN` still parses. This is the *only* prerelease gate change needed — do **not** add per-PR rc-increment logic or relax the "differ from base" rule.
- **Graduating off rc to the same-number final is a legitimate bump the gate must allow.** Coming off the rc line (`2.0.0rc19` → **`2.0.0`** final) is the natural cycle close, but the de-anchored parse makes `2.0.0rc19` and `2.0.0` both `(2,0,0)`, so a naive `pr == base` check (and a `feature` label demanding `v2.1.0`) **wrongly rejects the graduation** — even though `AwesomeVersion` knows `2.0.0 > 2.0.0rc19`. The gate special-cases it: when the PR version is final, equals the base tuple, **and** the last release was a prerelease, pass it ("final graduates its own prerelease"); a `pr == base` where the last release was already *final* still fails (real unchanged version). Covered by `test_final_graduates_prerelease`.

**Compare the gate against the last published *release*, not `main` HEAD.** Comparing to `main` forces **every** PR to bump beyond the previous merged PR, so versions inflate per-PR (rc4, rc5, rc6…) with no release between them. Instead resolve the base from the latest published release tag — `gh release list --exclude-drafts --limit 1 --json tagName --jq '.[0].tagName'`, strip the leading `v` — and pass only when the manifest version **differs from that**. Now several unreleased PRs can sit at the same in-progress version (the first PR of a cycle bumps `main` once; later PRs ride it), and the single bump folds into whatever release is cut next. A PR that doesn't change the manifest still passes as long as `main` is already ahead of the last release — which it is, mid-cycle.

**Exempt Dependabot from the version gate.** Dependabot PRs never touch `manifest.json`, and right after a release (`main` == last release) a no-bump PR equals the released version → the gate's "unchanged" rule trips. Add `&& github.event.pull_request.user.login != 'dependabot[bot]'` to the **failing** steps' `if:` (the "unchanged" and "incorrect version" comment-and-`exit 1` steps), *not* a job-level `if:` — a job-level skip can read as a missing required check, whereas skipping just the failing steps keeps the job **green** for Dependabot while staying strict for humans. The push-context run already passes (the failing steps are `pull_request`-only). With this, Dependabot PRs fold into the next release with no bump, exactly as intended.

> ⚠️ **Orphaned-branch trap (the dev-PR auto-merges fast — this WILL bite repeatedly).** `create-dev-pr.yml` opens a draft PR that gets merged to `main` as soon as it's approved/auto-merged. **Any commit you push to `feat/rcN` after that merge is stranded** — it's not on `main` and not in the release, even though `git status` on the branch looks fine. It also leaves the branch's manifest equal to `main`'s, so `check-manifest-version` fails. **Guard every time, not just when you remember:**
> 1. At the **start** of any rc work and before claiming work is "pushed/live", run `git fetch origin` then `git log --oneline origin/main..feat/rcN`. If `main` already contains a merge of this branch, the branch is spent.
> 2. When a cycle has merged/released: **branch fresh** `git checkout -b feat/rc(N+1) origin/main`, `git cherry-pick` the orphaned commits (oldest-first), bump `manifest.json` to the next `rcN` **and** `ENGINE_VERSION` (firmware/version.py + the integration's mirror) if any firmware changed, run the sync + guards, push, then delete the merged branch (local + remote).
> 3. Don't keep committing onto a `feat/rcN` whose PR has merged — start the next branch immediately after a release.

---

### ⚠️ GITHUB_TOKEN suppresses workflows ONLY on the bot's `opened` event — `synchronize` from a human push still fires

Narrow, often-misunderstood footgun: **the `pull_request: opened` event from a PR that `create-dev-pr.yml` opens with the default `secrets.GITHUB_TOKEN` is suppressed** (GitHub's anti-recursion rule — events caused by `GITHUB_TOKEN` don't trigger new runs). So `pull_request`-triggered workflows (`lint_pr`, `pr-labeler`, autolabeler, `check-manifest-version`'s PR part) **do not run on that first auto-open**.

**But it stops there.** Every *later* push you make to the branch fires a `pull_request: synchronize` event whose `triggering_actor` is **you** (your SSH push), not the token — so all those workflows run normally from the second push on. Verified empirically: on a bot-authored dev PR (author `github-actions[bot]`, no PAT, empty secret list), `lint_pr` / `pr-labeler` / autolabeler / manifest-check all ran and passed, every one with `triggering_actor` = the human, because the branch had several pushes. The suppression swallows exactly **one** event — the bot's `opened`.

**Practical upshot:** with **no PAT**, a branch pushed **more than once** (i.e. nearly always) gets full automation — the auto-PR opens, and your next push triggers all checks. The footgun only bites a branch pushed **exactly once** then merged untouched. Don't reach for a PAT reflexively; it's rarely needed.

Fixes, in order of preference:
- **Usually nothing** — push more than once (you will anyway) and `synchronize` covers it. This is the default the canonical workflows rely on (no PAT needed).
- **No-secret hardening for the must-always-enforce gate:** add a `push:` trigger (`branches-ignore: [main]`) to `check-manifest-version` so the version gate runs on the branch push regardless of PR events — covers even the single-push case. Default the base ref to `main` when there's no PR context (`${{ github.event.pull_request.base.ref || 'main' }}`) and guard PR-only steps with `if: github.event_name == 'pull_request'` (label lookups, PR comments).
- **PAT (only if you truly need single-push auto-PRs fully checked):** open the dev PR with a fine-grained, repo-scoped PAT (`Pull requests: write` + `Contents: read`, short expiry) instead of `GITHUB_TOKEN` — PAT-authored events aren't suppressed, so even the `opened` fires everything. Costs a secret to rotate; reserve for when single-push branches matter.

**`create-dev-pr.yml` hardening** (prevents duplicate/stale PRs seen in practice):
- Add `concurrency: {group: dev-pr-${{ github.ref }}, cancel-in-progress: true}` so rapid pushes can't race into two PRs.
- Skip PR creation when the branch has **0 commits ahead of main** (`git rev-list --count origin/main..HEAD`) — otherwise pushing to an already-merged branch re-spawns a PR.
- On update, re-set the **title** (`gh pr edit --title`) to the current winning commit type — the autolabeler re-labels from the new title on the next `synchronize`. (Don't manage labels in this workflow; that's the autolabeler's job.)

---

## Dependabot (for a HA custom integration)

`.github/dependabot.yml` with `commit-message.prefix: "chore"` on each ecosystem (so titles read `chore: bump …` → the autolabeler maps `chore` → patch). Know what it actually buys you:

- **`github-actions`** — the real value. Bumps `actions/checkout`, `setup-python`, action pins across all workflows.
- **`pip`** — points at `requirements.test.txt` / `pyproject`. **Near-useless if those are unpinned** (no version specifier = nothing to bump). Keep it for when something gets pinned, but don't expect PRs.
- **`manifest.json` `requirements` are invisible to Dependabot** — it can't parse the manifest, and the entries are open `>=` ranges (HA installs the latest matching anyway), so there's nothing to *routinely* bump. Raising a `>=` floor is a deliberate safety/feature act, not automation — **unless** you want the floors kept current.

**Keeping `>=` floors current (custom, since Dependabot can't):** a small `scripts/update_manifest_floors.py` (parse manifest requirements, query PyPI `…/pypi/{name}/json` for the latest non-prerelease, raise the floor if newer; `--check` to dry-run) plus a scheduled `update_manifest_floors.yml` (`schedule:` + `workflow_dispatch`) that runs it and — on a change — commits to a branch and pushes, letting `create-dev-pr` open the PR. Don't add a second PR-creator (e.g. `peter-evans/create-pull-request`); it races `create-dev-pr` into duplicate PRs. The floor-bump PR needs **no manifest version bump** under the last-release gate model above.

**Two gotchas Dependabot forces, both covered above:** the **version gate** must compare against the last release and **exempt `dependabot[bot]`** (see the versioning section), and the release notes must **scrub Dependabot's body fluff via `replacers`** while keeping `$BODY` for human detail (see the canonical release-notes pattern in release-drafter — *not* the old "drop `$BODY`" workaround).

---

## Debugging discipline

- **Trace before naming a cause** — grep the path (publish → subscribe → handler), confirm in code; a pre-trace hunch is a guess, not the diagnosis.
- **Multi-entry service fan-out:** a `hass.services.async_call(DOMAIN, svc, …)` with no target loops **all** config entries. An entity action that should hit only its own device must pass its own `entry_id`/`device_id` and the handler must filter — default to "all" only for a deliberate bulk call.

---

## Mode 2 — Modify existing integration

Identify the integration domain from `custom_components/`. Then ask what to add or change:

- Add new platform
- Add/update translations
- Add options flow
- Add reconfigure flow (`async_step_reconfigure`)
- Add reauth flow (`async_step_reauth`)
- Add or update `quality_scale.yaml`
- Add GitHub workflows
- Update manifest version
- Other

Apply the same patterns and code style as Mode 1.

---

## Mode 3 — Lint & quality check

1. Run `ruff check custom_components/` — fix all actionable issues; suppress intentional ones with `# noqa` and a reason
2. Run `python -m pyright custom_components/` — fix all actionable issues
3. Check `quality_scale.yaml` exists; if not, offer to create it
4. Check `manifest.json` — correct `documentation` URL pointing to the repo, keys in order (`domain`, `name`, then alphabetical)
5. Report: files changed · issues fixed · issues intentionally suppressed (with rationale) · remaining manual work

---

## Mode 4 — Audit (skill conformance)

**Why this is separate from lint.** Mode 3 (lint) answers *is the code hygienic* — ruff/pyright/manifest order, tool-driven. Mode 4 answers *was this skill actually followed* — are the canonical workflows present and correct, the documented patterns applied, the antipatterns gone, `quality_scale.yaml` honest. The skill has repeatedly been *used* while specific items were missed (stale action pins, a deprecated notify path, an optimistic `exempt`, a hand-created PR). Lint can't catch those; the audit does. **Run it before claiming a tier and before merge — it's part of definition-of-done.**

**Two layers, because a checklist you must remember to run gets skipped:**
1. **Mechanical gate (`scripts/skill_audit.sh`, enforced by `quality_audit.yml` on every PR).** Greps the high-confidence, machine-checkable subset and fails CI on any violation. This is what *stops* regressions — it can't be forgotten.
2. **Judgement checklist (below).** The items a grep can't decide — run these by reading the code.

### Mechanical gate — `scripts/skill_audit.sh`

```bash
#!/usr/bin/env bash
# Skill-conformance audit: verifies the ha-integration skill was actually followed —
# canonical workflows present, action pins current, antipatterns absent, quality_scale
# present. Mechanical subset of Mode 4. Exit 1 on any FAIL. Runs locally and in CI.
set -uo pipefail

CC=$(ls -d custom_components/*/ 2>/dev/null | head -1)
fail=0
FAIL() { echo "❌ FAIL: $*"; fail=1; }
WARN() { echo "⚠️  WARN: $*"; }

# --- Canonical workflows present ---
for w in create-dev-pr pr-labeler release_drafter semantic_release lint_pr \
         hacs_validate hassfest_validate python_validate check-manifest-version; do
  [ -f ".github/workflows/$w.yml" ] || FAIL "missing .github/workflows/$w.yml"
done
[ -f .github/release-drafter.yml ] || FAIL "missing .github/release-drafter.yml"
[ -f .github/dependabot.yml ]      || FAIL "missing .github/dependabot.yml"

# --- Action pins current (stale majors Dependabot would immediately bump) ---
grep -rnE 'actions/checkout@v[1-6]\b'                 .github/workflows/ && FAIL "stale actions/checkout (use v7)"
grep -rnE 'actions/setup-python@v[1-5]\b'             .github/workflows/ && FAIL "stale actions/setup-python (use v6)"
grep -rnE 'softprops/action-gh-release@v[12]\b'       .github/workflows/ && FAIL "stale action-gh-release (use v3)"
grep -rnE 'amannn/action-semantic-pull-request@v[1-5]\b' .github/workflows/ && FAIL "stale semantic-pull-request (use v6)"

# --- Workflow correctness ---
grep -q "Remove superseded" .github/workflows/pr-labeler.yml 2>/dev/null \
  || FAIL "pr-labeler.yml missing the removal-only superseded-label step"
grep -q "dependabot\[bot\]" .github/workflows/check-manifest-version.yml 2>/dev/null \
  || WARN "check-manifest-version may not exempt dependabot[bot]"
grep -q "gh release list" .github/workflows/check-manifest-version.yml 2>/dev/null \
  || WARN "check-manifest-version may not compare against the last published release"

# --- Antipatterns in integration code (high-confidence) ---
if [ -n "$CC" ]; then
  ap() { grep -rnE "$1" "$CC" 2>/dev/null && FAIL "$2"; }
  ap 'discovery\.async_load_platform' "deprecated discovery.async_load_platform (use NotifyEntity / platform forward)"
  ap 'BaseNotificationService'         "deprecated BaseNotificationService (use NotifyEntity)"
  ap 'update_before_add=True'          "update_before_add=True (populate via property or _handle_coordinator_update)"
  ap 'OptionsFlowHandler'              "deprecated OptionsFlowHandler name (use OptionsFlow)"
  ap 'PlatformNotReady'                "PlatformNotReady in a config-entry integration (use ConfigEntryNotReady)"
  ap '_LOGGER\.[a-z]+\([[:space:]]*f"' "f-string in a logging call (use lazy % args — ruff G004)"
  ti=$(grep -rn '# type: ignore' "$CC" 2>/dev/null | grep -v 'import-untyped')
  [ -n "$ti" ] && { echo "$ti"; FAIL "bare # type: ignore (Platinum: only [import-untyped] with a reason)"; }
  grep -rq 'from __future__ import annotations' "$CC"__init__.py 2>/dev/null \
    || WARN "no 'from __future__ import annotations' in __init__.py"

  # --- quality_scale + manifest honesty ---
  [ -f "${CC}quality_scale.yaml" ] || FAIL "missing quality_scale.yaml"
  M="${CC}manifest.json"
  grep -q '"integration_type"' "$M" 2>/dev/null || FAIL "manifest.json missing integration_type"
  grep -q '"issue_tracker"'    "$M" 2>/dev/null || FAIL "manifest.json missing issue_tracker (HACS requires it)"
fi

[ "$fail" = 0 ] && { echo "✅ skill audit passed"; exit 0; } || { echo "skill audit FAILED"; exit 1; }
```

`.github/workflows/quality_audit.yml`:
```yaml
name: Skill Audit

on:
  push:
    branches: [main]
  pull_request:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: bash scripts/skill_audit.sh
```

Add `"scripts/*" = ["T20", "INP001"]` to ruff `per-file-ignores` if any audit helper is Python (the bash script needs no ignore). When the skill adds a new antipattern or canonical workflow, **add the matching check here** — the gate is only as current as its rules.

### Judgement checklist (read the code — a grep can't decide these)

- **Workflows behave, not just exist:** `create-dev-pr` trims the title with `xargs`, has `concurrency` + 0-ahead skip, and no label step; `release_drafter` is push-only with no second autolabeler; `check-manifest-version` compares to the **last published release** and exempts `dependabot[bot]` on the *failing steps*.
- **Patterns applied:** `runtime_data` (not `hass.data[DOMAIN][entry_id]`) for entry state; coordinator `async_shutdown()` on unload; `async_remove_config_entry_device` present if the integration creates a device; `DeviceInfo` TypedDict; `_attr_has_entity_name = True`; typed `ConfigEntry` alias; modern `NotifyEntity` (or a directly-registered service for custom `data`).
- **`quality_scale.yaml` honest:** every canonical rule listed; every `exempt` carries a real `comment`; no optimistic `exempt` masking a gap (e.g. `stale-devices` exempt while a device *is* created); the `manifest.json` tier claimed only when every rule at/below it is `done`/`exempt`.
- **Tests mock the boundary:** a real setup-entry `LOADED` test exists (not just `async_setup_component`); the transport is mocked, not the integration's own functions; a two-entry parallel `LOADED` test exists if multiple devices are allowed; parsers have unit tests.
- **Commit/PR discipline:** subjects are single tight imperatives; the PR was opened by `create-dev-pr`, not hand-created; the version bumped once vs the last release per the type label.

**Report:** per-item pass/fail with `file:line` evidence · what the mechanical gate caught · remaining manual work. Fix findings before claiming the tier.

---

## Mode 5 — Log triage

Triage a Home Assistant log (`home-assistant.log`, a copied `.md`/`.txt` dump, or the **Settings → System → Logs** download). Goal: turn thousands of lines into a short ranked list of *actionable* issues, separating real bugs from the constant background noise HA emits. **A raw error count is meaningless** — one slow client can emit 1000+ identical lines; one config typo emits one. Rank by distinct root cause, not by line count.

### Step 1 — Build (or load) the device inventory FIRST

Logs identify clients/devices by **opaque tokens** — an IP, a browser user-agent, a Z-Wave `node_id`, a `notify.mobile_app_*` slug, a UniFi/camera hostname. Triage stalls every time on "what *is* `192.168.13.179`?". Resolve it **once**, up front, into a persistent map so every future triage is instant.

**The map is user/environment-specific — it does NOT belong in this (shareable) skill repo.** Keep it in a **local, git-ignored file next to the logs** (e.g. `device_map.md` in the log directory) or in Claude auto-memory. Never commit a home's IP/device layout to a public repo.

**Up-front Q&A** — when no map exists, extract the distinct tokens from the log and ask the user to name each once:

```bash
# Web/app clients: IP + device fingerprint (SM-X210 = Galaxy Tab, KFTRPWI = Amazon Fire, etc.)
grep -oE "from [0-9.]+ \(Mozilla[^)]*Build/[^ ;]+" LOG | sort -u
# All LAN IPs by frequency
grep -oE "192\.168\.[0-9]+\.[0-9]+" LOG | sort | uniq -c | sort -rn
# Named device tokens worth resolving
grep -oE "mobile_app_[a-z0-9_]+|node_id=[0-9]+|notify\.[a-z0-9_]+" LOG | sort | uniq -c | sort -rn
```

Then ask the user to fill **device · room/owner · role** for each token. Store as a table:

```markdown
| Token | Device | Room / owner | Role |
|-------|--------|--------------|------|
| 192.168.13.179 (SM-X210) | Galaxy Tab A9+ | Kitchen | Wall dashboard |
| node_id=3 | Z-Wave keypad | Front door | Alarmo front pinpad |
| notify.mobile_app_caracal2 | Phone | (owner) | Alarm notifications |
```

Decode common fingerprints without asking: `SM-*` = Samsung Galaxy (Tab/phone), `KF*`/`Build/PS*` = Amazon Fire, `Pixel*` = Google Pixel, `iPad`/`iPhone` = Apple. Ask only for room/role.

### Step 2 — Aggregate by logger, not by line

```bash
grep -oE "(ERROR|WARNING) \([^)]+\) \[[^]]+\]" LOG | sort | uniq -c | sort -rn
```

Collapse each logger cluster to one row. Then read **one representative line** per cluster — not all of them.

### Step 3 — Classify each cluster: noise vs actionable

**Known noise — acknowledge once, do not chase:**

| Pattern | Why it's noise |
|---------|----------------|
| `[homeassistant.loader] We found a custom integration X which has not been tested` | Boot banner, **one per HACS integration**, every restart. Count ≈ number of custom integrations. Benign. |
| `[websocket_api.http.connection] ... Reached 4096 pending messages` | A **single slow client** can't drain the state_changed queue — almost always a tablet/dashboard right after restart. Check it's **one IP** over a **bounded window** (resolve the IP via the map). Self-heals on reconnect. Burst at boot = client weight, not a code bug; *continuous* = genuinely overloaded dashboard (trim history-graph / auto-entities cards). |
| `[snitun.*]`, `ClientConnectionResetError`, `Task exception was never retrieved` | Nabu Casa Cloud / network transients. Ignore unless frequent + correlated with an outage. |
| transient device fetch (`spotify`, `apple_tv`/`pyatv`, weather) | One-off API/device blips. Ignore unless sustained — sustained → that integration's reauth/availability. |

**Actionable — real bugs to fix:**

- **`extra keys not allowed @ data['<key>']`** in a script/automation `call_service` → a **service-schema deprecation**. The big recurring one: `light.turn_on` dropped **`color_temp`** → use **`color_temp_kelvin`** (kelvin = `1000000 / mired`). Also `white_value` (removed), `effect` keys that moved. Grep config for the dead key and replace.
- **`Action notify.mobile_app_* not found`** / **`Service … not found`** → a referenced entity/service was renamed or its device removed (re-onboarded phone, deleted integration). Update the automation/Alarmo action to the current slug.
- **Z-Wave `NotFoundError: Value N-CC-… not found on node Node(node_id=N)`** → a `zwave_js.set_value` targets a value id the node no longer exposes (re-interview, firmware change, wrong endpoint). Resolve `node_id` via the map, re-check the value id in the device's Z-Wave page.
- **`Bad credentials` / auth errors** (`github`, etc.) → expired token/PAT. Reconfigure that integration.
- **Anything under `custom_components.<your_domain>`** → your code. Trace it (publish→subscribe→handler) per the Debugging discipline section; this is the only cluster the rest of this skill directly acts on.

### Step 4 — Report

Ranked table: **severity · cluster · root cause · fix · evidence (`timestamp` / `file:line`)**. State explicitly which clusters are *known noise* (so the user stops worrying about a scary count) and which are *actionable*. Resolve every opaque token through the device map so the report reads in plain device names ("Kitchen wall tablet", not `192.168.13.179`). If a fix is config-side (scripts/automations/integration settings) and you only have the log, say so and offer to apply it once given the config path.

> **Scope note:** most HA log errors are **config / automation / external-device** issues, *not* custom-integration code — Mode 5 triages and routes them, but the editing patterns in this skill apply only to the `custom_components.<your_domain>` cluster. Don't add a home's specific errors to this skill; add only a **new reusable noise/actionable *pattern*** here when one recurs across triages.
