# Setting the repository up on GitHub

One-time setup that lives in GitHub's settings, not in the repo: the release token, the
required checks, the dependency graph and the supply-chain guards. Every item here is a
setting no file in the repo can carry, and each one fails quietly until the first CI run.
`scripts/bootstrap_repo.sh` does most of it in one command.

Copying the templates, and what may be changed in a copy, is `reference/github-actions.md`.

- `RELEASE_TOKEN` — set this up before the first release
- What the grant allows
- Make the checks required — a workflow is not a gate until it can block a merge
- The eight required contexts, and what must never be required
- A cancelled check blocks; a skipped one does not
- A matrix renames the check
- `Dependency review` needs the dependency graph enabled
- Bypass configuration
- For AI sessions
- Supply chain

## `RELEASE_TOKEN` — set this up before the first release

⚠️ **One secret, once per repo, or `auto_draft_pr.yml` cannot open a PR that checks can run
on.** GitHub suppresses workflow events caused by `GITHUB_TOKEN`, so a PR opened with it
fires no `pull_request_target`: no checks run, the required ones never report, and the PR is
permanently unmergeable. That is why `create-dev-pr.yml` was removed. Without the secret the
opener does not fall back to `GITHUB_TOKEN` — it prints a `::warning::` and exits 0, so the
run is green with an annotation and no PR appears. Nothing red tells you it is missing; `skill_audit.py` is what
fails a repo that ships the opener with neither the secret nor the App pair set.

The **release** path needs no token: both the full release and its next rc are kept as
drafts, and publishing a draft is a human action, so its events fire normally.

**Two ways to provide it. Pick by how many repos you maintain.**

**A GitHub App (preferred for more than one repo).** Installed once, covers every repo you
install it on, mints tokens per run that expire in an hour, and survives you rotating your
own credentials. Events it causes do trigger workflows, which is the whole requirement.

1. github.com → Settings → Developer settings → GitHub Apps → **New GitHub App**
2. Name it (e.g. `<you>-release-bot`), untick **Webhook → Active**
3. **Repository permissions**: `Contents: Read and write`, plus `Pull requests: Read and
   write` if you use `auto_draft_pr.yml` — nothing else
4. Create it, note the **App ID**, then **Generate a private key** (downloads a `.pem`)
5. Install it: the App's page → **Install App** → pick the repos
6. In each repo: Settings → **Secrets and variables** → **Actions** → **Secrets** tab →
   **New repository secret** → `APP_ID` (the numeric ID), then again for `APP_PRIVATE_KEY`
   (the whole `.pem` contents, including the BEGIN/END lines) → **Add secret**
7. In `auto_draft_pr.yml`, mint the token before the step that needs it:
   ```yaml
   # Pin the SHA, and give the comment a major.minor — `check_action_pins` rejects
   # both a bare tag and a comment reading just `# v2`.
   - uses: actions/create-github-app-token@<sha>  # v2.0.0
     id: app-token
     with:
       app-id: ${{ secrets.APP_ID }}
       private-key: ${{ secrets.APP_PRIVATE_KEY }}
   # then use ${{ steps.app-token.outputs.token }} wherever RELEASE_TOKEN appears
   ```

**A fine-grained PAT (fine for a single repo).** Simpler, but tied to your account and it
expires on a date you have to remember.

1. github.com → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → **Generate new token**
2. **Resource owner**: your account · **Repository access**: Only select repositories →
   this repo
3. **Repository permissions**: `Contents: Read and write`, plus `Pull requests: Read and
   write` if you use `auto_draft_pr.yml` — nothing else. (`Metadata: Read` is added
   automatically and cannot be removed.)
4. **Expiration**: 90 days or less
5. **Generate token**, copy the `github_pat_…` value — it is shown once
6. Repo → **Settings** → **Secrets and variables** → **Actions** → **Secrets** tab →
   **New repository secret** → Name `RELEASE_TOKEN`, paste into **Secret** → **Add secret**

### What the grant allows

`Contents: write` covers creating releases, tags and commits in the repos it is scoped to.
Adding `Pull requests: write` lets it open the draft PR — and, unavoidably, merge one, since
GitHub does not separate those. Neither permission can edit rulesets or branch protection,
change repository settings, or reach any repo outside its scope, so a required-checks ruleset
still holds.

Without `Pull requests: write`, `auto_draft_pr.yml` fails with
`Resource not accessible by personal access token (repository.pullRequests)`. That matters
because this token exists to *trigger* workflows — anything it can do, a workflow it starts
can do too.

**Rotating.** Paste a new value into the same secret; nothing else changes. An App's private
key is rotated the same way, and its tokens expire hourly regardless.

## Make the checks required — a workflow is not a gate until it can block a merge

GitHub will let a PR merge with every workflow red, so until a ruleset requires them the
stack is decorative. Copy `templates/ruleset.json` to the repo root and apply it once:

```bash
gh api -X POST repos/<owner>/<repo>/rulesets --input ruleset.json
```

It requires the eight job-name contexts the templates produce, and keeps deletions and
force-pushes blocked. `skill_audit.py` fails a repo whose default branch has no required
checks — **but only where it can ask GitHub.** With `gh` missing, unauthenticated, or holding
a token without `Administration: read`, that check and the `RELEASE_TOKEN` one downgrade to a
warning reading `NOT CHECKED, not passed`, and the audit still reports green overall. A clean
run in a sandbox or a token-limited CI is not evidence the ruleset exists; read the warnings.

**`scripts/bootstrap_repo.sh` does all of this once**, from the repo root after the first
push: description, topics, issues, the dependency graph, `core.hooksPath`, the ruleset (only
if `ruleset.json` is at the repo root — it skips otherwise), and the `RELEASE_TOKEN` secret,
prompted rather than passed as an argument.

```bash
bash scripts/bootstrap_repo.sh "One-line description of the integration"
```

### The eight required contexts, and what must never be required

A *check* runs on a pull request and can be required, so a red one blocks the merge. The
eight in `ruleset.json`: `CC labelling`, `CC label validation`, `CC title validation`,
`HACS validation`, `Hassfest manifest validation`, `Ruff, Pyright and Pytest`,
`ha-integration conformance check`, and `Dependency review`.

The first three all concern the label and are **not** redundant — each reports a failure the
other two cannot. Why, and what each catches, is `reference/github-actions.md`.

There is no `Version validation` context: the job was removed. The release tag owns the
version, so no PR carries a bump and there was nothing left for it to check. The version the
PR's labels imply is now written into `CC label validation`'s job summary, which is the job
that already knows the label is right.

Everything else — `Auto draft PR`, `Auto release zip`, `Auto draft releases` — is process
automation firing on pushes and releases. Not a weaker check: not a check at all, and
requiring one blocks every PR on a context that never reports.

Two ways to get this wrong, both of which block every PR permanently:

- **A context the repo does not produce.** Each of the eight comes from a canonical workflow,
  and `skill_audit.py` fails a repo missing any of them — so in a conforming repo the honest
  fix is to add the missing workflow, not to drop the context. Dropping is for a repo that has
  deliberately left the canonical set (no `quality_audit.yml`, no `dependency_review.yml`);
  drop the matching context or PRs wait forever for a check that never runs.
- **A path-filtered workflow.** `Panel type-check and tests` from `panel_bundle.yml` is absent
  from the shipped ruleset for this reason: it triggers only on panel changes, so on a
  Python-only PR it never reports and a required context would wait forever. Do not require
  it. What ships to users is protected instead by `release.yml`, which rebuilds the bundle
  before packing the zip.

### A cancelled check blocks; a skipped one does not

GitHub is explicit that a skipped job satisfies a required check, so job-level `if:` guards
are fine. Cancelled runs are the hazard. Trigger on `labeled`/`unlabeled` with
`cancel-in-progress`, and a bot applying several labels at once starts a run per label; the
concurrency group cancels all but the last, and those cancelled check-runs make the rollup
`FAILURE` with nothing broken. The PR then reports `mergeable: MERGEABLE` and still cannot
merge. Drop those two trigger types — the in-workflow autolabeler cannot fire them anyway,
because the default token suppresses events it causes.

Confirmed by re-running a single cancelled run: the rollup went from `FAILURE` to `SUCCESS`
with nothing else changed.

### A matrix renames the check

GitHub names a matrix job's check-run `<job name> (<value>)`. The template's
`python_validate.yml` job is named `Ruff, Pyright and Pytest`, so giving it a matrix would
make it report as `Ruff, Pyright and Pytest (3.14)` while the ruleset waits on the bare name.
The template therefore pins a scalar `python-version` and has no matrix. Either drop a
single-value matrix or put the suffixed name in the ruleset; never assume the context equals
the job name.

### `Dependency review` needs the dependency graph enabled

Settings → Advanced Security. With it off the action does not skip — it fails, so the check
is red on every PR forever. Verified on a test repo: seven workflows green, this one red
alone. `bootstrap_repo.sh` enables it, and says so loudly if it cannot.

### Bypass configuration

A ruleset granting admins `bypass_mode: always` does not constrain anyone holding admin; the
push reports `Bypassed rule violations` and proceeds, so the list stays empty. If you must
overrule — and *Merge discipline* in `reference/discipline.md` gives exactly one sanctioned
reason, proven by diff — disable the ruleset, merge, and re-enable it. That is deliberate,
reversible, and leaves an audit-log entry.

### For AI sessions

An agent running with your `gh` credentials merges exactly as you do, and bypass entries are
evaluated by actor, so any bypass you hold it inherits. Two things make that silent: a broad
allow-rule such as `Bash(gh pr *)` pre-approves `gh pr merge` with no prompt, and an agent
with admin can lift any rule it can see. Narrow the allow-rule to read-only verbs
(`gh pr view`, `gh pr list`), and give the agent a credential without **Administration** if it
should not edit rulesets or force-push. A restriction the agent can lift is friction, not a
limit.

## Supply chain

Two cheap workflows ship with the stack. `dependency_review.yml` fails a PR that adds a
dependency carrying a **high-severity** advisory, reading the PR's own diff; lower severities
are deliberately not gated, because Dependabot raises those on its own schedule.
`issue_stale.yml` labels issues and PRs untouched for 60 days and **never closes them**
(`days-before-close: -1`) — a closed report is a lost report.

Actions are pinned by commit SHA with the version in a trailing comment, because a tag is
mutable: whoever owns the action can repoint it at new code, which then runs with the
workflow's token. `skill_audit.py` fails a workflow that uses a bare tag, or a SHA with
nothing saying what it is.

How Dependabot maintains those pins, and why re-copying a template can move one backwards, is
`reference/dependabot.md`.
