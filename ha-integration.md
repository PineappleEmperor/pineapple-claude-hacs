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
- `custom_components/` exists → ask: **Scaffold** new integration / **Modify** existing / **Lint & quality check**?

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
- `hacs.json` — minimal content: `{"name": "My Integration"}` (HACS only strictly requires `name`; add `"homeassistant": "2024.1.0"` for minimum HA version)
- `pyproject.toml`
- `pyrightconfig.json`
- `README.md`
- `.gitignore`
- `custom_components/{domain}/brand/icon.svg` — placeholder 256×256 icon (source)
- `custom_components/{domain}/brand/logo.svg` — placeholder logo, 2:1 ratio, transparent background (source)
- `custom_components/{domain}/brand/icon.png` — **required by HACS brands validation**
- `custom_components/{domain}/brand/logo.png` — include for completeness

Generate PNGs from SVGs:
```
convert -background none -density 144 custom_components/{domain}/brand/icon.svg custom_components/{domain}/brand/icon.png
convert -background none -density 144 custom_components/{domain}/brand/logo.svg custom_components/{domain}/brand/logo.png
```

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
- `.github/workflows/semantic_release.yml` — triggers on `v*.*.*` tag push; uses `softprops/action-gh-release@v2` with `generate_release_notes: true`. Tags containing `beta` auto-marked as prerelease. No npm, no semantic-release tooling needed.
- `.github/workflows/create-dev-pr.yml` — triggers on every push to non-main branches; auto-creates a draft PR with title from commits (`feat:` wins over `fix:` wins over last commit). Updates PR body with commit list on subsequent pushes. Copy from `~/ha-imap-parcel/.github/workflows/create-dev-pr.yml`. ⚠️ After computing `TITLE`, always add `TITLE=$(echo "$TITLE" | xargs)` before `echo "title=$TITLE" >> $GITHUB_OUTPUT` — GitHub Actions env var interpolation can add surrounding whitespace that breaks `lint_pr.yml` semantic title validation. Do NOT add a `label` job — labeling is handled automatically by `pr-labeler.yml` via `release-drafter` autolabeler, which fires on `opened`, `reopened`, and `synchronize` events. This means the label re-evaluates on every push: if a later commit has a higher conventional-commit type (breaking `!` > `feat` > `fix` > `chore`), the label upgrades automatically.
- `.github/workflows/release.yml`
- `.github/workflows/release_drafter.yml` — must include both `push` (main) and `pull_request` triggers; needs `pull-requests: write` permission for autolabeler to apply labels.
- `.github/workflows/pr-labeler.yml`
- `.github/workflows/lint_pr.yml`
- `.github/workflows/hacs_validate.yml`
- `.github/workflows/hassfest_validate.yml`
- `.github/workflows/python_validate.yml`
- `.github/workflows/check-manifest-version.yml`
- `.github/pr-labeler.yml`
- `.github/release-drafter.yml`

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
- `async_unload_entry`: call `async_unload_platforms`; `entry.runtime_data` cleaned up automatically
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
- Don't pass `update_before_add=True` to `async_add_entities` — coordinator handles updates

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
- Serve a built JS bundle and register the panel once (not per entry), guarded by a `hass.data` flag; remove on last unload:
  ```python
  from homeassistant.components import frontend, panel_custom
  from homeassistant.components.http import StaticPathConfig
  await hass.http.async_register_static_paths(
      [StaticPathConfig("/{domain}_panel/editor.js", str(Path(__file__).parent / "panel" / "editor.js"), False)])
  await panel_custom.async_register_panel(hass, frontend_url_path="{domain}",
      webcomponent_name="{domain}-panel", module_url="/{domain}_panel/editor.js",
      sidebar_title="...", sidebar_icon="mdi:view-grid", require_admin=True)
  # unload: frontend.async_remove_panel(hass, "{domain}")
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

**Keep messages short.** Tight imperative subject; **subject-only by default**. Add a body ONLY when the *why* is non-obvious, or for breaking changes / migration notes — never to restate what the diff already shows. Long bodies that narrate the change are noise.

**Put the narrative in the release, not the commit.** The human-readable "what changed and why it matters" belongs in the **PR description / release notes** (surfaced by release-drafter / `generate_release_notes`), which is where users actually read it. Keep commits terse; write the detail once, in the release description.

**Match release-drafter when writing the PR body.** If `change-template` includes `$BODY`, the PR description is inlined **under** its category heading (e.g. `### 🚀 Features`). So the body must nest cleanly: use **bold emoji sub-heads** (`**🧩 Engine**`), not `#`/`##` — top-level headings render bigger than the category and clash. Mirror the config's emoji category style, and label the PR so it lands in the intended category (e.g. a `major`/`xfeature` label → 🚨 Breaking Change). Note release-drafter draws the PR body via the GraphQL path; `gh pr edit` can fail on the Projects-classic deprecation — set title/body via `gh api -X PATCH repos/{o}/{r}/pulls/{n} -f title=… -F body=@file` instead.

**Types and semver mapping:**

| Type | Semver | Notes |
|------|--------|-------|
| `feat` | MINOR | New feature |
| `fix` | PATCH | Bug fix |
| `feat!` / `BREAKING CHANGE:` | MAJOR | Breaking change — any type with `!` or `BREAKING CHANGE` footer |
| `chore`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style` | PATCH | No user-facing change |

**How this flows through the repo workflows:**

1. `create-dev-pr.yml` picks the PR title from commits: `feat` (incl. `feat!`) wins over `fix` wins over last commit. Its label step then detects a breaking `!` first (`grep -qiE '^[a-z]+(\(.+\))?!:'`) → `xfeat`, else maps `feat`→`feature`, `fix`→`fix`, `chore|docs`→`chore`
2. `pr-labeler.yml` / `release_drafter.yml` autolabeler applies a label from the PR title on every push — priority: breaking (`xfeat`) > `feature` > `fix` > `chore`
3. `release-drafter.yml` config maps labels → semver bump: `feature` → minor, `fix`/`chore` → patch, `major`/`xfeat`/`xfeature` → major
4. On tag push (`v*.*.*`), `semantic_release.yml` cuts the GitHub release

**Breaking changes (`feat!` / `xfeat`) are captured automatically — required wiring in two places:**
- **`release-drafter.yml` autolabeler:** a breaking rule **before** the feature rule, matching any type with `!`: `title: ['/^\w+(\(.+\))?!:/']` → label `xfeat` (branches `/^(xfeat|xfeature|breaking)\/.+/`). The `feature`/`fix`/`chore` rules must require a colon, **not** `!` (`/^(feat|feature)(\(.+\))?:/i`), so a `feat!:` title lands in the breaking bucket only, not both. `xfeat`/`xfeature`/`major` are in the `major` `version-resolver` and the 🚨 Breaking Change category (first category wins for display).
- **`create-dev-pr.yml` label step:** the `if … grep -qiE '^[a-z]+(\(.+\))?!:'` branch above sets `LABEL="xfeat"`; include `xfeat` in the stale-label cleanup loop (`for L in feature fix chore xfeat`) so a downgrade from breaking clears it.

Without both, a `feat!` is silently treated as a minor `feature` — the regex-less `feature` rule swallows the `!`.

⚠️ **Type-vocab gap (don't hand-label around it):** both `create-dev-pr.yml`'s label step and the autolabeler only map `feat|fix|chore|docs`. A commit/PR typed `ci:`, `refactor:`, `build:`, `perf:`, `style:`, `revert:` matches **nothing** → no label → the PR lands in **no** release-drafter category. The fix is the *type*, not a manual `gh` label patch (which masks the gap and is clobbered on the next push): give the headline commit a mapped type (e.g. `chore:` not `ci:` for a workflow tweak). Also: `create-dev-pr.yml` derives the PR title from `feat` > `fix` > **last commit subject** — so when no commit is feat/fix, order the headline commit **last**, or it won't be the title.

**HA `manifest.json` version** must be bumped manually to match the intended release version before merging — `check-manifest-version.yml` enforces that it's been updated.

⚠️ **Bump discipline (learned the hard way):** before every push to a feature branch, `git fetch origin` **first** (the local `origin/main` ref goes stale as PRs merge — trusting a stale ref means bumping wrongly and the gate failing on the real value), then compare the branch's `manifest.json` version to `origin/main`'s and bump in the same push. Bump level must match the PR's type label (the version-check workflow keys its expected version off the label): `feat`→minor, `fix`/`chore`/`test`→patch. After a PR merges mid-work, the branch sits at the now-merged version → the next push needs a fresh bump.

**Prerelease (rc) cycle:** to ship release candidates while keeping the final target version fixed (e.g. finalize as `v2.0.0` after `rc1`, `rc2`…), carry a **PEP440 prerelease** in the manifest: `2.0.0rc2` — `AwesomeVersion` accepts it (modifier `rc2`, and `2.0.0 > 2.0.0rc2 > …rc1`), and hassfest/HACS validate it. The GitHub release uses the **prerelease flag** (and a `v2.0.0-rc2` tag); the `X.Y.Z` number stays frozen across the cycle. `check-manifest-version.yml` needs two tweaks to cope: (1) the base-version parse regex must tolerate a suffix — anchor `^([0-9]+)\.([0-9]+)\.([0-9]+)` without `$`, since once an rc PR merges the *base* carries `rcN` too; (2) skip the bump-type "incorrect version" suggestion when the PR version is a prerelease (detect `(rc|alpha|beta|a|b|dev)[0-9]*$`) — the "must differ from base" rule still applies, so rc# increments per PR while the target number doesn't move.

---

### ⚠️ GITHUB_TOKEN suppresses workflow events on auto-created PRs

The biggest CI footgun: **a PR opened/updated by a workflow using the default `secrets.GITHUB_TOKEN` does NOT emit `pull_request` events** (GitHub's anti-recursion rule). So every `pull_request`-triggered workflow — `pr-labeler.yml`, `hassfest_validate.yml`, `check-manifest-version.yml`, etc. — **silently never runs** on the dev PRs that `create-dev-pr.yml` creates. Symptoms: labels never applied, version bumps never enforced, validations skipped until a human pushes/reopens.

Two fixes:
- **Proper fix:** create the dev PR with a **PAT** (personal access token secret) instead of `GITHUB_TOKEN` — PAT-authored PRs do emit events, so all downstream `pull_request` workflows run normally. Costs a long-lived secret to manage.
- **No-secret fix:** add a `push:` trigger (`branches-ignore: [main]`) to each check so it runs on the branch push (always fires, regardless of how the PR was made). Default the base ref to `main` when there's no PR context, and guard PR-only steps with `if: github.event_name == 'pull_request'` (e.g. label lookups, PR comments). This is what made `check-manifest-version` actually enforce.

**`create-dev-pr.yml` hardening** (prevents duplicate/stale PRs seen in practice):
- Add `concurrency: {group: dev-pr-${{ github.ref }}, cancel-in-progress: true}` so rapid pushes can't race into two PRs.
- Skip PR creation when the branch has **0 commits ahead of main** (`git rev-list --count origin/main..HEAD`) — otherwise pushing to an already-merged branch re-spawns a PR.
- On update, re-set the **title** (`gh pr edit --title`) and **replace** stale type labels (remove `feature`/`fix`/`chore`, add the current one) — `gh pr edit --add-label` only adds, so a PR keeps a stale `feature` label/title after its commits change to fixes, making the version check demand the wrong bump.

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
