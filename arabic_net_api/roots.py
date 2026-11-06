"""مزوّد الجذر: معنى الجذر من بنك HFN (HFN_ROOTS_v3، عشرة معاجم مع الوسيط)، ومقاييس ابن فارس احتياطاً،
والتحيّز المكاني لمعاني الجذر في الشجرة. كلّه نصّ OCR لم يُحقَّق → شاهدٌ لا حكم."""
from __future__ import annotations

import json
import os
from functools import lru_cache

from ._common import OCR, REPOS, K, feature, on_path

PROVIDER = "roots"
MAQAYIS_JSON = os.path.join(REPOS["maqayis"], "output", "maqayis_all_roots.json")


@lru_cache(maxsize=1)
def _root_meaning():
    with on_path(os.path.join(REPOS["hfn"], "tools")):
        from root_meaning import root_meaning
    return root_meaning


@lru_cache(maxsize=1)
def _maqayis():
    if not os.path.exists(MAQAYIS_JSON):
        return {}
    d = json.load(open(MAQAYIS_JSON, encoding="utf-8"))
    return {K(r["display"]): r for r in d["roots"]}


def meaning(root: str, full: bool = False) -> list[dict]:
    out = []
    r = _root_meaning()(root)
    for lx in r.get("lexicons", []):
        ms = lx.get("meanings") or []
        out.append(feature("root_meaning", ms if full else [m[:400] for m in ms[:2]], provider=PROVIDER,
                           status=OCR, source=lx["lexicon"], match="ROOT", evidence=lx.get("status", ""),
                           record_id=lx.get("record_id", ""), root=r.get("K", "")))
    if not out:
        m = _maqayis().get(K(root))
        if m:
            out.append(feature("root_meaning", [m["body_snippet"]], provider=PROVIDER, status=OCR,
                               source="مقاييس اللغة (ابن فارس) — maqayis_all_roots.json", match="ROOT",
                               evidence=f'axes={m.get("axes_count")}', record_id=str(m.get("id")), root=K(root)))
    return out


def tahayyuz(root: str) -> list[dict]:
    from word_tree import tahayyuz as T
    d = T.for_root(root)
    if not d or not d.get("noun_senses"):
        return []
    return [feature("tahayyuz", d, provider=PROVIDER, status="CANDIDATE", source="word_tree.tahayyuz (سيبويه 1/35–36، 1/403–405)",
                    match="ROOT")]
