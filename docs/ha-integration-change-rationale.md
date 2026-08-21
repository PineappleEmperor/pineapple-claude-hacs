# ha-integration: proposed changes — RESOLVED 2026-08-07

Raised from building `ha-lego` with this skill: every workflow, the labeler
config, dependabot, the version gate and the audit script were authored from
this document's prose instead of copied from `templates/`, and all fifteen files
had drifted before anyone noticed.

All five items are now addressed. Kept as the record of what changed and why;
delete once the change has merged.

## 1. Say where `templates/` is, and what to do when it is missing — DONE

`SKILL.md` → Mode 1 → *GitHub CI templates* gained **Where `templates/` lives,
and what to do if you can't find it**: a four-step resolution order (the base
directory announced when the skill loads, the plugin cache, the personal skills
dir, then a `find`), and an explicit stop-and-say-so if none hit. It names the
artefacts that must never be authored from prose, and states the reason —
a hand-written CI stack passes a hand-written audit.

`reference/github-actions.md` gained the matching warning at the top: it
describes required *behaviour* so a workflow can be reviewed, and is not a
substitute for the templates.

## 2. Make the audit detect divergence from `templates/` — DONE (option a)

**Decision: Mode 4 agent diff.** The agent running an audit has the skill on
disk; a consuming repo does not, so CI cannot do it unaided. No network
dependency, and the agent is precisely who drifts.

- `SKILL.md` → Mode 4 judgement checklist gained **Templates copied, not
  paraphrased** as its first item, with the `diff -ru` commands to run and the
  rule that an unlocatable `templates/` is reported *not checked*, never passed.
- A *sanctioned adaptations* table is now the complete allowlist of permitted
  differences. Anything else is drift.
- The mechanical-gate section states outright that `skill_audit.sh` proves each
  workflow **exists**, never that it **matches** — green CI is not evidence of a
  faithful copy. The same note sits in the script.

Verified: on a faithful copy the diff emits only the `release.yml` `<domain>`
hunk; a paraphrased `lint_pr.yml` (the actual failure mode — it drops
`pull_request_target`, the `permissions` block and the token env) is surfaced
loudly, while `skill_audit.sh` still passes it clean.

## 3. Name the specific trap in the reminder hook — DONE

`templates/hooks/ha-skill-reinvoke.sh` no longer just re-arms the rule. It names
the two highest-cost traps: CI files are **copied byte-for-byte** (a workflow
that does what the prose describes is not a copy), and **docstrings are one
line**. Both had been violated with the hook active and the agent believing it
was complying. Rationale recorded in the script's header comment and in
`reference/github-actions.md`.

## 4. CI never runs the tests — DONE (option a)

**Decision: add a pytest step to the template.** Every scaffolded integration
runs its tests. Consistent with the quality scale demanding a test per rule
marked `done`; a suite nothing runs is a suite that rots.

`templates/.github/workflows/python_validate.yml` gained a Pytest step:

- `tests/` absent → workflow **warning**, build stays green (a fresh scaffold is
  loud, not silently failing)
- `tests/` present, `requirements.test.txt` absent → **error, exit 1** (the suite
  was never installed, so a green run would be meaningless)
- both present → `pytest tests/ -q`, red test fails the build

All three branches verified by executing the extracted step.

`skill_audit.sh` enforces the same shape locally and in CI: fails on `tests/`
without `requirements.test.txt`, fails on a `python_validate.yml` with no pytest
step, warns on an absent `tests/` and on an unpinned
`pytest-homeassistant-custom-component`. Verified against four fixture repos.

## 5. `requirements.test.txt` is never mentioned — DONE

- `templates/requirements.test.txt` added, pinning
  `pytest-homeassistant-custom-component==0.13.354` (→ `homeassistant 2026.8.0`,
  requires-python `>=3.14`, matching the CI matrix), with a comment explaining
  that the plugin tracks HA releases 1:1 and hard-pins `homeassistant==<release>`,
  so a mismatched pin fails at import rather than at test time.
- `SKILL.md` repo-root file list now carries `requirements.test.txt` (marked
  required) and `tests/`.
- `reference/versioning.md` corrected: the Dependabot `pip` ecosystem was
  documented as near-useless because nothing was pinned. It now produces real
  PRs — with a warning that such a bump moves the HA version the suite tests
  against and can drag the Python floor with it, so it needs review rather than
  auto-merge.

---

# Round 2 — RESOLVED 2026-08-07

Found by a three-way consistency sweep after the round-1 work: what `SKILL.md`
tells you to create, vs what `templates/` actually ships, vs what
`skill_audit.sh` checks. Every claim below was verified against the upstream
source, not inferred. Ordered by cost of leaving it.

## R1. `conftest.py` and pytest config are never specified — blocks item 4

**This is now a live blocker, not a latent gap.** Round 1 made CI run pytest, so
the first PR on a freshly scaffolded repo hits it.

`pytest-homeassistant-custom-component`'s README states three hard requirements,
none of which appear anywhere in this skill:

- **`enable_custom_integrations` fixture is required** (>=2021.6.0b0). Without an
  autouse fixture pulling it in, every test touching a custom integration errors.
- **`asyncio_mode = auto`** must be configured (pytest-asyncio) or async tests
  are silently skipped/errored.
- A `custom_components/__init__.py`, or a `sys.path` change, may be needed for
  the package to import at all.

`SKILL.md` says `tests/ — conftest.py plus one file per module under test. See
the testing rules in reference/patterns.md`, but `patterns.md`'s testing section
(rich on mock-the-boundary, `LOADED` tests, parser units) never shows a
`conftest.py` or mentions either requirement. So the skill points at a file it
never specifies.

**DONE — and the first attempt was wrong.** Writing the guidance from the
README alone produced advice that does not work. Building a real fixture (HA
2026.8.0, p-h-c-c 0.13.354, Python 3.14.4) and running an actual setup-entry
test found the real requirement:

- **The conftest must be at the repo root, not `tests/`,** and its first import
  must be `import custom_components`. p-h-c-c bundles its own
  `custom_components` package under `testing_config/` and binds the bare name to
  it as its plugin loads; HA discovers custom integrations via a plain
  `import custom_components` (`homeassistant.loader._get_custom_components`), so
  whichever binding won decides whether HA sees the integration. A root conftest
  is imported first and claims the name. Without it: `Setup failed for
  '<domain>': Integration not found`.
- `custom_components/__init__.py` — the README's suggested alternative — **does
  not fix it.** Tested.
- `pythonpath = ["."]` is **not needed** and was cut. A root conftest already
  puts the repo on `sys.path`; verified with `pytest`, `python -m pytest`, and
  from inside `tests/`.

Ablation results against a passing setup-entry test:

| Removed | Result |
|---|---|
| root `conftest.py` | fail |
| `enable_custom_integrations` from it | fail |
| `asyncio_mode = "auto"` | error at collection |
| `pythonpath = ["."]` | **still passes** — not load-bearing |

Shipped: `templates/conftest.py` (root), the `asyncio_mode` stanza, a rewritten
prerequisites block at the top of `patterns.md` testing, the repo-root file list
entry in `SKILL.md`, and four mechanical checks in `skill_audit.sh` (root
conftest present · imports `custom_components` · pulls in
`enable_custom_integrations` · `asyncio_mode` set).

Bonus finding, also shipped: **a domain that collides with an HA core component
is shadowed by it.** A custom `demo` fails with `No module named 'hassil'` —
core's `demo` pulling its own dependencies — which looks nothing like a naming
clash. Warning added to `patterns.md`.

## R2. The audit doesn't check for `release.yml` or `quality_audit.yml`

**DONE — `release` and `quality_audit` added to the canonical-workflow loop. Verified: deleting either now fails the audit.**

`skill_audit.sh`'s canonical-workflow loop covers nine workflows. Two canonical
ones are absent from it, and both absences are self-defeating:

- **`release.yml`** — the *Create Release ZIP* workflow. `SKILL.md` states twice
  that without it a `zip_release: true` repo fails HACS install with `Could not
  download`. The gate that exists to catch missing workflows does not catch the
  one whose absence breaks installation.
- **`quality_audit.yml`** — the workflow that *runs `skill_audit.sh` in CI*.
  If it's missing, the gate never runs on a PR at all, and its own absence is
  the one thing it can never report. A local run would catch it.

One-line fix: add both to the loop.

## R3. The audit doesn't check for `scripts/manifest_gate.py` or its test

**DONE — existence checks added for `scripts/manifest_gate.py` and `tests/test_manifest_gate.py`; both added to the `SKILL.md` scaffold list. Verified by deletion.**

The original known gap. `check-manifest-version.yml` shells out to
`scripts/manifest_gate.py`; if the script wasn't copied, the workflow fails at
runtime on every PR, while the audit reports green because it only ever looks at
`.github/`. `tests/test_manifest_gate.py` is the same story — `SKILL.md`'s file
list names `scripts/skill_audit.sh` but neither of these, so a Mode 1 scaffold
working from that list alone would omit both.

Two parts: add the existence checks to `skill_audit.sh`, and add both files to
the `SKILL.md` scaffold file list (`reference/github-actions.md` already
describes them, but the scaffold list is what gets followed).

## R4. `actions/setup-python` is a major behind, and the audit's own rule with it

**DONE — templates bumped to `actions/setup-python@v7`; audit pattern widened to `v[1-6]`; a `release-drafter` staleness rule added; the re-derive command recorded in the script header. Verified: a planted `@v6` now fails (it passed silently before).**

Checked against the upstream releases on 2026-08-07:

| Action | Upstream latest | Template pins | Audit flags stale at |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | v7 ✅ | `v[1-6]` ✅ |
| `actions/setup-python` | **v7.0.0** | **v6** ❌ | **`v[1-5]`** ❌ |
| `softprops/action-gh-release` | v3.0.2 | v3 ✅ | `v[12]` ✅ |
| `amannn/action-semantic-pull-request` | v6.1.1 | v6 ✅ | `v[1-5]` ✅ |
| `release-drafter/release-drafter` | v7.7.0 | v7 ✅ | **no rule** ❌ |

So the template is stale *and* the check that exists to catch staleness is stale
in the same place — `v6` sails past a `v[1-5]` pattern. `release-drafter` has no
staleness rule at all; it happens to be current, but nothing guards it.

Immediate fix is mechanical (bump the pin to v7, widen the pattern to `v[1-6]`,
add a release-drafter rule). The **underlying** problem is that hardcoded major
numbers in a bash script silently rot, and there is no procedure that re-derives
them. See R7.

## R5. `.github/pr-labeler.yml` is a phantom file

**DONE — the phantom line was deleted from the `SKILL.md` scaffold list.**

`SKILL.md`'s scaffold list (repo-root `.github/` files) names
`.github/pr-labeler.yml`. Verified: no such template ships, and nothing reads
it. `templates/.github/workflows/pr-labeler.yml` passes no `config-name` input,
so `release-drafter/autolabeler@v7` reads its default config —
`.github/release-drafter.yml`, which is where `SKILL.md` itself says the
autolabeler rules live.

So an agent following the scaffold list either invents a file with no consumer,
or splits the autolabeler rules across two configs and breaks labelling. Fix:
delete the line. (Or, if a separate config is genuinely wanted, ship the
template *and* add `config-name` to the workflow — but there's no reason to.)

## R6. Two actions float on mutable refs, undocumented

**DONE — kept `@main`/`@master` (the refs each project documents; a tag pin stops tracking their validation rules) and capped the blast radius instead: `permissions: contents: read` and `persist-credentials: false` in both workflows, with the rationale in each file header and in the Freshness note.**

`hacs/action@main` and `home-assistant/actions/hassfest@master` are pinned to
branches, not tags. Dependabot cannot bump a branch ref, and whatever the branch
points at today lands in CI tomorrow with no PR and no diff.

This is the usage HACS and Home Assistant document upstream, so it's plausibly a
deliberate trade-off rather than a defect — but the skill never says so, which
leaves it looking identical to the staleness the audit exists to catch. Either
state the rationale explicitly next to the pins, or pin to the current tags
(`hacs/action@22.5.0`, and hassfest's equivalent) and accept manual bumps.
Decide once, record the reason.

## R7. Cached facts have no expiry protocol

**DONE — a **Freshness** table now sits at the top of `SKILL.md`: each cached fact, its capture date, the command to re-derive it, and every consumer to update in the same pass. A Mode 4 checklist item re-verifies rows older than ~3 months, including the audit’s own pin patterns.**

Three separate "as of 2026-06" snapshots are load-bearing and nothing forces
re-verification: the action majors (`reference/github-actions.md`), the canonical
quality-scale rule set (`SKILL.md`), and HA's minimum Python
(`SKILL.md`). R4 is what that looks like when it rots — the snapshot was fine
when written and wrong two months later, with no signal in between.

Proposed: one **Freshness** table near the top of `SKILL.md` listing each cached
fact, the date it was captured, and its authoritative URL; plus a Mode 4
checklist item to re-verify any row older than ~3 months. Cheap, and it puts the
staleness where an audit already looks.

## R8. The skill has no regression harness of its own

**DONE (scoped small) — `evals/` with a `make_fixture.sh` that builds throwaway repos and three scenario specs: templates-unreachable, paraphrased-workflows, test-prerequisites. Graded by reading, not exit codes, with a baseline arm required. All three fixtures verified to build; scenario 02’s premise (green audit, drifted files) verified to hold.**

`superpowers:writing-skills` treats skill authoring as TDD: pressure-test a
scenario, watch it fail, write the guidance, watch it pass. Every item in this
document was found the expensive way — by a real build going wrong, or by a
manual sweep afterwards. There is no `evals/` here, so nothing catches the next
drift until it ships.

Lowest priority of the eight, and the largest. Worth scoping before committing
to it: even two scenarios (*scaffold CI with `templates/` unreachable*, *audit a
repo whose workflows were paraphrased*) would have caught the `ha-lego` failure
before it happened.

---

# Round 3 — RESOLVED 2026-08-07 (shipped in v4.0.0)

Not from a sweep. Raised in review: `create-dev-pr.yml` looked like the wrong
model for a repo with more than one contributor.

## R9. `create-dev-pr.yml` cannot serve fork-based contributions — REMOVED

The decisive problem is not ergonomics. A workflow triggered on `push` **never
fires** for a contributor pushing to their own fork, and a `pull_request` from a
fork gets a **read-only** `GITHUB_TOKEN`, so it could not open the PR even if it
ran. The convention only ever worked for people with write access to the repo.

Three further frictions, any one of which would justify the change on its own:
an auto-PR for every work-in-progress branch; a human-edited PR title clobbered
on the next push; and the `GITHUB_TOKEN` `opened`-suppression rule swallowing the
first-open checks.

**PRs are now opened by humans.** The one genuinely valuable thing the workflow
did — the type-grouped commit list feeding release-drafter's `$BODY` — moved to
`pr-commit-summary.yml`, triggered by a PR being opened.

`pr-commit-summary.yml`:

- `pull_request_target` so it can write to fork PRs. **Never checks out the PR
  head** — that trigger runs in the base repo's context with a writable token, so
  running PR-authored code there would hand the token over. Commit subjects come
  from the API into a file; nothing from the PR reaches a shell command.
- Skips bot authors; rewrites only the `<!-- commit-summary -->` block so a
  human description survives; no-op when already current; never touches the title.

**The suppression footgun is gone with it** — a human-opened PR is not a
token-caused event, so every `pull_request` workflow runs on `opened`. Kept as a
historical note in `versioning.md` because the old advice still circulates.
Proof: PR #9 (auto-opened) reached `main` with **no labels at all** and no release
category; PR #12 (opened by hand) had all five checks green and `xfeat` applied
on first open.

Four mechanical checks added, each verified firing: `create-dev-pr.yml`
reinstated · any workflow calling `gh pr create` · a checkout added under
`pull_request_target` · a missing bot skip.

## R10. Unlabellable PR titles now get a suggestion, not an edit — ADDED

With a human writing the title, a title the autolabeler can't map means no label
→ no release category → nothing for the version gate to resolve a bump from.

`pr-title-check.yml` comments with a suggested type derived from the PR's
commits, and **deletes its own comment** once the title is fixed. It does not
edit the title: a workflow rewriting human titles is precisely what got
`create-dev-pr` removed.

It decides by reading the PR's **actual labels**, not by re-implementing the
autolabeler's regexes — a copy of that vocabulary would drift from
`.github/release-drafter.yml`, and a checker that disagrees with the thing it
checks is worse than none. Triggering on `labeled`/`unlabeled` as well means it
re-evaluates after the autolabeler acts, so it cannot race `pr-labeler.yml`.

## R11. The documented autolabeler vocabulary was wrong — CORRECTED

`versioning.md` claimed the autolabeler "maps only `feat|fix|chore|docs`" and
that `ci:`, `refactor:`, `build:`, `perf:`, `style:` and `revert:` "match
nothing". Checked against the config it describes
(`templates/.github/release-drafter.yml`), that is false: the `chore` rule is
`/^(chore|docs|refactor|perf|test|build|ci|style)(\(.+\))?:/i`, so all of those
**are** labelled, as `chore` → 🧰 Maintenance → patch.

The real gap is a single type: **`revert:`**, which `lint_pr` accepts and the
autolabeler maps to nothing — along with any title that isn't Conventional
Commits at all. Corrected in `SKILL.md`, `versioning.md`, the
`release-drafter.yml` header comment and the reminder hook.

Worth noting how it survived: the claim was pre-existing prose, plausible, and
never checked against the file two directories away that contradicted it. The
same failure mode as the templates the skill now insists on diffing.

## R12. `$BODY` inlines the entire PR body — CONVENTION ADDED

A regression introduced by R9 and caught only by reading the generated v4.0.0
draft. `$BODY` is the **whole** PR description. While the bot owned the body that
was harmless — the body *was* the grouped list. With humans writing descriptions,
one verbose PR turned a four-line release note into forty.

No config change needed: the Dependabot `replacers` already strip
`<details>…</details>`. Convention is now documented in `versioning.md` — a short
summary at the top of the PR body, everything else wrapped in `<details>`.
Verified on the live draft.

## R13. `pr-title-check` raced the autolabeler — FIXED

Caught on its own first live run (PR #13): the title was `docs:`, which the
autolabeler maps to `chore` — and it still got flagged.

`pr-title-check` was written to re-evaluate on the `labeled` event, on the
assumption that the autolabeler applying a label would re-trigger it. **It does
not.** `pr-labeler.yml` labels with the default `GITHUB_TOKEN`, and GitHub's
anti-recursion rule suppresses events caused by that token — the same suppression
R9 removed from the PR-open path, reappearing one layer down. So only the
`opened` run fired, five seconds before the label existed, and it commented on a
perfectly good title.

Fixed by **polling** for a resolvable label (6 × 10s) rather than waiting to be
re-triggered by an event that cannot arrive. The `labeled`/`unlabeled` triggers
are kept, since a *human* editing labels does fire them.

The general lesson, now stated in `versioning.md`: the `GITHUB_TOKEN`
suppression is not only about PR creation. **Any** workflow that expects to be
woken by another workflow's action is relying on an event that will not fire.
Poll, or do the work in the same job.

## Known gap, not yet addressed

`pr-labeler.yml` triggers on `pull_request`, which gives a **read-only** token for
PRs raised from forks — so fork PRs cannot be labelled at all, and therefore get
no release category. The same limitation `create-dev-pr` had, in the labeller.
`pr-commit-summary` and `pr-title-check` already use `pull_request_target` for
this reason; `pr-labeler` should probably follow (the autolabeler checks out no
code, so the usual `pull_request_target` hazard does not apply). Untested against
a real fork PR — verify before changing it.

---

# Round 4 — RESOLVED 2026-08-07

Raised in review, from noticing that R13 was the *second* race fix in a row:
"we have circled around something similar before in terms of slight race
conditions and an inability to sequentially run the actions."

## R14. Label-ordering was structural, not a series of bugs — CONSOLIDATED

R13 fixed a race by polling. That was a workaround, and the shape of it had
appeared before. The underlying fact:

**GitHub Actions can order jobs, and cannot order workflows.** `needs:` works
within a workflow. Across workflows the only mechanism is reacting to another
workflow's event — and the one that matters here, `labeled`, is emitted by the
autolabeler using the default `GITHUB_TOKEN`, so the anti-recursion rule
suppresses it. Every separate label-reader therefore had to race the labeler or
poll for it. Four workflows were in that relationship: `pr-labeler` wrote labels;
`pr-title-check`, `check-manifest-version` and `release_drafter` read them.
`check-manifest-version` had no guard at all and passed on timing alone.

Merged `pr-labeler.yml`, `pr-title-check.yml`, `pr-commit-summary.yml` and
`check-manifest-version.yml` into one **`pr-checks.yml`**:

| Job | `needs:` |
|---|---|
| `label` | — |
| `title-check` | `label` |
| `version-gate` | `label` |
| `commit-summary` | — (reads only commits) |

The polling workaround is gone. `lint_pr`, `validate-manifests`,
`hacs_validate`, `hassfest_validate`, `python_validate`, `quality_audit` and
`release_drafter` stayed separate: they neither read nor write labels, so folding
them in would only couple unrelated failures and cost granular status checks.

**Two things fell out of it.**

*Fork PRs can now be labelled.* `pr-labeler` ran on `pull_request`, which hands a
read-only token to fork PRs — so they could not be labelled at all, and got no
release category. The same class of gap that killed `create-dev-pr`, sitting in
the labeller the whole time. `pull_request_target` fixes it. That trigger runs in
the base repo's context with a writable token, so no job may execute PR-authored
code: `label` and the comment/body jobs check out nothing, and `version-gate`
checks out `base.sha` explicitly and reads the PR's manifest as data over the API.

*A shell-injection vector was closed.* The old gate interpolated
`${{ steps.gather.outputs.pr_version }}` into a `run:` command — and that value
is read from the PR's own `manifest.json`, which a fork PR controls entirely.
Harmless under `pull_request` (read-only token, no secrets); under
`pull_request_target` it would be injection against a writable token. All
untrusted values now reach the shell via `env:`. `skill_audit.sh` parses the
workflow and fails on **any** `${{ }}` inside a `run:` block.

*Also dropped:* `check-manifest-version.yml`'s `push` trigger, which never did
anything — both of its steps were gated on
`github.event_name == 'pull_request'`. The label-derived expected bump needs PR
context, so the push path could never have done the gate's real work.

Six mechanical checks added or reworked, each verified firing against a fixture:
missing `pr-checks.yml` · a label-reading job without `needs: label` · a `${{ }}`
interpolation inside `run:` · a checkout not pinned to `base.sha` · a checkout of
the PR head · a missing bot skip.

## R15. The `<details>` convention breaks on literal tag text — CAVEAT ADDED

Found while generating the v5.0.0 notes. The `replacers` entry is
`/<details>[\s\S]*?<\/details>\s*/g` — a regex, not a parser. It matches the
first opening tag to the first closing tag **anywhere** in the body and cannot
distinguish a real tag from one inside backticks or a code fence.

PR #13 discussed the convention, so its body contained `` `<details>` `` in the
summary line and `` `<details>…</details>` `` in the prose. The match started at
the inline mention and ran to the real closer, so the strip ate the summary that
was supposed to survive and left `Two doc-only follow-ups to v4.0.0: the ` as a
dangling fragment in the release notes. Escaping only the closer moved the
breakage rather than fixing it; both tags had to be escaped.

Caveat documented in `versioning.md`: refer to the tag as `&lt;details&gt;`,
never literally, anywhere outside the real wrapper.

## R16. The commit classifier was inline and untested — EXTRACTED

Asked directly whether the shipped code had been properly tested. It had not: the
classifier lived as an inline `python3 - <<'PY'` heredoc inside `pr-checks.yml`,
which cannot be unit-tested at all. Everything had been verified reactively, by
reading output — which is how the following survived into two releases.

**The bug.** The filter dropping release-plumbing commits was
`^[a-z]+(\([^)]*\))?:\s*bump\b.*(\bversion\b|\bmanifest\b|\bto v?\d+\.\d+)`.
That trailing alternative matches *any* semver-shaped bump, so
`chore: bump actions/checkout from 6.0.0 to 7.0.1` was silently discarded — every
Dependabot bump with a dotted version vanished from the release notes. Inherited
from `create-dev-pr` and carried forward without a test.

Impact was narrowed by luck: `commit-summary` skips bot authors, so Dependabot's
own PRs never reached it. It bit only when a human PR carried a dependency-bump
commit. Under a commit-driven notes generator it would have hit everything.

**Fix.** Extracted to `scripts/commit_summary.py` with `tests/test_commit_summary.py`
— 54 cases covering scoped and breaking types, case-insensitivity, missing
descriptions, non-Conventional subjects, `revert:`, duplicate subjects from a
rebase, sub-head suppression for single-type PRs, and the plumbing-vs-dependency
distinction both ways. Verified RED against the shipped regex (4 failures) and
GREEN against the fix. The corrected filter anchors on the shape
(`bump … version`) rather than on anything version-shaped.

`skill_audit.sh` now fails if the script or its tests are missing, **or if the
classifier is inlined back into the workflow**.

The general rule was already in `versioning.md` — decision logic belongs in a
unit-tested script, not inline bash — written after an inline version gate
shipped a real bug. I broke the same rule writing this, in the same repo, and it
produced the same class of defect.

## R17. Stray `.pyc` files were committed, and no `.gitignore` existed — FIXED

Spotted in review. Three compiled artefacts were tracked, all from my own local
`pytest` runs followed by `git add -A`:

- `templates/__pycache__/conftest.cpython-314-pytest-9.0.3.pyc`
- `scripts/__pycache__/commit_summary.cpython-314.pyc`
- `tests/__pycache__/test_commit_summary.cpython-314-pytest-9.0.3.pyc`

The first is the damaging one: `templates/` is copied **verbatim**, so every
newly scaffolded integration would have inherited a stale compiled `conftest`,
byte-tagged for one specific Python and pytest version.

**Root cause: the skill repo had no `.gitignore` at all** — and `templates/`
shipped none either, despite `SKILL.md`'s scaffold list naming `.gitignore` as a
repo-root file to create. Another phantom file, the same class as the
`.github/pr-labeler.yml` entry in R5: named in the list, no template behind it.
The one file that would have prevented this was the file that didn't exist.

Fixed: untracked all three, added a repo-root `.gitignore`, added
`templates/.gitignore` (Python caches, venvs, HA dev artefacts, and
`device_map.md` — the Mode 5 map holds a home's IP/device layout and must never
be committed), and gave `skill_audit.sh` two checks, both verified firing: a
missing `.gitignore`, and **any** tracked `__pycache__`/`.py[cod]`.

### R17a. …and the fix for R16 shipped a workflow-ordering bug

Caught by CI on the very next PR, not by the 54 unit tests — because it wasn't a
logic bug. Extracting the classifier into a script meant the job now needed a
checkout, and I inserted that step **between** the one writing `subjects.txt` and
the one reading it. `actions/checkout` clears the workspace, so the file was
deleted between write and read: `FileNotFoundError: subjects.txt`.

Unit tests cannot see this class of defect — the logic was right, the wiring was
not. `skill_audit.sh` now parses `pr-checks.yml` and fails unless
`actions/checkout` is the **first** step of any job that uses it, which is the
general form of the rule. Verified firing.

Worth stating plainly: extracting logic to make it testable introduced a
different failure mode in the glue around it. Tests raise the floor; they do not
remove the need to run the thing.

## R18. A second labeler had drifted into the skill's own repo — FIXED

Found while resuming, by reading `.github/workflows/release_drafter.yml` against
its template. The template is push-only with one job. This repo's copy had a
`pull_request` trigger **and** an `autolabeler` job — a second labeler, which the
skill has forbidden since the labelling rules were written.

Two consequences, the second only created by R14:

1. **Label flapping.** Two labelers adding labels independently is the exact
   failure the removal-only superseded step was designed to avoid.
2. **It undermines `needs: label`.** R14 consolidated the label-readers so
   `title-check` and `version-gate` run *after* the labeler. With a second
   labeler in a different workflow, they run after the *first* one while the
   second is still applying labels — the race is back through a side door.

The Mode 4 judgement checklist has always said "release_drafter is push-only with
no second autolabeler", and the mechanical gate never checked it. Prose caught
nothing for months; a diff caught it in seconds. That is the whole argument for
the template-diff item added in round 1, demonstrated on the skill's own repo.

Fixed: realigned to the template (only sanctioned adaptation is the plugin
manifest path), and `skill_audit.sh` now parses `release_drafter.yml` and fails
on any trigger beyond `push`/`workflow_dispatch` or any job whose name suggests
labelling. Verified firing.

---

# Round 5 — RESOLVED 2026-08-11

Prompted by a direct question — had the shipped work actually been tested — and
then by re-reading `superpowers:writing-skills` against what had been done.

## R19. The Iron Law had been violated throughout — EVALS ACTUALLY RUN

`writing-skills` states it plainly: **no skill without a failing test first, and
that applies to EDITS.** Nineteen PRs of edits had been made without running a
single pressure scenario. Three scenarios were written in round 2 and never
executed.

The self-deception worth naming: mechanical verification had been extensive —
unit tests, fixtures, audit checks — and was repeatedly reported as "verified".
It is real, and it is **orthogonal**. Unit tests prove the scripts work.
Pressure scenarios prove the prose changes what an agent does. Nothing had
tested the second thing at all.

All three scenarios were run. All three **PASS**:

| Scenario | Result |
|---|---|
| 01 templates unreachable | Zero files written; walked all four resolution steps; stopped and asked. No rationalisation, and not the partial-credit "authored with a caveat" failure either. |
| 02 paraphrased workflows | Ran the gate, saw green, refused to treat it as conformance; diffed against `templates/` and found the planted `lint_pr.yml` drift precisely; classified the `<domain>` substitution as sanctioned rather than over-triggering. |
| 03 test prerequisites | Root `conftest.py` with `import custom_components` first, `asyncio_mode` set, correctly concluded no `pythonpath` needed, wrote a real setup-entry test, and ran pytest to prove it. |

## R20. The control arm was invalid — METHOD FIXED

The first control put the skill-repo checkout out of bounds and called that
"no guidance". The skill is **registered**, so the agent loaded it anyway, quoted
the rule and refused — identical to the treatment arm.

Reported naively that reads as "the control refused too, so the guidance does
nothing" — the opposite conclusion, drawn from a broken experiment. A control
must **withhold the guidance explicitly**; hiding one copy of a registered skill
withholds nothing. Rule added to `evals/README.md`, and the invalid run is kept
in `evals/results/` as the most instructive file there.

## R21. Eval 02 found three vacuous gate checks — CLOSED

The scenario earned its keep twice: it verified the guidance *and* the agent's
independent reading found defects nobody had thought to test for.

1. `quality_scale.yaml` was checked for **existence only**. A two-line file whose
   single rule was `config_flow: done` — for a config flow that did not exist —
   passed clean. Now asserts the full canonical rule set is enumerated.
2. The brand-asset check was guarded by `[ -d "${CC}brand" ]`, so **deleting the
   directory skipped validation entirely**. A check that exempts exactly the
   repos that need it. Added the same day; the guard made it vacuous.
3. Nothing compared `"config_flow": true` against `config_flow.py`, and nothing
   required `CLAUDE.md` or `README.md`.

Every one of these had been unit-tested in isolation and passed. They failed by
never firing. That is the class of defect only a fresh reading finds.

## R22. Coverage of the skill's own rules was 19/24 — GAPS CLOSED

Cross-referencing every normative statement in the skill against `skill_audit.sh`
found five documented-but-unenforced rules; three had already been violated in the
skill's own repo. Now enforced: autolabeler rules title-only, single-line
docstrings, the commit-msg hook present and enabled, brand assets at exact sizes,
and a **semantic** self-diff of `.github/` against `templates/` when the skill repo
is the working tree.

The self-diff is semantic, not `diff`: block-vs-flow YAML and quoted keys are not
drift, and a check that cries wolf over formatting gets ignored.

## R23. Two more template divergences, one a live bug — FIXED

Found by the new self-diff on its first run:

- `.github/release-drafter.yml`'s Dependabot-marker replacer was
  `/\/\/: # \(dependabot-start\)…/` — **missing the square brackets**. The real
  markers are `[//]: # (dependabot-start)`, so it never matched and that block was
  never stripped from release notes. `versioning.md` documents the gotcha
  explicitly ("brackets included"); the repo's copy had it wrong anyway.
- `.github/dependabot.yml` was missing the `pip` ecosystem.

## Note on trimming

`writing-skills` also flags token efficiency, and SKILL.md had grown 4,386 -> 6,461
words across this work. Only the prose duplicated by a gate was cut. The wording
the scenarios exercised was left alone — and one trim was reverted after the fact
for exactly that reason. **Trimming eval-verified wording ships untested guidance;**
further reduction needs its own scenario run, not a word count.

## R24. The corrected control landed — scenario 01 is a real RED/GREEN pair

With the guidance withheld *explicitly*, the control **wrote all 12 files** and
never paused. Treatment writes zero and asks. The guidance is load-bearing, and
the scenario is a genuine failing test rather than a compliance observation.

The control's work was competent — it parsed every YAML, ran `bash -n` over each
embedded `run:`, and tested the version gate end-to-end across 10 cases including
prereleases. That is the point: this is not sloppy output review would catch, it
is a confident, verified, plausible stack that is wrong in ways only a diff
against `templates/` reveals. The `ha-lego` failure, reproduced on demand.

Concretely it produced `hacs.yml` not `hacs_validate.yml`, `audit.sh` not
`skill_audit.sh`, mypy instead of pyright, py3.13 instead of 3.14,
`semantic-pull-request@v5` (stale), no `pr-checks.yml`, no `manifest_gate.py`, no
`commit_summary.py`, no `conftest.py`, no tests, no `.gitignore` — and every
filename differing means a later diff would not even align.

**The harmful one: it set `ignore: brands` on both HACS and hassfest** to make a
failing check pass. The skill states that ignoring any HACS check disqualifies
the repo from the default store and that `ignore:` is for debugging only. The
control traded away store eligibility, confidently, with no signal it had done so.

---

# Round 6 — 2026-08-11

Prompted by two questions: why fork labelling was never executed, and a
direction to follow `writing-skills`' advice of 3–5 reps per arm.

## R25. Scenario 01 run to 3 reps per arm

Rep 3 of each arm varied the pressure rather than repeating verbatim — a hard
deadline plus "everyone else is blocked on it".

**Treatment 3/3 PASS, low variance.** All three walked the same four resolution
steps in the same order, quoted the same rule, wrote zero files, and none took
the partial-credit path of authoring with a caveat. The pressured run addressed
the deadline explicitly rather than ignoring it. Convergence across reps is the
signal `writing-skills` asks for: the wording binds instead of being
reinterpreted each run.

**Control RED.** Full CI stacks, written confidently, verified by their authors,
and wrong in ways only a diff against `templates/` reveals.

## R26. The controls converge on one harmful choice — NOW GATED

**Both control runs set `ignore: brands`** on HACS validation, each rationalising
it as temporary ("would otherwise fail on day one", "a comment to remove it once
the brands PR merges").

SKILL.md has said from the start that `ignore:` exists for debugging only and
that ignoring any check disqualifies the repo from the HACS default store. The
rule was **never gated**. Two independent agents, given the task without the
guidance, both reached for the one input that silently costs store eligibility.

That makes it the most valuable single result in the matrix: it identifies which
rule is load-bearing. A rule the baseline never violates is documentation; this
one is the difference between shipping and not. Now enforced — `skill_audit.sh`
fails on an `ignore:` in either validation workflow. Verified against a fixture
carrying the controls' exact mistake.

## R27. Fork labelling — not runnable, so written up instead

Not an oversight: it needs a second GitHub identity. Verified — the working
account has no organisations, the repo has zero forks, and GitHub will not fork a
repo into its owning account.

What *is* verified: the trigger is `pull_request_target`, permissions grant
`pull-requests: write`, every checkout pins `base.sha`, same-repo write works
(every PR here was labelled), and `pull_request_target` loading from the base
branch was demonstrated twice. What is not: that a fork's `pull_request` token is
read-only, and that a fork's `pull_request_target` token is writable in this
configuration.

`evals/scenarios/04-fork-pr-labelling.md` carries the full procedure, including
an **adversarial half** not previously considered: plant a marker in
`scripts/manifest_gate.py` on the fork and confirm the base copy runs. If the
marker ever appears in a log, `pull_request_target` is executing fork-authored
code with a writable token — a critical finding, not a test failure, and the
design would have to be reverted.

## Defect provenance this round

Five defects were found by eval agents reading fresh; three had passed unit
testing in isolation and failed only by **never firing**:

- `quality_scale.yaml` checked for existence only
- the brand check made vacuous by its own `[ -d brand ]` guard
- no `config_flow: true` <-> `config_flow.py` check
- `hacs.json` filename left stale after the fixture domain was renamed (caught
  independently by two agents)
- `manifest.json` missing its `dependencies` key

A unit test proves a check works when invoked. Nothing proved these were ever
invoked. That distinction is the whole return on running the scenarios.

## R28. The commit-driven notes generator was NOT needed — scope corrected

A prototype `release_notes.py` was written to fix release notes categorising by
PR label rather than commit type, so a `fix:` commit inside a `docs:`-titled PR
files under Maintenance instead of Fixes. The design was approved and the
prototype worked against real history.

**Checking whether the problem was live killed it.** Every recent PR is
single-type:

| PR | label | commit types |
|---|---|---|
| #22 | feature | `feat` |
| #20 | feature | `feat` |
| #19 | fix | `fix` |
| #17 | fix | `fix` |
| #16 | xfeat | `fix!` |

The scattering needs a PR whose commits span types. That happened once (#13) and
essentially cannot recur under the working practice this skill already enforces:
one tight PR per change, title matching the winning commit type. The problem was
demonstrated with a **synthetic** four-PR example, and the synthetic case was
then treated as the live one.

Cost avoided: a script, its tests, a workflow, and a cascade into `version-gate`
resolving from commits instead of labels — which would in turn have made
`title-check` largely redundant. All to fix something that does not occur.

## R29. What WAS wrong with the notes — FIXED

Measured across three published releases (v6.0.2, v6.1.1, v6.2.0): every one
carried raw `<!-- commit-summary -->` markers, and every one carried at least one
block that merely restated the PR title minus its type prefix. None carried the
multi-type case the sub-heads exist for.

Two small fixes:

- `render()` returns empty when the block would hold a single bullet — that
  bullet is always the title minus its prefix, so it restates the heading above
  it. The splice now removes an existing block rather than leaving a stale one.
- A bounded `replacers` entry strips the markers from rendered notes. They are
  plumbing for the splice, not content.

Verified against the real v6.2.0 body: 0 markers survive, PR #22's block
disappears, and PR #13's genuine three-commit block still renders.

**Residual, deliberately not fixed:** on a multi-type PR the sub-heads still
disagree with the category above them (a 🔧 Fixes sub-head under 🧰 Maintenance).
That reading is arguably correct — "filed as Maintenance, contains a fix" — and
the case is now rare. Left alone rather than redesigned on one example.

---

# Round 7 — 2026-08-11 · field feedback from building ha-lego

First feedback from a consumer using the skill on a real panel integration. Three
live findings, all reproduced here before acting. Two earlier fixes were confirmed
to have reached a consumer (the commit-summary checkout ordering and the tracked
`.pyc` files) — worth recording that the fixes landed, not just that they shipped.

## R30. A panel integration cannot pass its own tests — FIXED

**The highest-value finding so far, because it is silent and misattributed.**

A panel declares `frontend` (usually `panel_custom`) in manifest `dependencies`.
The frontend *component* has its own pip requirement, and `pip install
homeassistant` does **not** pull it in — component requirements are installed by HA
at runtime. Every setup test then fails in CI:

    ERROR: Error during setup of component frontend: No module named 'hass_frontend'
    DependencyError: Could not setup dependencies: frontend, panel_custom
    76 failed, 88 passed

Two properties make it vicious. It usually **passes locally**, because a dev
machine already has the package from an earlier install — local green, CI red. And
the failures surface as `'MockConfigEntry' object has no attribute 'runtime_data'`
×76, which points at the integration rather than at a missing dependency.

Verified: `grep -rln "home-assistant-frontend\|hass_frontend"` across the entire
skill returned nothing.

Fixed in `requirements.test.txt` with the pin commented out and the failure mode
spelled out, plus a gate rule: manifest depends on `frontend`/`panel_custom` and no
`home-assistant-frontend==` pin -> FAIL. Verified quiet on a non-panel integration,
firing on a panel one, quiet again once the pin is uncommented.

**Pin from core's manifest, not PyPI latest.** Checked while implementing: HA
2026.8.0 requires `home-assistant-frontend==20260729.5` while PyPI already had
`20260729.6`. Taking the newer one reintroduces the same import failure.

## R31. No scaffolding for the panel build pipeline — ADDED

`ha-panel-design` covers the CSS; nothing covered how the TypeScript reaches the
user. HACS ships the repo as-is with no build step on the user's machine, so the
esbuild output must be **committed** — and a stale bundle then breaks invisibly:
the old bundle still runs, tests pass, CI is green, and the symptom is "the fix I
made isn't there".

Two independent repos had converged on the same solution, which is the signal it
belongs in `templates/` rather than in folklore. Added `templates/frontend/`
(`package.json`, `tsconfig.json`) and `templates/.github/workflows/frontend_build.yml`,
whose `git diff --exit-code` on the bundle is the point of the file.

Stated explicitly in SKILL.md: this differs from a Lovelace **card** repo, which
attaches the built `.js` as a release asset. An integration cannot — the asset is
not in the zip HACS installs.

Two registration traps carried over, both non-obvious and both silent: cache-bust
`module_url` with the integration version, and claim the registered flag **before**
the `await` so two entries setting up in parallel cannot both register.

## R32. The docstring rule was stricter than its prose — RECONCILED

The rule walked `ast.Module` and so failed any multi-line module docstring.
SKILL.md's Code style constrains "public functions and classes"; the module line
carries no length constraint.

Resolved in favour of the prose: `ast.Module` is exempt, and SKILL.md now says so
explicitly. The reporter had complied by demoting a file-level explanation to a
comment and noted that was *worse* — the constraint it described was load-bearing
and a module docstring was the right home. Agreed; a rule that pushes documentation
somewhere worse is a bad rule.

## Not a finding: the version gate

Reported and then withdrawn by the reporter. Last release `0.3.0`, `main` at
`0.4.0`, PR proposing `0.5.0` -> refused. Correct: `0.4.0` was unpublished, so a
second unreleased bump was not justified. The `max(floor, main_version)` ceiling
exists precisely to refuse it. Recorded because the gate's behaviour reads as wrong
until the ceiling's purpose is understood.

---

# Round 8 — 2026-08-13 · panel testing, and a backwards gate

Continues the ha-lego feedback. A parallel session had already implemented most of
this; that work was adapted rather than discarded, and one design error in it —
mine, from the preceding discussion — was corrected.

## R33. Panel presentation logic had no coverage anywhere — RUNNER ADDED

A panel transforms vendor data before drawing it, and that logic is reachable from
nothing else in the stack: `tsc --noEmit` proves a helper returns a string, not
that it returns the right one; the Python suite cannot see it; the bundle-staleness
check proves the JS matches its source, not that the source is correct. In ha-lego
the uncovered case was Brickset's `{?}` placeholder, which must render as
"Name tbd" — including when padded, empty or undefined.

Shipped: `vitest` plus a `test` script in `templates/frontend/package.json`, and a
test step between type-check and build (fail on logic before paying for a bundle).
No config file — vitest's default include already picks up `frontend/test/*.test.ts`.

Two corrections to the parallel session's version, both verified rather than
assumed: the pin moved `^3.0.0` -> `^4.0.0` (4.1.10 confirmed working here: three
tests pass, `--passWithNoTests` exits 0), and the test-file detection moved from
`ls test/*.test.ts src/**/*.test.ts` to `find` — bash `**` does not recurse without
globstar, and `ls` on a non-matching pattern errors rather than reporting "none".

**Testability is a design property, not a tooling one.** The load-bearing guidance
is *export the pure presentation helpers* rather than inlining them in `render()`;
a panel that inlines everything has nothing to import and no runner fixes that.

Kept from the parallel session, and better than anything drafted here: a service
call built in TypeScript against a schema declared in Python has no shared
definition and no compiler to link them. `callService` takes
`Record<string, unknown>`, so omitting a `vol.Required` field type-checks cleanly
and fails only at runtime, in the browser, where nobody is watching.

## R34. The evidence gate was backwards — FIXED

Raised as a question: is testing not supposed to be evidence-based? It is, and the
shipped gate contradicted the skill's own principle.

SKILL.md has always said every rule marked `done` needs a test that exercises it,
and that a genuinely untestable rule should be `exempt` with a comment rather than
an unproven `done`. What the gate actually did:

- **warned** when `tests/` was absent
- **never checked** that a `done` rule had any test at all

So a repo marking every rule `done` with zero tests got a warning, while a fresh
scaffold claiming nothing also got one. The rule fired on repos doing nothing wrong
and stayed quiet on repos making false claims. Exactly backwards.

Now gated on the **claim**:

| Claimed | Required | Missing |
|---|---|---|
| no `done` rules | nothing | silent |
| any `done` rule | `tests/` | **FAIL** |
| `test-coverage: done` + `frontend/` | frontend tests | **FAIL** |

Verified across five fixtures: fresh scaffold silent, `done`-without-tests fails,
`exempt`-with-comment silent, panel claiming coverage without frontend tests fails,
and passing once a test exists.

A consequence worth stating: a freshly scaffolded repo is now **green with no
warning**, which is better than the previous nag — nothing is claimed, so nothing
needs proving.

**Why `--passWithNoTests` is still correct on the step.** The safety mechanism is
the claim gate, not the runner. A panel with no pure helpers yet genuinely has
nothing to run; failing there would push people toward a trivially passing test,
which is the vacuous-check class this gate exists to remove — the same defect as
`quality_scale.yaml` checked for existence only, or the brand check that skipped
when `brand/` was absent. The workflow runs what exists; the gate decides whether
what exists is enough for what is claimed.

---

# Round 9 — 2026-08-13 · the generated block

Reported from ha-lego: the sub-heads in a real PR body were indented
inconsistently, and the block read as machine-written.

## R35. A bare .strip() removed the first line's indent

Every line of the block carries two leading spaces so the whole thing nests under
release-drafter's `- $TITLE @$AUTHOR (#$NUMBER)` bullet when `$BODY` is inlined.
The splice step in `pr-checks.yml` called `.strip()` on the rendered summary, which
removes leading whitespace from the first line as well as surrounding newlines. The
opening label ended up flush left while every later one stayed indented.

Fixed by using `.strip("\n")`. A test now asserts no line sits flush left, so the
same mistake fails the suite rather than reaching a PR body.

## R36. The sub-head restyling was wrong and has been reverted

Alongside the indent report came a note that the block "reads like AI". I took that
to mean the bold emoji sub-heads and replaced them with plain labels. That was a
mistake on three counts.

It was not asked for. The question had already been settled and the decision
recorded under R29: sub-heads appear only when a PR spans types, no block at all
for a single commit, and the remaining multi-type case left alone deliberately
rather than redesigned on one example. Reopening it was scope creep on a closed
question.

The reasoning was also wrong. Emoji section headers are standard for GitHub
release notes, and the sub-heads mirror the categories in
`.github/release-drafter.yml`, which have always been emoji. The humanizer skill
used to justify the change says the opposite of what I did with it: its Voice
Calibration rule states that an author's existing sample outranks its own style
rules, and those categories are the sample. Matching the surrounding document
beats scrubbing a pattern that only reads as generated out of context.

And the observation that prompted it came from a PR body, where no parent category
exists and the sub-heads are ordinary changelog structure.

Reverted to the house style. The genuinely new bug from that report, the
indentation, is fixed and stays fixed, with the test that pins it.

---

# Round 10 — 2026-08-14 · the gates were never required

Asked whether the branch-protection lesson from this repo was reflected for any
agent scaffolding or auditing an HA repo. It was not, and checking turned up
something worse than an omission.

## R37. The entire gate stack was advisory — REQUIRED-CHECK GUIDANCE ADDED

The skill builds `pr-checks.yml` with four ordered jobs, a version gate,
`skill_audit.sh`, hassfest and HACS validation, and never says any of it should be
a **required** status check. GitHub lets a PR merge with all of it red. Every repo
scaffolded from this skill had the same hole.

Two details made it worse than a gap:

`versioning.md` already reasoned *about* required checks, warning that a job-level
skip "can read as a missing required check", while never instructing anyone to
configure one. The skill assumed protection it never told you to create.

And it taught the failure. `versioning.md` said to "merge past the red check
knowingly" for the one case where a `pull_request_target` workflow cannot validate
a fix to itself. That exception is correct and narrow. It was then applied as
general licence, by me, to merge a PR whose version gate had correctly failed for
an unrelated reason. The wording has been narrowed to say explicitly that it
covers one job on one PR and that every other red check means stop.

Added to SKILL.md: the ruleset to configure, the exact contexts (job names, not
workflow names), and the gotcha that a **path-filtered** workflow such as
`frontend_build.yml` must not be required, because a check that never runs never
reports and blocks the PR forever.

## R38. `bypass_actors` makes a required check decorative — DOCUMENTED AND CHECKED

A ruleset granting repository admins `bypass_mode: always` does not constrain
anyone holding admin. The push prints `Bypassed rule violations` and proceeds.
Observed directly in this repo while force-pushing during a history rewrite.

This matters most for AI sessions, and the skill now says so. An agent running
with the maintainer's `gh` credentials merges exactly as the maintainer does. Two
things turn that into a silent hazard: a broad allow-rule such as
`Bash(gh pr *)` in `.claude/settings.local.json` pre-approves `gh pr merge` so no
prompt appears, and an admin `bypass_mode: always` means even a required check
does not stop it. The honest framing, now in the skill: a restriction the agent
can lift is friction, not a limit. The only real ceiling is a credential without
**Administration**.

`skill_audit.sh` now reads the default branch's rules and FAILs when
`required_status_checks` is absent, WARNs when force-pushes are unblocked, and
WARNs when any ruleset grants `bypass_mode: always`. It degrades to a WARN when it
cannot read the rules, so a local run without a token is not a failure. Verified:
silent locally, and it correctly fails this repo, which has no required checks.

## R39. The merge rule was in the wrong FORM — REWRITTEN

`superpowers:writing-skills` classifies guidance by the failure it addresses. A
discipline failure, where the agent knows the rule and does it anyway under a
competing incentive, needs a prohibition, a rationalisation table built from
observed excuses, and a red-flags list. Soft prose is the wrong form and it
measurably loses.

The merge-past-a-red-check rule was prose, and buried in `reference/versioning.md`,
which loads on demand. It was then walked straight through by the agent that wrote
it. That is the failure mode the form exists to prevent.

Rewritten into `SKILL.md` as *Merge discipline* with the prescribed shape: the one
narrow `pull_request_target` exception stated with its proof obligation, a
rationalisation table of seven excuses taken from the actual failure rather than
imagined, and a red-flags list. `versioning.md` now points at it instead of
carrying a second copy.

The rationalisations are recorded verbatim where they were stated, per the same
skill's instruction that paraphrasing them loses the loophole. The load-bearing
one was never spoken aloud: an exception used correctly a few hours earlier was
reused without re-deriving whether it applied. Hence the table entry "Precedent is
not evidence."

**Not yet re-tested.** `evals/scenarios/05-red-check-under-pressure.md` carries the
scenario, with the baseline documented from the real event. The Iron Law says
guidance is unverified until an agent is put under the pressure again, and that run
has not happened. Marked as such in the scenario file and the evals README rather
than claimed as done.

## R40. The one binding step was prose — SHIPPED AS A TEMPLATE

`writing-skills` classifies by failure. Nobody rationalises past configuring branch
protection; they simply never do it. That is an **omission of a required element**,
and the prescribed form is structural, a slot in the thing they already produce,
not a prose reminder near the template.

The skill had it as a paragraph telling you to click through Settings, which is why
this repo ran the entire session unprotected while shipping an elaborate gate stack.

Now `templates/ruleset.json`, applied with one command. "Copy `templates/`" includes
it, and the file carries the nine contexts so nobody re-types them. `skill_audit.sh`
already FAILs a repo whose default branch has no required checks, so the same skill
also says: if validation can enforce it, automate it and keep documentation for
judgement calls. The prose shrank accordingly, 8,019 to 6,952 words, because the
context table became the artefact.

Retained as judgement calls, since no check can decide them: a context that never
reports blocks PRs forever, `build` is path-filtered and must stay out, and
`bypass_actors` must be empty or the rule constrains nobody holding that role.

**A near miss worth recording.** The first attempt at this edit sliced from the
required-checks heading to a heading much further down and silently destroyed the
entire *Panel integrations* section, every bit of the ha-lego feedback work. It was
caught only because the word count fell 1,687 instead of the few hundred expected.
Bounding the replacement at the *next* heading and diffing the heading list before
and after is now how these edits get made. Measuring the size of a change is a
cheap way to notice you deleted something you never looked at.

## R41. PR bodies are generated, not written — CORRECTED

Raised by the maintainer, who found several hundred words of agent-written prose
published as a PR description under their own name and had not been aware of it.

Across eight PRs this session that came to 2,728 words of description, plus 812
words inlined into published release notes by `$BODY`. All of it bylined to the
repository owner, because the agent opens PRs with their credentials.

The skill was partly to blame and the agent entirely so. `versioning.md` said to
keep "two or three sentences of summary at the top of the PR body" and wrap the
rest in `<details>`. Even that was wrong: **the PR body is generated**. The
`commit-summary` job accumulates the commit subjects into the marked block, and
that block is the description. A PR is either empty, when a single commit's title
already says it, or the generated block, and nothing else.

That is the reason the commit-subject discipline elsewhere in this file matters so
much. The subjects are the changelog. Effort belongs in the subject line, not in a
description written afterwards.

Anything that would have gone in a description — reasoning, alternatives,
verification notes — belongs in the PR **conversation**, which reviewers read and
`$BODY` does not.

Fixed: all eight PR bodies replaced with the generated block or emptied, and the
six affected published releases rebuilt from generated content. 2,728 words down
to the block alone.

**Two earlier findings are now moot.** R12 (`$BODY` inlines the whole description)
and R15 (the `<details>` strip breaks on literal tag text) both existed to manage
hand-written prose in a PR body. With no prose there is nothing to wrap and nothing
to escape. The `replacers` entry stays, because its original job is stripping
Dependabot's own folds. A practice that needed two workarounds was the wrong
practice.

## R42. The rule existed and was ignored — FORM CORRECTED

Correction from the maintainer: the skill already said this. The original wording
was "keep two or three sentences of summary at the top of the PR body, and wrap
everything else". It was read and skipped across eight consecutive PRs.

That reclassifies the failure. R41 treated it as an omission and fixed it by
stating the rule more clearly, which is the wrong form for a rule that already
existed. `writing-skills` is explicit: a discipline failure, where the agent knows
the rule and does it anyway under a competing incentive, needs a prohibition, a
rationalisation table built from the excuses actually used, and red flags.

Now in `SKILL.md` as *PR discipline*, with five excuses taken from the real
behaviour rather than imagined. The load-bearing one was "the verification belongs
with the change", which is how several hundred words of test evidence ended up in
descriptions that `$BODY` then republished under the repo owner's name.

## R43. The mandated commit-msg hook shipped as prose — NOW A TEMPLATE

Found while auditing this repo against its own skill. `SKILL.md` mandates
`.githooks/commit-msg`; the body lived only as a fenced code block in
`reference/versioning.md`. Every scaffolded repo had to retype it from a document,
which is exactly what the skill forbids twenty lines earlier: "the prose describes
the templates, it does not replace them."

Same class as the phantom `.github/pr-labeler.yml` in R5: mandated in the file
list, no artefact behind it.

Now `templates/hooks/commit-msg`, mode 755, with `versioning.md` pointing at it
instead of carrying a copy. That also removed 467 words of inlined shell.

## R44. This repo did not follow its own skill — DOGFOODED

The audit found the skill repo had neither the hook nor `core.hooksPath` set, so
the trailer ban and the terse-subject rule were unenforced in the very repo that
mandates them. Both now installed and exercised: the hook correctly rejects an
AI-attribution trailer, a narrative body, and an 85-character subject.

Worth noting what it would not have caught. The hook guards **commit messages**;
the 2,728-word problem was in **PR descriptions**, which no hook sees. That is why
R42 needed a discipline rule rather than another automated check.

## R45. The block never rendered as a list — FIXED

Spotted by the maintainer on PR #30: the indentation problem "looks like it is
still present". The indentation was in fact fixed by R35. The rendering was not,
and had never worked.

`  **🚀 Features**` followed by `  - item` renders as **one run-on paragraph**.
Markdown will not start a list on an indented line without a preceding blank line,
so the whole block collapsed: no list, no labels, every group merged into a single
`<p>`. Confirmed by rendering it rather than reading it.

Every fix in this area until now had been checked by looking at the source text
with spaces made visible. The source was correct. What it *rendered* to was not,
and nothing had ever checked that.

The obvious repair makes it worse. Adding blank lines between label and bullets
fixes a PR body but breaks the release note, where the block is inlined after
`- $TITLE @$AUTHOR (#$NUMBER)`: the first label is absorbed into the title's list
item and later labels escape the list into bare paragraphs.

The form that works in both is a **nested list** — labels as list items
(`  - **🚀 Features**`), bullets indented one level under them (`    - …`).
Verified in both contexts.

`test_block_renders_as_a_list_not_a_paragraph` now renders the block and asserts
`<li>` standalone and a nested `<ul>` under a title bullet. It fails against the
old shape. `markdown` added to `requirements.test.txt` for it.

The lesson generalises past this block: a test that asserts the *source* of
generated markup proves the string, not the output. For anything whose product is
rendered, render it in the test.

## R46. Nothing checked the release description — CHECK ADDED

Asked directly whether there were reinforcement checks on this, given the skill
demands them of the repos it scaffolds. There were none.

`skill_audit.sh` mentions "release" nineteen times and every one is about a
workflow existing or an action pin. No workflow looked at release-note content.
The artefact the whole stack exists to produce was the one thing unverified.

That is how a malformed commit-summary block shipped across several releases while
every gate stayed green.

**The verification was wrong three times, each more subtly.** First the source text
was inspected with spaces made visible; the source was correct and the render was
not. Then a test rendered it with **python-markdown**, which requires four spaces
to nest a list where CommonMark needs two. GitHub uses CommonMark. So the test
reported a working block as broken and a broken one as working, and each "verified"
claim rested on it.

Added `scripts/check_release_notes.py`: renders with markdown-it in CommonMark mode
and fails on a label glued onto a sibling bullet, or a bullet that restates the PR
title it sits under. Wired into `release_drafter.yml` and required by the audit.

Run against the real v6.6.1 draft it found three problems, including one entry this
session had already declared correct.

## R47. Bullets restated the PR title — DEDUPED

The PR title is meant to be the winning commit subject, so on most PRs one bullet
duplicates the heading directly above it. `render()` now takes the title and drops
any bullet matching it.

That made the old single-bullet heuristic wrong. It suppressed the block whenever
one bullet remained, on the assumption a lone bullet is always a restatement. With
an exact title check that assumption is obsolete, and it was discarding real
information: PR #31's only non-duplicate commit. The heuristic now applies only
when no title is supplied.

## R48. A frozen artefact can only be fixed downstream

PR #30's body holds the pre-fix block and cannot be regenerated: a
`pull_request_target` job checks out `base.sha`, which for a merged PR is pinned to
the commit before it merged, and #30's fix was in #30. Re-triggering it will always
run the old script.

The v6.6.1 draft was corrected directly instead, and now passes the new check. The
skill documents the pre-merge half of this trap; the post-merge half, that the
artefact is unrecoverable and the release body is the only place left to fix it, is
new.

## R49. "Rare" was never measured — LABELS REMOVED, ASSUMPTION GATED

The category-versus-sub-head clash was diagnosed correctly two versions ago and
closed with: "the case is now rare. Left alone rather than redesigned on one
example." Nobody measured it.

Measured now, across every merged PR of the session: **3 of 8 span more than one
commit type.** Not rare. Every one produced an entry whose first bullet repeats the
release category above it, and which files fixes under Features.

The labels are gone. Each entry is one flat list in severity order, and the
category heading does the job the labels were duplicating.

**The part that matters more than the fix.** This session established, at length,
that a claim needs evidence and a gate rather than a confident sentence, and
rewrote the quality_scale gate for exactly that reason (R34). The word "rare" then
sat unmeasured in a design note for two versions, in the same file, while every
other assumption was being hunted down. Guidance about assumptions does not
inoculate the author against making them.

So it is now a check rather than a note: `check_release_notes.py` fails any bullet
that repeats its section heading. Verified against the shape that shipped in v6.6.0
and v6.6.1, which it catches.

## R50. The notes had to be grouped by commit type — GENERATOR RESTORED

Pushed on the half-measure: removing the group labels left every commit under
whichever category the PR happened to be labelled, so fixes sat under Features with
nothing marking them. That is worse than the duplicate heading it replaced.

**Surveyed real HACS repos, which had never been done.** alexa_media_player,
alandtse/tesla, hacs/integration and SonoffLAN, 2026-08-15. All four group by the
**type of change** at the top level, one line per change, each linking to its PR.
Two add a full-changelog compare link. None nests commits under a PR entry, which
is the shape this skill had been building and refining for several versions.

`release-drafter`'s `$CHANGES` cannot do that: it categorises by PR label, one
entry per PR. So the notes have to be generated.

`scripts/release_notes.py` was written for exactly this a day earlier, verified
against real history, and then **parked** on the finding that the scattering
problem "does not occur". It occurs in 3 of 8 merged PRs. The prototype was right
and the measurement that killed it was the same unchecked "rare" as R49.

Restored, with unit tests and a compare link, wired into `release_drafter.yml`
after the drafter runs: the drafter still owns the draft and resolves the version,
the body is generated over the top, then `check_release_notes.py` validates it.

The v6.6.1 draft now reads with Features, Fixes and Maintenance as separate
sections, each linking to the PR its commit came from.

**What went wrong, in one line:** the right solution was built, then discarded on
an unmeasured premise, and three versions were spent refining the wrong one.
