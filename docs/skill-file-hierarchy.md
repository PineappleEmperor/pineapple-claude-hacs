# File hierarchy for the ha-integration skill

Repo-local. Decides which file owns which topic, so a fact has one home and every other
file points at it. Derived by counting where each topic is actually discussed, then
resolving each conflict deliberately — not by guessing intent.

## The rule

**A file owns a topic when it is the file a reader opens *for that task*.** Not the file
that mentions it most, and not the file where it is most interesting. Everything else
links.

Three tiers:

1. **SKILL.md** — routes. Owns nothing except the mode table and the invariants that cause
   damage when missed. Any fact stated here is stated *only* here.
2. **Task files** — one per trigger. Own their topic outright.
3. **Fact files** (`freshness.md`) — own values that rot, with dates and re-derivation
   commands. Task files cite them; they never restate the values.

## Ownership

| Topic | Owner | Why that file, and who defers |
|---|---|---|
| version model, labels, semver | `versioning.md` | The reader is cutting or gating a release. `commits.md`, `scaffold.md`, `audit.md` link. |
| commit subjects, PR body | `commits.md` | The reader is writing a commit. `discipline.md` keeps the *behaviour* (what to do under pressure), not the format. |
| what the release notes are built from | `commits.md` | It is a consequence of commit discipline. `github-actions.md` describes the workflow that runs it; `versioning.md` links. |
| repo setup on GitHub: token, required checks, ruleset, dependency graph | `github-setup.md` | The reader is configuring a repo. `discipline.md` and `versioning.md` link. |
| workflow contracts — what each must do and must not | `github-actions.md` | The reader is reviewing a workflow. Owns template fidelity, since that is a workflow-review concern. |
| PR openers | `github-actions.md` | It is a workflow contract. `github-setup.md` owns only the *token* the opener needs. |
| merge under a red check, and tracing before naming a root cause | `discipline.md` | Two behavioural rules with no artefact of their own. Everything about *format* left for `commits.md`; ruleset config is `github-setup.md`. |
| test harness prerequisites, mocking | `testing.md` | The reader is writing a test. `scaffold.md` lists the files and links here for why. |
| code patterns, typing, file structure | `patterns.md` | The canonical lookup for code inside `custom_components/`: pattern → rule → copyable snippet. Other files cite it; none restate it. |
| building a panel-serving integration — registration, the committed bundle, staleness, the frontend pin, websocket backing | `panels.md` | The reader is building or fixing a panel integration. `patterns.md` states the general async-setup race rule and points here for the panel code. |
| quality scale rules and evidence | `quality-scale.md` | The reader is claiming a tier. |
| Dependabot: ecosystems, grouping, floors, exemption | `dependabot.md` | The reader is configuring or debugging Dependabot. `versioning.md` and `github-setup.md` link. |
| scaffolding: what to ask, what to generate | `scaffold.md` | The reader is starting a repo. |
| audit procedure — the judgement items | `audit.md` | The reader is auditing. Owns no facts of its own; it cites the owners. |
| values that rot | `freshness.md` | Dated, with a re-derivation command per row. |

## Conflicts found, and how each was resolved

| Topic | Split | Resolution |
|---|---|---|
| panel | `panels.md` 28 · `patterns.md` 23 | panels.md owns delivery; patterns.md keeps the parallel-setup race only |
| Dependabot | 4 files, 8/8/7/3 | dependabot.md owns; the other three link |
| merge rule | `discipline.md` 6 · `github-setup.md` 6 | discipline.md owns the rule; github-setup.md owns the ruleset config |
| commit subjects | `commits.md` 10 · `discipline.md` 7 | commits.md owns format; discipline.md owns behaviour |
| labels | `versioning.md` 16 · `github-actions.md` 8 | versioning.md owns the mapping; github-actions.md owns the job that applies it |
| test harness | `testing.md` 10 · `scaffold.md` 5 | testing.md owns; scaffold.md lists the files and links |

## Why not enforce this with a checker

Tried, reverted. A phrase deny-list is unbounded — "bumped manually" slipped past a list
containing "bump the manifest". Ownership-by-keyword flags legitimate mentions and cannot
tell a restatement from a pointer without reading. The hierarchy is a decision to be
applied by whoever edits, checked in review, not a regex.
