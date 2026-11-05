"""
tahayyuz.py — طبقة التحيّز المكاني لعقدة «ذات» في الشجرة (قراءة فقط؛ CANDIDATE)

يقرأ data/wordnet/wordnet_tahayyuz.json الذي يبنيه tahayyuz/build_tahayyuz.py.
الأصناف من نصّ سيبويه (الكتاب 1/35–36 ، 1/403–405 ، 1/418–419):
  MUTAHAYYIZ     ذاتٌ لها جثّة            (subtype MAKAN = مكانٌ مختصّ)
  HAYYIZ_MUBHAM  حيّزٌ مبهم نسبيّ          (ZARF ظرف / JIHA جهة / MIQDAR_MASAFA مقدار مسافة)
  MANA           معنى لا جثّة له
  ZAMAN          زمان
  DEFER          لم يُحسم — للمالك

    from word_tree.tahayyuz import for_synset, for_root
    for_synset('mountain.n.01')  → {'class': 'MUTAHAYYIZ', 'subtype': 'MAKAN', 'label_ar': 'ذات متحيّزة — مكان مختصّ', ...}
    for_root('جبل')              → توزيع أصناف معاني الجذر في الشجرة
"""
from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wordnet")
_TAH = os.path.join(_DATA, "wordnet_tahayyuz.json")
_SYN = os.path.join(_DATA, "wordnet_synsets.json")

LABEL_AR = {
    "MUTAHAYYIZ": "ذات متحيّزة (لها جثّة)",
    "HAYYIZ_MUBHAM": "حيّز مبهم نسبيّ",
    "MANA": "معنى (لا جثّة له)",
    "ZAMAN": "زمان",
    "DEFER": "لم يُحسم — للمالك",
}
SUBLABEL_AR = {
    "MAKAN": "مكان مختصّ",
    "ZARF": "ظرف مكان",
    "JIHA": "جهة",
    "MIQDAR_MASAFA": "مقدار مسافة",
    "MIQDAR_MISAHA": "مقدار مساحة (غير منصوص)",
    "TAXON": "جنس تصنيفيّ (كلّي)",
    "GHAYB": "غيبيّ/أسطوريّ",
}


@lru_cache(maxsize=1)
def _table() -> dict:
    if not os.path.exists(_TAH):
        return {}
    return json.load(open(_TAH, encoding="utf-8"))["synsets"]


@lru_cache(maxsize=1)
def _root_index() -> dict:
    idx: dict[str, list[str]] = {}
    if not os.path.exists(_SYN):
        return idx
    for x in json.load(open(_SYN, encoding="utf-8"))["synsets"]:
        if x.get("pos") != "n":
            continue
        for r in x.get("roots") or []:
            idx.setdefault(r, []).append(x["id"])
    return idx


def for_synset(synset_id: str) -> dict:
    """تحيّز معنى واحد. يعيد {} إن لم يكن اسماً في الطبقة."""
    rec = _table().get(synset_id)
    if not rec:
        return {}
    out = dict(rec)
    lab = LABEL_AR.get(rec["class"], rec["class"])
    if rec.get("subtype"):
        lab += " — " + SUBLABEL_AR.get(rec["subtype"], rec["subtype"])
    out["label_ar"] = lab
    return out


def for_root(root: str) -> dict:
    """توزيع أصناف التحيّز على معاني الجذر الاسمية (عدٌّ لا حكم)."""
    ids = _root_index().get(root, [])
    t = _table()
    c = Counter(t[i]["class"] for i in ids if i in t)
    return {"root": root, "noun_senses": len(ids), "by_class": dict(c), "status": "CANDIDATE", "is_fact": False}
