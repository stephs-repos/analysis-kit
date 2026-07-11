"""
report.py — generate a self-contained HTML status report for this analysis.

What it answers, at a glance and per finding: what has this analysis produced,
what decisions/caveats/backlog question sit behind each statistic, and — most
importantly — is anything OUT OF SYNC and what to do about it.

It is a DERIVED VIEW: it re-runs the trust machinery (validate.py) in-process
every time, so regenerate it (`make report`) to trust it. Output is written to
analysis/output/report.html, which is gitignored (the `*.html` rule) — do not
commit it as a source of truth.

Not a findings-producing step: named without a NN_ prefix so `make findings`
(which globs analysis/[0-9][0-9]_*.py) never runs it.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from analysis import ...` works on a direct run

from analysis import validate  # noqa: E402
from analysis._findings import _load  # noqa: E402

OUT = ROOT / "analysis" / "output" / "report.html"
DECISIONS_MD = ROOT / "live-docs" / "DECISIONS.md"
TRUST_MEMO_MD = ROOT / "live-docs" / "TRUST_MEMO.md"
CAVEATS_MD = ROOT / "memory" / "data_quality_caveats.md"
BACKLOG_MD = ROOT / "live-docs" / "ANALYSIS_BACKLOG.md"

esc = html.escape


def project_name() -> str:
    try:
        return json.loads((ROOT / "analysis-kit.json").read_text()).get("project_name") or "project"
    except Exception:
        return "project"


# ── consume validate.py in-process ───────────────────────────────────────────

def gather_validation(findings: list[dict]):
    """Return (per_finding{fid:(ok,msg)}, global_failures, global_warnings).

    Hazards handled: validate.failures/warnings_ are module lists that accumulate
    (clear + snapshot); mode-carrying checks are called with fast=False so a
    desync is failure-severity; import decisions once. replay_finding is called
    directly (not run_replay) so per-finding results stay out of the global
    snapshot. check_* print via ok/fail/warn — suppress that stdout.
    """
    dec = validate._import_decisions()
    per_finding = {f.get("id"): validate.replay_finding(f, dec) for f in findings}
    validate.failures.clear()
    validate.warnings_.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        validate.check_aggregate_freshness(findings, fast=False)
        validate.check_decisions_caveats_sync(findings, fast=False)
        validate.check_source_sizes(findings)
        validate.check_trust_memo_orphans(findings)
        validate.check_source_hash_consistency(findings)
        validate.check_schema_drift(findings)
    return per_finding, list(validate.failures), list(validate.warnings_)


# ── light parsers for the surrounding live-docs ──────────────────────────────

def _sections(text: str, id_re: str) -> list[tuple[str, str, str]]:
    """Yield (id, title, body) for each `### <id> — <title>` section."""
    pat = re.compile(rf"^###\s+({id_re})\b[ \t]*[—:-]?[ \t]*(.*?)\n(.*?)(?=^###\s|\Z)",
                     re.M | re.S)
    return [(m.group(1), m.group(2).strip(), m.group(3)) for m in pat.finditer(text)]


def _field(body: str, name: str) -> str | None:
    m = re.search(rf"\*\*{name}:\*\*\s*(.*?)\s*$", body, re.M)
    return m.group(1).strip() if m else None


def parse_backlog() -> dict:
    if not BACKLOG_MD.exists():
        return {}
    out = {}
    for aid, title, body in _sections(BACKLOG_MD.read_text(), r"A-\d+"):
        out[aid] = {"title": title,
                    "status": _field(body, "Status") or "unknown",
                    "question": _field(body, "Question") or title}
    return out


def parse_decisions() -> dict:
    if not DECISIONS_MD.exists():
        return {}
    out = {}
    for drid, title, body in _sections(DECISIONS_MD.read_text(), r"DR-\d+"):
        out[drid] = {"title": title, "rule": _field(body, "Rule") or title,
                     "status": (_field(body, "Status") or "unknown").lower()}
    return out


def parse_trust_memo() -> dict:
    """{fid: bucket-heading} — the one clean existing F-NNN cross-reference."""
    if not TRUST_MEMO_MD.exists():
        return {}
    buckets, current = {}, None
    for line in TRUST_MEMO_MD.read_text().splitlines():
        h = re.match(r"^##\s+(.*?)\s*$", line)
        if h:
            current = h.group(1).strip()
        elif current:
            for fid in re.findall(r"F-\d{3,}[a-z]?", line):
                buckets.setdefault(fid, current)
    return buckets


def load_manifests() -> dict:
    """Map a derived-table path → its provenance manifest.

    The join is exact (manifest['output'] == a finding's source path), so the
    report can show a finding's lineage — which RAW file(s) the table was
    derived from, via which DRs, and when — straight from the same manifest the
    freshness gate validates. No inference, self-updating on rebuild.
    """
    out, d = {}, ROOT / "analysis" / "output"
    if not d.exists():
        return out
    for mp in d.glob("*.manifest.json"):
        try:
            m = json.loads(mp.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(m, dict) and m.get("output"):
            out[m["output"]] = m
    return out


def parse_caveats() -> list[dict]:
    if not CAVEATS_MD.exists():
        return []
    out = []
    for m in re.finditer(r"^###\s+(.*?)\n(.*?)(?=^###\s|\Z)", CAVEATS_MD.read_text(), re.M | re.S):
        out.append({"heading": m.group(1).strip(), "severity": _field(m.group(2), "Severity") or "—"})
    return out


# ── per-finding view model ───────────────────────────────────────────────────

def fmt_value(f: dict) -> str:
    ct, v = f.get("check_type"), f.get("value")
    if isinstance(v, (int, float)):
        if ct == "proportion":
            return f"{v:.1%}"
        if ct in ("scalar", "rate"):
            return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.4g}"
    if ct == "distribution":
        return "distribution (see detail)"
    if ct == "matrix":
        return "matrix (see detail)"
    return esc(str(v))


def health_of(ok: bool, msg: str) -> str:
    m = (msg or "").lower()
    if "manual check_type" in m:
        return "manual"
    if ok:
        return "verified"
    if "missing" in m or "not present" in m or ("source" in m and "changed" not in m):
        return "cannot-verify"
    return "drifted"


HEALTH_CHIP = {
    "verified": ("ok", "verified"),
    "drifted": ("bad", "DRIFTED"),
    "cannot-verify": ("warn", "cannot verify"),
    "manual": ("warn", "manual — audit"),
}


def replay_fix(msg: str) -> str:
    m = msg.lower()
    if "value mismatch" in m:
        return ("The stored number no longer matches the code. Run `make findings`, "
                "review `git diff analysis/output/findings.json`, then bless or fix it.")
    if "sha256" in m or "row count" in m:
        return ("The source data changed since this was recorded. Rebuild the derived "
                "table (re-run its build script), then `make findings`.")
    if "missing" in m or "not present" in m:
        return "The source isn't present locally — fetch the raw data to verify."
    return "Run `make validate` to see the full detail."


def check_fix(name: str) -> str:
    if name.startswith("aggregate:freshness"):
        return ("A materialised table is stale versus its inputs. Rebuild it "
                "(re-run its build script), then `make findings`.")
    if name.startswith("source_size"):
        return ("This source is large — full-file replay may be slow or OOM. Consider a "
                "materialised intermediate (docs/REBUILD_PIPELINE.md).")
    if name.startswith("aggregate:unverifiable"):
        return ("Raw source not present locally (it's gitignored). Fetch it to fully verify — "
                "findings still replay against the pinned aggregate.")
    if name.startswith("decisions_caveats:pending"):
        return ("A caveat is still marked 'Pending decision' — decide it (register a DR-NNN) "
                "or confirm it's intentionally deferred.")
    if name.startswith("decisions_caveats"):
        return "A DR and the caveats register disagree — reconcile DECISIONS.md and memory/data_quality_caveats.md."
    if name.startswith("trust_memo"):
        return "TRUST_MEMO cites a finding id that doesn't line up — fix the memo."
    if name.startswith("source_hash"):
        return "Findings disagree on a source snapshot, or a source hash is unpinned."
    if name.startswith("schema_drift"):
        return "A source no longer matches its locked schema — investigate the data shape."
    return "Review `make validate` output."


def source_html(s: dict, manifests: dict) -> str:
    """Render one input source, with derived-from lineage when it's a materialised
    table (its path matches a manifest's `output`)."""
    path = s.get("path", "")
    base = (f'<span class="mono">{esc(path)}</span> '
            f'<span class="chip neutral">{esc((s.get("sha256") or "unpinned")[:12])}</span>')
    m = manifests.get(path)
    if not m:
        return base
    inp = m.get("inputs", {})
    raws = "; ".join(
        f'<span class="mono">{esc(rp)}</span> <span class="chip neutral">{esc((rh or "")[:12])}</span>'
        for rp, rh in (inp.get("sources") or {}).items()) or "—"
    drs = ", ".join(inp.get("dr_set", []))
    via = f' via <span class="mono">{esc(drs)}</span>' if drs else ""
    when = f' · built {esc(m["built_at"])}' if m.get("built_at") else ""
    return f'{base}<div class="lineage">↳ derived from {raws}{via}{when}</div>'


# ── HTML rendering ───────────────────────────────────────────────────────────

# Slightly blue-biased neutrals (chosen, not a flat grey); semantic ok/warn/bad
# kept distinct from the blue accent. Theming is token-level: OS preference via
# the media query, and the viewer's data-theme toggle overriding it both ways.
_LIGHT = ("--bg:#ffffff;--fg:#1f2328;--muted:#59636e;--card:#f6f8fa;--border:#d1d9e0;"
          "--ok:#1a7f37;--okbg:#dafbe1;--warn:#9a6700;--warnbg:#fff8c5;--bad:#cf222e;--badbg:#ffebe9;--accent:#0969da")
_DARK = ("--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--card:#151b23;--border:#3d444d;"
         "--ok:#3fb950;--okbg:#12261e;--warn:#d29922;--warnbg:#272115;--bad:#f85149;--badbg:#25171c;--accent:#4493f8")
_THEME = (f":root{{{_LIGHT}}}"
          f"@media(prefers-color-scheme:dark){{:root{{{_DARK}}}}}"
          f":root[data-theme=light]{{{_LIGHT}}}"
          f":root[data-theme=dark]{{{_DARK}}}")
_COMPONENTS = """
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg)}
.wrap{max-width:960px;margin:0 auto;padding:24px 20px 64px}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.05rem;margin:32px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.sub{color:var(--muted);font-size:.85rem;margin:0 0 20px}
.banner{border-radius:8px;padding:14px 16px;font-weight:600;margin:0 0 8px;border:1px solid transparent}
.banner.ok{background:var(--okbg);color:var(--ok);border-color:var(--ok)}
.banner.warn{background:var(--warnbg);color:var(--warn);border-color:var(--warn)}
.banner.bad{background:var(--badbg);color:var(--bad);border-color:var(--bad)}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.72rem;font-weight:600;white-space:nowrap;vertical-align:middle}
.chip.ok{background:var(--okbg);color:var(--ok)}.chip.warn{background:var(--warnbg);color:var(--warn)}.chip.bad{background:var(--badbg);color:var(--bad)}
.chip.neutral{background:var(--card);color:var(--muted);border:1px solid var(--border)}
details{background:var(--card);border:1px solid var(--border);border-radius:8px;margin:8px 0;overflow:hidden}
summary{cursor:pointer;padding:12px 14px;list-style:none;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
summary::-webkit-details-marker{display:none}
summary .fid{font-weight:700;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
summary .val{font-weight:700}summary .claim{flex:1;min-width:180px;color:var(--muted)}
.body{padding:0 14px 14px;border-top:1px solid var(--border)}
.body dl{display:grid;grid-template-columns:130px 1fr;gap:4px 14px;margin:12px 0 0}
.body dt{color:var(--muted);font-size:.82rem}.body dd{margin:0}
.body ul{margin:4px 0;padding-left:18px}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em;background:var(--card);padding:1px 4px;border-radius:4px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
th{color:var(--muted);font-weight:600}
.action{border-left:3px solid var(--bad);background:var(--card);padding:10px 12px;border-radius:0 6px 6px 0;margin:8px 0}
.action.amber{border-left-color:var(--warn)}
.action .what{font-weight:600}.action .fix{color:var(--muted);font-size:.9rem;margin-top:3px}
.empty{color:var(--muted);font-style:italic}
.lineage{color:var(--muted);font-size:.85em;margin:3px 0 0 4px;padding-left:9px;border-left:2px solid var(--border)}
h1,h2{text-wrap:balance}
summary .val,table,.body dl{font-variant-numeric:tabular-nums}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""

CSS = _THEME + _COMPONENTS


def _chip(kind: str, label: str) -> str:
    return f'<span class="chip {kind}">{esc(label)}</span>'


def render(findings, per_finding, gfail, gwarn, backlog, decisions, memo, caveats, manifests) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # action items
    actions = []
    for fid, (ok, msg) in per_finding.items():
        if health_of(ok, msg) == "drifted":
            actions.append(("bad", f"{fid} — {msg}", replay_fix(msg)))
    for name, msg in gfail:
        actions.append(("bad", f"{name} — {msg}", check_fix(name)))
    for name, msg in gwarn:
        actions.append(("amber", f"{name} — {msg}", check_fix(name)))

    n = len(findings)
    verified = sum(1 for ok, m in per_finding.values() if health_of(ok, m) == "verified")
    reds = sum(1 for s, _, _ in actions if s == "bad")
    ambers = sum(1 for s, _, _ in actions if s == "amber")

    if reds:
        bcls, btxt = "bad", f"{reds} thing(s) out of sync — see action items below"
    elif ambers:
        bcls, btxt = "warn", f"All {verified}/{n} findings verified · {ambers} advisory item(s) to review"
    else:
        bcls, btxt = "ok", f"All {n} findings verified against live code + data — in sync"

    p = [f'<div class="wrap"><h1>Analysis Status Report</h1>',
         f'<p class="sub">{esc(project_name())} · generated {now} · <em>derived view — regenerate with '
         f'<code>make report</code> to trust it</em></p>',
         f'<div class="banner {bcls}">{esc(btxt)}</div>']

    # action items section
    if actions:
        p.append('<h2>Out of sync — action items</h2>')
        for sev, what, fix in actions:
            cls = "action amber" if sev == "amber" else "action"
            p.append(f'<div class="{cls}"><div class="what">{esc(what)}</div>'
                     f'<div class="fix">{esc(fix)}</div></div>')

    # findings
    p.append(f'<h2>Findings ({n})</h2>')
    if not findings:
        p.append('<p class="empty">No findings registered yet.</p>')
    for f in findings:
        fid = f.get("id", "?")
        ok, msg = per_finding.get(fid, (False, "not replayed"))
        state = health_of(ok, msg)
        hk, hl = HEALTH_CHIP[state]
        tag = f.get("counterfactual_tag", "—")
        bucket = memo.get(fid, "not in trust memo")
        claim = f.get("claim", "")
        # summary line
        p.append("<details><summary>"
                 f'<span class="fid">{esc(fid)}</span> '
                 f'<span class="val">{fmt_value(f)}</span> '
                 f'<span class="claim">{esc(claim)}</span> '
                 f'{_chip(hk, hl)} {_chip("neutral", tag)} {_chip("neutral", bucket)}'
                 "</summary>")
        # body — full provenance
        srcs = "<br>".join(source_html(s, manifests)
                           for s in f.get("input", {}).get("sources", []))
        decs = "".join(
            f'<li><span class="mono">{esc(d)}</span> '
            f'{_chip("neutral", decisions.get(d, {}).get("status", "unknown"))} '
            f'{esc(decisions.get(d, {}).get("rule", "—"))}</li>'
            for d in f.get("decisions", [])) or "<li class='empty'>none recorded</li>"
        addr = "".join(
            f'<li><span class="mono">{esc(a)}</span> '
            f'{_chip("neutral", backlog.get(a, {}).get("status", "unknown"))} '
            f'{esc(backlog.get(a, {}).get("question", "unknown backlog item"))}</li>'
            for a in f.get("addresses", [])) or "<li class='empty'>none</li>"
        cavs = "".join(f"<li>{esc(c)}</li>" for c in f.get("caveats", [])) or "<li class='empty'>none</li>"
        repro = f.get("reproducibility", {})
        p.append('<div class="body"><dl>'
                 f'<dt>value</dt><dd>{fmt_value(f)} <span class="chip neutral">{esc(f.get("check_type","?"))}</span></dd>'
                 f'<dt>replay</dt><dd>{_chip(hk, hl)} {esc(msg)}</dd>'
                 f'<dt>trust</dt><dd>tag {esc(tag)} · memo: {esc(bucket)}</dd>'
                 f'<dt>code</dt><dd><span class="mono">{esc(f.get("code_path",""))}</span></dd>'
                 f'<dt>source</dt><dd>{srcs or "<span class=empty>none</span>"}</dd>'
                 f'<dt>filters</dt><dd><span class="mono">{esc(str(repro.get("filters", [])))}</span> · '
                 f'rows {esc(str(repro.get("row_count_after_filter","?")))}</dd>'
                 f'<dt>decisions</dt><dd><ul>{decs}</ul></dd>'
                 f'<dt>addresses</dt><dd><ul>{addr}</ul></dd>'
                 f'<dt>caveats</dt><dd><ul>{cavs}</ul></dd>'
                 '</dl></div></details>')

    # backlog
    p.append('<h2>Backlog</h2>')
    if backlog:
        addressed = {a: fid for fid, f in ((x.get("id"), x) for x in findings)
                     for a in f.get("addresses", [])}
        rows = "".join(
            f'<tr><td class="mono">{esc(aid)}</td>'
            f'<td>{_chip("neutral", d["status"])}</td>'
            f'<td>{esc(d["question"])}</td>'
            f'<td class="mono">{esc(addressed.get(aid, "—"))}</td></tr>'
            for aid, d in backlog.items())
        p.append(f'<table><tr><th>id</th><th>status</th><th>question</th><th>finding</th></tr>{rows}</table>')
    else:
        p.append('<p class="empty">No backlog items.</p>')

    # decisions
    p.append('<h2>Decisions</h2>')
    if decisions:
        cited = {}
        for f in findings:
            for d in f.get("decisions", []):
                cited.setdefault(d, []).append(f.get("id"))
        rows = "".join(
            f'<tr><td class="mono">{esc(drid)}</td>'
            f'<td>{_chip("ok" if d["status"]=="active" else "warn", d["status"])}</td>'
            f'<td>{esc(d["rule"])}</td>'
            f'<td class="mono">{esc(", ".join(cited.get(drid, [])) or "—")}</td></tr>'
            for drid, d in decisions.items())
        p.append(f'<table><tr><th>id</th><th>status</th><th>rule</th><th>cited by</th></tr>{rows}</table>')
    else:
        p.append('<p class="empty">No decisions.</p>')

    # caveats register
    p.append('<h2>Caveats register</h2>')
    if caveats:
        rows = "".join(f'<tr><td>{esc(c["heading"])}</td><td>{_chip("neutral", c["severity"])}</td></tr>'
                       for c in caveats)
        p.append(f'<table><tr><th>caveat</th><th>severity</th></tr>{rows}</table>')
    else:
        p.append('<p class="empty">No caveats recorded.</p>')

    p.append("</div>")
    return "\n".join(p)  # inner content only (no skeleton) — see wrappers below


def full_document(content: str) -> str:
    """Standalone self-contained HTML file (for `make report` / opening locally)."""
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Analysis Status Report — {esc(project_name())}</title><style>{CSS}</style></head>"
            f"<body>{content}</body></html>")


def body_fragment(content: str) -> str:
    """Body-only fragment for the Artifact tool, which supplies its own
    <!doctype>/<head>/<body> skeleton. A <style> tag in body content is valid
    HTML5, and all CSS is inline (no external requests — Artifact CSP-safe)."""
    return f"<style>{CSS}</style>\n{content}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the analysis status report.")
    ap.add_argument("--artifact", metavar="PATH",
                    help="write a body-only HTML fragment to PATH (for the Artifact tool) "
                         "instead of the standalone file")
    args = ap.parse_args()

    findings = _load()
    per_finding, gfail, gwarn = gather_validation(findings)
    content = render(findings, per_finding, gfail, gwarn,
                     parse_backlog(), parse_decisions(), parse_trust_memo(), parse_caveats(),
                     load_manifests())

    if args.artifact:
        out = Path(args.artifact)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body_fragment(content), encoding="utf-8")
    else:
        out = OUT
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(full_document(content), encoding="utf-8")

    reds = sum(1 for ok, m in per_finding.values() if health_of(ok, m) == "drifted") + len(gfail)
    status = "OUT OF SYNC" if reds else "in sync"
    rel = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"wrote {rel} — {len(findings)} findings, {status} "
          f"({len(gfail)} failures, {len(gwarn)} warnings)")


if __name__ == "__main__":
    main()
