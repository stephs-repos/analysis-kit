# reference/

Project-context materials. The split:

| Path | Contents | Tracked in git? |
|---|---|---|
| `reference/` (this directory) | Briefs, data dictionaries, FAQs, prior art, screenshots | **Yes** — committed |
| `reference/raw-data/` | Actual data files (CSV, Excel, Parquet, JSON…) | **No** — gitignored by default |

The split is deliberate: raw data is large, often sensitive, and refreshed externally. Briefs and dictionaries are small, shareable, and stable — they should be visible immediately on `git clone` so a new analyst joining the project has context.

## What typically lives here

- `brief.{md,pdf}` — stakeholder scope, deadlines, deliverable expectations
- `data-dictionary.md` — column definitions, data sources, refresh cadence
- `stakeholder-correspondence/` — important emails, meeting notes
- `prior-art/` — papers, dashboards, prior analyses you're building on
- `screenshots/` — anything visual that informs the work

## Format guidance

Prefer **markdown** for anything you might edit, link to from tooling, or reference programmatically. PDFs are fine for fixed source documents (signed contracts, vendor briefs, academic papers) but problematic for living documents because they:

- Bloat the repo
- Can't be diffed in pull requests
- Can't be cross-referenced from `live-docs/` or vignettes

If you have a vendor PDF that's the source of truth (e.g., a data dictionary), the pattern is: keep the PDF for provenance, AND maintain a markdown shadow that re-states the conventions in linkable form. The PDF is the audit trail; the markdown is the working surface.

## What does NOT go here

- **Data files.** They go in `raw-data/` — see `raw-data/README.md`. Mixing them under the same directory means either you accidentally commit data with PII, or you accidentally hide your brief from teammates.
- **Cleaned or derived data.** That lives in `analysis/output/`.
- **Internal working documents.** Those are the live-docs (`live-docs/TRUST_MEMO.md`, `DECISIONS.md`, etc.) — see `CLAUDE.md` for the live-doc registry. Reference materials are *inputs* to the project; live-docs are *artefacts* the project produces.
