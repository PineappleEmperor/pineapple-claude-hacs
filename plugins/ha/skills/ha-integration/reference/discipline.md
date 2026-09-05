# Commit, PR and merge discipline

What to do when a check is red, and what to do before naming a root cause. Neither has an
artefact that can enforce it. Commit and PR-body format is `reference/commits.md`.

- Merge discipline — never merge a red check
- One exception, and it is narrow
- The exception gets misapplied
- Red flags — stop
- Debugging discipline

## Merge discipline — never merge a red check

**A failing check is the gate working. Merging past it is not a judgement call.**

Violating the letter of this rule is violating the spirit of it. The gate stack in this skill exists to stop bad merges; an agent that reasons its way past a red check has removed the only thing standing between a mistake and `main`.

### One exception, and it is narrow

A `pull_request_target` workflow loads its definition from the **base** branch, so a PR fixing that workflow is always checked by the broken copy and can never go green on its own. That is the only sanctioned case. It covers **one job, on one PR, whose own definition the PR changes**. To use it you must first prove it with a diff (`git show origin/main:.github/workflows/pr-checks.yml` against the branch's), say in the PR that the failure is the bug being fixed, and verify on the next PR.

| Excuse | Reality |
|---|---|
| "I understand why it's red" | Understanding a failure is a reason to fix it, not to merge it. |
| "The content is correct, only the check is wrong" | Then fix the check. A wrong check is a defect, not an exemption. |
| "It's the `pull_request_target` self-validation case" | Prove it with the diff, on that job, on that PR. If you did not check, it is not that case. |
| "I merged past a red check earlier for a good reason" | That merge carried its own proof. This one needs its own. Precedent is not evidence. |
| "The version/label/content is right anyway" | The gate said otherwise. It is reporting what it can see; if it is wrong about that, say why in writing before merging. |
| "It's only advisory, GitHub let me" | Advisory means GitHub will not stop you, not that the check is wrong — a red check that is merely not required *yet* is still reporting a real failure. Read the log. Which checks are required, and why, is `reference/github-setup.md`. |
| "Re-running it would waste minutes" | Minutes against a bad merge on `main`. |

### The exception gets misapplied

Applied once legitimately, it was reused hours later on a PR it did not cover: the version gate had failed correctly because the PR carried no label, and the merge went through with the failure undiagnosed. Re-derive the diff every time before claiming it.

## Red flags — stop

- About to run `gh pr merge` while any check is red
- Diagnosing a failure **after** merging rather than before
- Reusing a previous exception without re-deriving why it applies
- Reaching for `--admin`, `--force`, or a `bypass_actors` entry to get a merge through
- Telling yourself the failure is "unrelated" without having read the log

**All of these mean the same thing: stop, read the log, then fix it or explain in writing.**

---

## Debugging discipline

- **Trace before naming a cause** — grep the path (publish → subscribe → handler), confirm in code; a pre-trace hunch is a guess, not the diagnosis.
- **Suspect the fan-out first** when an action hits more devices than it should — the service-call shape that causes it is in `reference/patterns.md`.

---
