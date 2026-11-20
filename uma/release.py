"""Reading a UMDB data release (contract umdb-release/1).

A release folder, as written by `umdb release` in the UMDB repository, holds (among other files)
what UMA reads:

  manifest.json                     contract, version, DOI, dates, counts, licences, file checksums
  umdb.sqlite.zst | umdb.sqlite.gz  the catalog database (or an uncompressed umdb.sqlite)
  analysis/                         STRIGA results (striga_manifest.json, hypotheses_status.tsv, report.json,
                                    hypotheses/<ID>/), optional

UMA only reads releases; it never talks to NCBI or to the UMDB harvester.
"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import urllib.request
from typing import Any, Dict, Optional

from .util import log

CONTRACTS = {"umdb-release/1"}
UMDB_REPO = "aglucaci/UMDB"
CACHE_DIR = "releases"   # git-ignored


class Release:
    def __init__(self, path: str, work_dir: Optional[str] = None):
        self.path = os.path.abspath(path)
        # where a compressed database is unpacked; never inside the release folder, which stays as published
        self.work_dir = os.path.abspath(work_dir or os.path.join(CACHE_DIR, ".db"))
        mf = os.path.join(self.path, "manifest.json")
        if not os.path.exists(mf):
            raise FileNotFoundError(f"{mf} not found: is {path} an unpacked UMDB release?")
        with open(mf, encoding="utf-8") as fh:
            self.manifest: Dict[str, Any] = json.load(fh)
        contract = self.manifest.get("contract")
        if contract not in CONTRACTS:
            raise ValueError(f"{path}: release contract {contract!r} is not supported by this UMA "
                             f"(supports {', '.join(sorted(CONTRACTS))}); update UMA or use an older release")
        self.version: str = self.manifest["version"]

    def file(self, rel: str) -> Optional[str]:
        p = os.path.join(self.path, rel)
        return p if os.path.exists(p) else None

    def database(self) -> str:
        """Path to the uncompressed SQLite database (unpacked once into work_dir, keyed by version and size)."""
        plain = os.path.join(self.path, "umdb.sqlite")
        if os.path.exists(plain):
            return plain
        zst, gz = self.file("umdb.sqlite.zst"), self.file("umdb.sqlite.gz")
        if not (zst or gz):
            raise FileNotFoundError(f"no umdb.sqlite[.zst|.gz] in {self.path}")
        src_size = os.path.getsize(zst or gz)
        plain = os.path.join(self.work_dir, f"umdb-{self.version}-{src_size}.sqlite")
        if os.path.exists(plain):
            return plain
        os.makedirs(self.work_dir, exist_ok=True)
        log(f"Decompressing {os.path.basename(zst or gz)} to {plain}")
        tmp = plain + ".part"
        if gz:
            with gzip.open(gz, "rb") as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        else:
            try:
                from compression import zstd  # type: ignore[import-not-found]  # Python 3.14+
                with zstd.open(zst, "rb") as src, open(tmp, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
            except ImportError:
                subprocess.run(["zstd", "-d", "-q", "-f", zst, "-o", tmp], check=True)
        os.replace(tmp, plain)
        return plain

    def info(self) -> Dict[str, Any]:
        """What the site says about the release it shows."""
        m = self.manifest
        return {"version": self.version, "doi": m.get("doi"), "created_utc": m.get("created_utc"),
                "database_built_utc": m.get("database_built_utc"), "url": m.get("url"),
                "analysis": (m.get("analysis") or {}).get("pipeline")}


def fetch(version: str = "latest", repo: str = UMDB_REPO, dest: str = CACHE_DIR) -> str:
    """Download a release's assets from GitHub Releases (tag v<version>) into releases/<version>/."""
    api = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if version == "latest" else f"tags/v{version}")
    with urllib.request.urlopen(urllib.request.Request(api, headers={"Accept": "application/vnd.github+json"})) as r:
        rel = json.load(r)
    tag = rel["tag_name"]
    out = os.path.join(dest, tag.lstrip("v"))
    os.makedirs(out, exist_ok=True)
    # Assets are the release's files flattened with '__' for '/', e.g. collections__global-wastewater.tsv.gz,
    # or one umdb-<version>.tar.gz bundle, which is unpacked.
    for a in rel.get("assets", []):
        name = a["name"]
        target = os.path.join(out, name.replace("__", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.path.exists(target):
            log(f"  {name} ({a['size'] / 1e6:.1f} MB)")
            urllib.request.urlretrieve(a["browser_download_url"], target)
        if name.endswith(".tar.gz") and name.startswith("umdb-"):
            shutil.unpack_archive(target, out)
    nested = [d for d in os.listdir(out) if os.path.isdir(os.path.join(out, d)) and
              os.path.exists(os.path.join(out, d, "manifest.json"))]
    return os.path.join(out, nested[0]) if not os.path.exists(os.path.join(out, "manifest.json")) and nested else out
