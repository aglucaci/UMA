"""Small helpers shared by the UMA build (logging, number formatting, secret scrubbing)."""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
import time
from typing import Any

VERBOSITY = int(os.environ.get("UMA_VERBOSITY", "1"))
COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
_STYLES = {"good": "32", "warn": "33", "bad": "31", "num": "36", "dim": "2", "head": "1;34"}


def paint(text: Any, style: str) -> str:
    text = str(text)
    if not COLOR or style not in _STYLES:
        return text
    return f"\033[{_STYLES[style]}m{text}\033[0m"


def num(value: Any) -> str:
    return paint(f"{value:,}" if isinstance(value, int) else value, "num")


def log(msg: str, level: int = 1) -> None:
    if VERBOSITY >= level:
        print(f"{paint('[' + time.strftime('%H:%M:%S') + ']', 'dim')} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{paint('warning:', 'warn')} {msg}", file=sys.stderr, flush=True)


def fmt_duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s" if m else f"{s}s"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# A release never contains NCBI keys, but submitter text is copied verbatim into the
# project files, so strip api_key= / email= query parameters defensively.
_SECRET_FIRST = re.compile(r"\?(?:api_key|email)=[^&\"'\s\\<>]*&?")
_SECRET_LATER = re.compile(r"&(?:api_key|email)=[^&\"'\s\\<>]*")


def scrub_secrets(text: str) -> str:
    if "api_key=" not in text and "email=" not in text:
        return text
    return _SECRET_LATER.sub("", _SECRET_FIRST.sub("?", text))
