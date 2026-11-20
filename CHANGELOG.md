# Changelog

## 1.0.0 (2026-11-20)

* UMA becomes its own repository, split from UMDB (where it was the website in `docs/` and `scripts/umdb_harvester/site.py`); the history of the site code is preserved, the history of generated data is not.
* `uma build` builds `docs/db/` from a UMDB release (contract `umdb-release/1`): a release folder, a fetched version, or `latest` from GitHub Releases. Collections and research-package templates are copied from the release instead of being recomputed.
* Every data page names the UMDB release it shows (version, catalog build date, DOI, STRIGA version).
* Analytics has a **Findings** section: STRIGA's hypothesis results bundled with the release (`docs/db/analysis.json`), with caveats and a CSV download.
* Workspace research packages record the UMDB release version and DOI in `cohort.json` and `CITATION.bib`.
* The site is branded UMA and served at https://aglucaci.github.io/UMA/; the old UMDB address redirects here.
* Workflows: tests on every push; **Build site from a UMDB release** (manual or `repository_dispatch` from UMDB) commits the rebuilt data.
