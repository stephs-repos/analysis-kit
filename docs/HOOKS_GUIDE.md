# Hooks guide

Hooks are the deterministic surface that turns the trust contract into something the agent can't ignore. analysis-kit ships three.

## Tier policy

The default hook policy is **fast on Stop, full on commit**. This is the form that survives in practice — block-always produces hook fatigue and people set `disableAllHooks` within weeks (community evidence: GitHub issues #34713, #9603, #46727; multiple post-mortems).

| Hook | Event | Mode | What it checks |
|---|---|---|---|
| `validate-on-stop.sh` | Stop | Fast | findings.json schema, file existence, no orphan F-NNN refs in TRUST_MEMO |
| `block-unvalidated-commit.sh` | PreToolUse on Bash (`git commit`) | Full | Everything fast does, plus replay every finding |
| `findings-coverage-on-edit.sh` | PostToolUse on Edit/Write | Soft warn | Edited files in `analysis/` should have findings; warns if not |

Fast = ~1 second. Full = up to 30 seconds depending on project size.

## What "block" means

In Claude Code, a PreToolUse hook can return:
- exit 0: allow the tool call
- exit 2 with `{"decision": "block", "reason": "..."}` to stderr: block the tool call

`block-unvalidated-commit.sh` exits 2 if validate.py is red, with a reason string Claude shows the user. The user can override by running git commit manually outside Claude — that's a deliberate hatch.

`validate-on-stop.sh` exits non-zero if validate.py fast-mode is red. Claude reports the failure in-turn but doesn't refuse to stop hard — community evidence shows aggressive Stop-blocking causes false-positive premature-end behaviour.

## What "fast mode" means

`validate.py --fast`:
- Verifies `findings.json` parses.
- Verifies every `code_path` resolves to an existing file.
- Verifies every cited F-NNN in `TRUST_MEMO.md` exists in findings.json.
- Verifies `revision_history` is non-empty for every finding.
- Verifies `OBSERVED`-tagged findings have `measurement_ref`.
- **Does not** re-read raw data or replay any computation.

Full mode adds:
- Reads `data_contract.source` for each finding.
- Applies `data_contract.filters`.
- Verifies `row_count_after_filter` matches.
- Replays the computation and compares to stored value.

## Disabling

If a hook is wrong, fix it or remove it deliberately. **Do not** add a `--no-verify` shortcut. The escape hatch is editing `.claude/settings.json` to drop the hook — visible in git, reviewable in PRs.

If the agent sets `disableAllHooks: true` autonomously, that's a framework failure — file an issue.

## Common interactions

- **Pre-commit (git's native pre-commit) + analysis-kit hooks:** these are independent. Git's pre-commit fires when the user runs `git commit` directly. analysis-kit's PreToolUse hook fires when *Claude* runs `git commit`. Both can co-exist; keep them doing different jobs (lint/typecheck in pre-commit; finding replay in analysis-kit).
- **Slow validate.py:** if full-mode validate takes >60 seconds, split it. Keep replay-cheap checks in fast mode; gate replay-expensive checks behind `validate.py --replay-only` invoked by CI rather than a hook.
- **CI:** `validate.py --full` should run on every PR. Hooks are local; CI is the team-level gate.

## Writing a new hook

1. Drop the script in `.claude/hooks/<name>.sh`.
2. Make it executable (`chmod +x`).
3. Wire it in `.claude/settings.json`.
4. Document it here.
5. The script reads the tool input from stdin (Claude Code hook spec). Use `jq` to parse.
6. Exit 0 to allow, exit 2 with stderr JSON to block.

## Failure modes

- **Hook hangs:** make every hook complete in <2s for fast / <60s for full. If you can't, decompose the work and run the slow part in CI.
- **Hook outputs to stdout:** Claude shows it. Be terse. Use stderr for messages meant for blocking decisions.
- **Hook reads from stdin twice:** the input is consumed once. Save it to a variable: `input=$(cat)`.
