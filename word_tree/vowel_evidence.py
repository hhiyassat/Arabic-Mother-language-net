"""
vowel_evidence.py — هل اختلاف التشكيل اختلافُ فعلٍ أم خطأُ رسم؟ (قراءة فقط؛ CANDIDATE)

القاعدة (حكم المالك 2026-11-06): المطابقة بالحروف والحركات معاً، ولكن التشكيل المخالف
لا يُرفض إلا بدليل — من أيّ مصدر عندنا، ومنه الترجمة الإنجليزية في WordNet. فالتشكيل قد يكون
خطأً في المصدر (WordNet موحَّد بلا حركات بحكم L1، والوسيط يكتب «اصْفَرَ» بلا شدّة).

الأحكام (verdict):
  EXACT            الحروف والحركات معاً بعد NFC                                   → يُبقى
  SUKUN_ONLY       لا فرق إلا السكون                                              → يُبقى، معلَّماً
  UNVOWELLED_QUERY السؤال بلا حركات (كما يرد من WordNet)                          → يُبقى، معلَّماً
  UNRESOLVED       تشكيلٌ مخالف ولا دليل على أنّه فعلٌ آخر                         → يُبقى، معلَّماً (لا يُرفض)
  DIFFERENT_VERB   تشكيلٌ مخالف ودليلٌ مسمّى على أنّه فعلٌ آخر                      → يُرفض، بدليله

الأدلّة (كلٌّ منها يكفي للرفض، ويُذكر بمصدره):
  HFN      التشكيلان كلاهما حدثٌ مستقلّ في HFN (معرّفان ووزنان).
  WASIT    الوسيط يفرد لكلٍّ من التشكيلين مدخلاً مشكولاً يوافقه ويخالف الآخر (wasit_frames.compatible).
  فإن لم يُشهد إلا لأحد التشكيلين فالآخر قد يكون خطأ رسمٍ له → لا دليل.
  EN       الترجمة الإنجليزية: أطر الفعل في synset مسمّى (WordNet frames) تخالف تعدّي الموجود.
           تُسجَّل في evidence ويُعلَّم en_conflict، ولا تَرفض وحدها: قيس الرفض بها على WordNet
           فصحّ 10/15 (ويلسون 0.42، دون 0.78) — التعدّي في الإنجليزية غير التعدّي في العربية
           (خدع/cheat.v.03 لازم هناك متعدٍّ هنا). ولا تُستعمل إلا مع synset مسمّى.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from functools import lru_cache

_AMLN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _hfn_rel():
    """AMLN_HFN_RELEASE أو أحدث release_vN فيه MANIFEST (كما في hfn_release.py؛ مكرَّر هنا لأنّ الوحدة تُحمَّل منفردة)."""
    if os.environ.get("AMLN_HFN_RELEASE"):
        return os.environ["AMLN_HFN_RELEASE"]
    b = os.path.join(os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net")), "HusseinFrameNet", "release")
    if not os.path.isdir(b):
        return "release_v45"
    r = [d for d in os.listdir(b) if d.startswith("release_v") and d[9:].isdigit() and os.path.exists(os.path.join(b, d, "MANIFEST.json"))]
    return max(r, key=lambda d: int(d[9:])) if r else "release_v45"


HFN_DIR = os.path.join(os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net")), "HusseinFrameNet",
                       "release", _hfn_rel())  # إصدار جداول ahdath/
WN_LOOKUP = os.path.join(_AMLN, "data", "wordnet", "wordnet_lookup_unified.json")

_HARAKAT = re.compile("[ً-ْٰ]")
_SUKUN = "ْ"
# أطر WordNet (nltk): ما فيه مفعولٌ مباشر، وما لا مفعول فيه. 26 (that CLAUSE) خارجهما.
EN_TRANS = {5, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 30, 31}
EN_INTRANS = {1, 2, 3, 4, 6, 7, 12, 13, 22, 23, 27, 28, 29, 32, 33, 34, 35}
KEEP = {"EXACT": True, "SUKUN_ONLY": True, "UNVOWELLED_QUERY": True, "UNRESOLVED": True, "DIFFERENT_VERB": False}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())


def letters(s: str) -> str:
    return _HARAKAT.sub("", nfc(s)).replace("ـ", "")


def skeleton(s: str) -> str:
    """الحروف مع توحيد مقاعد الهمزة: اختلاف رسم الهمزة رسمٌ لا دليل."""
    return letters(s).translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ء": "ا"}))


def vowelled(s: str) -> bool:
    return bool(_HARAKAT.search(nfc(s)))


@lru_cache(maxsize=1)
def _hfn() -> dict:
    p = os.path.join(HFN_DIR, "events.csv")
    idx: dict[str, list[tuple[str, str]]] = {}
    if os.path.exists(p):
        for e in csv.DictReader(open(p, encoding="utf-8")):
            idx.setdefault(nfc(e["verb"]), []).append((e["event_id"], e["form"]))
    return idx


@lru_cache(maxsize=1)
def _wasit():
    ext = os.path.join(_AMLN, "ahdath", "ext")
    if ext not in sys.path:
        sys.path.insert(0, ext)
    import wasit_frames as WF
    if not os.path.exists(WF.WASIT):
        return WF, {}
    W: dict[str, list[str]] = {}
    for line in open(WF.WASIT, encoding="utf-8"):
        r = json.loads(line)
        for s in r["sources"].values():
            for c in s.get("claims") or []:
                hw = (c.get("headword") or "").strip().split()
                if hw:
                    W.setdefault(WF.bare(hw[0]), []).append(hw[0])
    return WF, W


@lru_cache(maxsize=1)
def _wn_lookup() -> dict:
    return json.load(open(WN_LOOKUP, encoding="utf-8")) if os.path.exists(WN_LOOKUP) else {}


def _wn():
    try:
        from nltk.corpus import wordnet as wn
        wn.synset("hit.v.01")
        return wn
    except Exception:
        return None


def english(synset: str) -> dict | None:
    """تعريف synset وأطره ومتعدٍّ هو أم لازم بالإنجليزية (None إن لم يُتح nltk أو لم يكن فعلاً)."""
    wn = _wn()
    if not wn or not synset or ".v." not in synset:
        return None
    try:
        ss = wn.synset(synset)
    except Exception:
        return None
    fr = set(ss.frame_ids()) | {f for l in ss.lemmas() for f in l.frame_ids()}
    t = fr & EN_TRANS
    i = fr & EN_INTRANS
    trans = "متعدي" if t and not i else "لازم" if i and not t else "مشترك" if (t or i) else ""
    return dict(synset=synset, definition=ss.definition(), frames=sorted(fr), trans=trans)


def synsets_of(word: str) -> list[str]:
    """synsets الأفعال لحروف الكلمة في WordNet العربي (المفتاح موحَّد بلا حركات بحكم L1)."""
    return [s for s in _wn_lookup().get(letters(word), []) if ".v." in s]


def _en_conflict(en: dict | None, found_trans: str) -> bool:
    return bool(en and en["trans"] in ("متعدي", "لازم") and found_trans in ("متعدي", "لازم")
                and en["trans"] != found_trans)


def judge(query: str, found: str, found_trans: str = "", synset: str | None = None) -> dict:
    """حكم المطابقة بين السؤال والموجود في الجدول، بأدلّته. keep=False لا يكون إلا بدليلٍ مسمّى."""
    q, f = nfc(query), nfc(found)
    ev = []
    en = english(synset) if synset else None
    if en:
        ev.append(dict(source="EN", synset=en["synset"], definition=en["definition"], frames=en["frames"],
                       en_trans=en["trans"], found_trans=found_trans))
    if q == f:
        v = "EXACT"
    elif skeleton(q) != skeleton(f):
        v = "DIFFERENT_VERB"
        ev.insert(0, dict(source="LETTERS", note="الحروف مختلفة"))
    elif not vowelled(q):
        v = "UNVOWELLED_QUERY"
    elif q.replace(_SUKUN, "") == f.replace(_SUKUN, ""):
        v = "SUKUN_ONLY"
    else:
        v = "UNRESOLVED"
        WF, W = _wasit()
        # الدليل أن يكون كلٌّ من التشكيلين فعلاً قائماً بنفسه في المصدر؛ فإن لم يُشهد إلا لأحدهما
        # فالآخر قد يكون خطأ رسمٍ له (الوسيط يكتب «اصْفَرَ» لـ اصْفَرَّ) → لا دليل.
        hq, hf = _hfn().get(q, []), _hfn().get(f, [])
        if hq and hf and not set(hq) & set(hf):
            ev.insert(0, dict(source="HFN", event_id=hq[0][0], form=hq[0][1], other_event_id=hf[0][0],
                              other_form=hf[0][1], release=os.path.basename(HFN_DIR),
                              note=f"«{q}» ({hq[0][1]}) و«{f}» ({hf[0][1]}) حدثان مستقلّان في HFN"))
            v = "DIFFERENT_VERB"

        def _hw(a, b):
            return next((hw for hw in W.get(WF.bare(q), []) if len(_HARAKAT.findall(hw)) >= 2
                         and WF.compatible(hw, a) and not WF.compatible(hw, b)), None)
        wq, wf = _hw(q, f), _hw(f, q)
        if wq and wf:
            ev.append(dict(source="WASIT", headword=wq, other_headword=wf,
                           note=f"الوسيط يفرد «{wq}» و«{wf}» مدخلين"))
            v = "DIFFERENT_VERB"
    # الترجمة تُسجَّل دليلاً ويُعلَّم بها، ولا تَرفض وحدها: قيس رفضها على WordNet فصحّ 10/15 (ويلسون 0.42 < 0.78؛
    # التعدّي الإنجليزي غير العربي: خدع/cheat.v.03، قاد/drive.v.02، صوّب/sight.v.02).
    flags = ["en_conflict"] if _en_conflict(en, found_trans) else []
    if v == "UNRESOLVED" and not ev:
        ev.append(dict(source="NONE", note="تشكيلٌ مخالف بلا دليل على أنّه فعلٌ آخر — لا يُرفض"))
    return dict(match=v, keep=KEEP[v], evidence=ev, flags=flags)
