---
name: ha-integration
description: Use when developing or troubleshooting a Home Assistant custom integration — Python code under `custom_components/`. Covers building, fixing, or reviewing the integration's backend: config/options/reauth/reconfigure flows, the data coordinator and entity platforms (sensor, switch, notify, fan, etc.), manifest, services, diagnostics, and quality_scale. Reach for it on symptom-style reports too: an entity going unavailable after restart, a notify/custom service breaking after an HA update, a `device_class`/`state_class` mismatch HA complains about, a reconfigure flow request, or CI/Dependabot/HACS/hassfest issues on an integration repo. Also use to read or triage a `home-assistant.log` — finding the real fault among thousands of noisy lines. NOT for Lovelace cards, dashboard/panel UI styling, template sensors in YAML, or generic non-HA Python. Invoke before editing integration code; re-invoke after /compact.
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

## When to use this skill

Use it when the task touches any of: a `custom_components/<domain>/` package, a `manifest.json` with a `domain`, a config/options/reauth/reconfigure flow, a `DataUpdateCoordinator` or entity platform (`sensor.py`, `notify.py`, …), `services.yaml`/`quality_scale.yaml`, the integration's GitHub CI (the `create-dev-pr`/release-drafter/hassfest/HACS stack), or a Home Assistant log to triage. Symptoms that should pull you here: "add a sensor/platform", "config flow won't validate", "hassfest/HACS check failing", "what `state_class` for this `device_class`", "Dependabot keeps bumping actions", "this PR's version gate is red", "what's spamming my HA log".

**When NOT to use:** Home Assistant *panel / display UI* work (Lit/TS web component, CSS, layout) — that's the `ha-panel-design` skill. Generic Python/CI work in a repo that isn't an HA integration.

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
- `diagnostics.py` (Gold requirement — see `reference/patterns.md`)
- One file per selected platform (e.g. `button.py`, `sensor.py`)
- Additional files as needed: `api.py`, `coordinator.py`, `models.py`, `entity.py`, `helpers.py` (see `reference/patterns.md`)

**Repo root:**
- `CLAUDE.md` — project instructions. **Always include a rule telling future AI sessions to invoke this `ha-integration` skill before writing/modifying integration code, and to re-invoke after `/compact`** (compaction drops the skill's guidance). Keep this enforcement **per-repo, not global** — a project file is the right scope; do not push a user's global config on others. Suggested snippet:
  ```markdown
  ## AI sessions
  Before writing or modifying integration code (config flow, platforms, manifest,
  websocket, services…), invoke the `ha-integration` skill. Re-invoke it after any
  `/compact`, since compaction can drop the skill's guidance from context.
  ```
  (A user may *additionally* wire personal `SessionStart` + `UserPromptSubmit` hooks in their own `~/.claude/settings.json` to re-arm the rule and anchor the CI conventions per-turn — see `reference/github-actions.md` (reminder-hook recipe) for the full recipe. That's a personal convenience; the canonical, shareable enforcement still lives in the repo's `CLAUDE.md`.)
- `hacs.json` — `name` is the only strict requirement, but the canonical setup ships a **zip release**: `{"name": "My Integration", "content_in_root": false, "zip_release": true, "filename": "<domain>.zip"}` (add `"homeassistant": "2024.1.0"` for a minimum HA version). `zip_release` makes HACS download a release **asset** named `<filename>` instead of the tag source archive — so it **requires** the `release.yml` *Create Release ZIP* workflow (`templates/.github/workflows/release.yml`) to build and attach that asset on every published release. **Without that workflow, HACS install fails with `Could not download`** (the symptom of a `zip_release` repo whose release has no attached zip). Drop `zip_release`/`filename` only if you deliberately want HACS to pull the whole tagged repo archive instead.
- `pyproject.toml`
- `pyrightconfig.json`
- `README.md` — **include the AI-assistance disclaimer** as a GitHub `> [!NOTE]` admonition box. Link the skill name to its public repo. Template:
  ```markdown
  > [!NOTE]
  > **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/pineapple-claude-hacs) skill. Architecture and final review are mine; every change is human-reviewed before it merges.
  ```
- `.gitignore`
- `.githooks/commit-msg` — terse-commit + AI-trailer-rejection hook (see `reference/versioning.md`); enable once per clone with `git config core.hooksPath .githooks` (document this in `CLAUDE.md`)
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
- `.github/workflows/release.yml` — **Create Release ZIP.** Triggers on `release: published`; zips the contents of `custom_components/<domain>/` (files at the **zip root**, not nested) and attaches it as the `<filename>` asset declared in `hacs.json`. **Required whenever `hacs.json` sets `zip_release: true`** — HACS downloads that asset, so a missing zip = `Could not download` on install. Body in `templates/.github/workflows/release.yml`; rationale in `reference/github-actions.md`. (The `release: published` trigger fires when a human publishes the drafted release; a release *created* by `GITHUB_TOKEN` would be suppressed by the anti-recursion rule, so publish from the draft, don't auto-create via token.)
- `.github/workflows/create-dev-pr.yml` — triggers on every push to non-main branches; auto-creates a draft PR with **title from commits** (`feat:` wins over `fix:` wins over last commit). Updates PR body with commit list on subsequent pushes. **Body in `templates/.github/workflows/create-dev-pr.yml`** (this skill is the source of truth — don't copy from another repo); rationale in `reference/github-actions.md`. ⚠️ After computing `TITLE`, always add `TITLE=$(echo "$TITLE" | xargs)` before `echo "title=$TITLE" >> $GITHUB_OUTPUT` — GitHub Actions env var interpolation can add surrounding whitespace that breaks `lint_pr.yml` semantic title validation. **Do NOT add a label step here** — labelling is the autolabeler's job (below). Since this sets the title to the winning commit type, autolabelling off the title is effectively commit-driven; a second labeler here just causes flapping.
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
- `.github/dependabot.yml` — see `reference/versioning.md` (Dependabot).

#### GitHub CI templates

The full, self-contained CI stack ships in the skill's **`templates/`** dir (mirrors the target repo layout — `templates/.github/workflows/*.yml`, `templates/.github/*.yml`, `templates/scripts/*`, `templates/tests/*`, `templates/hooks/*`). Copy as-is; no external repo. One file per workflow/config/script.

**Read `reference/github-actions.md` before changing any workflow** — it holds the must-preserve behaviours: the sole title-only labeler + removal-only superseded-label step, `$BODY` + bounded Dependabot `replacers`, the last-published-release version gate (with `dependabot[bot]` exempt and the unit-tested `manifest_gate.py`), the `create-dev-pr` title/concurrency/0-ahead rules, the `GITHUB_TOKEN` `opened`-suppression footgun, and the optional personal reminder-hook recipe.

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

### Implementation patterns, file structure, typing & testing

See **`reference/patterns.md`** — `__init__`/coordinator/entity/notify patterns, `entry.runtime_data`, `DeviceInfo`, the modern `NotifyEntity` path, `from __future__ import annotations` + typed-`ConfigEntry` rules, the file-split conventions, and the **mock-the-boundary** testing rules (real setup-entry `LOADED` test, two-entry parallel test, parser unit tests).

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

### Conventional Commits, versioning & CI gating

See **`reference/versioning.md`** — Conventional Commits → semver mapping, the **single bump as the last commit before merge** discipline, the prerelease/rc cycle, the **last-published-release** version gate, Dependabot, and the `GITHUB_TOKEN` workflow-suppression footgun.

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

The full script is **`templates/scripts/skill_audit.sh`** (copy to `scripts/`, `chmod +x`). It fails (exit 1) on: a missing canonical workflow; a stale action pin (checkout < v7, setup-python < v6, action-gh-release < v3, semantic-pull-request < v6); an antipattern in `custom_components/` (`discovery.async_load_platform`, `BaseNotificationService`, `update_before_add=True`, `OptionsFlowHandler`, `PlatformNotReady`, f-string logging, bare `# type: ignore`); or a missing `quality_scale.yaml` / `integration_type` / `issue_tracker`. Keep its rules in lockstep with this skill — when you add an antipattern or canonical workflow here, add the check there.

Enforce it in CI with **`templates/.github/workflows/quality_audit.yml`** — runs `scripts/skill_audit.sh` on every PR, so conformance can't be silently skipped.

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
