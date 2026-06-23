---
description: Create, modify, and lint Home Assistant custom integrations — custom_components packages, manifest.json, config/options/reauth/reconfigure flows, coordinator + entity platforms, services, diagnostics, quality_scale.yaml — targeting Platinum quality scale. Use before writing or modifying any HA integration code; re-invoke after /compact.
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
- `CLAUDE.md` — project instructions. **Always include a rule telling future AI sessions to invoke this `ha-integration` skill before writing/modifying integration code, and to re-invoke after `/compact`** (compaction drops the skill's guidance). Keep this enforcement **per-repo, not global** — a project file is the right scope; do not push a user's global config on others. Suggested snippet:
  ```markdown
  ## AI sessions
  Before writing or modifying integration code (config flow, platforms, manifest,
  websocket, services…), invoke the `ha-integration` skill. Re-invoke it after any
  `/compact`, since compaction can drop the skill's guidance from context.
  ```
  (A user may *additionally* wire a personal `SessionStart`/`UserPromptSubmit` hook in their own `~/.claude/settings.json`, guarded on `custom_components/*/manifest.json`, to re-arm the rule — but that's a personal convenience; the canonical, shareable enforcement lives in the repo's `CLAUDE.md`.)
- `hacs.json` — minimal content: `{"name": "My Integration"}` (HACS only strictly requires `name`; add `"homeassistant": "2024.1.0"` for minimum HA version)
- `pyproject.toml`
- `pyrightconfig.json`
- `README.md` — **include the AI-assistance disclaimer** as a GitHub `> [!NOTE]` admonition box. Link the skill name to its public repo. Template:
  ```markdown
  > [!NOTE]
  > **AI assistance:** I'm a programmer; this project is built with AI (Claude, via Claude Code) for implementation, code review, and QA — under human direction, guided by my [`ha-integration`](https://github.com/PineappleEmperor/pineapple-claude-hacs) skill. Architecture and final review are mine; every change is human-reviewed before it merges.
  ```
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
- `.github/workflows/create-dev-pr.yml` — triggers on every push to non-main branches; auto-creates a draft PR with **title from commits** (`feat:` wins over `fix:` wins over last commit). Updates PR body with commit list on subsequent pushes. Copy from `~/ha-imap-parcel/.github/workflows/create-dev-pr.yml`. ⚠️ After computing `TITLE`, always add `TITLE=$(echo "$TITLE" | xargs)` before `echo "title=$TITLE" >> $GITHUB_OUTPUT` — GitHub Actions env var interpolation can add surrounding whitespace that breaks `lint_pr.yml` semantic title validation. **Do NOT add a label step here** — labelling is the autolabeler's job (below). Since this sets the title to the winning commit type, autolabelling off the title is effectively commit-driven; a second labeler here just causes flapping.
- `.github/workflows/release.yml`
- `.github/workflows/release_drafter.yml` — owns the draft release notes (categories + `version-resolver` + `$BODY`); both `push` (main) and `pull_request` triggers; `pull-requests: write`.
- `.github/workflows/pr-labeler.yml` — runs `release-drafter/release-drafter/autolabeler@v7` on `pull_request` (opened/reopened/synchronize). The **sole labeler.**
- `.github/workflows/lint_pr.yml`
- `.github/workflows/hacs_validate.yml`
- `.github/workflows/hassfest_validate.yml`
- `.github/workflows/python_validate.yml` — **pin the matrix to HA's current minimum Python** (as of 2026-06, `["3.14"]` — HA dev requires 3.14.2+; `pip install homeassistant` refuses older). Test the *floor* HA supports, and re-check it at developers.home-assistant.io/docs/development_environment when HA bumps. Keep this in lockstep with `pyproject.toml` ruff `target-version = "py314"` and pylint `py-version = "3.14"`, and `pyrightconfig.json`.
- `.github/workflows/check-manifest-version.yml`
- `.github/pr-labeler.yml`
- `.github/release-drafter.yml` — autolabeler rules are **title-only** (no `branch:` rules). The release-drafter autolabeler can only match title/body/branch/files (never commit subjects), so label off the **title** — which `create-dev-pr` already derives from the commits. Keep it the one-and-only labeler; don't also label in `create-dev-pr.yml`.

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

### Testing — mock at the boundary, not your own code

The most dangerous test is the one that passes while the integration is broken. It happens when a test **patches the integration's own functions** instead of the external dependency.

**Mock only at the external boundary** — the third-party client, socket, or library (`imaplib.IMAP4_SSL`, `aiohttp` via `aioclient_mock`, the vendored device lib, `serial`). Then the integration's *own* wiring runs: reading `entry.data`/`entry.options` into attributes, building requests, parsing responses, populating the coordinator. **Never patch your own `_async_update_data`, `email_triage`, `api.fetch`, etc.** — doing so stubs out exactly the code a refactor is most likely to break, so the test stays green through the regression.

> **Real failure that motivated this rule:** a `runtime-data` refactor dropped the `entry.data → self.host/credential` reads from the coordinator's `__init__`. Every coordinator test passed because they patched the data-fetch function, so the missing attributes were never read. Setup then crashed at runtime with `AttributeError: object has no attribute 'host'`. A test that mocks the *transport* and runs the real fetch (or even just constructs the coordinator and asserts it read the config) fails loudly. The fix-forward is also the `api.py` split: pass config as explicit constructor args so pyright catches a missing field, instead of a helper reaching into `self.<attr>` set elsewhere (an untyped runtime contract that survives refactors silently).

**`test-before-setup` means a real config-entry setup.** Add a `MockConfigEntry`, call `hass.config_entries.async_setup(entry.entry_id)`, and assert `entry.state is ConfigEntryState.LOADED` plus that entities exist — with only the transport mocked. This exercises `async_setup_entry` end to end (credential reads, `async_config_entry_first_refresh`, `runtime_data`, platform forward, entity creation). A `async_setup_component(hass, DOMAIN, {})` test only proves the (unused) YAML path returns `True` and is near-worthless for a config-entry integration. **If you scaffold an `init_integration` fixture, actually use it** — an unused setup fixture is a tell that the highest-value test was skipped.

**Unit-test the pure logic directly** — regex parsers, date/format extraction, data transforms (`order_parse`, `voucher_parse`, `sort_orders`, …) take a string/object and return a value with no HA and no mocks. They carry the highest regression risk and are the cheapest to cover; a parser with zero tests is a standing liability.

**Minimum coverage before claiming a tier:** config-flow (happy path + each error + reauth/reconfigure), a real setup-entry `LOADED` test, coordinator success + auth-failure + the credential-read path against a mocked transport, unload, and a unit test per parser. Wire the regression test *first* on any bug fix: confirm it fails on the unpatched code, then fix.

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

1. `create-dev-pr.yml` sets the PR **title** from the winning commit type (`feat` > `fix` > last commit). It does **no** labelling.
2. `pr-labeler.yml` runs the **release-drafter autolabeler** — the sole labeler — keyed on the PR **title** (title-only rules; no `branch:`). Since the title is the winning commit type, the label tracks the commits: breaking `type!:` → `xfeat`, `feat|feature:` → `feature`, `fix:` → `fix`, `chore|docs:` → `chore`. The breaking `!` rule must precede `feature` (else `feat!` is swallowed as a minor `feature`).
3. `release-drafter.yml` config maps labels → semver bump: `feature` → minor, `fix`/`chore` → patch, `major`/`xfeat`/`xfeature` → major.
4. On tag push (`v*.*.*`), `semantic_release.yml` cuts the GitHub release

⚠️ **One labeler, title-only — don't hand-roll a second one.** The autolabeler can only match title/body/branch/files (never commit subjects). Label off the **title** (which `create-dev-pr` derives from commits) and keep it the *only* labeler. Pitfalls that bit hard: (a) a second label step in `create-dev-pr.yml` **fights** the autolabeler → labels flap (add/remove every push); (b) `branch:` rules flap when the branch name disagrees with the commits (e.g. branch `chore/…`, commits `feat:`) — so use **title-only** rules. Resist re-adding custom bash to "label from commit subjects"; the title already encodes the winning type. (Minor: the autolabeler only *adds*, so if the dominant type changes mid-PR a stale label can linger — the `version-resolver` still takes the highest, and it's rare since a PR is usually one type.)

⚠️ **Type-vocab gap:** the autolabeler title rules map only `feat|fix|chore|docs` (+ `!` → `xfeat`). A title typed `ci:`, `refactor:`, `build:`, `perf:`, `style:`, `revert:` matches **nothing** → no label → no release-drafter category. Since `create-dev-pr` picks the title as `feat` > `fix` > last commit, ensure at least one commit is a mapped type (e.g. `chore:` not `ci:` for a workflow-only PR) so the title lands on something labellable. Don't hand-patch the label (clobbered next push).

**HA `manifest.json` version** must be bumped manually to match the intended release version before merging — `check-manifest-version.yml` enforces that it's been updated.

⚠️ **Bump discipline (learned the hard way):** the manifest bump is the **single, last commit of a PR before it merges** — not a per-push act. **Before even suggesting a bump, check whether the same PR is still being iterated; if so, don't bump.** A red `check-manifest-version` while a PR is in progress is expected and fine — it goes green when you add the one bump commit at the end. The bump **value is the version the PR will be published as** (the next release), and it gets set **once**; don't re-bump it on later pushes to the same PR. When you do set it: `git fetch origin` **first** (the local `origin/main` ref goes stale as PRs merge), compare to `origin/main`'s version, and match the level to the PR's type label (the gate keys its expected version off the label): `feat`→minor, `fix`/`chore`/`test`→patch, breaking→major. The exception that *does* re-bump mid-PR: the PR's type escalates (`fix`→`feat`→`feat!`), changing the label-derived expected version.

**Prerelease (rc) cycle:** release candidates are published via the GitHub **prerelease flag** + a `v…-rcN` tag; the manifest carries a matching **PEP440 prerelease** (`2.0.0rc1`) which `AwesomeVersion`/hassfest/HACS accept (`2.0.0 > 2.0.0rc1`). Two rules that bit hard:
- **rc numbers track *published* candidates, not PRs.** You only increment `rc1`→`rc2` when you actually cut a new published rc; you do **not** invent `rc2`/`rc3` per-PR to satisfy the gate. The version stays frozen at the current rc across iteration; it changes only as the pre-merge bump to the version being published.
- **A prerelease deliberately changes gate behaviour:** a prerelease version only needs to *differ from base* — so the gate must **skip** the label-derived "incorrect version" suggestion when the PR version matches `(rc|alpha|beta|a|b|dev)[0-9]*$` (otherwise a `feature`-labelled `2.0.0rc1` PR fails, demanding `v2.1.0`). Also de-anchor the base parse (`^([0-9]+)\.([0-9]+)\.([0-9]+)` without `$`) so a base that already carries `rcN` still parses. This is the *only* prerelease gate change needed — do **not** add per-PR rc-increment logic or relax the "differ from base" rule.

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
- **Usually nothing** — push more than once (you will anyway) and `synchronize` covers it. This is what the reference repos actually rely on (no PAT in any of them).
- **No-secret hardening for the must-always-enforce gate:** add a `push:` trigger (`branches-ignore: [main]`) to `check-manifest-version` so the version gate runs on the branch push regardless of PR events — covers even the single-push case. Default the base ref to `main` when there's no PR context (`${{ github.event.pull_request.base.ref || 'main' }}`) and guard PR-only steps with `if: github.event_name == 'pull_request'` (label lookups, PR comments).
- **PAT (only if you truly need single-push auto-PRs fully checked):** open the dev PR with a fine-grained, repo-scoped PAT (`Pull requests: write` + `Contents: read`, short expiry) instead of `GITHUB_TOKEN` — PAT-authored events aren't suppressed, so even the `opened` fires everything. Costs a secret to rotate; reserve for when single-push branches matter.

**`create-dev-pr.yml` hardening** (prevents duplicate/stale PRs seen in practice):
- Add `concurrency: {group: dev-pr-${{ github.ref }}, cancel-in-progress: true}` so rapid pushes can't race into two PRs.
- Skip PR creation when the branch has **0 commits ahead of main** (`git rev-list --count origin/main..HEAD`) — otherwise pushing to an already-merged branch re-spawns a PR.
- On update, re-set the **title** (`gh pr edit --title`) to the current winning commit type — the autolabeler re-labels from the new title on the next `synchronize`. (Don't manage labels in this workflow; that's the autolabeler's job.)

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
