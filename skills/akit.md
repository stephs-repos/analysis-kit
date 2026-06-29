---
name: akit
description: Index of the analysis-kit skill set. Run this when the user asks "how do I use analysis-kit?" or invokes /akit with no args. Lists the workflow skills and explains when each is used.
---

# /akit

Index skill for the analysis-kit workflow. The skill set is deliberately small — three focused workflow skills (`/akit-start`, `/akit-fill`, `/akit-finding`) plus `/akit-next`, a resumable conductor that detects where you are and routes you to the next step. There is **no skill that does everything automatically**: every step that could ship a wrong claim requires explicit user accept — `/akit-next` routes and offers, it never decides.

## The workflow

```
  1. /akit-start <project-name>      scaffold a new analysis-kit project
                ↓
       (user drops raw data into reference/raw-data/
        and project context into reference/ directly)
                ↓
  2. /akit-fill                       walk through MUST_CUSTOMIZE markers,
                                      drafting from @reference/, prompting
                                      accept/edit/skip on each
                ↓
       (initial setup is complete; analysis can begin)
                ↓
  3. /akit-finding "<hypothesis>"     register one finding with code path,
                                      input + reproducibility, caveats,
                                      counterfactual tag — workhorse, continuous
```

## The skills

| Skill | When to invoke |
|---|---|
| `/akit-start <name>` | Once per new project. Scaffolds a fresh analysis-kit project. |
| `/akit-fill` | Once after you've dropped reference materials. Fills in `MUST_CUSTOMIZE` markers across CLAUDE.md, live-docs, and memory entries. |
| `/akit-finding "..."` | Continuously. Each time you have a concrete claim to register, run this with a one-line hypothesis. |
| `/akit-next` | Anytime you're unsure of the next step, or returning after a break. Detects the project's phase and routes you to the single next action. |

## What's deliberately not a skill

- **Validate.** `python analysis/validate.py` is one command and the hooks already run it on Stop and commit. No skill needed.
- **Profile data.** `python analysis/01_inspect_raw.py` is one command. After it runs, use `/akit-finding` for each finding you want to register.
- **DR-NNN decisions.** Auto-proposing data-cleaning rules from raw data is high false-positive. For now, surface these in conversation; future versions may add `/akit-decide`.
- **Vignette drafting.** Better as a freeform Claude prompt than a skill, until the patterns crystalize.

## When the user asks "how do I start?"

Tell them:

1. Run `/akit-start <project-name>` to scaffold.
2. Drop raw data into `reference/raw-data/` and project context (brief, dictionary, prior art) into `reference/` directly.
3. Run `/akit-fill` to populate `MUST_CUSTOMIZE` markers from the reference materials.
4. Inspect the data with `python analysis/01_inspect_raw.py`.

…or, at any point, just run `/akit-next` — it detects where the project is and tells the user the single next action. It's the lowest-friction entry point for someone who doesn't want to memorise the sequence.
5. As claims emerge, run `/akit-finding "<one-line hypothesis>"` for each one.

## Project detection

Every skill except `/akit-start` requires the cwd to be inside an analysis-kit project. The detection check is: **`analysis-kit.json` exists in the cwd or a parent**. If not, the skill should bail clearly with: "this doesn't look like an analysis-kit project. Run `/akit-start` first, or `cd` to a project root."
