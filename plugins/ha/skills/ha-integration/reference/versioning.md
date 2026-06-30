# Conventional Commits, versioning & CI gating

Reference for `ha-integration`. Loaded on demand.

### Conventional Commits & Semantic Versioning

**Commit format:**
```
<type>[(<scope>)][!]: <description>

[optional body — one blank line after description]

[optional footers — BREAKING CHANGE: <detail>]
```

**Keep messages short.** Tight imperative subject; **subject-only by default**. Add a body ONLY when the *why* is non-obvious, or for breaking changes / migration notes — never to restate what the diff already shows. Long bodies that narrate the change are noise. Subject in imperative mood, lowercase after the colon, no trailing period.

**No AI-attribution trailers.** Don't append `Co-Authored-By: Claude`, tool/session links, or any "generated with…" line to commits — keep the authorship history clean. (If a harness injects such trailers by default, strip them.) A `Co-Authored-By:` for a *real* human collaborator is fine.

⚠️ **Enforce the trailer ban with a `commit-msg` hook — prose alone isn't enough.** A coding harness can inject `Co-Authored-By: Claude` / `Claude-Session:` on *every* commit via a standing instruction, which fights this rule turn after turn; the agent keeps "remembering" the harness default over the skill and regresses. The fix is deterministic enforcement at the git layer, not memory. Ship `.githooks/commit-msg` (terse-subject + no-narrative-body + **AI-trailer rejection**), add it to the scaffold's repo-root files, and tell contributors to enable it once per clone in `CLAUDE.md`: `git config core.hooksPath .githooks`.
```bash
#!/usr/bin/env bash
# Enforce terse commits: subject <=72 chars, no narrative body, no AI-attribution trailers.
# Body lines allowed only as trailers (Key: value), Closes/Refs/Fixes #N, or any body when a
# BREAKING CHANGE footer is present. Enable once per clone: git config core.hooksPath .githooks
msg_file="$1"
subject="$(grep -v '^#' "$msg_file" | sed -n '1p')"

if [ "${#subject}" -gt 72 ]; then
  echo "commit-msg: subject is ${#subject} chars (>72). Keep it terse." >&2
  exit 1
fi
case "$subject" in "Merge "*|"Revert "*|"fixup! "*|"squash! "*) exit 0 ;; esac

# Reject harness-injected AI-attribution trailers (this skill bans them). A real human
# Co-Authored-By is still fine.
if grep -v '^#' "$msg_file" | grep -Eqi '^Co-authored-by:[[:space:]]*Claude|^Claude-Session:|Generated with .*(Claude|Anthropic)'; then
  echo "commit-msg: AI-attribution trailer not allowed (strip Co-Authored-By: Claude / Claude-Session)." >&2
  exit 1
fi

if grep -q 'BREAKING CHANGE' "$msg_file"; then
  exit 0
fi

bad=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in \#*) continue ;; esac
  printf '%s' "$line" | grep -Eq '^[A-Za-z][A-Za-z-]*: ' && continue
  printf '%s' "$line" | grep -Eq '^(Closes|Refs|Fixes|Resolves) #' && continue
  bad="$line"
  break
done < <(grep -v '^#' "$msg_file" | tail -n +2)

if [ -n "$bad" ]; then
  echo "commit-msg: narrative body line not allowed:" >&2
  echo "    $bad" >&2
  echo "Keep commits subject-only; put detail in the PR / release notes." >&2
  exit 1
fi
exit 0
```

**Put the narrative in the release, not the commit.** The human-readable "what changed and why it matters" belongs in the **PR description / release notes** (surfaced by release-drafter / `generate_release_notes`), which is where users actually read it. Keep commits terse; write the detail once, in the release description.

**Match release-drafter when writing the PR body.** If `change-template` includes `$BODY`, the PR description is inlined **under** its category heading (e.g. `### 🚀 Features`). So the body must nest cleanly: use **bold emoji sub-heads** (`**🧩 Engine**`), not `#`/`##` — top-level headings render bigger than the category and clash. Mirror the config's emoji category style, and label the PR so it lands in the intended category (e.g. a `major`/`xfeature` label → 🚨 Breaking Change). Note release-drafter draws the PR body via the GraphQL path; `gh pr edit` can fail on the Projects-classic deprecation — set title/body via `gh api -X PATCH repos/{o}/{r}/pulls/{n} -f title=… -F body=@file` instead.

> ✅ **Canonical release-notes pattern (Dependabot + `$BODY` + `replacers` scrub) — the standard for every repo.** Keep `$BODY` in `change-template` so **human** PRs surface their grouped mini-changelog (`create-dev-pr` builds it — see below), and scrub Dependabot's noise with release-drafter **`replacers`** (native regex find/replace over the *rendered* notes). This **supersedes the older "drop `$BODY` when Dependabot is on" advice** — that worked but threw away the human per-commit detail. release-drafter has **no per-category `change-template`** (verified), so `$BODY` is global (all PRs or none); `replacers` is the only way to keep human detail *and* strip bot fluff.
>
> - **Group the dev-PR body by commit type** in `create-dev-pr.yml`: classify each `origin/main..HEAD` subject (`breaking`/`feat`/`fix`/`maint`/`other`), emit bold emoji sub-heads (`  **🚀 Features**`, `  **🐛 Fixes**`, `  **🧰 Maintenance**`…) with the descriptions under each, written to `$GITHUB_OUTPUT` via a heredoc. release-drafter inlines `$BODY` verbatim under the PR's one category and does **no** intra-body sorting, so the grouping must happen at body-generation time.
> - **`change-template`** keeps the two-line `$BODY` form:
>   ```yaml
>   change-template: |-
>     - $TITLE @$AUTHOR (#$NUMBER)
>     $BODY
>   ```
> - **`replacers`** scrub Dependabot's fluff. All patterns must be **bounded** (no `$`/end-of-string anchor) — the changelog concatenates every PR's `$BODY`, so an end-anchored strip bleeds across PRs and eats later human entries:
>   ```yaml
>   replacers:
>     - search: '/<details>[\s\S]*?<\/details>\s*/g'                                  # release-note/commit folds
>       replace: ''
>     - search: '/\[!\[Dependabot compatibility score\][^\n]*\n?/g'                   # compat badge
>       replace: ''
>     - search: '/Dependabot will resolve[^\n]*\n?/g'                                 # rebase boilerplate line
>       replace: ''
>     - search: '/\[\/\/\]: # \(dependabot-start\)[\s\S]*?\[\/\/\]: # \(dependabot-end\)\s*/g' # command block — markers are `[//]: # (...)`, brackets included
>       replace: ''
>     - search: '/<br\s*\/?>\s*/g'
>       replace: ''
>   ```
>   Leaves Dependabot's clean opener (`Bumps [pkg] from a to b.`) as the body — a fine one-liner. Regex over bot output is inherently brittle: revisit if Dependabot changes its format. (The full `create-dev-pr.yml` that builds the grouped `$BODY` is inlined in the *create-dev-pr.yml template* appendix above — no external repo needed.)
>
> **Adopt this in every repo** — enable Dependabot (`github-actions` ecosystem at minimum) *and* the `$BODY`+grouping+`replacers` release-drafter, so release notes carry real per-PR detail without bot noise everywhere. (A repo on the old title-only template is behind, not "configured differently".)

**Types and semver mapping:**

| Type | Semver | Notes |
|------|--------|-------|
| `feat` | MINOR | New feature |
| `fix` | PATCH | Bug fix |
| `feat!` / `BREAKING CHANGE:` | MAJOR | Breaking change — any type with `!` or `BREAKING CHANGE` footer |
| `chore`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style` | PATCH | No user-facing change |

**How this flows through the repo workflows:**

1. `create-dev-pr.yml` sets the PR **title** from the winning commit type (`feat` > `fix` > last commit). It does **no** labelling.
2. `pr-labeler.yml` runs the **release-drafter autolabeler** — the sole labeler — keyed on the PR **title** (title-only rules; no `branch:`). Since the title is the winning commit type, the label tracks the commits: breaking `type!:` → `xfeat`, `feat|feature:` → `feature`, `fix:` → `fix`, `chore|docs:` → `chore`. The breaking `!` rule must precede `feature` (else `feat!` is swallowed as a minor `feature`).
3. `release-drafter.yml` config maps labels → semver bump: `feature` → minor, `fix`/`chore` → patch, `major`/`xfeat`/`xfeature` → major.
4. On tag push (`v*.*.*`), `semantic_release.yml` cuts the GitHub release

⚠️ **One labeler, title-only — don't hand-roll a second one.** The autolabeler can only match title/body/branch/files (never commit subjects). Label off the **title** (which `create-dev-pr` derives from commits) and keep it the *only* labeler. Pitfalls: (a) a second label step in `create-dev-pr.yml` **fights** the autolabeler → labels flap (add/remove every push); (b) `branch:` rules flap when the branch name disagrees with the commits (e.g. branch `chore/…`, commits `feat:`) — so use **title-only** rules. Resist re-adding custom bash to "label from commit subjects"; the title already encodes the winning type.

⚠️ **Stale superseded labels — NOT rare in a squash + rc-cycle repo.** The autolabeler only *adds*, never removes. When a PR's title flips type mid-life (`fix:` → `feat:` as scope grows — routine on a long-lived `feat/rcN` branch), the **old type label lingers alongside the new one**. release-drafter is PR-granular and lists a PR under **every** matching label's category, so a double-labelled PR shows up under *two* headings (e.g. both `## 🚀 Features` and `## 🔧 Fixes`) with its full `$BODY` duplicated under each. The `version-resolver` still picks the highest for the bump, but the **release notes are wrong**. This is common — not "rare since a PR is usually one type"; rc-cycle PRs routinely accrue mixed types and a flipping title. Fix with a **removal-only** step after the autolabeler (removal-only can't flap — it only ever subtracts the non-winning labels, keyed on the same title the autolabeler reads):
```yaml
# pr-labeler.yml, step AFTER autolabeler@v7
- name: Remove superseded type labels
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GH_REPO: ${{ github.repository }}  # job has no checkout — gh would else fail "not a git repository"
    TITLE: ${{ github.event.pull_request.title }}
    PR: ${{ github.event.pull_request.number }}
  run: |
    if   printf '%s' "$TITLE" | grep -qiE '^[a-z]+(\([^)]*\))?!:';        then WIN=xfeat
    elif printf '%s' "$TITLE" | grep -qiE '^(chore|docs)(\([^)]*\))?:';   then WIN=chore
    elif printf '%s' "$TITLE" | grep -qiE '^fix(\([^)]*\))?:';            then WIN=fix
    elif printf '%s' "$TITLE" | grep -qiE '^(feat|feature)(\([^)]*\))?:'; then WIN=feature
    else exit 0  # title maps to no managed label; leave labels untouched
    fi
    CURRENT=$(gh pr view "$PR" --json labels --jq '.labels[].name')
    for L in xfeat feature fix chore; do
      [ "$L" = "$WIN" ] && continue
      # `if` (not `grep && gh`): a no-match grep as the step's last command
      # returns 1 under `bash -e`, failing the step even when nothing's wrong.
      if printf '%s\n' "$CURRENT" | grep -qx "$L"; then
        gh pr edit "$PR" --remove-label "$L"
      fi
    done
```
The `!`-breaking branch must come first (else `feat!` matches the `feat` arm). This is still **one source of truth** — the title — and removal-only, so it can't fight the autolabeler the way a second *adding* step does. Needs `pull-requests: write`. **Note this only fixes the *labels* (one PR → one category).** Within a single squash PR whose body lists mixed-type commits, the commits stay together under that PR's one category — sort *those* by grouping the PR body itself by commit type in `create-dev-pr.yml` (bold emoji sub-heads), since release-drafter inlines `$BODY` verbatim under the category and does no intra-body sorting.

⚠️ **Type-vocab gap:** the autolabeler title rules map only `feat|fix|chore|docs` (+ `!` → `xfeat`). A title typed `ci:`, `refactor:`, `build:`, `perf:`, `style:`, `revert:` matches **nothing** → no label → no release-drafter category. Since `create-dev-pr` picks the title as `feat` > `fix` > last commit, ensure at least one commit is a mapped type (e.g. `chore:` not `ci:` for a workflow-only PR) so the title lands on something labellable. Don't hand-patch the label (clobbered next push).

**HA `manifest.json` version** must be bumped manually to match the intended release version before merging — `check-manifest-version.yml` enforces that it's been updated.

⚠️ **Bump discipline:** the manifest bump is the **single, last commit of a PR before it merges** — not a per-push act. **Before even suggesting a bump, check whether the same PR is still being iterated; if so, don't bump.** A red `check-manifest-version` while a PR is in progress is expected and fine — it goes green when you add the one bump commit at the end. The bump **value is the version the PR will be published as** (the next release), and it gets set **once**; don't re-bump it on later pushes to the same PR. When you do set it: `git fetch origin` **first** (the local `origin/main` ref goes stale as PRs merge), compare to `origin/main`'s version, and match the level to the PR's type label (the gate keys its expected version off the label): `feat`→minor, `fix`/`chore`/`test`→patch, breaking→major. The exception that *does* re-bump mid-PR: the PR's type escalates (`fix`→`feat`→`feat!`), changing the label-derived expected version.

**Prerelease (rc) cycle:** release candidates are published via the GitHub **prerelease flag** + a `v…-rcN` tag; the manifest carries a matching **PEP440 prerelease** (`2.0.0rc1`) which `AwesomeVersion`/hassfest/HACS accept (`2.0.0 > 2.0.0rc1`). Two rules:
- **rc numbers track *published* candidates, not PRs.** You only increment `rc1`→`rc2` when you actually cut a new published rc; you do **not** invent `rc2`/`rc3` per-PR to satisfy the gate. The version stays frozen at the current rc across iteration; it changes only as the pre-merge bump to the version being published.
- **A prerelease deliberately changes gate behaviour:** a prerelease version only needs to *differ from base* — so the gate must **skip** the label-derived "incorrect version" suggestion when the PR version matches `(rc|alpha|beta|a|b|dev)[0-9]*$` (otherwise a `feature`-labelled `2.0.0rc1` PR fails, demanding `v2.1.0`). Also de-anchor the base parse (`^([0-9]+)\.([0-9]+)\.([0-9]+)` without `$`) so a base that already carries `rcN` still parses. This is the *only* prerelease gate change needed — do **not** add per-PR rc-increment logic or relax the "differ from base" rule.
- **Graduating off rc to the same-number final is a legitimate bump the gate must allow.** Coming off the rc line (`2.0.0rc19` → **`2.0.0`** final) is the natural cycle close, but the de-anchored parse makes `2.0.0rc19` and `2.0.0` both `(2,0,0)`, so a naive `pr == base` check (and a `feature` label demanding `v2.1.0`) **wrongly rejects the graduation** — even though `AwesomeVersion` knows `2.0.0 > 2.0.0rc19`. The gate special-cases it: when the PR version is final, equals the base tuple, **and** the last release was a prerelease, pass it ("final graduates its own prerelease"); a `pr == base` where the last release was already *final* still fails (real unchanged version). Covered by `test_final_graduates_prerelease`.

**Compare the gate against the last published *release*, not `main` HEAD.** Comparing to `main` forces **every** PR to bump beyond the previous merged PR, so versions inflate per-PR (rc4, rc5, rc6…) with no release between them. Instead resolve the base from the latest published release tag — `gh release list --exclude-drafts --limit 1 --json tagName --jq '.[0].tagName'`, strip the leading `v` — and pass only when the manifest version **differs from that**. Now several unreleased PRs can sit at the same in-progress version (the first PR of a cycle bumps `main` once; later PRs ride it), and the single bump folds into whatever release is cut next. A PR that doesn't change the manifest still passes as long as `main` is already ahead of the last release — which it is, mid-cycle.

**Exempt Dependabot from the version gate.** Dependabot PRs never touch `manifest.json`, and right after a release (`main` == last release) a no-bump PR equals the released version → the gate's "unchanged" rule trips. Add `&& github.event.pull_request.user.login != 'dependabot[bot]'` to the **failing** steps' `if:` (the "unchanged" and "incorrect version" comment-and-`exit 1` steps), *not* a job-level `if:` — a job-level skip can read as a missing required check, whereas skipping just the failing steps keeps the job **green** for Dependabot while staying strict for humans. The push-context run already passes (the failing steps are `pull_request`-only). With this, Dependabot PRs fold into the next release with no bump, exactly as intended.

> ⚠️ **Orphaned-branch trap (the dev-PR auto-merges fast).** `create-dev-pr.yml` opens a draft PR that gets merged to `main` as soon as it's approved/auto-merged. **Any commit you push to `feat/rcN` after that merge is stranded** — it's not on `main` and not in the release, even though `git status` on the branch looks fine. It also leaves the branch's manifest equal to `main`'s, so `check-manifest-version` fails. **Guard every time, not just when you remember:**
> 1. At the **start** of any rc work and before claiming work is "pushed/live", run `git fetch origin` then `git log --oneline origin/main..feat/rcN`. If `main` already contains a merge of this branch, the branch is spent.
> 2. When a cycle has merged/released: **branch fresh** `git checkout -b feat/rc(N+1) origin/main`, `git cherry-pick` the orphaned commits (oldest-first), bump `manifest.json` to the next `rcN` **and** `ENGINE_VERSION` (firmware/version.py + the integration's mirror) if any firmware changed, run the sync + guards, push, then delete the merged branch (local + remote).
> 3. Don't keep committing onto a `feat/rcN` whose PR has merged — start the next branch immediately after a release.

---

### ⚠️ GITHUB_TOKEN suppresses workflows ONLY on the bot's `opened` event — `synchronize` from a human push still fires

Narrow, often-misunderstood footgun: **the `pull_request: opened` event from a PR that `create-dev-pr.yml` opens with the default `secrets.GITHUB_TOKEN` is suppressed** (GitHub's anti-recursion rule — events caused by `GITHUB_TOKEN` don't trigger new runs). So `pull_request`-triggered workflows (`lint_pr`, `pr-labeler`, autolabeler, `check-manifest-version`'s PR part) **do not run on that first auto-open**.

**But it stops there.** Every *later* push you make to the branch fires a `pull_request: synchronize` event whose `triggering_actor` is **you** (your SSH push), not the token — so all those workflows run normally from the second push on. Verified empirically: on a bot-authored dev PR (author `github-actions[bot]`, no PAT, empty secret list), `lint_pr` / `pr-labeler` / autolabeler / manifest-check all ran and passed, every one with `triggering_actor` = the human, because the branch had several pushes. The suppression swallows exactly **one** event — the bot's `opened`.

**Practical upshot:** with **no PAT**, a branch pushed **more than once** (i.e. nearly always) gets full automation — the auto-PR opens, and your next push triggers all checks. The footgun only bites a branch pushed **exactly once** then merged untouched. Don't reach for a PAT reflexively; it's rarely needed.

Fixes, in order of preference:
- **Usually nothing** — push more than once (you will anyway) and `synchronize` covers it. This is the default the canonical workflows rely on (no PAT needed).
- **No-secret hardening for the must-always-enforce gate:** add a `push:` trigger (`branches-ignore: [main]`) to `check-manifest-version` so the version gate runs on the branch push regardless of PR events — covers even the single-push case. Default the base ref to `main` when there's no PR context (`${{ github.event.pull_request.base.ref || 'main' }}`) and guard PR-only steps with `if: github.event_name == 'pull_request'` (label lookups, PR comments).
- **PAT (only if you truly need single-push auto-PRs fully checked):** open the dev PR with a fine-grained, repo-scoped PAT (`Pull requests: write` + `Contents: read`, short expiry) instead of `GITHUB_TOKEN` — PAT-authored events aren't suppressed, so even the `opened` fires everything. Costs a secret to rotate; reserve for when single-push branches matter.

**`create-dev-pr.yml` hardening** (prevents duplicate/stale PRs seen in practice):
- Add `concurrency: {group: dev-pr-${{ github.ref }}, cancel-in-progress: true}` so rapid pushes can't race into two PRs.
- Skip PR creation when the branch has **0 commits ahead of main** (`git rev-list --count origin/main..HEAD`) — otherwise pushing to an already-merged branch re-spawns a PR.
- On update, re-set the **title** (`gh pr edit --title`) to the current winning commit type — the autolabeler re-labels from the new title on the next `synchronize`. (Don't manage labels in this workflow; that's the autolabeler's job.)

---

## Dependabot (for a HA custom integration)

`.github/dependabot.yml` with `commit-message.prefix: "chore"` on each ecosystem (so titles read `chore: bump …` → the autolabeler maps `chore` → patch). Know what it actually buys you:

- **`github-actions`** — the real value. Bumps `actions/checkout`, `setup-python`, action pins across all workflows.
- **`pip`** — points at `requirements.test.txt` / `pyproject`. **Near-useless if those are unpinned** (no version specifier = nothing to bump). Keep it for when something gets pinned, but don't expect PRs.
- **`manifest.json` `requirements` are invisible to Dependabot** — it can't parse the manifest, and the entries are open `>=` ranges (HA installs the latest matching anyway), so there's nothing to *routinely* bump. Raising a `>=` floor is a deliberate safety/feature act, not automation — **unless** you want the floors kept current.

**Keeping `>=` floors current (custom, since Dependabot can't):** a small `scripts/update_manifest_floors.py` (parse manifest requirements, query PyPI `…/pypi/{name}/json` for the latest non-prerelease, raise the floor if newer; `--check` to dry-run) plus a scheduled `update_manifest_floors.yml` (`schedule:` + `workflow_dispatch`) that runs it and — on a change — commits to a branch and pushes, letting `create-dev-pr` open the PR. Don't add a second PR-creator (e.g. `peter-evans/create-pull-request`); it races `create-dev-pr` into duplicate PRs. The floor-bump PR needs **no manifest version bump** under the last-release gate model above.

**Two Dependabot consequences, both covered above:** the **version gate** must compare against the last release and **exempt `dependabot[bot]`** (see the versioning section), and the release notes must **scrub Dependabot's body fluff via `replacers`** while keeping `$BODY` for human detail (see the canonical release-notes pattern in release-drafter — *not* the old "drop `$BODY`" workaround).

---
