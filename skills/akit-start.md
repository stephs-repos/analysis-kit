---
name: akit-start
description: Scaffold a new analysis-kit project. Wraps bootstrap/new-project.sh with a guided flow — asks for tier, runs the bootstrap, and tells the user what to do next. Invoked as /akit-start <project-name>.
---

# /akit-start

Scaffold a new analysis-kit project from the templates.

## Pre-flight

1. Verify the analysis-kit clone is reachable. The install script wrote the kit root into this skill at install time:

   ```
   AKIT_ROOT=__AKIT_ROOT__
   ```

   If `$AKIT_ROOT/bootstrap/new-project.sh` does not exist, tell the user:
   "I can't find the analysis-kit bootstrap script at `$AKIT_ROOT`. Re-run the install script or set the path manually."
   Then stop.

2. Parse the user's invocation:
   - The first argument is the project name (e.g., `customer-churn-2026`). If absent, ask: "what's the project name?"
   - Optional: `--minimum` or `--full`. If neither was supplied, ask: "minimum or full tier? (minimum is the default — adds vignette/Quarto in full)"

3. Resolve the target path. Default: `./<project-name>`. Confirm with the user before proceeding: "I'll create the project at `<absolute path>`. OK?"

4. Verify the target doesn't already exist with content. If it does, stop and tell the user: "`<path>` exists and is non-empty. Pick a different name or remove the directory first."

## Run the bootstrap

5. Run:

   ```bash
   $AKIT_ROOT/bootstrap/new-project.sh <target-path> --<tier> --name "<project-name>" --github-user "<user's github>"
   ```

   Capture the output. If it fails (non-zero exit), show the error and stop.

6. After success, run `cd <target-path>` so the rest of the session is in the new project.

7. Run `python analysis/validate.py --fast` to confirm the scaffold is healthy. Should print "ALL CHECKS PASSED". If it doesn't, something's wrong with the kit — surface the error to the user and stop.

## Hand-off

8. Tell the user:

   ```
   ✓ scaffolded <project-name> at <target-path>

   Next steps:
   1. Drop your raw data files into reference/raw-data/
   2. Drop project context (brief, data dictionary, prior art) into reference/ directly
      — see reference/README.md for the convention
   3. When the reference materials are in place, run /akit-fill
      to populate MUST_CUSTOMIZE markers across the project

   Unsure what to do at any point? Run /akit-next — it detects the
   project's phase and tells you the single next step.
   ```

9. Do NOT proceed to fill markers automatically. The user needs to drop reference materials first; without them, `/akit-fill` would have nothing to draft from. Wait for the user to invoke `/akit-fill` themselves.

## Critical rules

- Never overwrite an existing project. The bootstrap script enforces this; trust its check.
- Never invoke `/akit-fill` from this skill. The two steps must be separate so the user has time to populate `reference/` between them.
- Never run `pip install -r requirements.txt` automatically. The user may want to use a virtual env or dev container; ask before installing dependencies.
