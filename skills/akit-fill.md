---
name: akit-fill
description: Walk through MUST_CUSTOMIZE markers in an analysis-kit project. Draft content for each from data + reference materials, prompting the user to accept/edit/skip on every marker. Never auto-applies. Invoked as /akit-fill.
---

# /akit-fill

Walk through every `MUST_CUSTOMIZE` marker (a double-brace placeholder carrying inline instructions) in the project, drafting content grounded in the reference materials, and prompting the user to accept/edit/skip on each one.

This is the highest-stakes skill in the set: the content set here propagates into every downstream decision. Follow the procedure exactly. Do not skip steps. Do not batch-accept.

## Pre-flight

1. Confirm the cwd is an analysis-kit project: `analysis-kit.json` must exist. If not, stop and tell the user:
   "this doesn't look like an analysis-kit project. Run `/akit-start <name>` first, or `cd` to a project root."

2. Resolve the marker-scanner and run it against the current project — prefer the copy shipped inside the scaffold, fall back to the analysis-kit clone:

   ```bash
   SCAN=".claude/akit/check-must-customize.sh"
   [ -f "$SCAN" ] || SCAN="__AKIT_ROOT__/bootstrap/check-must-customize.sh"
   bash "$SCAN" .
   ```

   (`__AKIT_ROOT__` is substituted with the absolute path to the kit when the skill is installed.) Capture the file list.

3. If 0 markers remain, tell the user "nothing to fill; you're set" and stop.

4. **Critical context check.** Inspect what's in `reference/`:
   - `reference/raw-data/` — list filenames; don't load contents yet
   - `reference/` directly — read every text/markdown file in full; for PDFs, note the filename and tell the user you can read text-extracted content if they extract it

   If `reference/` contains *only* the README.md (no actual project context), STOP and tell the user:
   "I need project context first. Drop a brief, data dictionary, or scope note into `reference/` (alongside `raw-data/`, not inside it) and re-run `/akit-fill`. Without context I'd be drafting from thin air."

   Don't proceed without reference content. Drafting MUST_CUSTOMIZE markers from a blank slate produces generic placeholder text that defeats the marker's purpose.

## The walk-through

5. For each file in the check-must-customize output, in this order. The order is load-bearing: `project_overview.md` is the **single source** for project context, and two later markers are distillations of it.

   1. `memory/project_overview.md` — THE source: goal, audience, deliverable, timeline, stakeholders, scope. Draft it fully from `reference/`; this is the highest-stakes accept of the walk-through.
   2. `CLAUDE.md` — the goal paragraph: distill it from what was just accepted in `project_overview.md` (agent-facing, one paragraph). Cite the overview as the source.
   3. `README.md` — the project description: another one-paragraph distillation of `project_overview.md` (public-facing).
   4. `memory/stakeholder_stance.md` — how the audience views the work. Different source: a stakeholder conversation or the brief's framing notes, not the overview. If neither exists yet, offer skip.
   5. `memory/data_quality_caveats.md` — seed caveats known *before* first data contact (stated collection quirks, known suppression rules). If none are known, offer skip; profiling will populate it.
   6. `live-docs/DATA_PROFILE.md` — the raw-data inventory (file, shape, source, snapshot date); the narrative refines after `02_profile.py` runs.

   That's the whole setup surface. `FIRST_ENTRY` stubs elsewhere (live-docs, `analysis/*.py`) are lifecycle placeholders — the first DR-NNN, A-NNN, or methodology entry lands there during analysis. They are not this skill's job and are invisible to the scanner.

6. For each `MUST_CUSTOMIZE` block (double-brace marker with instruction text) in a file you're processing:

   a. Show the user:
      - File and approximate line number
      - The inline instruction text verbatim (this is your brief)

   b. Draft a proposal that satisfies the inline instruction, grounded in the reference materials. Cite the source: "from `reference/project-brief.pdf` p2" or "inferred from `reference/data-dictionary.md` section 3."

   c. If the reference materials don't say enough to draft, say so plainly: "I can't draft this from what's in `reference/` — what would you say?" Don't fabricate. A concrete "I don't know" is better than a confidently-wrong placeholder.

   d. Ask: "Accept (a), edit (e), or skip (s)?"

   e. On `a`: replace the entire marker — double-braces included — with the drafted text using the Edit tool.
      On `e`: take the user's text verbatim, replace the marker with it.
      On `s`: leave the marker untouched. Note the file/location in a "skipped" list.

7. After processing all files (skipping the `analysis/` ones per step 5), re-run the scanner from step 2 (`bash "$SCAN" .`) and report:

   - X markers filled
   - Y skipped (list locations so the user can return to them)
   - Z remaining (should match Y if you followed the procedure correctly)

## Hand-off

8. Tell the user:

   ```
   ✓ MUST_CUSTOMIZE walk-through complete.
     X markers filled, Y skipped (in: <files>)
     (FIRST_ENTRY stubs in live-docs and analysis/ fill themselves during
     analysis — first decision, first finding, first log entry.)

   Next steps:
   - Inspect the data: python analysis/01_inspect_raw.py
   - Register your first finding: /akit-finding "<one-line hypothesis>"
   ```

## Critical rules

- **Never accept-all silently.** Each marker is a separate prompt. The friction is the value.
- **Never fabricate content the reference materials don't support.** "Stakeholder is the leadership team" without a brief that says so is a hallucination, even if it sounds plausible.
- **Never edit `analysis/` files or `FIRST_ENTRY` stubs in this pass.** Their content depends on the data and on DR-NNN decisions that haven't been made yet. `/akit-finding` and normal analysis work handle them.
- **Fill `memory/project_overview.md` before its distillations.** If the user asks to do CLAUDE.md or README first, explain the order: one source, two derivations — reversing it reintroduces the drift the order exists to prevent.
- **If the user gets impatient and says "just fill them all in,"** push back: "I can do that, but the markers are designed to surface project-specific decisions. Skipping the review step usually means the project ships with shallow context that compounds in later analyses. Want me to do it anyway?"
