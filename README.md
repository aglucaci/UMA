# UMA: findings and records from UMDB data releases

**https://aglucaci.github.io/UMA/**

UMA is the website for one versioned release of the Urban Microbiome Database (UMDB). It has two parts:

* **Findings**: what STRIGA found when it analysed exactly this release's catalog. Every registered hypothesis with its status, result, key numbers, caveats, figures and tables.
* **Records**: every study, BioSample, run, place and country in the release, searchable by accession, title, centre or place name, as frozen in the release.

It is one of three repositories:

| Repository | Role |
| --- | --- |
| [UMDB](https://github.com/aglucaci/UMDB) | Harvests and curates the catalog and publishes versioned releases. Its own browser, at [aglucaci.github.io/UMDB](https://aglucaci.github.io/UMDB/), shows the **live** catalog after every harvest (Explorer, Atlas, Analytics, Collections, Workspace) |
| [STRIGA](https://github.com/aglucaci/STRIGA) | Analyses a UMDB catalog; its results are bundled into the release |
| **UMA** (this one) | Shows one **release**: its findings and its records |

```text
UMDB release <V> (GitHub Release umdb-<V>.tar.gz) ──uma build──► docs/data/ ──GitHub Pages──► aglucaci.github.io/UMA
```

UMA never reads the moving catalog: every number on it comes from the release named in the header and footer, so what you cite is what you saw.

## Pages

| Page | What it shows |
| --- | --- |
| Overview (`index.html`) | The release: counts, findings at a glance, habitats, countries, version, DOI, rule versions, download |
| Findings (`findings.html`, `?id=C1`) | All hypotheses, filterable by status and track; each one with its result, key results, caveats, figures and tables (CSV/TSV downloads) |
| Search (`search.html?q=`) | Studies (title, centre, accession; filter by habitat, assay, country) and places/countries by name; accessions open their record |
| Records (`study.html?acc=`, `sample.html?acc=`, `run.html?acc=`, `place.html?id=` / `?country=`) | The record as frozen in the release: tier and evidence, validated location next to the submitted text, runs, downloads |
| About (`about.html`) | Release metadata, citation, licences, every file in the release with its SHA-256 |

Short routes work through `404.html`: `/study/PRJNA271013`, `/sample/…`, `/run/…`, `/place/<GeoNames id>`, `/country/US`, `/finding/C1`.

## Building the site

```bash
bin/uma build latest             # fetch the latest UMDB release and write docs/data/ (about 30 s)
bin/uma build 2026.11.20         # or a given version; or a release folder (../UMDB/dist/releases/<V>)
bin/uma serve                    # preview at http://localhost:8765
bin/uma test                     # unit tests (standard library; node for two parity checks)
```

`uma fetch <V>` only downloads. The builder needs only the Python standard library (and `zstd`, or Python 3.14+, for `umdb.sqlite.zst`). The **Build site from a UMDB release** workflow does the same on GitHub and commits `docs/`, which GitHub Pages publishes.

## Repository layout

```text
UMA/
├── docs/                       the static site (GitHub Pages serves this folder)
│   ├── index.html, findings.html, search.html, study.html, sample.html, run.html, place.html, about.html, 404.html
│   ├── assets/                 uma.css, uma.js (frame, data, renderers), records.js (record pages)
│   └── data/                   written by `uma build` (committed): release.json, findings.json + findings/<ID>/,
│                               studies.json, places.json, p/<ACC>.json, ix/<NN>.json
├── uma/                        release.py (reads a release), build.py (writes docs/data/), cli.py
├── bin/uma
├── tests/                      build tests on tests/fixtures/release (a tiny release written by UMDB's own code)
├── ARCHITECTURE.md, DATA_DICTIONARY.md, CHANGELOG.md, LICENSE
└── README.md
```

## License and citation

CC BY-NC-SA 4.0 ([LICENSE](LICENSE)), like UMDB. Sequence data and submitter metadata remain governed by the INSDC policies of their source archives; places come from GeoNames (CC BY 4.0). Cite the UMDB release you used (version and DOI; the About page has the citation) and, for findings, the STRIGA version.
