"""أدوات مشتركة: المسارات، والتزامات المصادر، وسجلّ السمة، والمطابقة المشكولة."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from contextlib import contextmanager
from functools import lru_cache

HOME = os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net"))
REPOS = {
    "hfn": os.path.join(HOME, "HusseinFrameNet"),
    "wazn": os.path.join(HOME, "Arabic-Mother-language-wazn-net"),
    "amln": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "maqayis": os.path.join(HOME, "Maqaiys-roots"),
}

# الحالة (status) — والمرتبة (rank) دائماً CANDIDATE حتى يحكم المالك
MEASURED = "MEASURED_ACCEPTED"     # مسلكٌ قيس فبلغ حدّ ويلسون الأدنى ≥ 0.78
RELEASE = "RELEASE_CANDIDATE"      # من إصدار HFN المتحقَّق بـ MANIFEST
OCR = "UNVERIFIED_OCR"             # نصّ معجم مستخرج آلياً لم يُحقَّق

_SUKUN = "ْ"
_HARAKAT = re.compile("[ً-ْٰـ]")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())


def K(s: str) -> str:
    """مفتاح الجذر (حروف بلا حركات، والهمزات ← ء، ى ← ي) — للجذر وحده، لا للكلمة."""
    s = _HARAKAT.sub("", nfc(s))
    for a in "أإآؤئ":
        s = s.replace(a, "ء")
    return s.replace("ى", "ي").replace(" ", "")


def match_kind(found: str, query: str) -> str:
    """EXACT: الحروف والحركات معاً بعد NFC. SUKUN_ONLY: لا فرق إلا السكون. LETTERS: الحروف وحدها."""
    f, q = nfc(found), nfc(query)
    if f == q:
        return "EXACT"
    if f.replace(_SUKUN, "") == q.replace(_SUKUN, ""):
        return "SUKUN_ONLY"
    return "LETTERS"


def feature(name, value, *, provider, status, source, route="", measure="", match="EXACT", evidence="", **extra):
    r = dict(feature=name, value=value, provider=provider, status=status, rank="CANDIDATE", is_fact=False,
             route=route, measure=measure, source=source, match=match, evidence=evidence)
    r.update(extra)
    return r


@lru_cache(maxsize=None)
def commit(repo: str) -> str:
    try:
        return subprocess.run(["git", "-C", REPOS[repo], "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


@contextmanager
def on_path(p: str):
    """إضافةٌ مؤقّتة إلى sys.path تُزال بعد الاستيراد (wazn-net فيها حزمتا core وengines في أعلاها)."""
    added = p not in sys.path
    if added:
        sys.path.insert(0, p)
    try:
        yield
    finally:
        if added and p in sys.path:
            sys.path.remove(p)
