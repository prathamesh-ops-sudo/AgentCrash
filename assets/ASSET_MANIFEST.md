# Asset manifest

Each generated asset is produced from its editable source under `assets/source/`
by a deterministic script in `scripts/`, so contributors can regenerate them
after code or design changes. No asset is a fabricated benchmark, testimonial,
or live-capture claim.

## Generated assets (`assets/generated/`)

| Asset | Source | Script | Type | Captured/generated | License |
|-------|--------|--------|------|--------------------|---------|
| `social-preview.png` | `assets/source/social-preview.html` (design language) | `scripts/render_assets.py` | repository social preview (1280×640) | 2026-09-10 | Apache-2.0 |
| `scenario-card.png` | `assets/source/social-preview.html` (style) | `scripts/render_scenario_card.py` | scenario card (1200×630) | 2026-09-10 | Apache-2.0 |
| `viewer-shot.png` | **live capture** of the bundled React viewer | headless Chrome (`agentcrash serve` + `/viewer/`) | actual viewer UI screenshot (1280×1000) | 2026-09-10 | Apache-2.0 |
| `report-shot.png` | **live capture** of the standalone HTML report | headless Chrome over `assets/generated/sample-report.html` | actual report screenshot (1280×1200) | 2026-09-10 | Apache-2.0 |
| `sample-report.html` | real `agentcrash report` output (attack variant) | CLI | recorded replay evidence example | 2026-09-10 | Apache-2.0 |

## Editable sources (`assets/source/`)

| Asset | Purpose | License |
|-------|---------|---------|
| `logo.svg` | original reusable wordmark mark (gradient) | Apache-2.0 |
| `logo-monochrome.svg` | monochrome variant for favicon/watermarks | Apache-2.0 |
| `social-preview.html` | human-readable design source for the preview | Apache-2.0 |

## Notes

- All project artwork is original (first-party) and does not imitate OpenClaw's
  mascot or imply affiliation.
- `viewer-shot.png` and `report-shot.png` are **authentic**: captured by headless
  Chrome over the actual bundled viewer (started with `agentcrash serve`) and the
  real `agentcrash report` HTML output (attack variant of
  invoice-confidential-note). Never replace these with fabricated renderings.
- Glyphs used are system font fallbacks (Segoe UI / Arial) available on the
  capture machine; the rasterized PNGs embed these as pixels, so they are
  self-contained for hosting.
- Alt text and captions are required wherever an asset is reused (README,
  social, docs).