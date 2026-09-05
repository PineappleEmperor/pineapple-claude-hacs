---
name: ha-integration
description: Use when developing or troubleshooting a Home Assistant custom integration — Python code under `custom_components/`. Covers config/options/reauth/reconfigure flows, the data coordinator and entity platforms (sensor, switch, notify, fan, etc.), manifest, services, diagnostics, and quality_scale. Reach for it on symptom-style reports too: an entity going unavailable after restart, a notify/custom service breaking after an HA update, a `device_class`/`state_class` mismatch HA complains about, a reconfigure flow request, or CI/Dependabot/HACS/hassfest issues on an integration repo. NOT for Lovelace cards, panel/display UI styling (`ha-panel-design`), triaging a `home-assistant.log` (`ha-triage`), or generic non-HA Python. Invoke before editing integration code; re-invoke after /compact.
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

Use it when the task touches any of: a `custom_components/<domain>/` package, a `manifest.json` with a `domain`, a config/options/reauth/reconfigure flow, a `DataUpdateCoordinator` or entity platform (`sensor.py`, `notify.py`, …), `services.yaml`/`quality_scale.yaml`, the integration's GitHub CI (the `pr-checks`/release-drafter/hassfest/HACS stack). Symptoms that should pull you here: "add a sensor/platform", "config flow won't validate", "hassfest/HACS check failing", "what `state_class` for this `device_class`", "Dependabot keeps bumping actions", "this PR's release version looks wrong".

**When NOT to use:** Home Assistant *panel / display UI* work (Lit/TS web component, CSS, layout) — that's the `ha-panel-design` skill. Generic Python/CI work in a repo that isn't an HA integration.

---

## Step 1 — Detect mode

Check the working directory, pick a mode, then **read that mode's reference file before acting**.

| Mode | When | Read first |
|---|---|---|
| **Scaffold** | no `custom_components/`, or the user wants a new integration | `reference/scaffold.md`, then `reference/patterns.md` |
| **Modify** | `custom_components/` exists and something is being added or changed | `reference/patterns.md`. Adding a platform also touches `strings.json`/`translations/` and the tier claim — see `reference/quality-scale.md` |
| **Test** | writing or fixing tests for an integration | `reference/testing.md` — the root `conftest.py` and `asyncio_mode` prerequisites decide whether the suite runs at all |
| **Lint** | hygiene pass over existing code | this file, *Lint* below |
| **Audit** | verify the skill was actually followed | `scripts/skill_audit.py --list` (or the skill's `templates/scripts/skill_audit.py` if the repo never copied it), then `reference/audit.md` |
| **Release / repo setup** | first release, tokens, required checks | `reference/github-setup.md` — token, ruleset, dependency graph, required contexts. Then `reference/versioning.md` for how the version is decided, `reference/commits.md` for what the notes are built from, `reference/github-actions.md` for what each workflow must do |

The audit script lives at `scripts/skill_audit.py` in a repo that copied the templates.
Auditing a repo that never did — the case where the audit matters most — means running the
skill's own copy at `templates/scripts/skill_audit.py` against the repo root.

Reading a Home Assistant log is a different skill — `ha-triage`. How a panel **looks**
(type scale, colour, spacing, touch targets) is `ha-panel-design`. How a panel is **built and
served** — the committed bundle, its staleness check, registration and cache-busting, the
`home-assistant-frontend` pin — stays here, in `reference/panels.md`.

## Invariants — true in every mode

- **The release tag sets the version.** No PR carries a manifest bump; `release.yml` patches
  `manifest.json` at publish. Details in `reference/versioning.md`.
- **The commit subjects are the changelog**, so each is one tight imperative with a mapped
  Conventional Commit type. The PR body is for reviewers and is never generated.
- **Never merge a red check**, and never merge by disabling one. Why, and the exceptions that
  are not exceptions, in `reference/discipline.md`.
- **Templates are copied, not paraphrased.** Every deviation from `templates/` must be a listed
  adaptation — see `reference/audit.md`.
- **No `${{ }}` inside any `run:`** and no job checks out PR-authored code. `reference/github-actions.md`
  holds the workflow contracts.
- **Cached facts go stale silently.** Anything captured more than ~3 months ago gets re-derived
  before it is trusted — the table and its re-derivation commands are in `reference/freshness.md`.

## Reference map

| File | Holds |
|---|---|
| `reference/scaffold.md` | what to ask, what to generate, manifest key order, code style |
| `reference/patterns.md` | the code patterns every mode applies, plus file structure and typing |
| `reference/testing.md` | harness prerequisites, and mocking the boundary rather than your own code |
| `reference/commits.md` | commit subjects, why the PR body stays empty, what the notes are built from |
| `reference/github-setup.md` | RELEASE_TOKEN, required checks, dependency graph, supply chain |
| `reference/github-actions.md` | what each workflow must do, where `templates/` lives, and what may be changed in a copy |
| `reference/versioning.md` | tag-driven releases, labels, the draft model, the version gate |
| `reference/dependabot.md` | what it bumps, what it cannot reach, its effect on the gate |
| `reference/quality-scale.md` | the canonical rule set and what each tier demands |
| `reference/panels.md` | integrations that serve a custom panel |
| `reference/discipline.md` | commit, PR, merge and debugging discipline |
| `reference/audit.md` | the audit items a grep cannot decide |
| `reference/freshness.md` | cached facts, when captured, how to re-derive |

---

## Scaffold

Read `reference/scaffold.md`, then `reference/github-setup.md` when the repo needs its GitHub side configured. Ask the requirement questions in one go; do not generate files before they are answered.

---

## Modify existing integration

Identify the integration domain from `custom_components/`. Then ask what to add or change:

- Add new platform
- Add/update translations
- Add options flow
- Add or fix tests (start from `reference/testing.md`)
- Add reconfigure flow (`async_step_reconfigure`)
- Add reauth flow (`async_step_reauth`)
- Add or update `quality_scale.yaml`
- Add GitHub workflows
- Cut a release (publish the rc draft, then the full one)
- Other

Apply the same patterns and code style as a scaffold.

---

## Lint & quality check

1. Run `ruff check .` and `ruff format --check .` under the shipped `pyproject.toml` — fix all actionable issues; suppress intentional ones with `# noqa` and a reason
2. Run `python -m pyright custom_components/` — fix all actionable issues
3. Check `quality_scale.yaml` exists; if not, offer to create it
4. Check `manifest.json` — correct `documentation` URL pointing to the repo, keys in order (`domain`, `name`, then alphabetical)
5. Report: files changed · issues fixed · issues intentionally suppressed (with rationale) · remaining manual work

---

## Audit — skill conformance

Lint answers *is the code hygienic*. This answers *was the skill followed* — canonical
workflows present and correct, documented patterns applied, antipatterns gone,
`quality_scale.yaml` honest. Run it before claiming a tier and before merge.

Two layers:

1. **Mechanical gate** — `scripts/skill_audit.py`, run by `quality_audit.yml` on every PR.
   `scripts/skill_audit.py --list` prints every check and why it exists.
2. **Judgement checklist** — `reference/audit.md`. The items a grep can't decide.

⚠️ **Green CI is not evidence the templates were copied.** Why the gate cannot tell you that,
and how to check it yourself, is the first item of the judgement checklist.

---
