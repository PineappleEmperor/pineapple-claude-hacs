# Scaffolding an integration

What to ask, what to generate, and the conventions the generated code follows. Read with `reference/patterns.md` open — the code patterns live there.

- Gather requirements (ask all at once)
- Files to generate
- Brand assets are served from the integration's own `brand/` folder
- Sources
- manifest.json key order
- Implementation patterns, file structure, typing & testing
- Code style
- Commit conventions, versioning & CI gating

## Gather requirements (ask all at once)

1. **Domain** — snake_case, e.g. `my_device`. Must be stable; can't change later.
2. **Friendly name** — e.g. "My Device"
3. **Description** — one sentence
4. **IoT class** — `local_polling` / `local_push` / `cloud_polling` / `cloud_push` / `calculated`
5. **Data model** — polling (use `DataUpdateCoordinator`) or push (subscription)
6. **Auth model** — none / API key / OAuth / username+password
7. **Platforms** — button, sensor, binary_sensor, switch, light, number, select, text, notify, cover, climate, fan, lock, media_player, vacuum (pick any)
8. **MicroPython firmware?** (yes/no) — adds `firmware/` exclusion to pyrightconfig.json
9. **Licence** — default **MIT**. HACS validates that the repo has one GitHub can identify
   by SPDX, so a missing or bespoke licence fails `HACS validation` on the first PR with
   `The repository license could not be identified (SPDX: NOASSERTION)`. Write the real
   text of the chosen licence to `LICENSE`; a paraphrase does not resolve.
10. **Version** — default `0.1.0`

## Files to generate

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
  (`templates/hooks/` holds optional per-turn reminders for a user's own `~/.claude`; the canonical, shareable enforcement is this `CLAUDE.md` rule, which ships with the repo.)
- `hacs.json` — `name` is the only strict requirement, but the canonical setup ships a **zip release**: `{"name": "My Integration", "content_in_root": false, "zip_release": true, "filename": "<domain>.zip"}` (add `"homeassistant": "<oldest HA you actually test>"`; `runtime_data` alone needs 2024.2+, so do not copy an older floor from an example). `zip_release` makes HACS download a release **asset** named `<filename>` instead of the tag source archive — so it **requires** the `release.yml` *Create Release ZIP* workflow (`templates/.github/workflows/release.yml`) to build and attach that asset on every published release. **Without that workflow, HACS install fails with `Could not download`** (the symptom of a `zip_release` repo whose release has no attached zip). Drop `zip_release`/`filename` only if you deliberately want HACS to pull the whole tagged repo archive instead.

  > **The tag is the version, not the committed manifest** — how that works, and why no PR
  > carries a bump, is `reference/versioning.md`. What matters here: `skill_audit.py` fails a
  > `zip_release` repo whose `release.yml` does not patch the manifest before zipping.
- `pyproject.toml` — copy `templates/pyproject.toml` verbatim. Its `[tool.ruff]` tables are
  Home Assistant core's own rule set adapted for a custom integration (`google` docstrings,
  Python 3.14, no `from __future__ import annotations`), and its pytest table carries the
  `asyncio_mode = "auto"` without which the async tests never run and `skill_audit.py`
  fails the repo once `tests/` exists. The shipped `scripts/` and `tests/` are lint- and
  format-clean under those tables; a copy that relaxes them is drift.
- `pyrightconfig.json`
- `requirements.test.txt` — **required**; copy `templates/requirements.test.txt`. Why the pin matters, and what breaks without it: `reference/testing.md`.
- `conftest.py` — **required, at the repo root, not in `tests/`**; copy `templates/conftest.py`. Why it must be at the root: `reference/testing.md`.
- `tests/` — one file per module under test, plus the template's own tests for the tooling it
  ships. `skill_audit.py` requires `test_manifest_gate.py` and `test_commit_summary.py`; copy
  the rest of `templates/tests/` alongside whichever scripts you keep. Testing rules are
  `reference/testing.md`.

- `README.md` — **include the AI-assistance disclaimer** as a GitHub `> [!NOTE]` admonition box. Link the skill name to its public repo. Template:
  ```markdown
  > [!NOTE]
  > **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/ha-skills) skill. Architecture and final review are mine; every change is human-reviewed before it merges.
  ```
- `LICENSE` — the full text of the chosen licence (MIT unless told otherwise), so GitHub
  resolves an SPDX identifier and the HACS `license` check passes.
- `.gitignore` — copy `templates/.gitignore`. Covers `__pycache__/`, caches, venvs, HA dev artefacts (`.storage/`, `home-assistant.log*`, the `_v2.db`), and `device_map.md` (the `ha-triage` device map holds a home's IP/device layout and must never be committed). **Not optional:** without it a local `pytest` run plus a `git add -A` commits `.pyc` files, and a `.pyc` under `templates/` is then copied verbatim into every repo scaffolded from the skill. `skill_audit.py` fails on any tracked compiled artefact.
- `ruleset.json` — copy `templates/ruleset.json` to the repo root; what it requires and why is `reference/github-setup.md`.
- `.githooks/commit-msg` — copy `templates/hooks/commit-msg`, `chmod +x`. Terse-subject + AI-trailer rejection. **Enable once per clone: `git config core.hooksPath .githooks`** — an unenabled hook is a file, not a guard. Document that line in `CLAUDE.md`.
- `custom_components/{domain}/brand/icon.png` — **256×256**, required by HACS brands validation
- `custom_components/{domain}/brand/icon@2x.png` — **512×512** (see HiDPI note below)
- `custom_components/{domain}/brand/logo.png` — landscape, shortest side **128–256**
- `custom_components/{domain}/brand/logo@2x.png` — landscape, shortest side **256–512**

**The CI stack — copy whole, do not author.** Missing files here are ~13 separate audit
failures on the first run, so this is not an optional last step:

- `.github/workflows/` — eleven of the twelve in `templates/.github/workflows/`. The
  twelfth, `panel_bundle.yml`, belongs only to an integration that serves a panel and is
  copied with `frontend/` per `reference/panels.md`; on a repo with no `frontend/` its own
  first run fails. `skill_audit.py` requires it once `frontend/` exists and fails the
  superseded `frontend_build.yml`
- `.github/dependabot.yml` and `.github/release-drafter.yml`
- `scripts/` — all of `templates/scripts/`; `skill_audit.py` fails a repo missing any of
  `manifest_gate.py`, `commit_summary.py`, `release_notes.py`, `check_release_notes.py`,
  `version_sync.py`

What each workflow is for, and the only changes allowed in a copy, is
`reference/github-actions.md`.

### Brand assets are served from the integration's own `brand/` folder

Via the Brands Proxy API, from the HA version recorded in `reference/freshness.md`. The `home-assistant/brands` CDN `custom_integrations/` folder is **legacy** — do not rely on it for new work. Files are PNG, lossless; transparent background for wordmark/logo art (an LED-screen/device screenshot keeps its black background — that's the device, not a missing alpha).

> ⚠️ **The HACS store/search dashboard still reads the legacy `data-v2.hacs.xyz` (which mirrors the old brands CDN), NOT the inline `brand/` folder.** So an integration that ships *only* inline brand images — i.e. one that never got a `home-assistant/brands` entry, and now **can't** (brands auto-closes `custom_integrations/*` PRs) — renders **blank in the HACS dashboard** even though HA's own UI shows the icon correctly via the proxy. Integrations with a *legacy* brands entry (added before the Feb-2026 cutoff) keep showing in HACS. This is a HACS-side gap, not a repo defect — nothing to fix in the integration; it resolves when HACS points its dashboard at the proxy (tracked in hacs/integration #5171 and #5223). Don't try to "fix" it by PR-ing `home-assistant/brands` (auto-closed).
>
> ⚠️ **Ship the `@2x` variants or the icon flickers/fails on HiDPI.** The most common "icon shows only sometimes" bug is a present `icon.png` with **no `icon@2x.png`**: a Retina/zoomed client requests `@2x`, 404s, and falls back inconsistently. `icon@2x.png` (512²) and `logo@2x.png` are not optional. Exact, square sizes matter — an off-spec `icon.png` (e.g. 384²) also misbehaves.

### Sources

A placeholder may start as an SVG rasterised with `cairosvg` (ImageMagick's MSVG renderer botches text) or `convert -background none -density 144 in.svg out.png`. But the asset can equally be a **crisp nearest-neighbour upscale of a real device render** — for a pixel display this is the strongest branding. Pick by where HA shows it: the **logo** renders large (integration page / HACS) so a busy/detailed screen reads well; the **icon** renders small (~48px in the integrations list) so use a **simple, low-detail** screen (fewer, fatter pixels survive the shrink) — a full text-heavy screen turns to mush. Generate the PNG straight from the byte-faithful preview (`render_layout_png(..., scale=N)`), not a photo.

> HACS `check-brands` fails if `custom_components/{domain}/brand/icon.png` is absent and the integration is not listed in the HA brands repo.

**HACS validation — 9 checks**

⚠️ All nine must pass; none may be ignored (the `ignore:` input is off-limits — `reference/github-actions.md` has the workflow contract). Fix them here, at scaffold time, since each one maps to a file or a GitHub setting:

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
| `license` | An SPDX-identifiable `LICENSE` in the repo | File in repo |

The `description`, `issues`, `topics` and `license` checks fail silently until the first `hacs_validate` run — they're GitHub settings, not files.

## manifest.json key order

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

## Implementation patterns, file structure, typing & testing

See **`reference/patterns.md`** — `__init__`/coordinator/entity/notify patterns, `entry.runtime_data`, `DeviceInfo`, the modern `NotifyEntity` path, the typing rules (no `from __future__ import annotations`, typed `ConfigEntry`), the file-split conventions, with the **mock-the-boundary** testing rules in `reference/testing.md`.

---

## Code style

Typing, file structure and the code patterns themselves are `reference/patterns.md`. What a
scaffold must set up:

- Module docstring on every file. **This one may be multi-line** — a file-level explanation of a load-bearing constraint belongs here, not demoted to a comment.
- Short **single-line** docstrings on all public functions and classes. `skill_audit.py` fails a *multi-line* one **inside `custom_components/` only** — copied `scripts/` and `tests/` are not checked, and module docstrings are exempt. It does not check that a docstring is present at all; that part is on you.
- No inline comments unless the WHY is genuinely non-obvious
- `ruff check .` and `ruff format --check .` clean under the shipped `pyproject.toml`; pyright standard mode

---

## Commit conventions, versioning & CI gating

See **`reference/commits.md`** for commit subjects and what the notes are built from, and **`reference/versioning.md`** for the semver mapping, the prerelease/rc cycle, the **last-published-release** version gate, Dependabot, and the `GITHUB_TOKEN` workflow-suppression footgun.

---
