# 03 — test prerequisites — run against the split skill

**Date:** 2026-08-23 · **Verdict:** PASS

## Result

`pytest tests/ -q` → **1 passed**, plus `ruff` and `pyright` clean. The test is the real
thing the skill demands: `MockConfigEntry`, `hass.config_entries.async_setup(...)`, assert
`ConfigEntryState.LOADED` — not the near-worthless `async_setup_component` form.

## Routing

The **Test** row added to SKILL.md's mode table after the first router KAT is what routed
this run — quoted back verbatim by the agent, including its warning that "the root
`conftest.py` and `asyncio_mode` prerequisites decide whether the suite runs at all". The
previous KAT reached the same file only by elimination, so the fix is confirmed by a
scenario that depends on it.

## The part worth keeping

Both documented prerequisites were **verified by ablation**, not assumed:

| Removed | Observed |
|---|---|
| root `conftest.py` | `Setup failed for 'acmedev': Integration not found` |
| `asyncio_mode = "auto"` | collection error, not a test failure |

Both match what `patterns.md` predicts, so the prose is accurate as well as present.

## Gap found (fixed)

A third prerequisite was undocumented: **a `config_flow.py` that imports, whenever the
manifest sets `"config_flow": true`**. HA imports the flow module *during entry setup*, so
a manifest claiming a flow without the module fails the setup test with `Error importing
platform config_flow from integration <domain>` — which reads as a broken test and is
missing wiring. Now documented in `patterns.md` alongside the other two.
