"""arabic_net_api — واجهةٌ واحدة لكلّ ما في arabic-net، لمحلّل arabic-sarf-2026 وغيره (قراءة فقط؛ CANDIDATE).

مدخلٌ جامع فوق مزوّدات مستقلّة؛ ويُستدعى كلّ مزوّدٍ وحده أيضاً:

    from arabic_net_api import verb, root, sources
    r = verb('كَسَرَ')                       # كلّ السمات من كلّ المصادر
    r = verb('كَسَرَ', include={'wazn'})     # مصدرٌ بعينه
    r['features']['mutawaa'][0]['value']   # 'انْكَسَرَ'
    root('كسر')                            # معنى الجذر، وأحداث HFN، والتحيّز
    sources()                              # التزامات المستودعات، وإصدار HFN وبصمته

    from arabic_net_api import hfn, wazn, ahdath, roots   # المزوّدات منفردة

سجلّ كلّ سمة:
    feature, value, provider, status, rank='CANDIDATE', is_fact=False, route, measure, source, match, evidence, …
  status: MEASURED_ACCEPTED (مسلكٌ بلغ ويلسون ≥ 0.78) | RELEASE_CANDIDATE (إصدار HFN) | UNVERIFIED_OCR (نصّ معجم)
  match:  EXACT (الحروف والحركات بعد NFC) | SUKUN_ONLY | LETTERS | ROOT

المطابقة: match='exact' (الافتراضي، وهو حكم دستور sarf) يُبقي EXACT في features، ويضع ما سواه في excluded
بسببه — لا يُحذف صامتاً. match='letters' يُبقي الكلّ معلَّماً.
غياب مصدرٍ أو فشله لا يُسقط الطلب: يُذكر في missing.
"""
from __future__ import annotations

import os
from collections import defaultdict

from . import ahdath, hfn, roots, wazn
from ._common import REPOS, commit, nfc

__all__ = ["verb", "root", "sources", "hfn", "wazn", "ahdath", "roots", "PROVIDERS"]
VERB_PROVIDERS = ("hfn", "wazn", "ahdath")
ROOT_PROVIDERS = ("roots", "hfn", "tahayyuz")
PROVIDERS = sorted(set(VERB_PROVIDERS) | set(ROOT_PROVIDERS))


def _run(name, fn, out, missing):
    try:
        out.extend(fn())
    except Exception as e:  # مصدرٌ غائب أو معطّل: يُذكر ولا يُسقط الباقي
        missing.append(dict(provider=name, reason=f"{type(e).__name__}: {str(e)[:200]}"))


def _pack(query, recs, missing, match):
    feats, excluded = defaultdict(list), []
    for r in recs:
        if match == "exact" and r["match"] not in ("EXACT", "ROOT"):
            excluded.append(dict(r, excluded_reason=f'match={r["match"]} (يُشترط EXACT)'))
        else:
            feats[r["feature"]].append(r)
    return dict(query=query, rank="CANDIDATE", is_fact=False, features=dict(feats), excluded=excluded,
                missing=missing, sources=sources())


def verb(verb: str, root: str = "", form: str = "", include=None, match: str = "exact") -> dict:
    """كلّ ما تعرفه arabic-net عن فعلٍ مشكول: الحدث في HFN، والمصادر، والتعدّي، ومعنى الصيغة، والمشتقّات،
    والمطاوعة، والتعدية، وأثر الحدث، وجهة الفاعل؛ ومعنى الجذر إن طُلب 'roots' مع root."""
    inc = set(include or VERB_PROVIDERS)
    recs, missing = [], []
    if "hfn" in inc:
        _run("hfn", lambda: hfn.features(verb, root, form), recs, missing)
    if "wazn" in inc:
        _run("wazn", lambda: wazn.features(verb), recs, missing)
    if "ahdath" in inc:
        _run("ahdath", lambda: ahdath.features(verb), recs, missing)
    if "roots" in inc and root:
        _run("roots", lambda: roots.meaning(root), recs, missing)
    return _pack(nfc(verb), recs, missing, match)


def root(root: str, include=None, full: bool = False) -> dict:
    """الجذر: معناه في المعاجم (شاهد OCR)، وأحداثه في HFN، وتوزيع تحيّز معانيه الاسمية."""
    inc = set(include or ROOT_PROVIDERS)
    recs, missing = [], []
    if "roots" in inc:
        _run("roots", lambda: roots.meaning(root, full), recs, missing)
    if "hfn" in inc:
        _run("hfn", lambda: hfn.root_events(root), recs, missing)
    if "tahayyuz" in inc:
        _run("tahayyuz", lambda: roots.tahayyuz(root), recs, missing)
    return _pack(root, recs, missing, "letters")


_SOURCES = None


def sources() -> dict:
    """التزام كلّ مستودع وإصدار HFN — ثبّته في أثر التشغيل."""
    global _SOURCES
    if _SOURCES is None:
        s = {k: dict(path=p, commit=commit(k), present=os.path.isdir(p)) for k, p in REPOS.items()}
        try:
            s["hfn"].update(hfn.info())
        except Exception as e:
            s["hfn"]["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        _SOURCES = s
    return _SOURCES
