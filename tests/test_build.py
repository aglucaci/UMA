"""UMA build tests on a tiny UMDB release (tests/fixtures/release, contract umdb-release/1).

The fixture is written by UMDB's own release code from UMDB's test catalog (two BioSamples,
three runs, two BioProjects, one with two assays) plus a minimal STRIGA results folder.
Run: python3 -m unittest discover tests   (or: bin/uma test)
"""
import json
import os
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
        os.makedirs(os.path.join(cls.tmp.name, "docs", "assets"))
        cls.out = os.path.join(cls.tmp.name, "docs", "db")
        os.makedirs(cls.out)
        with open(os.path.join(cls.out, "srr_records_part000.json"), "w") as fh:
            fh.write("[]")
        cls.release = Release(rel, work_dir=os.path.join(cls.tmp.name, "db"))
        cls.manifest = build.build_site(cls.release, cls.out)
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

    def test_cube_totals_equal_sqlite_counts(self):
        cube, samples, summary = self.load("cube.json"), self.load("samples.json"), self.load("summary.json")
        rix = {k: i for i, k in enumerate(cube["cols"])}
        six = {k: i for i, k in enumerate(samples["cols"])}
        self.assertEqual(sum(r[rix["runs"]] for r in cube["rows"]), self.q("SELECT count(*) FROM runs"))
        self.assertEqual(sum(r[six["samples"]] for r in samples["rows"]),
                         self.q("SELECT count(DISTINCT sample_accession) FROM runs"))
        self.assertEqual((summary["totalRuns"], summary["totalBioSamples"], summary["totalProjects"]), (3, 2, 2))
        # the two-assay, two-project sample sits in one row, with set-valued dims
        D = samples["dims"]
        multi = [r for r in samples["rows"] if len(D["assaysets"][r[six["assays"]]]) == 2]
        self.assertEqual(len(multi), 1)
        self.assertEqual(len(D["projsets"][multi[0][six["projects"]]]), 2)

    def test_geography_and_project_files(self):
        geo, projects = self.load("geo.json"), self.load("projects.json")
        self.assertEqual([p[1] for p in geo["places"]], ["New York City"])
        self.assertIn("GeoNames", geo["attribution"])
        acc = projects["rows"][0][0]
        shard = self.load(os.path.join("p", build.shard_name(acc)))
        self.assertEqual(len(shard["runs"]), projects["rows"][0][5])
        self.assertFalse(os.path.exists(os.path.join(self.out, "srr_records_part000.json")))  # legacy removed

    def test_release_is_recorded(self):
        m = self.load("manifest.json")
        self.assertEqual(m["release"]["version"], "0.0.0-test")
        self.assertEqual(m["release"]["analysis"]["name"], "STRIGA")
        self.assertEqual(m["counts"]["biosamples"], 2)

    def test_collections_templates_and_analysis_come_from_the_release(self):
        self.assertEqual(len(self.load("collections.json")["collections"]), 6)
        self.assertTrue(os.path.exists(os.path.join(self.out, "collections", "global-wastewater.tsv.gz")))
        tpl = os.path.join(os.path.dirname(self.out), "assets", "cohort-templates.json")
        self.assertIn("readme", json.load(open(tpl)))
        a = self.load("analysis.json")
        self.assertTrue(a["available"])
        self.assertEqual([(h["id"], h["status"]) for h in a["hypotheses"]], [("C1", "supported")])
        self.assertEqual(a["pipeline"]["version"], "0.2.0")

    def test_unchanged_project_files_are_not_rewritten(self):
        acc = self.load("projects.json")["rows"][0][0]
        path = os.path.join(self.out, "p", build.shard_name(acc))
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


class IndexTests(unittest.TestCase):
    def test_ix_bucket_matches_browser(self):
        # docs/assets/db.js: last two digits of the accession, zero-padded; 'xx' without digits
        self.assertEqual(build.ix_bucket("SAMN03270027"), "27")
        self.assertEqual(build.ix_bucket("SRR5"), "05")
        self.assertEqual(build.ix_bucket("ABC"), "xx")


@unittest.skipUnless(shutil.which("node"), "needs node")
class BrowserParityTests(unittest.TestCase):
    def test_workspace_prng_matches_umdb(self):
        # UMDB's tests/test_cohorts.py checks the Python mulberry32 against these same values,
        # so a cohort balanced in the Workspace equals `umdb cohort export` of the same definition.
        js = os.path.join(ROOT, "docs", "assets", "workspace.js")
        src = open(js, encoding="utf-8").read()
        start = src.index("function mulberry32")
        body = src[start:src.index("\n  }\n", start) + 4]
        out = subprocess.run(["node", "-e", body + "\nconst r = mulberry32(20261119);"
                              "console.log([r(), r(), r(), r()].map((x) => x.toFixed(12)).join(' '))"],
                             capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(out, ["0.582067719661", "0.366967471316", "0.278875814751", "0.921800950775"])


if __name__ == "__main__":
    unittest.main()


class ReleaseFolderTests(unittest.TestCase):
    def test_build_leaves_the_release_folder_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            before = sorted(os.listdir(FIXTURE))
            r = Release(FIXTURE, work_dir=d)
            self.assertTrue(r.database().startswith(d))
            self.assertEqual(sorted(os.listdir(FIXTURE)), before)
