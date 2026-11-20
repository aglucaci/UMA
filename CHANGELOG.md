# Changelog

## 2.0.0 (2026-11-20)

UMA is rebuilt from scratch around a release, separate from UMDB's live-catalog browser:

* **Findings** (`findings.html`): every STRIGA hypothesis for the release, filterable by status and track, each with result, key results, caveats, figures and tables.
* **Search and records** (`search.html`, `study.html`, `sample.html`, `run.html`, `place.html`): studies, BioSamples, runs, places and countries as frozen in the release.
* **Overview** and **About**: release counts, version, DOI, rule versions, citation, licences and every file with its SHA-256.
* New data layout `docs/data/` (`release.json`, `findings.json`, `findings/<ID>/`, `studies.json`, `places.json`, `p/`, `ix/`) and a new builder (`uma/build.py`); new look (light and dark), no framework.
* Removed: the Explorer, Atlas, Analytics, Collections and Workspace. They live on in UMDB's own browser of the live catalog (aglucaci.github.io/UMDB).

## 1.0.0 (2026-11-20)

* UMA becomes its own repository, split from UMDB with the history of the site code; `uma build` builds the site from a UMDB release (contract `umdb-release/1`).
