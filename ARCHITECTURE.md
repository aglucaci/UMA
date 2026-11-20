# UMA architecture

How UMA turns one UMDB release into a static website. The catalog, its schema and the release format are documented in UMDB's [ARCHITECTURE.md](https://github.com/aglucaci/UMDB/blob/main/ARCHITECTURE.md); the analyses in [STRIGA](https://github.com/aglucaci/STRIGA).

```
UMDB release <V>  (contract umdb-release/1)
  manifest.json · umdb.sqlite.zst · reference/ · analysis/ (STRIGA: striga_manifest.json,
  hypotheses_status.tsv, report.json, hypotheses/<ID>/summary.json + figures + tables)
        │  uma fetch <V>    GitHub Release asset umdb-<V>.tar.gz → releases/<V>/ (git-ignored)
        │  uma build <V>    uma/release.py reads it; uma/build.py writes docs/data/
        ▼
docs/data/  release.json · findings.json · findings/<ID>/ · studies.json · places.json · p/<ACC>.json · ix/<NN>.json
        │  git commit → GitHub Pages
        ▼
https://aglucaci.github.io/UMA/
```

## Design

* **One release, never the live catalog.** UMDB's own browser shows the catalog as it is harvested; UMA shows a release. Every page names the release (header and footer), and the About page lists every file in it with its SHA-256.
* **Findings first.** STRIGA's results are UMA's main content, not a side panel: `findings.json` carries each hypothesis's status, result, question, caveats and key results, and its figures and tables are copied next to it. Hypotheses that were not run on this release (missing inputs, roadmap) are listed with that status, so the whole programme is visible.
* **Records as frozen.** Search and record pages read only the release's database, through a few small indexes and one file per study, so a record page shows exactly what the release contains, including the eligibility tier and the validated location next to the submitted text.
* **Static and small to load.** No server and no framework. A page loads `release.json` (a few KB) and what it needs: `findings.json` (about 20 KB), `studies.json` (about 2 MB) for search, `places.json` (about 0.3 MB), one `ix/<NN>.json` (about 250 KB) to find an accession's study, and that study's `p/<ACC>.json`. All URLs carry the release build time, so a rebuilt site never mixes cached files.
* **Strict contract.** `uma/release.py` refuses a release whose `contract` it does not know, and unpacks a compressed database into `releases/.db/`, never inside the release folder.

## What is not here

UMDB's live browser has the interactive Explorer, Atlas, Analytics charts, Collections and Workspace over the current catalog. UMA deliberately leaves those out; querying a release's Parquet tables in the browser (DuckDB-Wasm) is a possible next step.
