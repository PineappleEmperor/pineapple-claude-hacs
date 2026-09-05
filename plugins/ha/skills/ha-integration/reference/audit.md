# Audit — the judgement checklist

The audit items a grep cannot decide. `scripts/skill_audit.py --list` covers the mechanical ones.

## Judgement checklist (read the code — a grep can't decide these)

- **Templates copied, not paraphrased.** Compare `.github/`, `scripts/` and `tests/` against this skill's `templates/` (locate it per *Where `templates/` lives* in `reference/github-actions.md`). Every difference must appear in the sanctioned-adaptations table there. Files that merely *look* equivalent are not equivalent — in a consuming repo `skill_audit.py` checks each canonical workflow **exists**, never that it **matches**, so fifteen hand-written files once passed it clean. Compare **per file**, never per directory:
  ```bash
  T=<skill>/templates   # from the skill's announced base directory
  cd <repo root>
  ( cd "$T" && find .github scripts tests frontend -type f; \
    echo ./conftest.py; echo ./requirements.test.txt; echo ./ruleset.json ) | while read -r f; do
      [ -e "$T/$f" ] || continue
      cmp -s "$T/$f" "$f" || echo "DIFFERS: $f"
  done
  ```
  Then `diff -u` each file the loop names. Only what the sanctioned-adaptations table in `reference/github-actions.md` permits may differ; any other hunk is a finding — report it with the file and hunk, and restore from the template unless the diff is a listed adaptation. The loop is one-directional: it will not show you a file the repo has and the template does not, so scan `.github/` and `scripts/` for extras by eye. If `templates/` can't be located, report the audit item as **not checked**; do not mark it passed.
- **Workflows behave, not just exist.** Check each shipped workflow against the contract it must meet — `reference/github-actions.md` states them, one per workflow.
- **Patterns applied** — judged against `reference/patterns.md`: `runtime_data` (not `hass.data[DOMAIN][entry_id]`) for entry state; coordinator `async_shutdown()` on unload; `async_remove_config_entry_device` present if the integration creates a device; `DeviceInfo` TypedDict; `_attr_has_entity_name = True`; typed `ConfigEntry` alias; modern `NotifyEntity` (or a directly-registered service for custom `data`).
- **`quality_scale.yaml` honest** — the rule list and tier requirements are `reference/quality-scale.md`: every canonical rule listed; every `exempt` carries a real `comment`; no optimistic `exempt` masking a gap (e.g. `stale-devices` exempt while a device *is* created); the `manifest.json` tier claimed only when every rule at/below it is `done`/`exempt`.
- **Tests mock the boundary** — the rules are `reference/testing.md`: a real setup-entry `LOADED` test exists (not just `async_setup_component`); the transport is mocked, not the integration's own functions; a two-entry parallel `LOADED` test exists if multiple devices are allowed; parsers have unit tests.
- **Commit/PR discipline:** subjects and titles follow `reference/commits.md`, which names the types a title may carry. The version model is `reference/versioning.md` — check the repo against that, not against memory.
- **Cached facts still true.** Re-derive any row in the cached-facts table (`reference/freshness.md`) captured more than ~3 months ago, using the command in its *Re-derive with* column. Report each as still-current or stale-with-the-new-value, and update every consumer listed on that row in one pass.

**A green gate is not a green suite.** `skill_audit.py` checks that the canonical files
exist and inspects the content of a few (`pr-checks.yml`'s shape, the drafter wiring,
action pins). In an integration repo it does not diff a workflow against `templates/` —
it cannot see them, which is why the per-file comparison above is a human item. (In the
skill's own repo `check_self_diff` and `check_template_pins` do compare, because the
templates are right there.) It never runs the repo's tests either. An audit has passed
while `tests/test_version_sync.py` was failing from a stale template copy, and only
`pytest` found it. Run what CI runs — `ruff`, `pyright`, `pytest`, `version_sync.py` —
before reporting an audit clean, and treat a failing test in a *copied* file as your copy
being stale rather than a skill bug to hand back.

**Report:** per-item pass/fail with `file:line` evidence · what the mechanical gate caught · remaining manual work. Fix findings before claiming the tier.
