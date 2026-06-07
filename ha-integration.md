# Home Assistant Integration Assistant

Help create, modify, and lint Home Assistant custom integrations targeting **platinum quality scale**.

**Always fetch before coding** — these are the authoritative sources:
- Creating integrations: https://developers.home-assistant.io/docs/creating_integration_index/
- Config entries: https://developers.home-assistant.io/docs/config_entries_index/
- Config flows: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
- Data fetching + coordinator: https://developers.home-assistant.io/docs/integration_fetching_data/
- Setup failures: https://developers.home-assistant.io/docs/integration_setup_failures/
- Quality scale: https://developers.home-assistant.io/docs/integration_quality_scale/
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
- `quality_scale.yaml`
- One file per selected platform (e.g. `button.py`, `sensor.py`)

**Repo root:**
- `hacs.json`
- `pyproject.toml`
- `pyrightconfig.json`
- `README.md`
- `.gitignore`

**GitHub workflows** — look for existing workflow files in the current project first and replicate the same patterns. If none exist, use standard HA integration CI:
- `.github/workflows/semantic_release.yml`
- `.github/workflows/release.yml`
- `.github/workflows/release_drafter.yml`
- `.github/workflows/pr-labeler.yml`
- `.github/workflows/lint_pr.yml`
- `.github/workflows/hacs_validate.yml`
- `.github/workflows/hassfest_validate.yml`
- `.github/workflows/python_validate.yml`
- `.github/workflows/check-manifest-version.yml`
- `.github/pr-labeler.yml`
- `.github/release-drafter.yml`

---

### Implementation patterns

**`__init__.py`**
- Config-entry-based only — no new YAML integrations.
- `async_setup` only needed when loading legacy `notify` platform via `discovery.async_load_platform`; it must receive `hass_config` and pass it through.
- `async_setup_entry`:
  - Instantiate and store coordinator on `hass.data[DOMAIN][entry.entry_id]`
  - Call `await coordinator.async_config_entry_first_refresh()`
  - Call `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`
  - Raise `ConfigEntryNotReady` for transient failures (device offline, timeout, network error)
  - Raise `ConfigEntryAuthFailed` for invalid/expired credentials
- `async_unload_entry`: call `async_unload_platforms`, clean up `hass.data`
- `PLATFORMS` list excludes `notify` (loaded via discovery separately)

**Notify platform (legacy pattern)**
```python
hass.async_create_task(
    discovery.async_load_platform(
        hass, Platform.NOTIFY, DOMAIN,
        {CONF_DEVICE_ID: device_id}, hass_config,
    )
)
```

**`config_flow.py`**
- Extend `ConfigFlow` with `domain = DOMAIN`
- Include `OptionsFlowHandler` when the integration has configurable options
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
- Extend `CoordinatorEntity`
- Provide `device_info` — groups entities under a device in the UI
- Set `unique_id` on all entities
- Read state from `self.coordinator.data` only — never do I/O in properties

**`DataUpdateCoordinator` (polling)**
- `update_interval` minimum 5 s
- Raise `ConfigEntryAuthFailed` on auth errors inside `_async_update_data`
- Raise `UpdateFailed` on other errors

---

### Quality scale — target Platinum

Generate `quality_scale.yaml` with each rule set to `todo` or `done` as appropriate. Platinum adds on top of Gold:
- Full type annotations throughout
- Fully async codebase (no blocking I/O)
- Efficient data handling (no unnecessary polling or state writes)
- All HA coding and integration standards met

---

### Code style

- Module docstring on every file
- Short single-line docstrings on all public functions and classes
- No inline comments unless the WHY is genuinely non-obvious
- No trailing summaries after edits
- ruff + pylint compliant; pyright standard mode

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
4. Check `manifest.json` has correct `documentation` URL pointing to the repo
5. Report: files changed · issues fixed · issues intentionally suppressed (with rationale) · remaining manual work
