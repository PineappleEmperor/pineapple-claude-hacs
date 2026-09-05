# Testing an integration

Three prerequisites decide whether the suite runs at all, then one rule about what to mock.
The code patterns being tested are `reference/patterns.md`.

- Testing — prerequisites before any of the rules below apply
- Don't reuse a domain that exists in HA core
- Testing — mock at the boundary, not your own code
- Mock only at the external boundary
- The real failure that motivated this rule
- `test-before-setup` means a real config-entry setup
- If the integration allows multiple devices, test two entries set up in parallel
- Unit-test the pure logic directly
- Minimum coverage before claiming a tier
- Prefer future-dated fixtures over freezing the clock
- Push coordinator data to entities without scheduling timers
- Standalone helper scripts

## Testing — prerequisites before any of the rules below apply

`pytest-homeassistant-custom-component` does not work out of the box. Three requirements, each of which fails the *whole* suite rather than one test. The first two were verified by ablation — removing either stops a real setup-entry test passing — and the third by the import error it produces. Re-derive against the pinned harness version in `reference/freshness.md` if these stop matching what you see.

**1. A `conftest.py` at the repo root** — not in `tests/`. Copy `templates/conftest.py`. It does two jobs:

- **Claims the name `custom_components` for this repo.** p-h-c-c bundles its *own* `custom_components` package under `testing_config/` and binds the bare name to it as its plugin loads. HA discovers custom integrations with a plain `import custom_components` (`homeassistant.loader._get_custom_components`), so whichever binding won decides whether HA can see your integration. A root conftest is imported before the plugin, so `import custom_components` there claims the name first. **Without it every setup test fails with `Setup failed for '<domain>': Integration not found`** — which reads as a broken test, not missing wiring, and sends you debugging the integration instead of the harness. A `custom_components/__init__.py` does *not* fix this (tested); neither does `pythonpath`.
- **Pulls in `enable_custom_integrations`** autouse (required >= 2021.6.0b0). Fixtures that must initialise *before* it — `recorder_mock` is the known one — have to be requested ahead of it in the same signature.

**2. `asyncio_mode = "auto"`** in `pyproject.toml`, or pytest-asyncio never runs the async tests (they error at collection).

**3. A `config_flow.py` that imports**, whenever `manifest.json` sets `"config_flow": true`.
HA imports the flow module *during entry setup*, not only when a user opens the flow, so a manifest claiming a config flow without the module fails the setup test with `Error importing platform config_flow from integration <domain>` — which reads as a test problem and is a wiring problem. Found by running the setup test against an integration whose `__init__.py` had no `async_setup_entry` at all.

The shipped `templates/pyproject.toml` carries that table alongside the ruff rules; copy
the file rather than the block.

No `pythonpath` entry is needed: a root conftest already puts the repo root on `sys.path`, so `pytest` works from any directory (verified with `pytest`, `python -m pytest`, and from inside `tests/`).

The pinned `pytest-homeassistant-custom-component` in `requirements.test.txt` hard-pins `homeassistant==<matching release>`, so **that pin decides which HA the suite runs against** — a mismatch fails at import, not at test time. Keep it in lockstep with the `python_validate.yml` `python-version` (a scalar — the template ships no matrix).

### Don't reuse a domain that exists in HA core

A custom `demo`, `sun`, `light`… is shadowed by the built-in, and the failure surfaces as core's dependencies failing to import (`No module named 'hassil'` for `demo`), which looks nothing like a naming clash. Check `homeassistant/components/` before fixing the domain — it can't change later.

## Testing — mock at the boundary, not your own code

The most dangerous test is the one that passes while the integration is broken. It happens when a test **patches the integration's own functions** instead of the external dependency.

### Mock only at the external boundary

Mock the third-party client, socket, or library (`imaplib.IMAP4_SSL`, `aiohttp` via `aioclient_mock`, the vendored device lib, `serial`) and nothing inside the integration. Then the integration's *own* wiring runs: reading `entry.data`/`entry.options` into attributes, building requests, parsing responses, populating the coordinator. **Never patch your own `_async_update_data`, `email_triage`, `api.fetch`, etc.** — doing so stubs out exactly the code a refactor is most likely to break, so the test stays green through the regression.

### The real failure that motivated this rule

A `runtime-data` refactor dropped the `entry.data → self.host/credential` reads from the coordinator's `__init__`. Every coordinator test passed because they patched the data-fetch function, so the missing attributes were never read. Setup then crashed at runtime with `AttributeError: object has no attribute 'host'`. A test that mocks the *transport* and runs the real fetch (or even just constructs the coordinator and asserts it read the config) fails loudly. The fix-forward is also the `api.py` split: pass config as explicit constructor args so pyright catches a missing field, instead of a helper reaching into `self.<attr>` set elsewhere (an untyped runtime contract that survives refactors silently).

### `test-before-setup` means a real config-entry setup

Add a `MockConfigEntry`, call `hass.config_entries.async_setup(entry.entry_id)`, and assert `entry.state is ConfigEntryState.LOADED` plus that entities exist — with only the transport mocked. This exercises `async_setup_entry` end to end (credential reads, `async_config_entry_first_refresh`, `runtime_data`, platform forward, entity creation). A `async_setup_component(hass, DOMAIN, {})` test only proves the (unused) YAML path returns `True` and is near-worthless for a config-entry integration. **If you scaffold an `init_integration` fixture, actually use it** — an unused setup fixture is a tell that the highest-value test was skipped.

### If the integration allows multiple devices, test two entries set up in parallel

A single-entry `LOADED` test can't catch integration-global registration done per-entry (static paths, websocket commands, the panel) — the clash only fires on the *second* concurrent entry. Add a test that `add_to_hass`es two `MockConfigEntry`s and `await asyncio.gather(hass.config_entries.async_setup(e1.entry_id), …(e2.entry_id))`, then asserts **both** `state is ConfigEntryState.LOADED`. On the buggy per-entry code the second entry goes `SETUP_ERROR` with aiohttp `RuntimeError: Added route ... already registered`; it passes once the registration moves to `async_setup`. Unload both entries at the end, and if a fixture starts a self-rescheduling timer (e.g. `mqtt_mock`'s periodic loop) override the `expected_lingering_timers` fixture to `True` **in that module only** so it tolerates the fixture's own timer without masking leaks elsewhere.

### Unit-test the pure logic directly

Regex parsers, date/format extraction and data transforms (`order_parse`, `voucher_parse`, `sort_orders`, …) take a string or object and return a value, with no HA and no mocks. They carry the highest regression risk and are the cheapest to cover; a parser with zero tests is a standing liability.

### Minimum coverage before claiming a tier

Cover all of: config-flow (happy path + each error + reauth/reconfigure), a real setup-entry `LOADED` test (plus a **two-entry parallel `LOADED`** test if multiple devices are allowed), coordinator success + auth-failure + the credential-read path against a mocked transport, unload, and a unit test per parser. Wire the regression test *first* on any bug fix: confirm it fails on the unpatched code, then fix. Which rules demand a behavioural test before you may mark them `done`, and what each test must prove, is `reference/quality-scale.md`.

### Prefer future-dated fixtures over freezing the clock

For an end-to-end test that feeds a real captured payload (e.g. an `.eml`) through the mocked transport and asserts a sensor populates: if the payload has dates that must be "upcoming" for the integration to surface them, **shift the fixture's dates forward at runtime** (parse + rewrite, or template) rather than `freeze_time(...)`. Freezing the clock breaks anything that depends on the loop's time — most painfully it stops the **debouncer** that an `update_before_add` refresh relies on, so the entity never populates (state stays `unknown`), *and* it leaves a timer scheduled at the frozen wall-clock time that fails teardown. A live clock with future-dated data sidesteps both and keeps the fixture's real bytes/encoding.

### Push coordinator data to entities without scheduling timers

In a setup test, after `async_setup` + `async_block_till_done`, the entities may still read defaults (the on-add refresh is debounced and won't fire within `block_till_done`). Call `coordinator.async_update_listeners()` to notify entities from the **already-loaded** `coordinator.data` synchronously — unlike `async_refresh()` it schedules no new timer, so teardown stays clean. (The real fix for production is the `async_added_to_hass` initial-state population above; the test then needs no nudge at all.)

### Standalone helper scripts

The shipped `pyproject.toml` already exempts `scripts/*` from `T201` (print) and `INP001` (implicit namespace package), and `tests/**` from `INP001`, `PTH` and `SLF001` — tests legitimately reach into private members, and HA core ignores that rule under its own `tests/` too. Nothing needs adding for the copied tooling; it passes `ruff check` and `ruff format --check` as shipped. And `result["type"]`/`["errors"]`/`["reason"]` on a flow `ConfigFlowResult` are `reportTypedDictNotRequiredAccess` under pyright — use `result.get("type")` etc. in tests.

---
