# Dependabot for a HA custom integration

What Dependabot can bump, what it cannot reach, and why its PRs need no special handling.
Set up alongside `reference/github-setup.md`.

- Ecosystems worth enabling
- Keeping `>=` floors current, which Dependabot cannot do
- Dependabot needs no exemption
- Pins in your repo versus pins in the templates

### Ecosystems worth enabling

`.github/dependabot.yml` with `commit-message.prefix: "chore"` on each ecosystem (so titles read `chore: bump …` → the autolabeler maps `chore` → patch). Know what it actually buys you:

- **`github-actions`** — the real value. Bumps `actions/checkout`, `setup-python`, action pins across all workflows.
- **`pip`** — points at `requirements.test.txt` / `pyproject`. Real value now that the template ships `requirements.test.txt` **pinned** (`pytest-homeassistant-custom-component==…`); it stays near-useless in a repo that leaves test deps unpinned, since no version specifier means nothing to bump. ⚠️ A bump here effectively bumps the **HA version the suite tests against** — `pytest-homeassistant-custom-component` hard-pins `homeassistant==<matching release>` — so review these PRs rather than auto-merging: a bump can drag the Python floor with it, and the `python_validate.yml` `python-version`, ruff `target-version` and `pyrightconfig.json` must move in lockstep.
- **`manifest.json` `requirements` are invisible to Dependabot** — it can't parse the manifest, and the entries are open `>=` ranges (HA installs the latest matching anyway), so there's nothing to *routinely* bump. Raising a `>=` floor is a deliberate safety/feature act, not automation — **unless** you want the floors kept current.

### Keeping `>=` floors current, which Dependabot cannot do

Build a small `scripts/update_manifest_floors.py` — parse the manifest requirements, query
PyPI `…/pypi/{name}/json` for the latest non-prerelease, raise the floor if newer, with
`--check` to dry-run — plus a scheduled `update_manifest_floors.yml` (`schedule:` +
`workflow_dispatch`) that runs it and, on a change, commits to a branch, pushes and opens its
own PR. Guard with `gh pr list --head <branch> --state open` so a re-run updates rather than
duplicates, and give it a `chore:` title so the autolabeler files it. It is a second PR opener,
so it needs the `# skill-audit: sanctioned-opener` marker or the audit rejects it — the opener
policy and that marker are `reference/github-actions.md`. The floor-bump PR carries no version
bump.

---

### Dependabot needs no exemption

It used to. A `version-gate` job compared the PR's committed `manifest.json` version against
the last release, and a Dependabot PR — which never touches the manifest — tripped the
"unchanged version" rule right after a release. The exemption existed to skip that job.

**That job is gone.** The release tag owns the version, so nothing compares a committed one,
and the only PR-time gate is the label check — which already skips bots via
`github.event.pull_request.user.type != 'Bot'`. Dependabot PRs carry a `chore` label from
their `chore:` title, fold into the next release, and need no special case anywhere.

If you are looking at an older repo that still has `version-gate`, the exemption to keep is a
**job-level** `if:` — `github.event.pull_request.user.login != 'dependabot[bot]'` — which skips
the job rather than passing it falsely.

---

### Pins in your repo versus pins in the templates

Dependabot's `github-actions` ecosystem only scans `.github/workflows` at the repo root. Your
workflows are therefore bumped for you once `dependabot.yml` is in place; the skill's
`templates/` are maintained separately, in the skill's own repo. **Consequence for you:**
re-copying from `templates/` can move a pin *backwards* if the skill's copies are older than
what Dependabot has already given you. Diff before overwriting, and keep the newer pin — a
listed adaptation in `reference/github-actions.md`.
