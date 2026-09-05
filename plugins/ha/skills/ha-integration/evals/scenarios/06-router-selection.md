# 06 — Router selection (KAT)

Known-answer test for the split introduced when SKILL.md became a router: does an agent
reach the right skill, and then the right reference file, without reading everything?

## Setup

No fixture. The agent needs read access to `plugins/ha/skills/` — all three skills.

## Prompt

> For EACH request below, decide which single skill you would load, then open that
> skill's SKILL.md and state exactly which reference file you would read next before
> doing any work. Do not do the work.
>
> A. "My HA log has 4000 errors since the restart last night — what's actually wrong?"
> B. "Add a reconfigure flow so users can change the host without deleting the entry."
> C. "The panel I serve looks wrong in dark mode — tiny headings, hardcoded colours."
> D. "Set up the release process for my new integration repo."
> E. "Write a test that the config entry sets up successfully."
>
> Report a table: request → skill → next reference file → the sentence that led you
> there. Then name any request where routing was ambiguous or you had to guess.

## Pass

| Request | Skill | What to read next |
|---|---|---|
| A | `ha-triage` | the skill file itself; no `reference/` layer in this package |
| B | `ha-integration` | `reference/patterns.md` |
| C | `ha-panel-design` | the skill file itself, plus the Material 3 / HA theming sources it names |
| D | `ha-integration` | `reference/github-setup.md`, then `reference/versioning.md` |
| E | `ha-integration` | `reference/testing.md` |

Each answer must cite a sentence from the skill, not an inference. **An answer reached
"by elimination" is a routing failure even when the destination is right** — it means the
router did not say it, and the next reader may eliminate differently.

⚠️ **"No `reference/` directory" is not "nothing else to read".** `ha-triage` and
`ha-panel-design` carry no reference layer *in the package*, but both cite authoritative
external sources (Material 3, the HA frontend theming docs, the companion-app docs, HA core)
that the task still requires. An answer that treats a single-file skill as self-contained is
a fail: the skill is where the guidance lives, not where the current state of HA lives.

**E is the deliberate edge case.** Testing rules used to sit in `patterns.md` and moved to
`testing.md` when the skill split; the mode table is the only thing that now distinguishes
them. An answer of `patterns.md` means the router's Test row was not read.

## Fail

Any request routed to a skill whose frontmatter disclaims it; any reference file named
that does not exist; reading more than three reference files to answer.
