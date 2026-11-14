# Db2iLens assets

Visual assets for Db2iLens documentation and social cards.

## Included files

- **`db2ilens-logo-canva.png`** — Canva logo (512×512) used in the README
- **`db2ilens-icon-canva.png`** — Canva icon (128×128)
- **`db2ilens-logo.svg`** — SVG logo with "Db2iLens" text
- **`db2ilens-icon.svg`** — Icon-only SVG (favicon)
- **`social-preview.svg`** — Social preview artwork (1280×640)
- **`report-screenshot.png`** — Cropped top of the HTML discovery report (README)

## Regenerating the public demo report

Offline scans store `scan.source` as an **absolute path by design** (`Path.resolve()`).
For a public snapshot (`demo-report.html` at the repo root), rewrite `source` to a
relative path before rendering, then verify no machine metadata leaked:

```bash
# From the repo root
cd db2i-lens
uv run db2ilens scan --offline examples/mini_erp/ --out /tmp/scan.yaml

# Rewrite source to a portable relative path (manual step for public demos)
python3 - <<'PY'
from pathlib import Path
import yaml
p = Path("/tmp/scan.yaml")
doc = yaml.safe_load(p.read_text())
doc["source"] = "examples/mini_erp"
p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
PY

uv run db2ilens report /tmp/scan.yaml --format html --out demo-report.html

# Sanity check — must print nothing
rg -n -i '/home|michael|pop-os|Documents/developpement|hostname' demo-report.html || true
```

Do **not** commit a raw report that still contains absolute home paths.

## Regenerating `report-screenshot.png`

```bash
cd db2i-lens
# Ensure demo-report.html is clean (see above)
firefox --headless --new-instance --profile /tmp/ff-shot \
  --window-size 1280,2000 \
  --screenshot /tmp/report-full.png \
  "file://$(pwd)/demo-report.html"
# Crop the top of the report (title + summary + tables) to ~1100px height
```

Recommendations:
- Width ≥ 1280px
- Prefer the upper portion (summary + tables) over a squashed full page
- Include the "Db2iLens" header and severity summary cards

### Alternative (`wkhtmltoimage`)

```bash
wkhtmltoimage --width 1200 demo-report.html docs/assets/report-screenshot.png
```

## SVG → PNG

```bash
inkscape --export-type=png --export-filename=docs/assets/db2ilens-logo.png \
  docs/assets/db2ilens-logo.svg -w 400

rsvg-convert -w 400 docs/assets/db2ilens-logo.svg > docs/assets/db2ilens-logo.png

# Social preview (1280×640) for GitHub Settings → Social preview
rsvg-convert -w 1280 -h 640 docs/assets/social-preview.svg > docs/assets/social-preview.png
```

## Palette

- **Primary:** `#2563EB`
- **Secondary:** `#1D4ED8`
- **Background:** `#0B1220`
- **Text:** `#E2E8F0`
- **Muted text:** `#94A3B8`
