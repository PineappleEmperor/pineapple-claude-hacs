# Quality scale — target Platinum

The canonical rule set and what each tier demands.

- The tiers and what each demands
- Scaffold `quality_scale.yaml` from the start
- Gate-enforced, on the claim rather than on the tests
- Prove the rule, don't just claim it — hassfest checks structure, not behaviour

## The tiers and what each demands

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
  config-flow: done
  test-coverage: done
  diagnostics:
    status: exempt
    comment: Device exposes no sensitive runtime data worth redacting.
```
Valid statuses: `done`, `todo`, `exempt` (exempt requires a `comment`).

### Scaffold `quality_scale.yaml` from the start

Write it before the code, including when you are modifying an existing integration that lacks one, and treat it as the definition-of-done — don't discover rules by hitting them. **hassfest gotchas:** the file must list **every** canonical rule with a valid status, `exempt` **must** carry a `comment`, and **only add `"quality_scale": "<tier>"` to `manifest.json` once every rule up to that tier is `done`/`exempt`** — claiming a tier makes hassfest enforce it (a single `todo` at/below that tier fails CI). So: ship the yaml as a tracking ledger first, omit the manifest tier until a tier is fully met.

### Gate-enforced, on the claim rather than on the tests

`skill_audit.py` stays silent when nothing is marked `done` — a fresh scaffold claims nothing, so it has nothing to prove — and **fails** when any rule is `done` with no `tests/`, or when `test-coverage` is `done` while a `frontend/` panel has no tests of its own. `exempt` with a comment is always the honest alternative; `todo` is fine indefinitely.

### Prove the rule, don't just claim it — hassfest checks structure, not behaviour

⚠️ A green hassfest + a `done` in `quality_scale.yaml` only proves the file is well-formed and the manifest tier is a valid enum; hassfest **never runs the integration**, so it cannot tell you `diagnostics.py` actually redacts, the reconfigure flow works, `async_remove_config_entry_device` returns correctly, or that a `translation_key` used in code resolves in `strings.json`. (For HA core those rules are enforced by human reviewers; for a custom integration nothing enforces them.) So **every rule you mark `done` must have a test that exercises it** — marking `done` off code-presence alone is "claiming compliance" without showing it. Concretely, each of these needs its own test, not just the code: `reconfiguration-flow` (a reconfigure-success + reconfigure-error flow test), `diagnostics` (asserts the payload shape **and** that secrets are `**REDACTED**`), `stale-devices` (`async_remove_config_entry_device` → `False` while the device is live, `True` once it's gone), `exception-translations`/`entity-translations`/`icon-translations` (a test that scrapes the `translation_key`s used in code and asserts each exists in `strings.json` — catches a typo'd key that hassfest passes). If a rule is genuinely untestable, it should be `exempt` with a comment, not an unproven `done`.

**Canonical rule set — a snapshot; rules change. Re-verify per its row in `reference/freshness.md`.** All must appear in `quality_scale.yaml`:
- **Bronze:** `action-setup`, `appropriate-polling`, `brands`, `common-modules`, `config-flow-test-coverage`, `config-flow`, `dependency-transparency`, `docs-actions`, `docs-high-level-description`, `docs-installation-instructions`, `docs-removal-instructions`, `entity-event-setup`, `entity-unique-id`, `has-entity-name`, `runtime-data`, `test-before-configure`, `test-before-setup`, `unique-config-entry`
- **Silver:** `config-entry-unloading`, `log-when-unavailable`, `entity-unavailable`, `action-exceptions`, `reauthentication-flow`, `parallel-updates`, `test-coverage`, `integration-owner`, `docs-installation-parameters`, `docs-configuration-parameters`
- **Gold:** `entity-translations`, `entity-device-class`, `devices`, `entity-category`, `entity-disabled-by-default`, `discovery`, `stale-devices`, `diagnostics`, `exception-translations`, `icon-translations`, `reconfiguration-flow`, `dynamic-devices`, `discovery-update-info`, `repair-issues`, `docs-use-cases`, `docs-supported-devices`, `docs-supported-functions`, `docs-data-update`, `docs-known-limitations`, `docs-troubleshooting`, `docs-examples`
- **Platinum:** `async-dependency`, `inject-websession`, `strict-typing`

Common `exempt`s for a local-push MQTT device integration: `appropriate-polling` (push, no polling), `reauthentication-flow` (no integration-level auth), `inject-websession` (no cloud HTTP), `async-dependency` (only sync libs run in executor), `dynamic-devices` (one device per entry).

---
