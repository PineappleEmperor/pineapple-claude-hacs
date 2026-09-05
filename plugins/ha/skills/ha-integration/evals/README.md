# ha-integration evals

Regression scenarios for **the skill itself**. Not copied into a scaffolded
integration — `templates/` is what ships; this directory is maintenance.

## Why

Every defect in `docs/ha-integration-change-rationale.md` (repo root, deliberately
outside the plugin) was found the expensive way: a real build (`ha-lego`)
went wrong, or a manual sweep found it months later. Nothing catches the next
drift until it ships. `superpowers:writing-skills` treats skill authoring as
TDD — write the failing scenario, watch an agent fail it, write the guidance,
watch it pass. These are the failing scenarios, kept so a future edit can be
checked against the failures that motivated it.

## How to run one

Each scenario is a markdown file under `scenarios/`. It gives you a fixture, a
prompt, and the pass/fail criteria.

```bash
./make_fixture.sh <scenario-dir>     # builds a throwaway repo, prints its path
```

Then dispatch a **fresh** subagent — a new context, no skill preloaded beyond
what the scenario says to give it — with the scenario's *Prompt* verbatim, its
working directory set to the fixture. Read the transcript against *Pass* /
*Fail*.

**Grading is by reading, not by exit code.** These test judgement under
pressure, and the failure mode is an agent that produces plausible, confident,
wrong work. An automated assertion would mostly measure whether the agent used
the expected words. Read what it actually did.

**Always run the baseline arm too** — the same prompt with the guidance removed.
If the baseline already passes, the scenario is not testing anything and the
guidance it justifies should be cut. One sample per arm lies; run 3–5.

⚠️ **A control must WITHHOLD the guidance explicitly. Hiding files does not.**
This skill is registered, so an agent loads it whether or not you put the
skill-repo checkout out of bounds. The first control run did exactly that, found
the skill anyway, quoted the rule and refused — identical to the treatment arm.
Reported naively it would have produced the opposite conclusion ("the control
refused too, so the guidance does nothing") from a broken experiment.

State it as a constraint in the control prompt:

> Do NOT invoke, read, load, or search for the `ha-integration` skill or any file
> belonging to it. It is unavailable for this task. Work only from your own
> knowledge.

## Scenarios

| # | Scenario | Guards |
|---|---|---|
| 01 | `templates/` unreachable during scaffold | The `ha-lego` failure: agent authors CI from the prose, calls it done |
| 02 | Audit a repo whose workflows were paraphrased | The audit passing 15 hand-written files clean |
| 03 | Write the first test for a scaffolded integration | The pytest prerequisites (`conftest.py`, `asyncio_mode`) |
| 04 | A PR from a fork gets labelled | `pull_request_target` fork support. **Not runnable on a single account**; procedure written out, including the adversarial half that checks no fork code executes |
| 05 | A red check, under pressure | Merging past a failing check. **Baseline observed from a real event, guidance not yet re-tested** |
| 06 | Router selection (KAT) | The router sending a request to the wrong skill, or naming a reference file that does not exist |

## Results

`results/` holds one file per run: date, skill version, arm, verdict against the
scenario's stated criteria, and any findings the agent produced that we had not
planted. Record invalid runs too — `01-control-INVALID.md` is the record of a
broken control, and it is the most instructive file in there.

## Adding one

Add a scenario when a real failure gets past the skill — not for hypotheticals.
Record the *verbatim* rationalisation the agent used; that phrasing is the thing
the next revision has to close, and paraphrasing it loses the loophole.
