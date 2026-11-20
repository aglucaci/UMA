# UMA architecture

How UMA turns a UMDB release into a static website. The catalog itself, its schema and the release format are documented in UMDB's [ARCHITECTURE.md](https://github.com/aglucaci/UMDB/blob/main/ARCHITECTURE.md).

```
UMDB release <V>  (contract umdb-release/1)
  manifest.json · umdb.sqlite.zst · collections/ · reference/geonames/ ·
  documentation/cohort-templates.json · analysis/ (STRIGA)
        │  uma fetch <V>     (GitHub Release asset umdb-<V>.tar.gz → releases/<V>/)
        │  uma build <V>     (uma/release.py reads it; uma/build.py writes the site data)
        ▼
docs/db/   summary · geo · samples · cube · projects · p/<ACC> · ix/<NN> · collections ·
           population · analytics · analysis · manifest (names the release)
docs/assets/cohort-templates.json   (copied from the release)
        │  git commit → GitHub Pages
        ▼
https://aglucaci.github.io/UMA/
```

**What UMA relies on.** `uma/release.py` accepts only contracts it knows (`umdb-release/1`) and reads `manifest.json` (version, DOI, build metadata, `analysis`), the database, `collections/`, `documentation/cohort-templates.json`, `reference/geonames/countryInfo.txt` (country populations for the per-capita layer) and `analysis/` (STRIGA's `striga_manifest.json`, `hypotheses_status.tsv`, `report.json`). A compressed database is unpacked into `releases/.db/`, never inside the release folder.

**What UMA computes.** The sample and run cubes, the accession index, per-project files and the Analytics statistics are computed from the release's database at build time. Curated collections and the research-package templates are not recomputed: they are copied from the release so that the Workspace export and `umdb cohort export` of the same release write the same files, and the Workspace's seeded shuffle (`mulberry32`) matches UMDB's Python one (a test in each repository checks the same four values).

## Website data

The site loads `summary.json`, `geo.json`, `samples.json`, `cube.json` and `projects.json` (about 5 MB uncompressed for 477,000 runs) and fetches `p/<ACC>.json` when a project is opened or exported. Runs and BioSamples are aggregated separately so that both are counted exactly:

- `samples.json` has one row contribution per BioSample. A sample's projects and assays are encoded as sets, so a sample with runs of two assays, or shared by two studies, is still counted once (26,785 rows for 406,177 BioSamples).
- `cube.json` aggregates runs by the same dimensions (23,797 rows for 477,166 runs).
- `geo.json` is the validated location hierarchy both cubes index into.

`docs/assets/db.js` turns these into a query engine shared by the Explorer and the Map. A single pass over each cube computes the totals and, for every filter, the counts it would have with all other filters applied, so cascading country → region → city lists only offer combinations that exist. Filters live in the page address (`?country=US&region=US.NY&city_id=5128581&cyear=2018-2020`), so a selection on one page opens identically on the other. A test checks the cube totals against `COUNT(DISTINCT …)` in SQLite. Built by `uma/build.py`; unchanged files are left untouched. Field reference: [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

### v1.0 platform pages

The site is static (no build step, no server). Every page reads the files above through `docs/assets/db.js`:

| Page | Route | What it reads |
| --- | --- | --- |
| Explorer, Atlas | `explorer.html`, `global-map.html` | the cubes (`samples.json`, `cube.json`), `geo.json`, `population.json` (per-capita layer) |
| Study, BioSample, run | `study.html?acc=`, `sample.html?acc=`, `run.html?acc=` | `p/<ACC>.json`; BioSamples and runs are found through `ix/<NN>.json` |
| City, country, habitat | `city.html?id=`, `country.html?iso=`, `habitat.html?id=` | the cubes, filtered like the Explorer |
| Collections | `collections.html[?slug=]` | `collections.json`, `collections/<slug>.tsv.gz` |
| Workspace | `workspace.html` | the cubes (exact set operations over sample-cube rows) and project files (export) |
| Analytics | `analytics.html` | `cube.json`, `summary.json`, `analytics.json` |

`404.html` maps the routes `/study/<acc>`, `/sample/<acc>`, `/run/<acc>`, `/city/<id>`, `/country/<iso>`, `/habitat/<slug>` and `/collection/<slug>` to these pages on GitHub Pages. `assets/ui.js` holds shared labels, charts (each downloadable as CSV, and SVG charts as SVG or PNG) and Workspace storage (`localStorage`, key `umdb.workspace.v1`).

Because each BioSample is in exactly one sample-cube row, a cohort is a 0/1 mask over rows, and union, intersection and difference of cohorts are exact. Exporting a cohort loads the project files it touches and applies the same filters per sample (`sampleMatchesFull`); `scripts/umdb_harvester/cohorts.py` implements the same filters in SQL, and the same seeded balancing, so `umdb cohort export cohort.json` gives the same samples as the browser.

