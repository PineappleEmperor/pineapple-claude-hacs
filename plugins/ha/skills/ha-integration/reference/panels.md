# Integrations that serve a custom panel

Traps specific to shipping a Lit/TS panel from an integration. For how the panel should look, use the `ha-panel-design` skill.

- Register the static path and the panel in `async_setup`
- The bundle must be committed
- `home-assistant-frontend` must be pinned in `requirements.test.txt`
- Registration has two traps
- Testability is a design property, not a tooling one

Five things are non-obvious here, and each fails silently.

### Register the static path and the panel in `async_setup`
Once per process — per-entry registration races when two entries set up in parallel, so claim the `hass.data` flag before the `await`.

  ```python
  from pathlib import Path

  from homeassistant.components.http import StaticPathConfig


  async def async_setup(hass, config):  # once per process — no entry parallelism
      """Serve the panel bundle; registration itself is option-gated below."""
      await hass.http.async_register_static_paths(
          [
              StaticPathConfig(
                  "/{domain}_panel/editor.js",
                  str(Path(__file__).parent / "panel" / "editor.js"),
                  False,
              )
          ]
      )
      return True


  async def _refresh_panel(hass):  # from async_setup_entry — option-gated, toggleable
      if _panel_wanted(hass) and not hass.data.get(f"{DOMAIN}_panel"):
          hass.data[f"{DOMAIN}_panel"] = True  # claim BEFORE the await: setups race
          await panel_custom.async_register_panel(
              hass,
              frontend_url_path="{domain}",
              webcomponent_name="{domain}-panel",
              module_url="/{domain}_panel/editor.js",
              sidebar_title="...",
              sidebar_icon="mdi:view-grid",
              require_admin=True,
          )


  # last unload: frontend.async_remove_panel(hass, "{domain}")
  ```

### The bundle must be committed

HACS ships the repo as-is and runs no build step on the user's machine, so the esbuild output has to live inside `custom_components/<domain>/panel/` to reach the release zip. Copy `templates/frontend/{package.json,tsconfig.json}` and `templates/.github/workflows/panel_bundle.yml`. **This differs from a Lovelace *card* repo**, which attaches the built `.js` as a release asset — an integration cannot, because the asset isn't in the zip HACS installs.

**What users install is always a fresh build.** `release.yml` runs `npm run build` immediately before packing the zip, so a stale committed bundle cannot reach anyone; it warns instead. The rebuild lives in `release.yml` rather than its own workflow because two workflows on the same `release: published` event cannot be ordered, and a rebuild finishing after the zip was packed would ship the exact staleness it was meant to prevent.

A stale committed bundle is still worth avoiding — it makes the repo lie about what its source produces, and the symptom is "the fix I made isn't there" when someone reads the committed file. Run `npm run build` and commit the result.

### `home-assistant-frontend` must be pinned in `requirements.test.txt`

A panel declares `frontend` (usually `panel_custom` too) in manifest `dependencies`. The frontend *component* has its own pip requirement that `pip install homeassistant` does **not** pull in — component requirements are installed by HA at runtime. Without the pin every setup test fails in CI with `No module named 'hass_frontend'`, while typically **passing locally** because a dev machine already has the package. Worse, the failures read as `'MockConfigEntry' object has no attribute 'runtime_data'`, pointing at the integration rather than the missing dependency. Pin from **core's own manifest** for your HA version, not from PyPI latest:
```bash
curl -s https://raw.githubusercontent.com/home-assistant/core/<ha-version>/homeassistant/components/frontend/manifest.json
```
Gate-enforced: a manifest depending on `frontend`/`panel_custom` with no pin fails the audit.

### Registration has two traps
Cache-bust the module URL or a browser serves the previous panel after an update, and claim the registered flag **before** the `await` or two entries setting up in parallel both register:
```python
async def _register_panel(hass: HomeAssistant) -> None:
    if not hass.data.get(REGISTERED):
        hass.data[REGISTERED] = True  # claim BEFORE the await
        integration = await async_get_integration(hass, DOMAIN)
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=DOMAIN,
            module_url=f"{PANEL_MODULE_URL}?v={integration.version}",  # else cached
        )
```

### Testability is a design property, not a tooling one

A panel transforms vendor data
before drawing it, and that logic is reachable from nothing else in the stack: `tsc --noEmit`
proves a helper returns a string, not that it returns the right one; the Python suite cannot
see it; and the bundle-staleness check proves the JS matches its source, not that the source
is correct. So **export the pure presentation helpers** rather than inlining them in
`render()` — a panel that inlines everything has nothing to import, and no test runner fixes
that.

```ts
// panel.ts — exported, so a test can reach them
export function isNamed(item: Pick<Set, "name">): boolean { ... }
export function displayName(item: Pick<Set, "name">): string { ... }   // "{?}" -> "Name tbd"
```

The cases worth testing are the ones where the vendor's data is not what you would draw:
a placeholder standing in for an unannounced name, a missing price, a date that has already
passed, a sort comparator, a unit formatter. `templates/frontend/package.json` ships
`vitest` and a `test` script for this; it needs no config file, since vitest's default
include pattern already picks up `frontend/test/*.test.ts`. The runner never reaches users:
`release.yml` zips `custom_components/<domain>/` only, so `frontend/` is CI-time weight and
nothing more.

The same reasoning applies to anything the panel sends. A service call built in TypeScript
against a schema declared in Python has no shared definition and no compiler to link them —
`callService` takes `Record<string, unknown>`, so omitting a `vol.Required` field type-checks
cleanly and fails only at runtime, in the browser, where nobody is watching. A test that
captures the outgoing call and asserts its shape is the only thing that catches it.

> **Panel *styling* — sizing, type, colour, spacing — is the `ha-panel-design` skill, not this one.** This section covers only how the TypeScript reaches the user and how the integration registers it.
