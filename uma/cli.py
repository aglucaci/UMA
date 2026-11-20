"""uma: build and preview the UMA website from a UMDB data release.

  uma fetch [VERSION|latest]     download a release from github.com/aglucaci/UMDB into releases/<version>/
  uma build RELEASE [--doi DOI]  write docs/data/ from a release folder, a version, or 'latest'
  uma serve [--port 8765]        preview docs/ at http://localhost:8765
  uma test                       run the unit tests
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
import unittest

from . import __version__
from .release import CACHE_DIR, Release, fetch
from .util import log, paint


def _release_path(arg: str, repo: str) -> str:
    """A release folder, a version already fetched into releases/, or a version (or 'latest') to fetch now."""
    if os.path.isdir(arg):
        return arg
    cached = os.path.join(CACHE_DIR, arg.lstrip("v"))
    if arg != "latest" and os.path.isdir(cached):
        if os.path.exists(os.path.join(cached, "manifest.json")):
            return cached
        nested = [d for d in os.listdir(cached) if os.path.exists(os.path.join(cached, d, "manifest.json"))]
        if nested:
            return os.path.join(cached, nested[0])
    log(f"Fetching UMDB release {arg} from github.com/{repo}")
    return fetch(arg, repo)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="uma", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"uma {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download a UMDB release from GitHub Releases")
    f.add_argument("version", nargs="?", default="latest")
    f.add_argument("--repo", default="aglucaci/UMDB")
    b = sub.add_parser("build", help="build docs/data/ from a UMDB release")
    b.add_argument("release", help="release folder, a version (fetched if needed) or 'latest'")
    b.add_argument("--out", default=os.path.join("docs", "data"))
    b.add_argument("--repo", default="aglucaci/UMDB")
    b.add_argument("--doi", default="", help="DOI of the release, when it was minted after the release was built")
    s = sub.add_parser("serve", help="preview docs/")
    s.add_argument("--port", type=int, default=8765)
    sub.add_parser("test", help="run the unit tests")
    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        path = fetch(a.version, a.repo)
        log(f"{paint('Fetched', 'good')} UMDB release into {path}/; next: uma build {path}")
    elif a.cmd == "build":
        from .build import build_site
        release = Release(_release_path(a.release, a.repo))
        if a.doi:
            release.manifest["doi"] = a.doi
        build_site(release, a.out)
    elif a.cmd == "serve":
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory="docs")
        log(f"Serving docs/ at http://localhost:{a.port} (Ctrl-C stops)")
        http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler).serve_forever()
    elif a.cmd == "test":
        res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover("tests"))
        sys.exit(0 if res.wasSuccessful() else 1)
