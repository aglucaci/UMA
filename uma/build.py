"""Build UMA's data files (docs/data/) from one UMDB release.

UMA has two jobs, and its data follow them:

  Findings     what STRIGA found in this release's catalog
    release.json            the release: version, DOI, dates, counts, licences, STRIGA run
    findings.json           one entry per hypothesis: status, result, question, caveats,
                            key results, figures and tables (paths under findings/)
    findings/<ID>/          the figures (.png) and tables (.tsv) STRIGA wrote, copied as is

  Records      the catalog as frozen in this release, searchable by accession, title or place
    studies.json            one row per BioProject (title, centre, counts, years, countries, habitats, assays)
    places.json             validated places and countries with sample and study counts
    p/<ACC>.json            one study's BioSamples and runs (loaded when a record page opens)
    ix/<NN>.json            BioSample and run accession -> study accessions, split by the last
                            two digits of the accession

Nothing here is computed from a moving catalog: every number comes from the release.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List

from .release import Release
from .util import fmt_duration, log, num, paint, scrub_secrets, utc_now

DATA_VERSION = 1
URBAN = ("confirmed_urban", "probable_urban")
NO_PROJECT = "_none"
FIGURE_EXT = {".png", ".svg", ".jpg"}
TABLE_EXT = {".tsv", ".csv"}
MAX_TABLE_BYTES = 5_000_000   # larger tables stay in the release download


def _dump(obj: Any) -> bytes:
    return scrub_secrets(json.dumps(obj, ensure_ascii=False, separators=(",", ":"))).encode("utf-8")


def _write_if_changed(path: str, data: bytes) -> bool:
    """Write only when the content differs, so a rebuild touches only what changed."""
    try:
        with open(path, "rb") as fh:
            if fh.read() == data:
                return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    return True


def safe_name(accession: str) -> str:
    """File name for a study's record file (same rule as uma.js)."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", accession or NO_PROJECT)


def ix_bucket(accession: str) -> str:
    """Last two digits of an accession, zero-padded; 'xx' when it has none (same rule as uma.js)."""
    digits = re.sub(r"\D", "", accession or "")
    return digits[-2:].zfill(2) if digits else "xx"


def _round(x: Any, nd: int = 4) -> Any:
    return round(x, nd) if isinstance(x, float) else x


# ------------------------------------------------------------------ findings
def _findings(release: Release, out_dir: str) -> Dict[str, Any]:
    """STRIGA results: statuses from hypotheses_status.tsv, details and files from each hypotheses/<ID>/."""
    dst_root = os.path.join(out_dir, "findings")
    if os.path.isdir(dst_root):
        shutil.rmtree(dst_root)
    manifest_path = release.file("analysis/striga_manifest.json")
    if not manifest_path:
        return {"v": DATA_VERSION, "available": False, "hypotheses": []}
    with open(manifest_path, encoding="utf-8") as fh:
        striga = json.load(fh)
    rows: List[Dict[str, str]] = []
    status_path = release.file("analysis/hypotheses_status.tsv")
    if status_path:
        with open(status_path, encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split("\t")
            rows = [dict(zip(header, line.rstrip("\n").split("\t"))) for line in fh if line.strip()]
    registry: Dict[str, Dict[str, Any]] = {}
    if release.file("analysis/report.json"):
        with open(release.file("analysis/report.json"), encoding="utf-8") as fh:
            registry = {r.get("id"): r for r in (json.load(fh).get("hypotheses") or [])}
    src_root = release.file("analysis/hypotheses")
    out = []
    for r in rows:
        hid = r["id"]
        entry: Dict[str, Any] = {k: r.get(k, "") for k in ("id", "track", "program", "title", "status", "result")}
        for k in ("method", "decision_rule"):  # registry columns, shown when STRIGA provides them
            if registry.get(hid, {}).get(k):
                entry[k] = registry[hid][k]
        d_dir = os.path.join(src_root, hid) if src_root else ""
        if d_dir and os.path.exists(os.path.join(d_dir, "summary.json")):
            with open(os.path.join(d_dir, "summary.json"), encoding="utf-8") as fh:
                d = json.load(fh)
            entry.update({"question": d.get("question", ""), "caveats": d.get("caveats") or [],
                          "results": d.get("results") or {}, "generated_utc": d.get("generated_utc")})
            figures, tables, other = [], [], []
            for name in sorted(os.listdir(d_dir)):
                if name == "summary.json":
                    continue
                path = os.path.join(d_dir, name)
                ext = os.path.splitext(name)[1].lower()
                if ext in FIGURE_EXT or (ext in TABLE_EXT and os.path.getsize(path) <= MAX_TABLE_BYTES):
                    os.makedirs(os.path.join(dst_root, hid), exist_ok=True)
                    shutil.copyfile(path, os.path.join(dst_root, hid, name))
                    (figures if ext in FIGURE_EXT else tables).append(f"findings/{hid}/{name}")
                else:
                    other.append(name)
            entry.update({"figures": figures, "tables": tables, "release_only_files": other})
        out.append(entry)
    return {"v": DATA_VERSION, "available": True, "pipeline": striga.get("pipeline"), "input": striga.get("input"),
            "created_utc": striga.get("created_utc"), "params": striga.get("params"),
            "status_counts": dict(Counter(e["status"] for e in out)), "hypotheses": out}


# ------------------------------------------------------------------ records
SAMPLE_COLS = ["accession", "title", "tier", "context", "collection_date", "collection_year", "country", "region",
               "place_id", "place", "location_status", "lat", "lon", "submitted_location", "isolation_source",
               "env_broad_scale", "env_local_scale", "env_medium", "eligibility_reason"]
RUN_COLS = ["accession", "sample", "experiment", "assay", "strategy", "source", "layout", "platform", "instrument",
            "bases", "spots", "release_date", "download_url"]


def _records(con: sqlite3.Connection, out_dir: str) -> Dict[str, Any]:
    def q(sql: str) -> List[tuple]:
        return con.execute(sql).fetchall()

    countries = {r[0]: {"name": r[1], "continent": r[2]} for r in q("SELECT iso2, name, continent FROM countries")}
    admin1 = {r[0]: r[1] for r in q("SELECT code, name FROM admin1")}
    places = {r[0]: r[1:] for r in q("SELECT geonames_id, name, country_iso2, admin1_code, lat, lon, population FROM places")}

    # ---- BioSamples with their accepted location (a country or place only when verified or probable)
    log("  reading BioSamples")
    samples: Dict[str, List[Any]] = {}
    for r in q("""
        SELECT s.accession, s.title, s.urban_status, s.urban_context, s.collection_date, s.collection_year,
               CASE WHEN l.country_status IN ('verified','probable') THEN l.country_iso2 END,
               CASE WHEN l.country_status IN ('verified','probable') THEN l.admin1_code END,
               l.place_id, l.status, s.lat, s.lon, s.geo_loc_raw, s.isolation_source,
               s.env_broad_scale, s.env_local_scale, s.env_medium, s.eligibility_reason
        FROM samples s LEFT JOIN sample_locations l ON l.sample_accession = s.accession"""):
        (acc, title, tier, ctx, cdate, cyear, iso, a1, pid, lstatus, lat, lon, raw, src, ebs, els, em, reason) = r
        pl = places.get(pid) if pid else None
        samples[acc] = [acc, title, tier, ctx, cdate, cyear, iso, admin1.get(a1) if a1 else None, pid,
                        pl[0] if pl else None, lstatus, _round(lat), _round(lon), raw, src, ebs, els, em, reason]

    # ---- runs, grouped by study
    log("  reading runs")
    runs_by_project: Dict[str, List[List[Any]]] = defaultdict(list)
    samples_by_project: Dict[str, set] = defaultdict(set)
    projects_of_sample: Dict[str, set] = defaultdict(set)
    for r in q("""
        SELECT r.accession, r.sample_accession, r.experiment_accession, e.assay_class, e.library_strategy,
               e.library_source, e.library_layout, e.platform, e.instrument_model, r.bases, r.spots,
               substr(r.release_date, 1, 10), r.download_url, coalesce(r.project_accession, e.project_accession)
        FROM runs r LEFT JOIN experiments e ON e.accession = r.experiment_accession"""):
        proj = r[13] or NO_PROJECT
        runs_by_project[proj].append(list(r[:13]))
        if r[1]:
            samples_by_project[proj].add(r[1])
            projects_of_sample[r[1]].add(proj)
    for acc, proj in q("SELECT sample_accession, project_accession FROM project_samples"):
        if acc in samples and proj:
            samples_by_project[proj].add(acc)
            projects_of_sample[acc].add(proj)
    projects = {r[0]: r[1:] for r in q("SELECT accession, title, description, center_name, data_type, submission_date "
                                         "FROM projects")}
    order = sorted(set(runs_by_project) | set(samples_by_project))

    # ---- one record file per study; study, place and country indexes
    log(f"  writing {num(len(order))} study files")
    p_dir = os.path.join(out_dir, "p")
    os.makedirs(p_dir, exist_ok=True)
    keep, written, study_rows, counted = set(), 0, [], set()
    place_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"samples": 0, "urban": 0, "studies": set()})
    country_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"samples": 0, "urban": 0, "studies": set()})
    for proj in order:
        meta = projects.get(proj, (None,) * 5)
        srows = [samples[a] for a in sorted(samples_by_project.get(proj, ())) if a in samples]
        rrows = sorted(runs_by_project.get(proj, []), key=lambda x: x[0])
        doc = {"v": DATA_VERSION, "accession": proj, "title": meta[0], "description": meta[1], "center": meta[2],
               "data_type": meta[3], "submission_date": meta[4],
               "sample_cols": SAMPLE_COLS, "samples": srows, "run_cols": RUN_COLS, "runs": rrows,
               "sample_projects": {s[0]: sorted(projects_of_sample[s[0]]) for s in srows
                                   if len(projects_of_sample[s[0]]) > 1}}
        name = safe_name(proj) + ".json"
        keep.add(name)
        written += _write_if_changed(os.path.join(p_dir, name), _dump(doc))
        tiers = Counter(s[2] for s in srows)
        years = [r[11][:4] for r in rrows if r[11]]
        study_rows.append([proj, meta[0], meta[2], len(srows), len(rrows),
                           tiers["confirmed_urban"] + tiers["probable_urban"],
                           min(years) if years else None, max(years) if years else None,
                           [c for c, _ in Counter(s[6] for s in srows if s[6]).most_common(3)],
                           [c for c, _ in Counter(s[3] for s in srows if s[3] and s[2] in URBAN).most_common(2)],
                           [a for a, _ in Counter(r[3] for r in rrows if r[3]).most_common(3)]])
        for s in srows:
            if s[8]:
                place_stats[s[8]]["studies"].add(proj)
            if s[6]:
                country_stats[s[6]]["studies"].add(proj)
            if s[0] in counted:   # a BioSample shared by two studies counts once
                continue
            counted.add(s[0])
            urban = s[2] in URBAN
            for key, stats in ((s[8], place_stats), (s[6], country_stats)):
                if key:
                    stats[key]["samples"] += 1
                    stats[key]["urban"] += urban
    removed = 0
    for name in os.listdir(p_dir):
        if name.endswith(".json") and name not in keep:
            os.remove(os.path.join(p_dir, name))
            removed += 1

    # ---- accession index: BioSample -> [studies], run -> study
    ix: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for acc, projs in projects_of_sample.items():
        ix[ix_bucket(acc)][acc] = sorted(projs)
    for proj, rows in runs_by_project.items():
        for r in rows:
            ix[ix_bucket(r[0])][r[0]] = proj
    for bucket, entries in ix.items():
        _write_if_changed(os.path.join(out_dir, "ix", f"{bucket}.json"), _dump(dict(sorted(entries.items()))))

    studies = {"v": DATA_VERSION, "cols": ["accession", "title", "center", "samples", "runs", "urban_samples",
                                            "first_year", "last_year", "countries", "habitats", "assays"],
               "rows": sorted(study_rows, key=lambda r: (-r[3], r[0]))}
    place_rows = []
    for pid, st in place_stats.items():
        name, iso, a1, lat, lon, pop = places[pid]
        place_rows.append([pid, name, iso, admin1.get(a1) if a1 else None, _round(lat), _round(lon), pop,
                           st["samples"], st["urban"], sorted(st["studies"])])
    country_rows = [[iso, countries.get(iso, {}).get("name", iso), countries.get(iso, {}).get("continent"),
                     st["samples"], st["urban"], len(st["studies"])] for iso, st in country_stats.items()]
    placedoc = {"v": DATA_VERSION, "attribution": "Place names and identifiers: GeoNames (geonames.org), CC BY 4.0",
                "place_cols": ["id", "name", "country", "region", "lat", "lon", "population", "samples",
                               "urban_samples", "studies"],
                "places": sorted(place_rows, key=lambda r: (-r[7], r[0])),
                "country_cols": ["iso2", "name", "continent", "samples", "urban_samples", "studies"],
                "countries": sorted(country_rows, key=lambda r: (-r[3], r[0]))}
    log(f"  p/: {num(len(keep))} study files ({num(written)} written, {num(removed)} removed); "
        f"ix/: {num(len(ix))} files; {num(len(place_rows))} places")
    return {"studies": studies, "places": placedoc, "counts": {"studies": len(keep), "places": len(place_rows),
                                                               "biosamples": len(counted)}}


# ------------------------------------------------------------------ release
def _release_doc(release: Release, con: sqlite3.Connection, findings: Dict[str, Any]) -> Dict[str, Any]:
    m = release.manifest
    tiers = dict(con.execute("SELECT urban_status, count(*) FROM samples GROUP BY 1").fetchall())
    habitats = con.execute("""SELECT urban_context, count(*) FROM samples
                              WHERE urban_status IN ('confirmed_urban','probable_urban') AND urban_context IS NOT NULL
                              GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    return {"v": DATA_VERSION, "contract": m.get("contract"), "version": release.version, "doi": m.get("doi"),
            "url": m.get("url") or f"https://github.com/aglucaci/UMDB/releases/tag/v{release.version}",
            "created_utc": m.get("created_utc"), "database_built_utc": m.get("database_built_utc"),
            "schema_version": m.get("schema_version"), "eligibility_rules_version": m.get("eligibility_rules_version"),
            "geo_rules_version": m.get("geo_rules_version"), "query_profiles_version": m.get("query_profiles_version"),
            "counts": m.get("counts") or {}, "tiers": tiers, "urban_habitats": habitats,
            "license": m.get("license"), "licenses": m.get("licenses") or {}, "collections": m.get("collections") or [],
            "files": {k: {"bytes": v.get("bytes"), "sha256": v.get("sha256")}
                      for k, v in (m.get("files") or {}).items() if not k.startswith("analysis/")},
            "analysis": {"available": findings.get("available", False), "pipeline": findings.get("pipeline"),
                         "status_counts": findings.get("status_counts")},
            "built_utc": utc_now()}


def build_site(release: Release, out_dir: str = os.path.join("docs", "data")) -> Dict[str, Any]:
    t0 = time.time()
    db = release.database()
    log(f"Building UMA data in {out_dir}/ from UMDB release {paint(release.version, 'num')}")
    os.makedirs(out_dir, exist_ok=True)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    findings = _findings(release, out_dir)
    log(f"  findings: {len(findings['hypotheses'])} hypotheses" if findings["available"]
        else "  findings: none in this release")
    rec = _records(con, out_dir)
    rel = _release_doc(release, con, findings)
    con.close()
    for name, doc in (("release.json", rel), ("findings.json", findings), ("studies.json", rec["studies"]),
                      ("places.json", rec["places"])):
        _write_if_changed(os.path.join(out_dir, name), _dump(doc))
    log(f"{paint('UMA data ready', 'good')} in {fmt_duration(time.time() - t0)}: release {release.version}, "
        f"{num(rec['counts']['studies'])} studies, {num(rec['counts']['places'])} places")
    return rel
