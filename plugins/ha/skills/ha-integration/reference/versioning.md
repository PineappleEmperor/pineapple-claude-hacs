# Versioning, labels & CI gating

How a release version is decided, how labels drive it, and what the version gate enforces.
Commit and PR-title conventions are `reference/commits.md`; the GitHub-side settings are
`reference/github-setup.md`.

- One labeler, title-only — don't hand-roll a second one
- Stale superseded labels — NOT rare in a squash + rc-cycle repo
- Type-vocab gap (narrower than it looks — verify against the config, not from memory)
- Prerelease (rc) cycle
- Nothing is ever bumped by hand
- A `pull_request_target` workflow cannot validate a fix to itself
- Why every label job is in one workflow
- Orphaned-branch trap

### One labeler, title-only — don't hand-roll a second one

⚠️ The autolabeler can only match title/body/branch/files (never commit subjects). Label off the **title** and keep it the *only* labeler. Pitfalls: (a) a second label step in any workflow **fights** the autolabeler → labels flap (add/remove every push); (b) `branch:` rules flap when the branch name disagrees with the commits (e.g. branch `chore/…`, commits `feat:`) — so use **title-only** rules. Resist re-adding custom bash to "label from commit subjects"; the title already encodes the winning type.

### Stale superseded labels — NOT rare in a squash + rc-cycle repo

⚠️ The autolabeler only *adds*, never removes. When a PR's title flips type mid-life (`fix:` → `feat:` as scope grows — routine on a long-lived `feat/rcN` branch), the **old type label lingers alongside the new one**. release-drafter is PR-granular and lists a PR under **every** matching label's category, so a double-labelled PR shows up under *two* headings (e.g. both `## 🚀 Features` and `## 🔧 Fixes`) with the same change listed under two release sections. release-drafter still resolves the highest increment for the bump, but the **release notes are wrong**. This is common — not "rare since a PR is usually one type"; rc-cycle PRs routinely accrue mixed types and a flipping title.

The shipped fix is a **removal-only** step in `pr-checks.yml`'s `label` job, running after the autolabeler. Removal-only can't flap: it only ever subtracts the non-winning labels, keyed on the same title the autolabeler reads, so there is still **one source of truth**. Copy the job from `templates/.github/workflows/pr-checks.yml` — do not retype it from here. Two properties to preserve if you ever touch it: the `!`-breaking arm must be tested first (else `feat!` matches the `feat` arm), and the job needs `pull-requests: write`.

**This fixes the *labels* only — one PR, one category.** It does not decide where a mixed-type PR's commits land: the notes are built from commit subjects and each commit is classified on its own, so such a PR contributes to whichever sections its commits belong in.

### Type-vocab gap (narrower than it looks — verify against the config, not from memory)

⚠️ The autolabeler maps `feat`/`feature` → **feature**, `fix` → **fix**, `chore`/`docs`/`refactor`/`perf`/`test`/`build`/`ci`/`style` → **chore**, and any `type!:` → **xfeat**. So `ci:`, `refactor:`, `perf:`, `build:`, `style:` and `test:` **are** labelled (as `chore` → 🧰 Maintenance → patch).

The vocabularies are deliberately narrower than Conventional Commits and they are **not identical to each other**, so check both before adding a type:

- `lint_pr.yml` passes an explicit `types:` allowlist — the ten the autolabeler maps, and only those. `revert:` is the type the spec allows that maps to no label, and the allowlist is what keeps it out.
- The allowlist omits `feature`, which the autolabeler *does* map. A PR titled `feature: …` fails `CC title validation` even though its label would have resolved.

**The two run independently.** `lint_pr.yml` and `pr-checks.yml` are separate workflows on the same trigger, so a title `lint_pr` rejects still reaches the autolabeler — the rejection is a red check, not a gate on labelling.

Because of what `title-check` decides from (`reference/github-actions.md`, must-preserve behaviours), it also fires when the autolabeler did not run, when a label was removed by hand, or when a repo's `lint_pr.yml` has drifted off the allowlist. `needs: label` guarantees the autolabeler has already run. Don't hand-patch the label; the autolabeler rewrites it on the next `synchronize`. What the job enforces, and why it is the gate, is the same file.

### Prerelease (rc) cycle

Release candidates are published via the GitHub **prerelease flag** + a `v…-rcN` tag; the manifest carries a matching **PEP440 prerelease** (`2.0.0rc1`) which `AwesomeVersion`/hassfest/HACS accept (`2.0.0 > 2.0.0rc1`). Two rules:
- **rc numbers track *published* candidates, not PRs.** You only increment `rc1`→`rc2` when you actually cut a new published rc; you do **not** invent `rc2`/`rc3` per-PR to satisfy the gate. The version stays frozen across iteration: in a tag-driven repo nothing in the branch carries it at all — the rc number lives only in the tag you publish.
- **A prerelease deliberately changes gate behaviour:** a prerelease version only needs to *differ from base* — so the gate must **skip** the label-derived "incorrect version" suggestion when the PR version matches `(rc|alpha|beta|a|b|dev)[0-9]*$` (otherwise a `feature`-labelled `2.0.0rc1` PR fails, demanding `v2.1.0`). Also de-anchor the base parse (`^([0-9]+)\.([0-9]+)\.([0-9]+)` without `$`) so a base that already carries `rcN` still parses. This is the *only* prerelease gate change needed — do **not** add per-PR rc-increment logic or relax the "differ from base" rule.
- **Graduating off rc to the same-number final is a legitimate bump the gate must allow.** Coming off the rc line (`2.0.0rc19` → **`2.0.0`** final) is the natural cycle close, but the de-anchored parse makes `2.0.0rc19` and `2.0.0` both `(2,0,0)`, so a naive `pr == base` check (and a `feature` label demanding `v2.1.0`) **wrongly rejects the graduation** — even though `AwesomeVersion` knows `2.0.0 > 2.0.0rc19`. The gate special-cases it: when the PR version is final, equals the base tuple, **and** the last release was a prerelease, pass it ("final graduates its own prerelease"); a `pr == base` where the last release was already *final* still fails (real unchanged version). Covered by `test_final_graduates_prerelease`.

### Nothing is ever bumped by hand

`release.yml` writes `manifest.json` from the release tag at publish, so no PR carries a bump
and the committed value is a placeholder between releases. **Nothing gates a version at PR
time, because there is no version in the PR to gate** — what the merged labels imply for the
next release is reported in `CC label validation`'s summary, and the correctness of that
number rests entirely on the label being right.

### A `pull_request_target` workflow cannot validate a fix to itself

`pull_request_target` loads the workflow from the **base branch**, so a PR that fixes a
broken job is still checked by the broken copy on `main`. The job cannot pass until the fix
is merged, and it cannot be merged while the job is red.

That deadlock is the one sanctioned reason to merge past a red check, and the conditions on
it are narrow. Do not act on this paragraph: *Merge discipline* in `reference/discipline.md`
states them.

### Why every label job is in one workflow

GitHub suppresses workflow runs for events caused by the default `GITHUB_TOKEN`, so the
`labeled` event the autolabeler would fire never arrives and nothing can be keyed on it.
Every PR-time job that reads or writes a label therefore lives in `pr-checks.yml`, ordered
with `needs:` — the workflow contract, and what must not be split back out, is
`reference/github-actions.md`. **What it means for you: never key a version or label job on
another workflow's side effect, and never poll for one.**

The version gate is PR-time only for the same reason a label is: the expected bump is derived
from the PR's labels, so a `push:` trigger could only check the parts that need no label. The
template once had one and it was a no-op — every step was already gated on
`github.event_name == 'pull_request'`.

---

Dependabot's setup, grouping and floor management live in `reference/dependabot.md`.

### Orphaned-branch trap

A PR merges to `main` as soon as it's approved/auto-merged. **Any commit you push to `feat/rcN` after that merge is stranded** — it's not on `main` and not in the release, even though `git status` on the branch looks fine. **Guard every time, not just when you remember:**
1. At the **start** of any rc work and before claiming work is "pushed/live", run `git fetch origin` then `git log --oneline origin/main..feat/rcN`. If `main` already contains a merge of this branch, the branch is spent.
2. When a cycle has merged/released: **branch fresh** `git checkout -b feat/rc(N+1) origin/main`, `git cherry-pick` the orphaned commits (oldest-first), push, then delete the stale branch so nothing lands on it again. Nothing in the branch carries a version — the rc number is the tag you publish.
3. Don't keep committing onto a `feat/rcN` whose PR has merged — start the next branch immediately after a release.

