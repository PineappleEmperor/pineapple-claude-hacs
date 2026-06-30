# Implementation patterns, file structure, typing & testing

Reference for `ha-integration` Mode 1/2. Loaded on demand.

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
- **A `device_class` constrains which `state_class` is legal — verify the pair against the authoritative source, never guess.** HA hard-codes the allowed combinations in `DEVICE_CLASS_STATE_CLASSES` (`homeassistant/components/sensor/const.py`); a disallowed pair logs *"is using state class X which is impossible considering device class Y"* and silently drops long-term statistics. The constraint: `SensorDeviceClass.MONETARY` permits **only `{SensorStateClass.TOTAL}`** — `MEASUREMENT` is invalid for monetary. Don't "fix" an invalid combo by **deleting** `state_class` (that kills LTS entirely, a worse regression than the warning) — switch to a *valid* one. So a fluctuating money **balance** (settle-up debt, account balance) is `device_class=MONETARY` + `state_class=TOTAL`, not `MEASUREMENT`. Before setting any `device_class`/`state_class` pair, check the current mapping at https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/sensor/const.py (or the device-class table at developers.home-assistant.io/docs/core/entity/sensor) — the mapping changes between HA versions. Lock the chosen pair with an attribute test so a future rewrite can't silently drop it.

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
