# Implementation patterns, file structure and typing

The canonical lookup for code inside `custom_components/`: pattern, rule, copyable
snippet. Panel code is `reference/panels.md`; tests are `reference/testing.md`.

- `__init__.py`
- Notify platform (modern pattern — HA 2023.8+)
- `config_flow.py`
- Entity platform files
- `EntityDescription` pattern
- `UpdateEntity` (firmware/OTA install)
- `DataUpdateCoordinator` (polling)
- Entity push subscriptions
- `ConfigEntry` mutation
- Logging
- Custom services
- `services.yaml` + `strings.json` (hassfest rules)
- Register integration-global resources in `async_setup`, not `async_setup_entry`
- Diagnostics platform
- Config entry migration
- File structure conventions
- Typing
- Do not add `from __future__ import annotations`
- `TYPE_CHECKING` for expensive or circular imports
- Typed `ConfigEntry`
- Avoid `# type: ignore`
- MicroPython firmware files
- HA itself is fully typed

| Pattern | For |
|---|---|
| `` `__init__.py` `` | entry setup/unload, `runtime_data`, platform forward |
| Notify platform | the modern `NotifyEntity` path, not `BaseNotificationService` |
| `` `config_flow.py` `` | user/reauth/reconfigure steps, unique-id aborts |
| Entity platform files | `CoordinatorEntity`, `DeviceInfo`, naming, availability |
| `` `UpdateEntity` `` | firmware/OTA install |
| `` `DataUpdateCoordinator` `` | polling, backoff, shutdown |
| Entity push subscriptions | subscribe/unsubscribe lifecycle |
| `` `ConfigEntry` `` mutation | options updates without a reload loop |
| Logging | Silver `log-when-unavailable`, HA conventions |
| Custom services | registration, schema, `services.yaml` + `strings.json` |
| Typing | no `from __future__ import annotations`, `TYPE_CHECKING`, typed `ConfigEntry` |

### `__init__.py`

**Pick the shape HA models.** An entity platform when the thing has state a user would see
in history or on a dashboard. A registered service when it is an action with no state. An
option on the config entry when it is configuration. Notify is an entity platform because a
notifier is addressable; a one-shot "send this" with no addressable target is a service.

**Wire it in one change:**

1. `PLATFORMS` lists the platforms this integration provides, and each name has a module
   beside it — `async_forward_entry_setups` imports `<domain>/<platform>.py` per name.
2. `async_setup_entry` stores state on `entry.runtime_data`, then forwards:
   `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`.
3. `async_unload_entry` mirrors it:
   `return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)`, plus
   `await coordinator.async_shutdown()` when the unload succeeds.
4. If setup creates a device, add `async_remove_config_entry_device` so a user can remove it.
5. If the entity carries `_attr_translation_key`, add the matching block to `strings.json`
   and `translations/en.json` — `entity-translations` in `reference/quality-scale.md`.

`scripts/skill_audit.py` fails a repo whose `PLATFORMS` names a module that does not exist,
so the gate catches a half-wired platform without anyone having to remember this list.

### Notify platform (modern pattern — HA 2023.8+)
```python
# notify.py
from homeassistant.components.notify import NotifyEntity


class MyNotifyEntity(NotifyEntity):
    """The notify entity for one device."""

    _attr_has_entity_name = True
    _attr_name = "Notify"

    def __init__(self, hass, device_id: str) -> None:
        """Bind the entity to its device."""
        self.hass = hass
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_notify"  # per instance, not class scope

    # This is the real signature. NotifyEntity's service schema carries message and
    # title only, so there is no **kwargs and no `data` to read.
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send the message to the device."""


async def async_setup_entry(hass, entry, async_add_entities):
    """Add one notify entity for the config entry."""
    opts = {**entry.data, **entry.options}
    async_add_entities([MyNotifyEntity(hass, opts[CONF_DEVICE_ID])])
```
⚠️ **Do NOT use** `discovery.async_load_platform` + `BaseNotificationService` — deprecated, silently fails in recent HA versions.
⚠️ `NotifyEntity` only supports `message` and `title` — `data` is **not in its service schema**. If you need custom payload fields (animations, sounds, colours, etc.), register the service directly instead:
```python
# notify.py
from homeassistant.components.notify.const import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TITLE,
    DOMAIN as NOTIFY_DOMAIN,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DATA): dict,
    }
)


def make_notify_handler(hass: HomeAssistant, device_id: str):
    """Build the service handler bound to one device."""

    async def async_handle(call: ServiceCall) -> None:
        """Push the message, with any extra payload, to the device."""
        data = call.data.get(ATTR_DATA) or {}
        await push_to_device(hass, device_id, call.data[ATTR_MESSAGE], data)

    return async_handle


# __init__.py async_setup_entry:
if not hass.services.has_service(NOTIFY_DOMAIN, device_id):
    hass.services.async_register(
        NOTIFY_DOMAIN,
        device_id,
        make_notify_handler(hass, device_id),
        schema=SERVICE_SCHEMA,
    )
# async_unload_entry:
if hass.services.has_service(NOTIFY_DOMAIN, device_id):
    hass.services.async_remove(NOTIFY_DOMAIN, device_id)
```
This creates `notify.{device_id}` (e.g. `notify.living_room_display`) with full data support.

### `config_flow.py`
- `class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):` — `domain=` is a keyword arg, not a class attribute
- Include `OptionsFlow` (not `OptionsFlowHandler` — that name is deprecated) when the integration has configurable options
- Implement `async_step_reauth` for expired/invalid auth (Silver requirement)
- Implement `async_step_reconfigure` for changing connection settings (Gold requirement)
- `vol.Schema` — one entry per line, exactly as `ruff format` leaves it (the shipped format check rejects hand-aligned columns):
  ```python
  DATA_SCHEMA = vol.Schema(
      {
          vol.Required(CONF_HOST, default="192.168.1.1"): str,
          vol.Required(CONF_PORT, default=8080): int,
      }
  )
  ```

### Entity platform files
- Extend `CoordinatorEntity` (polling) or `Entity` (push)
- Access runtime state via `entry.runtime_data` not `hass.data[DOMAIN][entry.entry_id]`
- Use `DeviceInfo` TypedDict (from `homeassistant.helpers.device_registry`) — not a plain dict:
  ```python
  from homeassistant.helpers.device_registry import DeviceInfo


  @property
  def device_info(self) -> DeviceInfo:
      """The device this entity belongs to."""
      return DeviceInfo(identifiers={(DOMAIN, self._device_id)}, name="My Device")
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

### `EntityDescription` pattern

Preferred when an integration exposes many similar entities:
```python
@dataclass(frozen=True, kw_only=True)
class MySensorDescription(SensorEntityDescription):
    """Describes one sensor and where its value comes from."""

    value_fn: Callable[[MyData], float]


SENSORS: tuple[MySensorDescription, ...] = (
    MySensorDescription(
        key="temperature", translation_key="temperature", value_fn=lambda d: d.temp
    ),
    MySensorDescription(
        key="humidity", translation_key="humidity", value_fn=lambda d: d.humidity
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add one sensor per description."""
    coordinator = entry.runtime_data
    async_add_entities(MySensor(coordinator, desc) for desc in SENSORS)
```

### `UpdateEntity` (firmware/OTA install)
- `_attr_in_progress` only **greys out the dashboard install button** — it does **not** stop a programmatic re-entry. A service call, automation, or two near-simultaneous dashboard clicks can still re-enter `async_install` while an install is mid-flight, double-pushing the OTA. Add an **explicit re-entry guard** at the top of `async_install` (after any can't-install checks), windowed so a crashed/timed-out install can't wedge the entity forever:
  ```python
  async def async_install(self, version, backup, **kwargs) -> None:
      """Push the OTA once, refusing a second entry while one is in flight."""
      if self._reflash:
          raise HomeAssistantError("Layout change — reflash via USB, not OTA.")
      if self._installing and time.monotonic() - self._install_started < INSTALL_TIMEOUT:
          raise HomeAssistantError("An update is already in progress for this device.")
      self._installing = True
      self._install_started = time.monotonic()
      self._attr_in_progress = True
      self.async_write_ha_state()
      await self._push_ota(version)
  ```
  Clear `_installing` when the new version lands (or the same window elapses) in whatever resyncs state from the device manifest. The `in_progress` flag is for the UI; the boolean+timestamp is the actual lock.

### `DataUpdateCoordinator` (polling)
- `update_interval` minimum 5 s
- Set `always_update=False` when API responses support `__eq__` — avoids unnecessary state machine writes
- Raise `ConfigEntryAuthFailed` on auth errors inside `_async_update_data`
- Raise `UpdateFailed` on other errors; use `UpdateFailed(retry_after=60)` for rate-limited APIs
- For push APIs: use `coordinator.async_set_updated_data(data)` instead of adapting to polling

### Entity push subscriptions
- Subscribe in `async_added_to_hass`, unsubscribe in `async_will_remove_from_hass` — prevents resource leaks
- Never subscribe in `__init__`

### `ConfigEntry` mutation
- Never mutate `ConfigEntry` directly — always use `hass.config_entries.async_update_entry(entry, data=..., options=...)`

### Logging

Covers the Silver rule `log-when-unavailable` and HA's logging conventions.

- **The coordinator already gives you `log-when-unavailable` for free.** When `_async_update_data` raises `UpdateFailed`, `DataUpdateCoordinator` logs the *first* failure at **ERROR**, subsequent consecutive failures at **DEBUG** (no spam), and logs **recovery** automatically. So **do not** wrap the fetch in your own try/log — manual error logging there is double-logging and *fails* the rule. Same for `ConfigEntryNotReady`/`ConfigEntryAuthFailed`: HA logs the reason once; don't also `_LOGGER.exception(...)` in `async_setup_entry` (delete broad `try/except: log; raise` wrappers — they spam and add nothing).
- **Don't log-and-raise.** Raise the right exception and let HA log it: transient → `UpdateFailed`/`ConfigEntryNotReady`; auth → `ConfigEntryAuthFailed`; service/action errors → `HomeAssistantError`/`ServiceValidationError` (Silver `action-exceptions`). Logging *and* raising the same condition is noise.
- **Level discipline:** `INFO` is shown by default → use it almost never. **Setup / unload / teardown lifecycle = `DEBUG`, not `INFO`.** `WARNING` = recoverable thing the user should know; `ERROR` = unexpected, actionable bug (never for expected transient failures — those are exceptions HA handles). `DEBUG` = per-poll / developer detail.
- **Lazy `%` args, never f-strings:** `_LOGGER.debug("added %s", key)` not `f"added {key}"` — ruff `G004` / pylint `logging-fstring-interpolation` enforce. f-string args evaluate even when the level is disabled.
- **Never log secrets** — credentials, API keys, tokens, raw auth responses.
- Logger name (`logging.getLogger(__name__)`) already carries the module path — don't prefix messages with the integration name or "Home Assistant".
- Remove a module-level `_LOGGER` that ends up unused (e.g. after deleting lifecycle spam) — ruff won't flag an unused module global, so it lingers silently.

### Custom services
- Register in `async_setup` (not `async_setup_entry`) to avoid duplicate registration across multiple config entries
- Use `async_register_platform_entity_service()` for entity-targeted actions
- Document in `services.yaml`; add icons in `icons.json`
- A `selector: config_entry` renders a field labelled "Integration" (hardcoded in the HA frontend). To present a device dropdown, use `selector: device` with `integration: {domain}`, then resolve the HA device → config entry in the handler via `device_registry.async_get(hass).async_get(id)`.
- **Target the entry, or the call fans out.** `hass.services.async_call(DOMAIN, svc, …)` with no target reaches **every** config entry. An entity action that should touch only its own device passes its own `entry_id`/`device_id` and the handler filters on it; leave it untargeted only for a deliberate bulk call.

### `services.yaml` + `strings.json` (hassfest rules)
- The modern convention: `services.yaml` carries only field **structure** (selectors, `required`, `default`, collapsible `sections`); names/descriptions live in `strings.json` under a top-level `services` key (`services.{svc}.name/description`, `.fields.{key}.name/description`, `.sections.{key}.name`). Field keys are flat in `strings.json` even when nested in a `sections` block in `services.yaml`. Keep `translations/en.json` a copy of `strings.json`.
- **hassfest forbids literal URLs in `strings.json` descriptions** — `the string should not contain URLs`. Use plain text, or a `{placeholder}` filled via `description_placeholders` in the flow step. A markdown image `![x]({url})` with a placeholder is fine (no literal `http`).
- Collapsible service form: `fields: { appearance: { collapsed: true, fields: {...} } }` — sections are UI-only; the call data stays flat, so the voluptuous schema is unaffected.

### Register integration-global resources in `async_setup`, not `async_setup_entry`
The registration happens once per process; doing it per entry races when two entries set up in parallel. Claim the `hass.data` flag **before** the `await`, or both entries pass the check. The panel case, with the code, is `reference/panels.md`.

### Diagnostics platform

A Gold requirement. Add `diagnostics.py`:

```python
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_PASSWORD, CONF_API_KEY, "token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return the entry and its runtime data with secrets redacted."""
    return async_redact_data(
        {"entry": entry.as_dict(), "data": entry.runtime_data}, TO_REDACT
    )
```
No registration needed — HA discovers it automatically from the file name.

### Config entry migration

Implement `async_migrate_entry` in `__init__.py` whenever the stored `entry.data` schema changes:
```python
# In config flow:
class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow; the version pair says which stored entries need migrating."""

    VERSION = 2  # bump for breaking changes (fails setup if no handler)
    MINOR_VERSION = 1  # bump for compatible changes (setup continues without handler)


# In __init__.py:
async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bring a stored entry up to the current version."""
    if entry.version == 1:
        new_data = {**entry.data, "new_field": "default"}
        hass.config_entries.async_update_entry(
            entry, data=new_data, version=2, minor_version=1
        )
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

### Do not add `from __future__ import annotations`

Python 3.14, HA's floor, defers annotation evaluation natively (PEP 649), so forward
references and `TYPE_CHECKING`-only imports work without it. The import only switches Python
back to the older stringified behaviour, which some runtime tooling handles worse. Core bans
it, and the shipped `pyproject.toml` enforces the ban through ruff (`TID251`).

### `TYPE_CHECKING` for expensive or circular imports
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def uses_hass_in_annotations_only(hass: HomeAssistant) -> None:
    """The import never runs; deferred annotations resolve the name when asked."""
```

### Typed `ConfigEntry`

Alias the entry to its runtime type so `entry.runtime_data` is not untyped:
```python
# In coordinator.py or models.py:
from homeassistant.config_entries import ConfigEntry

type MyConfigEntry = ConfigEntry[MyCoordinator]  # Python 3.12+ / HA 2024.x


# In platform files:
async def async_setup_entry(
    hass: HomeAssistant, entry: MyConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the platform from the typed entry."""
    coordinator = entry.runtime_data  # typed as MyCoordinator, no cast needed
    async_add_entities(MySensor(coordinator, desc) for desc in SENSORS)
```

### Avoid `# type: ignore`

At Platinum quality a type suppression is a violation, not a shortcut. The common HA patterns that tempt one all have proper solutions:
- `hass.data[DOMAIN]` is untyped → don't use it; use `entry.runtime_data` with typed `ConfigEntry` instead
- `entry.runtime_data` assignment errors → solved by the typed `ConfigEntry` alias above
- Third-party library missing stubs → contribute stubs or use `cast()` with a comment explaining why

Only acceptable suppression: `# type: ignore[import-untyped]` on a third-party import with no available stubs, where contributing stubs is out of scope.

### MicroPython firmware files

Exclude them from Pyright entirely in `pyrightconfig.json`:
```json
{
  "exclude": ["firmware/"],
  "typeCheckingMode": "standard"
}
```

### HA itself is fully typed

Import its types directly rather than re-typing them:
```python
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
```

---

Testing — the harness prerequisites and what to mock — is `reference/testing.md`.
