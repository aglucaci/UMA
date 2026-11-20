# UMA data dictionary

The files the website loads. Fields of the release itself (tables, Parquet, run records) are in UMDB's [DATA_DICTIONARY.md](https://github.com/aglucaci/UMDB/blob/main/DATA_DICTIONARY.md).

## Website data (`docs/db/`)

The website loads a compact index built by `uma build` from one UMDB release, not every run record. Opening a BioProject fetches that project's file. Full tables are in the Parquet releases. All geography in these files comes from `sample_locations`: a country is published when `country_status` is verified or probable, a place when `status` is verified or probable. AI proposals never change counts or filters.

| File | Contents |
| --- | --- |
| `docs/db/summary.json` | Exact counts from SQLite, each labelled with its unit |
| `docs/db/geo.json` | Validated location hierarchy: countries, regions and places used by samples |
| `docs/db/samples.json` | BioSamples aggregated so that each sample is counted in exactly one row |
| `docs/db/cube.json` | Runs aggregated by the same dimensions |
| `docs/db/projects.json` | One row per BioProject |
| `docs/db/p/<ACC>.json` | One BioProject's samples and runs (`_none.json` for runs without a BioProject) |
| `docs/db/ix/<NN>.json` | Accession lookup: every BioSample and run accession → its BioProject (index into `projects.json` rows), split into 100 files by the accession's last two digits (`xx` if it has none). Lets `sample.html` and `run.html` find the right project file |
| `docs/db/collections.json` | Curated collections: definition (Explorer filters), inclusion criteria, suggested use and workflow, and summary statistics |
| `docs/db/collections/<slug>.tsv.gz` | One collection's runs: run, biosample, project, assay, layout, platform, bases, country, GeoNames id, city, habitat, collection date |
| `docs/db/population.json` | Every country's population (GeoNames), for per-capita map layers, including countries with no samples |
| `docs/db/analytics.json` | Precomputed catalog structure for the Analytics page: study concentration (Lorenz curve, Gini), collection-to-release delay, library sizes by assay, metadata completeness by assay |
| `docs/assets/cohort-templates.json` | README, download script and starter analyses of a research package; copied from the release (written there by UMDB's `cohorts.py`) so the browser and the CLI export the same files |
| `docs/db/manifest.json` | The release shown (`release`: version, DOI, URL, STRIGA version), build time, schema, rule, query and gazetteer versions, counts, file sizes |
| `docs/db/analysis.json` | STRIGA results from the release's `analysis/`: pipeline version and commit, input database hash, and one row per hypothesis (id, track, programme, title, status, result, question, caveats, files); `available: false` when the release has none |
| `docs/db/srr_records_manifest.json` | Kept for older loaders: `generated_utc`, `total_records`, empty `parts` |

Unchanged files are not rewritten, so a new release changes only the projects that changed. Download URLs and verbatim NCBI records are left out (they are in the database and releases).

### `geo.json`

`countries` rows (`country_cols`: iso2, numeric, name, continent, population), `admin1` rows (code, index into `countries`, name) and `places` rows (geonames_id, name, index into `countries`, index into `admin1` or null, lat, lon, population). `statuses` lists the location statuses that `loc` columns index into. `attribution` carries the GeoNames credit.

### `samples.json` (unit: BioSamples)

`cols` names the columns of each row in `rows`; `dims` holds the value lists that dictionary-encoded columns index into.

| Column | Type | Description |
| --- | --- | --- |
| `projects` | int → `dims.projsets` | The set of BioProjects the sample belongs to (each a list of indexes into `dims.project`) |
| `year` | int or null | SRA release year of the sample's earliest run |
| `cyear` | int or null | Collection year (`collection_date`) |
| `country`, `admin1`, `place` | int → `geo.json` lists, or null | Accepted location |
| `assays` | int → `dims.assaysets` | The set of assay classes among the sample's runs |
| `tier` | int → `dims.tier` | Sample-level eligibility tier |
| `context` | int → `dims.context` | Primary urban context (`""` = none) |
| `loc` | int → `dims.loc` | Place status (verified, probable, ambiguous, conflicting, unresolved) |
| `lat`, `lon` | float or null | Reported coordinates rounded to 0.01°, about 1 km (not inferred from place names) |
| `samples` | int | BioSamples in the row |

Because project and assay are sets, a sample in two projects or with runs of two assays is still one row: `sum(samples)` over any filter is exact.

### `cube.json` (unit: runs)

Columns `project`, `year` (run release year), `cyear`, `country`, `admin1`, `place`, `assay`, `tier` (run-level), `context`, `loc`, `ai` (index into `dims.ai`, or null), `runs`, `gbases`. It no longer has a `samples` column: count BioSamples with `samples.json`.

### `projects.json` and `p/<ACC>.json`

`projects.json`: `cols` = accession, title, center_name, data_type, submission_date, runs, samples, first_year, last_year.

`p/<ACC>.json`: `project` (accession, title, description, organism, data type, centre, dates); `samples` rows with `sample_cols` (accession, title, collection date, accepted country name, region name and place name, lat, lon, urban_status, urban_context, eligibility_reason, isolation_source, env_broad_scale, env_local_scale, env_medium, host, location_resolution, country_iso2, place_id, location_status, location_method, location_note, the submitted `geo_loc_raw`, collection_year); `runs` rows with `run_cols` (accession, index into `samples`, experiment, assay and library fields, platform, instrument, release date, spots, bases, average length, size in MB, organism label, run-level tier, experiment title); `ai` keyed by run accession (proposals, `status: "proposed"`).

### `summary.json`

| Field | Description |
| --- | --- |
| `units` | What each count means |
| `totalRuns`, `totalBioSamples`, `totalProjects` | Distinct counts (`runsWithoutProject` separately) |
| `totalCountries`, `totalCities` | Distinct accepted countries and GeoNames places |
| `geoResolvedRuns`, `geoResolvedBioSamples` | Runs and BioSamples with an accepted place |
| `location` | BioSamples per place status and per country status |
| `eligibility` | `[{name, runs, biosamples}]` per tier |
| `years` | `[{name, count}]` runs by **release year** |
| `collectionYears` | `[{name, count}]` BioSamples by **collection year** |
| `assays` | `[{name, count, biosamples}]` (`count` = runs) |
| `countries` | `[{iso2, name, biosamples, runs, count}]` (`count` = runs, for older pages) |
| `cities` | Top 200 `[{geonames_id, name, country, biosamples, runs, count}]` |
| `centers` | `[{name, count}]` runs per submitting centre |
| `largestProject`, `topProjects` | Largest BioProjects by runs |

