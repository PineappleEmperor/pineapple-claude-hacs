# Commit conventions

What a commit subject must look like, why the body stays empty, and what the release
notes are built from. Labels, gates and the release model are `reference/versioning.md`.

- Conventional Commits & Semantic Versioning
- Keep messages short
- No AI-attribution trailers
- Enforce the trailer ban with a `commit-msg` hook — prose alone isn't enough
- Put the narrative in the release, not the commit
- The PR body is for reviewers, and nothing users read
- Red flags — stop

## Conventional Commits & Semantic Versioning

**Commit format:**
```
<type>[(<scope>)][!]: <description>
```

Ten types a PR title may carry: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`. A commit may also be `revert:`; the draft opener retypes
that as `chore:` in the title it builds. A scope is tolerated and never generated. **`!`
is the only breaking marker.**
The labeler, the gate and the release notes read the subject and nothing else, so a
`BREAKING CHANGE:` footer declares a break that nothing acts on and the change ships as
non-breaking; the hook rejects the footer for that reason.

### Keep messages short
Tight imperative subject; **subject-only by default**. Add a body ONLY when the *why* is non-obvious, or for migration notes — never to restate what the diff already shows. Long bodies that narrate the change are noise. Subject in imperative mood, lowercase after the colon, no trailing period.

### No AI-attribution trailers
Don't append `Co-Authored-By: Claude`, tool/session links, or any "generated with…" line to commits — keep the authorship history clean. (If a harness injects such trailers by default, strip them.) A `Co-Authored-By:` for a *real* human collaborator is fine.

### Enforce the trailer ban with a `commit-msg` hook — prose alone isn't enough

⚠️ A coding harness can inject `Co-Authored-By: Claude` / `Claude-Session:` on *every* commit via a standing instruction, which fights this rule turn after turn; the agent keeps "remembering" the harness default over the skill and regresses. The fix is deterministic enforcement at the git layer, not memory. Ship `.githooks/commit-msg` (Conventional Commit subject shape + terse-subject + no-narrative-body + an **editorialising-word** reject + **AI-trailer rejection**), add it to the scaffold's repo-root files, and tell contributors to enable it once per clone in `CLAUDE.md`: `git config core.hooksPath .githooks`.
Body in **`templates/hooks/commit-msg`** — copy it to `.githooks/commit-msg`, `chmod +x`. Don't retype it from this document.

### Put the narrative in the release, not the commit

The human-readable "what changed and why it matters" belongs in the **release notes**, which is where users actually read it. Keep commits terse; write the detail once, in the release description. (GitHub's own `generate_release_notes` is not the mechanism here — the stack has exactly one body writer, and `skill_audit.py` fails a repo that enables a second.)

## The PR body is for reviewers, and nothing users read

**Release notes are generated from commit subjects, never from PR bodies.**
`scripts/release_notes.py` classifies each subject by its own Conventional Commit type and
groups them under Breaking / Features / Fixes / Maintenance / Other, one line each, linking
to the PR it arrived with and ending with a full-changelog compare link. The range it walks
is chosen by `release_drafter.yml`, which measures from the last **full** release rather than
the newest one, so every rc lists the cumulative set instead of just what changed since the
previous rc. This is what surveyed HACS repos do (alexa_media_player, alandtse/tesla, hacs/integration, SonoffLAN,
checked 2026-08-15); none of them nests commits under a PR entry.

**Why not release-drafter's `$CHANGES`.** It categorises each *PR* by its single label, so a
`fix:` commit inside a `feat:`-titled PR is filed under Features and a reader looking for
what was fixed finds no Fixes section. Measured on one session, 3 of 8 merged PRs spanned
more than one commit type, so this is the common case. What release-drafter still owns, and
how the generated body replaces its draft, is `reference/github-actions.md`.

So the body is optional context for reviewers: no job writes it, the draft PR arrives empty,
and writing the changelog into it says the same thing twice in a place users never read.
Which label puts a PR in which release category is `reference/versioning.md`. Note
release-drafter draws the PR body via the GraphQL path; `gh pr edit` can fail on the
Projects-classic deprecation — set title/body via
`gh api -X PATCH repos/{o}/{r}/pulls/{n} -f title=… -F body=@file` instead.

Reasoning, alternatives, verification evidence: those go in the PR **conversation**, where reviewers read them and the notes do not.

| Excuse | Reality |
|---|---|
| "This change is complex, it needs explaining" | Then it needs splitting, or better commit subjects. The subjects are the changelog. |
| "Reviewers need the reasoning" | Reviewers read the conversation. What users get is the commit subjects, so put the change in those. |
| "The verification belongs with the change" | It belongs in a comment. A description is not a lab notebook. |
| "I wrapped it in `<details>` so it's stripped" | The fold is for Dependabot's own output, not a licence to write an essay. |
| "It's only a few paragraphs" | Measured across eight PRs it was 2,728 words, all republished under the repo owner's byline. |

## Red flags — stop

- Typing prose into `gh pr create --body`
- Reaching for `<details>` in a PR description
- A description longer than its diff is interesting
- Explaining *why* anywhere the commit subjects should have said it

**All of these mean: put it in a comment, or fix the commit subjects.**

---
