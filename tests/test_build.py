"""UMA build tests on a tiny UMDB release (tests/fixtures/release, contract umdb-release/1).

The fixture is written by UMDB's own release code from UMDB's test catalog (two BioSamples,
three runs, two BioProjects, one BioSample in both with two assays) plus a minimal STRIGA
results folder. Run: python3 -m unittest discover tests   (or: bin/uma test)
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from uma import build  # noqa: E402
from uma.release import Release  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "release")


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        rel = os.path.join(cls.tmp.name, "release")
        shutil.copytree(FIXTURE, rel)
        cls.out = os.path.join(cls.tmp.name, "docs", "data")
        os.makedirs(os.path.join(cls.out, "p"))
        open(os.path.join(cls.out, "p", "PRJOLD1.json"), "w").write("{}")   # a study no longer in the release
        cls.release = Release(rel, work_dir=os.path.join(cls.tmp.name, "db"))
        cls.doc = build.build_site(cls.release, cls.out)
        cls.con = sqlite3.connect(cls.release.database())

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def load(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as fh:
            return json.load(fh)

    def q(self, sql):
        return self.con.execute(sql).fetchone()[0]

    def test_release_document(self):
        r = self.load("release.json")
        self.assertEqual((r["version"], r["contract"]), ("0.0.0-test", "umdb-release/1"))
        self.assertEqual(r["analysis"]["pipeline"]["name"], "STRIGA")
        self.assertEqual(sum(r["tiers"].values()), self.q("SELECT count(*) FROM samples"))
        self.assertTrue(all(not k.startswith("analysis/") for k in r["files"]))

    def test_findings_and_their_files(self):
        f = self.load("findings.json")
        self.assertTrue(f["available"])
        (h,) = f["hypotheses"]
        self.assertEqual((h["id"], h["status"], h["result"]), ("C1", "supported", "ok"))
        self.assertEqual(f["status_counts"], {"supported": 1})

    def test_studies_index_counts_match_the_database(self):
        s = self.load("studies.json")
        rows = [dict(zip(s["cols"], r)) for r in s["rows"]]
        self.assertEqual(sorted(r["accession"] for r in rows), ["PRJNA1", "PRJNA2"])
        self.assertEqual(sum(r["runs"] for r in rows), self.q("SELECT count(*) FROM runs"))
        prj2 = next(r for r in rows if r["accession"] == "PRJNA2")
        self.assertEqual(prj2["assays"], ["16S"])

    def test_study_files_and_accession_index(self):
        d = self.load("p/PRJNA2.json")
        samples = [dict(zip(d["sample_cols"], r)) for r in d["samples"]]
        self.assertEqual([s["accession"] for s in samples], ["SAMN1"])
        self.assertEqual(samples[0]["place"], "New York City")
        self.assertEqual(d["sample_projects"], {"SAMN1": ["PRJNA1", "PRJNA2"]})
        self.assertFalse(os.path.exists(os.path.join(self.out, "p", "PRJOLD1.json")))  # removed
        self.assertEqual(self.load(f"ix/{build.ix_bucket('SAMN1')}.json")["SAMN1"], ["PRJNA1", "PRJNA2"])
        self.assertEqual(self.load(f"ix/{build.ix_bucket('SRR3')}.json")["SRR3"], "PRJNA2")

    def test_places_count_each_biosample_once(self):
        p = self.load("places.json")
        places = [dict(zip(p["place_cols"], r)) for r in p["places"]]
        nyc = next(x for x in places if x["name"] == "New York City")
        self.assertEqual(nyc["samples"], 1)                 # SAMN1 is in two studies
        self.assertEqual(nyc["studies"], ["PRJNA1", "PRJNA2"])
        us = [dict(zip(p["country_cols"], r)) for r in p["countries"]][0]
        self.assertEqual((us["iso2"], us["samples"], us["studies"]), ("US", 1, 2))

    def test_rebuild_leaves_unchanged_files_alone(self):
        path = os.path.join(self.out, "p", "PRJNA1.json")
        mtime = os.path.getmtime(path)
        build.build_site(self.release, self.out)
        self.assertEqual(os.path.getmtime(path), mtime)


class ReleaseTests(unittest.TestCase):
    def test_unknown_contract_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "manifest.json"), "w") as fh:
                json.dump({"contract": "umdb-release/99", "version": "x"}, fh)
            with self.assertRaisesRegex(ValueError, "not supported"):
                Release(d)

    def test_build_leaves_the_release_folder_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            before = sorted(os.listdir(FIXTURE))
            self.assertTrue(Release(FIXTURE, work_dir=d).database().startswith(d))
            self.assertEqual(sorted(os.listdir(FIXTURE)), before)


@unittest.skipUnless(shutil.which("node"), "needs node")
class BrowserParityTests(unittest.TestCase):
    """uma.js must find files with the same names the builder writes."""

    def js(self, expr):
        src = open(os.path.join(ROOT, "docs", "assets", "uma.js"), encoding="utf-8").read()
        body = "\n".join(re.findall(r"^  const (?:safeName|ixBucket) = .*$", src, re.M))
        return subprocess.run(["node", "-e", body + f"\nconsole.log(JSON.stringify({expr}))"],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_ix_bucket_and_file_names_match(self):
        for acc in ("SAMN03270027", "SRR5", "ABC", "PRJNA271013"):
            self.assertEqual(json.loads(self.js(f"ixBucket({json.dumps(acc)})")), build.ix_bucket(acc))
        for acc in ("PRJNA271013", "odd/name", ""):
            self.assertEqual(json.loads(self.js(f"safeName({json.dumps(acc)})")), build.safe_name(acc or "_none"))


if __name__ == "__main__":
    unittest.main()
