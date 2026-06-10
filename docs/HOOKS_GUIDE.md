# Hooks guide

Hooks are the deterministic surface that turns the trust contract into something the agent can't ignore. analysis-kit ships three.

## Tier policy

The default hook policy is **fast on Stop, full on commit**. This is the form that survives in practice — block-always produces hook fatigue and people set `disableAllHooks` within weeks (community evidence: GitHub issues #34713, #9603, #46727; multiple post-mortems).

| Hook | Event | Mode | What it does |
|---|---|---|---|
| `validate-on-stop.sh` | Stop | Fast | Blocks the turn from ending while findings are red (one retry, then yields) |
| `block-unvalidated-commit.sh` | PreToolUse on Bash | Full | Blocks a `git commit` while any finding fails replay |
| `findings-coverage-on-edit.sh` | PostToolUse on edits | Nudge | Adds context reminding Claude to re-validate after editing a compute script |

Fast = ~1 second. Full = up to 30 seconds depending on project size.

## The I/O protocol (get this right)

Claude Code routes a hook's output by **event, exit code, and stream** — the
combination matters, and getting it wrong silently sends a message nowhere.

- **PreToolUse / Stop, block:** `exit 2` and write the reason to **stderr**. Claude
  reads stderr as the feedback. (Do *not* write a `{"decision": ...}` JSON blob to
  stderr — that is not how exit-2 blocking works; stderr is read as plain text.)
- **PreToolUse / Stop, allow:** `exit 0`.
- **PostToolUse, add context for Claude:** `exit 0` and print
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}`
  to **stdout**. Plain stdout text on a PostToolUse exit-0 goes to the *transcript
  only* — Claude never sees it. This is the trap the nudge hook used to fall into.

`block-unvalidated-commit.sh` runs full validate; on red it exits 2 with the
failing checks on stderr (so Claude sees what to fix without re-running). It fails
**closed**: if `jq` or `python3` is missing, a commit is blocked with an
explanation rather than slipping through — but a missing dependency never blocks
non-commit commands.

`validate-on-stop.sh` runs fast validate; on red it exits 2 so Claude sees the
failures before ending the turn. The `stop_hook_active` field in the Stop payload
guards against an infinite loop: if it's already `true` (we're inside a
stop-triggered continuation), the hook yields with exit 0. It fails **open** — if
`jq` is missing it allows the stop, because the safe failure for a Stop hook is
"let it stop", never "loop forever".

`findings-coverage-on-edit.sh` fires on edits to a compute script
(`analysis/NN_*.py` or `analysis/_decisions.py`) and emits an
`additionalContext` nudge to re-validate. Never blocks.

## Bypass surface (an honest limitation)

The commit gate detects `git commit` by pattern-matching the Bash command — it
tolerates `git -C <dir> commit`, `git -c k=v commit`, and collapsed whitespace,
and it ignores mentions inside other commands (`grep "git commit"`,
`git log --grep=commit`). But pattern-matching is not a shell parser: a commit
constructed through `eval`, a shell variable, or a wrapper script can slip past,
and a `cd /other-repo && git commit` is gated against *this* project's findings.
The gate raises the floor; it is not a sandbox. The deliberate, visible escape
hatch is removing the hook from `.claude/settings.json` (reviewable in git).

## What "fast mode" means

`validate.py --fast`:
- Verifies `findings.json` parses.
- Verifies every `code_path` resolves to an existing file.
- Verifies every cited F-NNN in `TRUST_MEMO.md` exists in findings.json.
- Verifies `revision_history` is non-empty for every finding.
- Verifies `OBSERVED`-tagged findings have `measurement_ref`.
- **Does not** re-read raw data or replay any computation.

Full mode adds:
- Reads each finding's `input.sources` (and verifies any pinned `sha256`).
- Applies `reproducibility.filters`.
- Verifies `reproducibility.row_count_after_filter` matches.
- Replays the computation and compares to stored value.

## Disabling

If a hook is wrong, fix it or remove it deliberately. **Do not** add a `--no-verify` shortcut. The escape hatch is editing `.claude/settings.json` to drop the hook — visible in git, reviewable in PRs.

If the agent sets `disableAllHooks: true` autonomously, that's a framework failure — file an issue.

## Common interactions

- **Pre-commit (git's native pre-commit) + analysis-kit hooks:** these are independent. Git's pre-commit fires when the user runs `git commit` directly. analysis-kit's PreToolUse hook fires when *Claude* runs `git commit`. Both can co-exist; keep them doing different jobs (lint/typecheck in pre-commit; finding replay in analysis-kit).
- **Slow validate.py:** if full-mode validate takes >60 seconds, keep the hook on `--fast` and run the full (default-mode) replay in CI rather than on every commit.
- **CI:** `python analysis/validate.py` (full mode is the default — there is no `--full` flag) should run on every PR. Use `--fast` for a quick structural-only gate. Hooks are local; CI is the team-level gate.

## Writing a new hook

1. Drop the script in `.claude/hooks/<name>.sh`.
2. Make it executable (`chmod +x`).
3. Wire it in `.claude/settings.json` — reference it as `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` (not a bare relative path, which won't resolve if Claude was launched from a subdirectory) and set a `timeout`.
4. Document it here.
5. The script reads the tool input from stdin (Claude Code hook spec). Use `jq` to parse — and decide whether a missing `jq` should fail open or closed for *your* hook.
6. Use the right output channel for the event (see "The I/O protocol" above): exit 2 + stderr to block PreToolUse/Stop; `additionalContext` JSON on stdout to feed Claude from PostToolUse.
7. For a Stop hook that can block, read `stop_hook_active` and yield when it's true, or you will create an infinite loop.

## Failure modes

- **Hook hangs:** set a `timeout` in settings.json and keep every hook well under it (<2s fast, <60s full). A timed-out PreToolUse hook is a *non-blocking* failure — i.e. the gate fails open — so don't let the commit hook run close to its timeout.
- **Message goes nowhere:** plain stdout on a PostToolUse exit-0 reaches only the transcript, and stderr on a Stop exit-1 reaches only the user. To reach *Claude*, use exit 2 (block) or `additionalContext`. See "The I/O protocol".
- **Missing `jq`:** decide the failure direction deliberately. The commit gate fails closed (blocks commits, allows other commands); the Stop and nudge hooks fail open.
- **Hook reads from stdin twice:** the input is consumed once. Save it to a variable: `input=$(cat)`.
