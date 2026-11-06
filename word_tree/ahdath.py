"""
ahdath.py — «الحدث يغيّر صفة الجنس» لعقدة الفعل في الشجرة (قراءة فقط؛ كلّه CANDIDATE)

يقرأ المسالك المقبولة بالقياس (ويلسون ≥ 0.78) من ahdath/ ولا يقرأ المحجوبة:
  R1     انفعل مسموع في معجمين ← الفعل مؤثّر في مفعوله، ومصدر انفعل اسمُ الأثر     (0.964)
         السند: كشف الأسرار:9670 «انفعل … إلا حيث يكون علاج وتأثير».
  R1W    نصّ الوسيط «X: مطاوع Yه» وصيغة Y من شكل النصّ                              (v2: 0.930، ويلسون 0.833)
         السند: الكليات:27626–27627 «والمطاوع يجيء مما كان فيه علاج».
  T_JAL  أفعل بنصّ الوسيط «جعله <اللازم>» ← المفعول يكتسب صفة اللازم                (25/25، ويلسون 0.867)
         السند: الكتاب:16451–16455 عن الخليل «أحزنته: جعلته حزيناً».
المحجوب (لا يُقرأ هنا): R2 (المتعدّي بلا مطاوع)، T (أفعل بالصيغة)، T_TAD (فعّل بنصّ جعله).

    from word_tree.ahdath import for_verb, for_root
    for_verb('كَسَرَ')  → [{'route': 'R1', 'fail': 'كَاسِر', 'maful': 'مَكْسُور', 'athar': 'انْكِسَار', ...}]
    for_root('حزن')     → كلّ ما في الجذر من المسالك المقبولة
"""
from __future__ import annotations

import csv
import os
import re
import unicodedata
from functools import lru_cache

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ahdath")

ROUTES = {
    "R1": {"file": "rules_R1.tsv", "wilson_low": None, "p": 0.964,
           "src": "كشف الأسرار:9670", "label_ar": "مؤثّر: له مطاوع على انفعل"},
    "R1W": {"file": "mutawaa_R1W_pool.tsv", "wilson_low": 0.833, "p": 0.930,
            "src": "الكليات:27626–27627", "label_ar": "مؤثّر: الوسيط ينصّ على مطاوعه"},
    "T_JAL": {"file": "taadiya_T_JAL.tsv", "wilson_low": 0.867, "p": 1.0,
              "src": "الكتاب:16451–16455", "label_ar": "متعدٍّ بالهمزة: المفعول يكتسب صفة اللازم"},
}

_HARAKAT = re.compile(r"[ً-ْٰـ]")


def _bare(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = _HARAKAT.sub("", s)
    return s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ء", "ا")


def _rows(name: str) -> list[dict]:
    p = os.path.join(_DIR, name)
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))


@lru_cache(maxsize=1)
def _hfn_verbs() -> dict:
    """event_id → فعل HFN المشكول (الإصدار نفسه الذي يقرأه vowel_evidence). مكتبة قياسية فقط: يحمَّل منفرداً."""
    p = os.path.join(os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net")), "HusseinFrameNet",
                     "release", os.environ.get("AMLN_HFN_RELEASE", "release_v36"), "events.csv")
    if not os.path.exists(p):
        return {}
    return {e["event_id"]: unicodedata.normalize("NFC", e["verb"].strip())
            for e in csv.DictReader(open(p, encoding="utf-8"))}


def _hfn_vowelled(text: str, event_id: str) -> str:
    """مطاوع R1W مكتوب بتشكيل نصّ الوسيط (OCR: «انقلب»، «تَطَهِرَ»). إن ربطه الصفّ بحدث HFN حروفُه حروفه
    فالتشكيل تشكيل HFN؛ وإلا يبقى النصّ كما هو (فحص الجذور، الدفعة 1: 27 من 140)."""
    h = _hfn_verbs().get(event_id or "")
    return h if h and _HARAKAT.sub("", h) == _HARAKAT.sub("", unicodedata.normalize("NFC", text or "")) else text


@lru_cache(maxsize=1)
def _table() -> list[dict]:
    out = []
    for r in _rows(ROUTES["R1"]["file"]):
        if r.get("mani"):
            continue
        out.append(dict(route="R1", root=r["root"], verb=r["verb"], event_id=r["event_id"], fail=r["fail"],
                        maful=r["maful"], mutawi=r["mutawaa"], athar=r["athar"], sifa="", rank="CANDIDATE"))
    for r in _rows(ROUTES["R1W"]["file"]):
        if r.get("mani"):
            continue
        out.append(dict(route="R1W", root=r["root"], verb=r["base"], event_id=r["base_event"], fail=r["fail"],
                        maful=r["maful"], mutawi=_hfn_vowelled(r["mutawi"], r["mutawi_event"]),
                        mutawi_text=r["mutawi"], athar=r["athar"], sifa="", rank="CANDIDATE"))
    for r in _rows(ROUTES["T_JAL"]["file"]):
        out.append(dict(route="T_JAL", root="", verb=r["verb"], event_id=r["event_id"], fail=r["fail"],
                        maful=r["maful"], mutawi=r["base"], athar="", sifa=r["sifa"], rank="CANDIDATE",
                        nass=r.get("jaala", "")))
    for x in out:
        x["src"] = ROUTES[x["route"]]["src"]
        x["label_ar"] = ROUTES[x["route"]]["label_ar"]
    return out


@lru_cache(maxsize=1)
def _by_verb() -> dict:
    idx: dict[str, list[dict]] = {}
    for x in _table():
        idx.setdefault(_bare(x["verb"]), []).append(x)
    return idx


# أثر المسلك في تعدّي الفعل الموجود (للمقارنة بالترجمة الإنجليزية): R1/R1W/T_JAL أفعالٌ متعدّية.
_ROUTE_TRANS = {"R1": "متعدي", "R1W": "متعدي", "T_JAL": "متعدي"}


def _judged(rows, verb, synset, keep_rejected, trans_of):
    """المطابقة بالحروف والحركات (vowel_evidence): EXACT يُبقى؛ والتشكيل المخالف لا يُرفض إلا بدليلٍ مسمّى
    (HFN أو الوسيط أو الترجمة الإنجليزية)؛ وكلّ سجلّ يحمل match وvowel_evidence."""
    from . import vowel_evidence as VE
    out = []
    for x in rows:
        j = VE.judge(verb, x["verb"], trans_of(x), synset)
        if j["keep"] or keep_rejected:
            out.append(dict(x, match=j["match"], keep=j["keep"], vowel_evidence=j["evidence"], vowel_flags=j["flags"]))
    return out


def for_verb(verb: str, synset: str | None = None, keep_rejected: bool = False) -> list[dict]:
    """ما في المسالك المقبولة للفعل. المرشّحون بالحروف، ثم يُحكم في كلٍّ بـ vowel_evidence.judge:
    ضَرَبَ لا يأخذ حكم ضَرُبَ (HFN يشهد أنّهما حدثان)؛ والسؤال بلا حركات يُبقي الكلّ معلَّماً.
    synset: معنى WordNet الذي جاء منه السؤال — ترجمته الإنجليزية دليلٌ على التعدّي."""
    return _judged(_by_verb().get(_bare(verb), []), verb, synset, keep_rejected,
                   lambda x: _ROUTE_TRANS.get(x["route"], ""))


def for_root(root: str) -> list[dict]:
    rb = _bare(root)
    return [dict(x) for x in _table() if (x["root"] and _bare(x["root"]) == rb)
            or (not x["root"] and len(rb) == 3 and all(c in _bare(x["verb"]) for c in rb))]


def summary() -> dict:
    from collections import Counter
    return dict(Counter(x["route"] for x in _table()))


# ── جهة الفاعل: محدِث أم محلّ قام به الحدث (ahdath/jiha.py) ─────────────────────
# السند: الصبّان (sabban.txt:2228–2229) «من وجد منه الفعل أو قام به … كضربت ومت».
# المقبول بالقياس (CLAUDE، ويلسون ≥ 0.78) وحده؛ المحجوب: J_LAWN (0.742، الحوض 30 فقط)، J_MUTAWAA (0.656).
JIHA_ROUTES = {
    "J_SAJIYYA": {"wilson_low": 0.890, "p": 1.0, "src": "الكتاب:16143–16144",
                  "label_ar": "فَعُلَ: الفاعل موصوف بخصلة قامت به، لا محدِث"},
    "J_DAA": {"wilson_low": 0.871, "p": 0.975, "src": "الكتاب:16016؛ 16108",
              "label_ar": "فَعِلَ لازم صفته فَعِل/أفعل/فعلان: الفاعل محلّ داء أو حال"},
}


@lru_cache(maxsize=1)
def _jiha() -> dict:
    idx: dict[str, list[dict]] = {}
    for r in _rows("jiha_pool.tsv"):
        if r["route"] not in JIHA_ROUTES:
            continue
        x = dict(route=r["route"], verb=r["verb"], event_id=r["event_id"], root=r["root"], jiha=r["jiha"],
                 musabbib_verb=r["musabbib_verb"], musabbib_route=r["musabbib_route"], sifa=r["sifa"],
                 trans_wasit=r.get("trans_wasit", ""),
                 src=JIHA_ROUTES[r["route"]]["src"], label_ar=JIHA_ROUTES[r["route"]]["label_ar"], rank="CANDIDATE")
        idx.setdefault(_bare(r["verb"]), []).append(x)
    return idx


def jiha(verb: str, synset: str | None = None, keep_rejected: bool = False) -> list[dict]:
    """جهة فاعل الفعل في المسالك المقبولة: jiha='MAHALL' (الفاعل محلّ قام به الحدث).
    musabbib_verb: الفعل الذي يُظهر المسبِّب فاعلاً إن وُجد في مسلك مقبول (T_JAL/R1/R1W)."""
    return _judged(_jiha().get(_bare(verb), []), verb, synset, keep_rejected, lambda x: x.get("trans_wasit", ""))
