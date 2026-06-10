---
name: akit-fill
description: Walk through MUST_CUSTOMIZE markers in an analysis-kit project. Draft content for each from data + reference materials, prompting the user to accept/edit/skip on every marker. Never auto-applies. Invoked as /akit-fill.
---

# /akit-fill

Walk through every `{{MUST_CUSTOMIZE — instructions...}}` marker in the project, drafting content grounded in the reference materials, and prompting the user to accept/edit/skip on each one.

This is the highest-stakes skill in the set: the content set here propagates into every downstream decision. Follow the procedure exactly. Do not skip steps. Do not batch-accept.

## Pre-flight

1. Confirm the cwd is an analysis-kit project: `analysis-kit.json` must exist. If not, stop and tell the user:
   "this doesn't look like an analysis-kit project. Run `/akit-start <name>` first, or `cd` to a project root."

2. The marker-scanner lives in the analysis-kit clone, not in the scaffolded project. Resolve its path and run it against the current project:

   ```bash
   AKIT_ROOT=__AKIT_ROOT__
   bash "$AKIT_ROOT/bootstrap/check-must-customize.sh" .
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

5. For each file in the check-must-customize output, in this order (most important first):

   1. `CLAUDE.md` — sets project goal and audience
   2. `memory/project_overview.md` — same context, agent-facing
   3. `memory/stakeholder_stance.md` — how the audience views the work
   4. `live-docs/TRUST_MEMO.md` — example placeholders only; will be filled with real findings later
   5. `live-docs/DATA_PROFILE.md` — populated by 02_profile.py; markers are usually placeholders for narrative
   6. `live-docs/DECISIONS.md` — leave as-is for now; `/akit-finding` will surface DR-NNN decisions as they emerge
   7. `live-docs/ANALYSIS_BACKLOG.md` — propose A-NNN entries from the brief
   8. `live-docs/TOOLING.md` — fill in if the brief specifies tools
   9. `live-docs/METHODOLOGY_LOG.md` — usually leave the placeholder; this fills in over time
   10. `memory/data_quality_caveats.md` — leave for now; populates after profiling
   11. `analysis/_decisions.py`, `analysis/schemas.py`, `analysis/02_profile.py`, `analysis/01_inspect_raw.py` — **SKIP in this pass.** These are stub functions; their content depends on the data and on DR-NNN decisions. They get filled in by `/akit-finding` and through normal analysis work.

6. For each `{{MUST_CUSTOMIZE — instruction text}}` block in a file you're processing:

   a. Show the user:
      - File and approximate line number
      - The inline instruction text verbatim (this is your brief)

   b. Draft a proposal that satisfies the inline instruction, grounded in the reference materials. Cite the source: "from `reference/project-brief.pdf` p2" or "inferred from `reference/data-dictionary.md` section 3."

   c. If the reference materials don't say enough to draft, say so plainly: "I can't draft this from what's in `reference/` — what would you say?" Don't fabricate. A concrete "I don't know" is better than a confidently-wrong placeholder.

   d. Ask: "Accept (a), edit (e), or skip (s)?"

   e. On `a`: replace the entire `{{MUST_CUSTOMIZE — ...}}` marker with the drafted text using the Edit tool.
      On `e`: take the user's text verbatim, replace the marker with it.
      On `s`: leave the marker untouched. Note the file/location in a "skipped" list.

7. After processing all files (skipping the `analysis/` ones per step 5), re-run `bash "$AKIT_ROOT/bootstrap/check-must-customize.sh" .` and report:

   - X markers filled
   - Y skipped (list locations so the user can return to them)
   - Z remaining (should match Y if you followed the procedure correctly)

## Hand-off

8. Tell the user:

   ```
   ✓ MUST_CUSTOMIZE walk-through complete.
     X markers filled, Y skipped (in: <files>)
     <N> markers in analysis/ stub files remain — those get filled by
     /akit-finding as you register findings.

   Next steps:
   - Inspect the data: python analysis/01_inspect_raw.py
   - Register your first finding: /akit-finding "<one-line hypothesis>"
   ```

## Critical rules

- **Never accept-all silently.** Each marker is a separate prompt. The friction is the value.
- **Never fabricate content the reference materials don't support.** "Stakeholder is the leadership team" without a brief that says so is a hallucination, even if it sounds plausible.
- **Never edit `analysis/` files in this pass.** Their content depends on the data and on DR-NNN decisions that haven't been made yet. `/akit-finding` handles them.
- **If the user gets impatient and says "just fill them all in,"** push back: "I can do that, but the markers are designed to surface project-specific decisions. Skipping the review step usually means the project ships with shallow context that compounds in later analyses. Want me to do it anyway?"
