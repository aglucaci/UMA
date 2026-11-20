# UMA: browser for the Urban Microbiome Database

**https://aglucaci.github.io/UMA/**

UMA is the website for browsing and searching UMDB data releases: every public urban microbiome sequencing study, BioSample and run that UMDB has found and screened, with validated locations, habitats and eligibility tiers, and the analyses STRIGA ran on the same release.

It is one of three repositories:

| Repository | Role |
| --- | --- |
| [UMDB](https://github.com/aglucaci/UMDB) | Harvests and curates the catalog from NCBI SRA, BioSample and BioProject, and publishes versioned **data releases** |
| [STRIGA](https://github.com/aglucaci/STRIGA) | Analyses a UMDB catalog (Nextflow); its results are bundled into the release |
| **UMA** (this one) | Builds and serves the website from one release |

```text
UMDB release <V> (GitHub Release umdb-<V>.tar.gz) ──uma build──► docs/db/ ──GitHub Pages──► aglucaci.github.io/UMA
```

UMA never talks to NCBI or to the harvester: it reads one release (contract `umdb-release/1`), and every page states which release it shows. A new harvest changes the website only once UMDB publishes a new release.

## What the site offers

| Page | What you can do |
| --- | --- |
| [Home](https://aglucaci.github.io/UMA/) | Paste any BioProject, BioSample or run accession and go straight to its page |
| [Explorer](https://aglucaci.github.io/UMA/explorer.html) | Filter studies, BioSamples and runs by validated place, habitat, assay, collection and release year, eligibility tier and location quality; every filter is in the address |
| Record pages | A page for every [study](https://aglucaci.github.io/UMA/study.html?acc=PRJNA271013), BioSample, run, city, country and habitat: submitted next to normalized metadata, curation evidence, quality flags, provenance |
| [Atlas](https://aglucaci.github.io/UMA/global-map.html) | Sample and study density, habitats, samples per capita with surveillance gaps, location confidence; export the visible area |
| [Analytics](https://aglucaci.github.io/UMA/analytics.html) | Coverage, growth, study concentration, release delay, library sizes, completeness, and **Findings**: STRIGA's hypothesis results for this release with caveats; every chart downloads as CSV, SVG or PNG |
| [Collections](https://aglucaci.github.io/UMA/collections.html) | Curated cohorts (global wastewater, transit, urban air, greenspace, virome, resistome) with inclusion criteria and run lists |
| [Workspace](https://aglucaci.github.io/UMA/workspace.html) | Save cohorts, combine them (union, intersection, difference), compare them, balance them with a seed, and download a research package that `umdb cohort export` reproduces exactly |

Short routes (`/study/PRJNA271013`, `/sample/…`, `/run/…`, `/city/<GeoNames id>`, `/country/US`, `/habitat/municipal-wastewater`, `/collection/<slug>`) work through `404.html`.

## Building the site

```bash
bin/uma fetch 2026.11.20         # download UMDB release v2026.11.20 into releases/ (or: latest)
bin/uma build 2026.11.20         # write docs/db/ from it (about a minute for the full catalog)
bin/uma serve                    # preview at http://localhost:8765
bin/uma test                     # unit tests (standard library; node for the PRNG parity test)
```

`uma build` also takes a release folder directly, for example one made locally in a UMDB checkout (`uma build ../UMDB/dist/releases/<V>`). It needs only the Python standard library (and `zstd`, or Python 3.14+, for `umdb.sqlite.zst`).

The **Build site from a UMDB release** workflow (`.github/workflows/build-from-release.yml`) does the same on GitHub: run it with a release version (or let UMDB trigger it), and it commits `docs/` to `main`, which GitHub Pages publishes.

## Repository layout

```text
UMA/
├── docs/                       the static site (GitHub Pages serves this folder)
│   ├── *.html                  pages
│   ├── assets/                 db.js (query engine), ui.js, entity.js, collections.js, workspace.js, site.css,
│   │                           cohort-templates.json (copied from the release)
│   └── db/                     website data built by `uma build` (committed)
├── uma/                        the builder: release.py (reads a release), build.py (writes docs/db/), cli.py
├── bin/uma
├── tests/                      build tests on tests/fixtures/release (a tiny release written by UMDB's own code)
├── ARCHITECTURE.md, DATA_DICTIONARY.md, CHANGELOG.md, LICENSE
└── README.md
```

## License and citation

CC BY-NC-SA 4.0 ([LICENSE](LICENSE)), like UMDB. Sequence data and submitter metadata remain governed by the INSDC policies of their source archives. Cite the UMDB release you used (version and DOI, shown at the bottom of every page); see UMDB's [CITATION.cff](https://github.com/aglucaci/UMDB/blob/main/CITATION.cff).
