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
  match:  EXACT | SUKUN_ONLY | UNVOWELLED_QUERY | UNRESOLVED | DIFFERENT_VERB | ROOT (انظر vowel_evidence)

المطابقة: match='exact' (الافتراضي، وهو حكم دستور sarf) يُبقي EXACT في features. والتشكيل المخالف لا يُرفض
إلا بدليل (word_tree.vowel_evidence: HFN، الوسيط، الترجمة الإنجليزية): ما قام عليه دليلٌ → excluded بدليله،
وما لا دليل عليه → pending (لا مقبول ولا مرفوض). match='letters' يُبقي غير المرفوض في features معلَّماً.
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


def _pack(query, recs, missing, match, synset=None):
    """EXACT/ROOT → features. والتشكيل المخالف يُحكم فيه بـ vowel_evidence: ما قام دليلٌ مسمّى على أنّه فعلٌ
    آخر (HFN، الوسيط، الترجمة الإنجليزية) → excluded بدليله؛ وما لا دليل عليه لا يُرفض → pending
    (في match='exact')، أو features معلَّماً (في match='letters')."""
    from word_tree import vowel_evidence as VE
    feats, excluded, pending = defaultdict(list), [], []
    for r in recs:
        if r["match"] in ("EXACT", "ROOT"):
            feats[r["feature"]].append(r)
            continue
        if "vowel_evidence" not in r:
            j = VE.judge(query, r.get("matched", ""), r.get("found_trans", ""), synset)
            r = dict(r, match=j["match"], vowel_evidence=j["evidence"], vowel_flags=j["flags"])
        if r["match"] == "EXACT":
            feats[r["feature"]].append(r)
        elif r["match"] == "DIFFERENT_VERB":
            src = "، ".join(e.get("note") or e["source"] for e in r["vowel_evidence"])
            excluded.append(dict(r, excluded_reason=f"فعلٌ آخر بدليل: {src}"))
        elif match == "exact":
            pending.append(dict(r, pending_reason=f'match={r["match"]}: لا يُقبل بلا تطابق الحركات، ولا يُرفض بلا دليل'))
        else:
            feats[r["feature"]].append(r)
    return dict(query=query, rank="CANDIDATE", is_fact=False, features=dict(feats), excluded=excluded,
                pending=pending, missing=missing, sources=sources())


def verb(verb: str, root: str = "", form: str = "", include=None, match: str = "exact",
         synset: str | None = None) -> dict:
    """كلّ ما تعرفه arabic-net عن فعلٍ مشكول: الحدث في HFN، والمصادر، والتعدّي، ومعنى الصيغة، والمشتقّات،
    والمطاوعة، والتعدية، وأثر الحدث، وجهة الفاعل؛ ومعنى الجذر إن طُلب 'roots' مع root.
    synset: معنى WordNet الذي جاء منه الفعل (مثل 'hit.v.01') — ترجمته دليلٌ في حكم التشكيل المخالف."""
    inc = set(include or VERB_PROVIDERS)
    recs, missing = [], []
    if "hfn" in inc:
        _run("hfn", lambda: hfn.features(verb, root, form), recs, missing)
    if "wazn" in inc:
        _run("wazn", lambda: wazn.features(verb), recs, missing)
    if "ahdath" in inc:
        _run("ahdath", lambda: ahdath.features(verb, synset), recs, missing)
    if "roots" in inc and root:
        _run("roots", lambda: roots.meaning(root), recs, missing)
    return _pack(nfc(verb), recs, missing, match, synset)


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
