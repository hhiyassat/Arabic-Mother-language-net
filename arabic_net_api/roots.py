"""مزوّد الجذر: معنى الجذر من بنك HFN (HFN_ROOTS_v3، عشرة معاجم مع الوسيط)، ومقاييس ابن فارس احتياطاً،
والتحيّز المكاني لمعاني الجذر في الشجرة. كلّه نصّ OCR لم يُحقَّق → شاهدٌ لا حكم."""
from __future__ import annotations

import csv
import json
import os
import re
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


_AMLN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMBEDDED_TSV = os.path.join(_AMLN, "data", "maqayis_embedded.tsv")
MAQAYIS_DB = os.path.join(_AMLN, "word_tree", "maqayis.db")
_HAR = re.compile(r"[ً-ْٰ]")


@lru_cache(maxsize=1)
def _embedded() -> dict:
    """جذرٌ مدفون في سجلّ مقاييس آخر (audit/build_maqayis_embedded.py): K → (المضيف، رقم السجلّ، الموضع، الكيف)."""
    if not os.path.exists(EMBEDDED_TSV):
        return {}
    return {r["root_K"]: r for r in csv.DictReader(open(EMBEDDED_TSV, encoding="utf-8"), delimiter="\t")}


def _embedded_text(eid: int, offset: int, n: int = 400) -> str:
    """نصّ المادّة المدفونة من body_text الكامل. الموضع محسوبٌ على النصّ بلا حركات، فيُترجم إلى النصّ المشكول."""
    if not os.path.exists(MAQAYIS_DB):
        return ""
    import sqlite3
    row = sqlite3.connect(MAQAYIS_DB).execute("select body_text from entries where id=?", (eid,)).fetchone()
    if not row:
        return ""
    body, seen = row[0], 0
    for i, ch in enumerate(body):
        if seen == offset:
            return body[i:i + n]
        if not _HAR.match(ch):
            seen += 1
    return ""


def key_variants(R: str, biliteral_naqis: bool = False) -> list[str]:
    """مفاتيح الجذر في عُرف المقاييس وWordNet (فحص الجذور، الدفعة 1): المضعّف حرفان (ربب→رب)،
    والناقص بالألف المقصورة أو بالياء/الواو (دنو→دنى).
    biliteral_naqis: والناقص بحرفيه الأوّلين أيضاً (يدي→يد: «الياء والدال»). هذا المفتاح يشترك فيه المضعّف
    (يد = يدد أو يدي)، فلا تستعمله الواجهة لاسترجاع المعنى؛ يستعمله الفحص ليعلّمه CONV ملتبساً."""
    out = []
    if len(R) == 3 and R[1] == R[2]:
        out.append(R[:2])
    if len(R) == 3 and R[2] in "ويى":
        out += [R[:2] + "ى", R[:2] + "ي", R[:2] + "و"]
    # مادّة جامعة عند ابن فارس (فحص الجذور، الدفعة 4). المفتاح بعد K:
    #   Xوء «والحرف المعتلّ والمهموز» (خطوأ، بكوأ، رفوأ) — للناقص وللمهموز اللام؛
    #   Xوي «والحرف المعتلّ … الواو والياء» (بروى، ثروى) ونادراً Xوا (دسوا) — للناقص وحده.
    if len(R) == 3 and R[2] in "ويى":
        out += [R[:2] + "وي", R[:2] + "وا", R[:2] + "وء"]
    if len(R) == 3 and R[2] == "ء":
        out.append(R[:2] + "وء")
    if biliteral_naqis and len(R) == 3 and R[2] in "ويى":
        out.append(R[:2])                    # الملتبس آخراً: لا يسبق المادّة الجامعة
    seen = []
    for v in out:
        if v != R and v not in seen:
            seen.append(v)
    return seen


def meaning(root: str, full: bool = False) -> list[dict]:
    out = []
    r = _root_meaning()(root)
    for lx in r.get("lexicons", []):
        ms = lx.get("meanings") or []
        out.append(feature("root_meaning", ms if full else [m[:400] for m in ms[:2]], provider=PROVIDER,
                           status=OCR, source=lx["lexicon"], match="ROOT", evidence=lx.get("status", ""),
                           record_id=lx.get("record_id", ""), root=r.get("K", "")))
    if not out:
        table, k = _maqayis(), K(root)
        key = k if k in table else next((v for v in key_variants(k) if v in table), None)
        m = table.get(key) if key else None
        if m:
            out.append(feature("root_meaning", [m["body_snippet"]], provider=PROVIDER, status=OCR,
                               source="مقاييس اللغة (ابن فارس) — maqayis_all_roots.json", match="ROOT",
                               evidence=f'axes={m.get("axes_count")}' + (f" · key={key}" if key != k else ""),
                               record_id=str(m.get("id")), root=k))
        elif k in _embedded():
            e = _embedded()[k]
            txt = _embedded_text(int(e["host_entry_id"]), int(e["offset"]))
            if txt:
                out.append(feature("root_meaning", [txt], provider=PROVIDER, status=OCR,
                                   source="مقاييس اللغة (ابن فارس) — maqayis.db (body_text)", match="ROOT",
                                   evidence=f'مدفون في سجلّ «{e["host_display"]}» عند {e["offset"]} ({e["how"]})',
                                   record_id=e["host_entry_id"], root=k))
    return out


def tahayyuz(root: str) -> list[dict]:
    from word_tree import tahayyuz as T
    d = T.for_root(root)
    if not d or not d.get("noun_senses"):
        return []
    return [feature("tahayyuz", d, provider=PROVIDER, status="CANDIDATE", source="word_tree.tahayyuz (سيبويه 1/35–36، 1/403–405)",
                    match="ROOT")]
