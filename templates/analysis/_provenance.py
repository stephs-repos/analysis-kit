"""
_provenance.py — manifests for materialised intermediate tables.

When a raw source is too big to replay per-finding (loading it whole would OOM,
or re-loading it on every `validate` is non-viable), the pattern is: build a
small derived table ONCE with the DR-NNN filters applied, and let findings
replay against that table instead of the raw source.

The risk is staleness — the table can drift from (a) the raw source or (b) a
changed DR definition, and native sha256 pinning on a *finding* only catches a
tampered table, not one stale against its inputs. This module writes a sidecar
manifest pinning the content hashes of everything the table was derived from;
validate.py's `check_aggregate_freshness` re-derives them and fails/warns on any
drift, forcing a conscious rebuild.

Usage (from a build script, after writing the output CSV):

    from analysis._provenance import write_manifest
    write_manifest(
        output="analysis/output/daily_ridership.csv",
        sources=["reference/raw-data/trips/big.zip"],
        dr_set=["DR-001", "DR-002"],
    )

This writes `analysis/output/daily_ridership.manifest.json`. Keep the output
deterministic (stable sort, fixed formatting) so its hash is stable across
rebuilds — otherwise the freshness check false-alarms.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _decisions_fingerprint() -> str:
    """Call _decisions.decisions_fingerprint() (single source of truth) by loading
    the module from its path, independent of the caller's sys.path setup."""
    path = ROOT / "analysis" / "_decisions.py"
    spec = importlib.util.spec_from_file_location("_decisions_for_fp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.decisions_fingerprint()


def write_manifest(*, output: str, sources: list[str], dr_set: list[str]) -> dict:
    """Write `<output>.manifest.json` pinning the content hashes of the output,
    its raw sources, the DR set, and the decisions fingerprint.

    Paths are relative to the project root. Returns the manifest dict.
    """
    out_path = ROOT / output
    if not out_path.exists():
        raise FileNotFoundError(f"output {output} does not exist — write it before the manifest")
    manifest = {
        "output": output,
        "output_sha256": _sha256(out_path),
        "inputs": {
            "sources": {s: _sha256(ROOT / s) for s in sources},
            "dr_set": list(dr_set),
            "decisions_fingerprint": _decisions_fingerprint(),
        },
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    # Convention: <stem>.manifest.json (e.g. daily.csv -> daily.manifest.json).
    manifest_path = out_path.parent / (out_path.name.rsplit(".", 1)[0] + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
