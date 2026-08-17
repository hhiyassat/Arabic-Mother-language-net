"""
wave11_ancestry.py — GRES-WAVE11
طبقة النسب الاشتقاقي الوجودي

سلسلة أنساب منضبطة من 11 عقدة:
  وجود → ذات → ماهية → خواص → صفات → مصدر → فعل → وزن → مشتق → علاقة → حكم

المصادر:
  • Maqayis   — وجود + ماهية   (نص الجذر + المحاور الدلالية)
  • Arabic Mother Net — تصحيح الجذر من الكلمة
  • Wazn/Mushtaqqat — صفات + مصدر + فعل + وزن + مشتق + علاقة
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ── مسارات المشروع ─────────────────────────────────────────────────────
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT_DIR)

from maqayis_v2.maqayis_api import MaqayisAPI
from word_tree.engines.noun_root_corrector import load_maqayis_index, extract_root_for_maqayis
from word_tree.engines.derivation_engine import derive, derive_from_dict, DerivationSet, MazidEntry
from word_tree.engines.morphological_engine import conjugate, ConjugationParadigm
from word_tree.engines.slots_engine import parse_predicate, PredicateStructure, Slot
from word_tree.core.types import RootType, Baab

# ── ملف بيانات الجذور التجريبية ────────────────────────────────────────
_PILOT_JSON = os.path.join(os.path.dirname(__file__), "data", "pilot_roots.json")


# ══════════════════════════════════════════════════════════════════════════
# هيكل WAVE11 الكامل
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Wave11Ancestry:
    """
    النسب الاشتقاقي الوجودي الكامل لكلمة/جذر.

    العقد الـ ١١:
      1. wujud     — وجود    : نص مقاييس الجذر الأصلي (ابن فارس)
      2. dhat      — ذات     : "ذات [صفة]ة" مُشتقَّة من الماهية + الصفات
      3. mahiyya   — ماهية   : المحاور الدلالية من مقاييس اللغة
      4. khawass   — خواص    : الأنواع الدلالية الإلزامية (SemanticType)
      5. sifat     — صفات    : اسم فاعل / مفعول / مكان / آلة
      6. masdar    — مصدر    : المصادر السماعية + المصدر القياسي
      7. fi3l      — فعل     : الصيغة الأصلية (ماضٍ مفرد مذكر غائب معلوم)
      8. wazn      — وزن     : الباب الصرفي (فَعَلَ يَفْعُلُ)
      9. mushtaqq  — مشتق    : الأوزان المزيدة II–X
      10. ilaqa    — علاقة   : الفتحات الدلالية (slots)
      11. hokm     — حكم     : مفتوح — لم يُبنَ بعد
    """
    # ── معلومات الجذر ──────────────────────────────────────────────────
    root:            str
    root_verified:   bool             # التحقق من وجوده في مقاييس اللغة
    source_word:     str              # الكلمة التي أعطت الجذر
    lookup_status:   str              # حالة البحث (maqayis_verified / …)

    # ── العقدة 1 ───────────────────────────────────────────────────────
    wujud:           str = ""         # وجود: نص ابن فارس
    # ── العقدة 2 ───────────────────────────────────────────────────────
    dhat:            str = ""         # ذات: مُشتقَّة
    # ── العقدة 3 ───────────────────────────────────────────────────────
    mahiyya:         list[str] = field(default_factory=list)   # محاور دلالية
    # ── العقدة 4 ───────────────────────────────────────────────────────
    khawass:         list[str] = field(default_factory=list)   # أنواع الفتحات الإلزامية
    # ── العقدة 5 ───────────────────────────────────────────────────────
    sifat:           dict = field(default_factory=dict)         # اسم فاعل / مفعول / مكان / آلة
    # ── العقدة 6 ───────────────────────────────────────────────────────
    masdar:          list[str] = field(default_factory=list)   # المصادر
    # ── العقدة 7 ───────────────────────────────────────────────────────
    fi3l:            str = ""         # الفعل الماضي
    # ── العقدة 8 ───────────────────────────────────────────────────────
    wazn:            str = ""         # الباب الصرفي
    # ── العقدة 9 ───────────────────────────────────────────────────────
    mushtaqq:        list[dict] = field(default_factory=list)  # المزيدات II–X
    # ── العقدة 10 ──────────────────────────────────────────────────────
    ilaqa:           list[dict] = field(default_factory=list)  # الفتحات الدلالية
    # ── العقدة 11 ──────────────────────────────────────────────────────
    hokm:            str = "OPEN"     # الحكم — لم يُبنَ بعد

    # ── جودة السلسلة ───────────────────────────────────────────────────
    chain_continuity: bool = False
    open_nodes:       list[str] = field(default_factory=list)
    warnings:         list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 0 — استنتاج نوع الجذر من الحروف
# ══════════════════════════════════════════════════════════════════════════

_WEAK = {"و", "ي", "ا"}

def _infer_root_type(root: str) -> RootType:
    """
    يستنتج نوع الجذر من حروفه بدون تشكيل.
    القاعدة الصرفية: موضع حرف العلة يحدد نوع الجذر.
    """
    chars = list(root)
    if len(chars) < 3:
        return RootType.SAHIH

    r1, r2, r3 = chars[0], chars[1], chars[2]

    # مضاعف: الحرف الثاني والثالث متماثلان
    if r2 == r3 and r2 not in _WEAK:
        return RootType.MUDAAF

    # لفيف مقرون: الحرف الثاني والثالث كلاهما حرف علة
    if r2 in _WEAK and r3 in _WEAK:
        return RootType.LAFIF_MAQRUN

    # لفيف مفروق: الحرف الأول والثالث كلاهما حرف علة
    if r1 in _WEAK and r3 in _WEAK:
        return RootType.LAFIF_MAFRUQ

    # مثال: الحرف الأول حرف علة
    if r1 == "و":
        return RootType.MITHAL_WAW
    if r1 == "ي":
        return RootType.MITHAL_YAA

    # أجوف: الحرف الثاني حرف علة
    if r2 in ("و", "ا"):
        return RootType.AJWAF_WAW
    if r2 == "ي":
        return RootType.AJWAF_YAA

    # ناقص: الحرف الثالث حرف علة
    if r3 in ("و", "ا"):
        return RootType.NAQIS_WAW
    if r3 == "ي":
        return RootType.NAQIS_YAA

    return RootType.SAHIH


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 0b — تحميل بيانات pilot_roots.json والبحث بالجذر
# ══════════════════════════════════════════════════════════════════════════

_pilot_cache: Optional[dict] = None

def _load_pilot() -> dict:
    global _pilot_cache
    if _pilot_cache is None:
        with open(_PILOT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        _pilot_cache = {entry["letters"]: entry for entry in data["roots"]}
    return _pilot_cache


def _get_pilot_entry(root: str) -> Optional[dict]:
    """ابحث عن الجذر في pilot_roots.json — None إذا لم يُوجَد."""
    return _load_pilot().get(root)


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 1 — وجود + ماهية من مقاييس اللغة
# ══════════════════════════════════════════════════════════════════════════

def _build_wujud_mahiyya(root: str, db_path: str) -> tuple[str, list[str], bool]:
    """
    يسترجع من مقاييس اللغة:
      wujud   — نص الجذر عند ابن فارس (body_text من أول مدخلة)
      mahiyya — المحاور الدلالية (axis_text)
    يُعيد (wujud, mahiyya, found)
    """
    api = MaqayisAPI(db_path)

    # جلب نص وجود
    r_lookup = api.query({"query_type": "ROOT_LOOKUP", "root": root})
    wujud = ""
    found = r_lookup.get("found", False)
    if found and r_lookup.get("results"):
        first = r_lookup["results"][0]
        wujud = first.get("body_text", "").strip()

    # جلب المحاور
    r_axes = api.query({"query_type": "ROOT_SEMANTIC_ORIGINS", "root": root})
    mahiyya: list[str] = []
    if r_axes.get("found"):
        mahiyya = [
            ax["axis_text"]
            for entry in r_axes["results"]
            for ax in entry.get("semantic_axes", [])
            if ax.get("axis_text", "").strip()
        ]

    api.close()
    return wujud, mahiyya, found


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 2 — صفات + مصدر + مشتق من derivation_engine
# ══════════════════════════════════════════════════════════════════════════

def _build_derivation(root: str, pilot: Optional[dict]) -> tuple[DerivationSet, list[str]]:
    """
    يُشغِّل المحرك الاشتقاقي.
    إذا توفَّر pilot: يستخدم بياناته الكاملة.
    إذا لم يتوفَّر: يستنتج نوع الجذر ويُقصِّر الباب على FAA_YAF_U.
    يُعيد (DerivationSet, warnings)
    """
    warnings: list[str] = []

    if pilot:
        try:
            ds = derive_from_dict(pilot)
            return ds, warnings
        except Exception as e:
            warnings.append(f"derive_from_dict فشل ({e}) — نرجع للاستنتاج التلقائي")

    # استنتاج بدون بيانات مخزَّنة
    root_type = _infer_root_type(root)
    baab      = Baab.FAA_YAF_U          # باب نصر — الافتراضي الأكثر شيوعاً
    warnings.append(f"الجذر '{root}' غير موجود في pilot_roots — نوع مُستنتَج: {root_type.value}, باب افتراضي: {baab.value}")

    chars = list(root)
    if len(chars) < 3:
        warnings.append(f"الجذر '{root}' أقل من ثلاثة أحرف — تخطّي الاشتقاق")
        ds = DerivationSet(root=root, root_type=root_type, baab=baab)
        return ds, warnings

    ds = derive(
        letters           = root,
        root_type         = root_type,
        baab              = baab,
        masadir_samiyya   = [],
        masdar_qiyasi     = None,
        ism_faail_stored  = None,
        ism_mafuul_stored = None,
        ism_makan_stored  = None,
        ism_zaman_stored  = None,
        ism_aala_stored   = None,
        awzaan_maqbuula   = {},
    )
    return ds, warnings


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 3 — فعل من morphological_engine
# ══════════════════════════════════════════════════════════════════════════

def _build_fi3l(root: str, root_type: RootType, baab: Baab) -> str:
    """
    يُولِّد صيغة الفعل الماضي (مفرد مذكر غائب معلوم) — الصيغة الأصلية.
    """
    try:
        paradigm: ConjugationParadigm = conjugate(root, root_type, baab)
        cells = paradigm.filter(mood="ماضٍ", voice="معلوم", person="غائب",
                                number="مفرد", gender="مذكر")
        if cells:
            return cells[0].form
        # fallback: أول خلية ماضٍ معلوم
        cells = paradigm.filter(mood="ماضٍ", voice="معلوم")
        if cells:
            return cells[0].form
    except Exception:
        pass
    return ""


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 4 — علاقة + خواص من slots_engine
# ══════════════════════════════════════════════════════════════════════════

def _build_ilaqa_khawass(
    pilot: Optional[dict],
    root: str,
) -> tuple[list[dict], list[str]]:
    """
    يُشغِّل محرك الفتحات إذا توفَّر pilot entry.
    يُعيد (ilaqa_list, khawass_list)
    """
    if not pilot or "predicate" not in pilot:
        return [], []

    try:
        ps: PredicateStructure = parse_predicate(root, pilot["predicate"])

        ilaqa = [
            {
                "name":        s.name,
                "sem_type":    s.sem_type.value,
                "example":     s.example,
                "optional":    s.optional,
                "preposition": s.preposition,
            }
            for s in ps.slots
        ]

        khawass = [s.sem_type.value for s in ps.mandatory()]
        return ilaqa, khawass

    except Exception as e:
        return [], [f"slots_engine خطأ: {e}"]


# ══════════════════════════════════════════════════════════════════════════
# الخطوة 5 — ذات مُشتقَّة
# ══════════════════════════════════════════════════════════════════════════

def _derive_dhat(mahiyya: list[str], sifat: dict) -> str:
    """
    يُشتقّ وصف الذات من الماهية + الصفات.
    صيغة: "ذات [صفة] — أصلها [محور]"
    """
    ism_f = sifat.get("ism_faail", "")
    axis  = mahiyya[0] if mahiyya else ""

    if ism_f and axis:
        return f"ذات {ism_f}ة — أصلها: {axis}"
    elif ism_f:
        return f"ذات {ism_f}ة"
    elif axis:
        return f"ذات — أصلها: {axis}"
    return "ذات (غير محدَّدة)"


# ══════════════════════════════════════════════════════════════════════════
# التحقق من استمرارية السلسلة
# ══════════════════════════════════════════════════════════════════════════

def _check_continuity(anc: Wave11Ancestry) -> None:
    """يفحص أي عقد مفتوحة ويضبط chain_continuity."""
    open_nodes: list[str] = []

    if not anc.wujud:            open_nodes.append("وجود")
    if not anc.dhat:             open_nodes.append("ذات")
    if not anc.mahiyya:          open_nodes.append("ماهية")
    if not anc.khawass:          open_nodes.append("خواص")
    if not anc.sifat:            open_nodes.append("صفات")
    if not anc.masdar:           open_nodes.append("مصدر")
    if not anc.fi3l:             open_nodes.append("فعل")
    if not anc.wazn:             open_nodes.append("وزن")
    if not anc.mushtaqq:         open_nodes.append("مشتق")
    if not anc.ilaqa:            open_nodes.append("علاقة")
    # حكم دائماً مفتوح — لم يُبنَ بعد
    open_nodes.append("حكم")

    anc.open_nodes       = open_nodes
    anc.chain_continuity = len(open_nodes) == 1  # فقط حكم مفتوح → السلسلة مكتملة


# ══════════════════════════════════════════════════════════════════════════
# نقطة الدخول الرئيسية
# ══════════════════════════════════════════════════════════════════════════

def wave11_build(
    words:      list[str],
    synset_id:  str,
    db_path:    str,
) -> Wave11Ancestry:
    """
    يبني السلسلة الكاملة لـ Wave11.

    المدخلات:
        words      — قائمة الكلمات (أولها عربي مفضَّل)
        synset_id  — معرف synset
        db_path    — مسار قاعدة بيانات مقاييس اللغة

    المخرجات:
        Wave11Ancestry — السلسلة الكاملة بـ 11 عقدة
    """
    warnings: list[str] = []

    # ── الخطوة A: استخراج الجذر من Arabic Mother Net ────────────────────
    idx = load_maqayis_index(db_path)
    root, status, src_word = extract_root_for_maqayis(words, idx)

    anc = Wave11Ancestry(
        root          = root or "",
        root_verified = (status == "maqayis_verified"),
        source_word   = src_word,
        lookup_status = status,
    )

    if not root:
        anc.warnings = [f"لم يُستخرَج جذر من {words} — status: {status}"]
        _check_continuity(anc)
        return anc

    # ── الخطوة B: العقدة 1 (وجود) + العقدة 3 (ماهية) من مقاييس ──────────
    wujud, mahiyya, maq_found = _build_wujud_mahiyya(root, db_path)
    anc.wujud   = wujud
    anc.mahiyya = mahiyya
    if not maq_found:
        warnings.append(f"الجذر '{root}' غير موجود في قاعدة مقاييس اللغة")

    # ── الخطوة C: الاشتقاق — العقد 5،6،8،9 ─────────────────────────────
    pilot = _get_pilot_entry(root)
    ds, deriv_warnings = _build_derivation(root, pilot)
    warnings.extend(deriv_warnings)

    # العقدة 5 — صفات
    anc.sifat = {
        k: v for k, v in {
            "ism_faail":  ds.ism_faail,
            "ism_mafuul": ds.ism_mafuul,
            "ism_makan":  ds.ism_makan,
            "ism_zaman":  ds.ism_zaman,
            "ism_aala":   ds.ism_aala,
        }.items() if v
    }

    # العقدة 6 — مصدر
    masdar_all = list(ds.masadir_samiyya)
    if ds.masdar_qiyasi:
        masdar_all.insert(0, ds.masdar_qiyasi)
    anc.masdar = masdar_all

    # العقدة 8 — وزن
    anc.wazn = ds.baab.value

    # العقدة 9 — مشتق
    anc.mushtaqq = [
        {
            "wazn":       m.wazn,
            "verb":       m.verb,
            "masdar":     m.masdar,
            "ism_faail":  m.ism_faail,
            "ism_mafuul": m.ism_mafuul,
            "meaning":    m.meaning,
            "wazn_op":    m.wazn_op,
        }
        for m in ds.mazidaat
    ]

    # ── الخطوة D: العقدة 7 — فعل من morphological_engine ────────────────
    anc.fi3l = _build_fi3l(root, ds.root_type, ds.baab)

    # ── الخطوة E: العقدتان 4 و10 — خواص + علاقة من slots_engine ─────────
    ilaqa, khawass = _build_ilaqa_khawass(pilot, root)
    anc.ilaqa   = ilaqa
    anc.khawass = khawass

    # ── الخطوة F: العقدة 2 — ذات مُشتقَّة ───────────────────────────────
    anc.dhat = _derive_dhat(mahiyya, anc.sifat)

    # ── الخطوة G: حكم — مفتوح ────────────────────────────────────────────
    anc.hokm = "OPEN"

    # ── الخطوة H: تحقق الاستمرارية ───────────────────────────────────────
    anc.warnings = warnings
    _check_continuity(anc)

    return anc


# ══════════════════════════════════════════════════════════════════════════
# العرض
# ══════════════════════════════════════════════════════════════════════════

def print_wave11(anc: Wave11Ancestry, synset_id: str = "") -> None:
    """يطبع السلسلة الكاملة بشكل مُنسَّق."""
    sep = "═" * 62
    print(f"\n{sep}")
    if synset_id:
        print(f"  WAVE11 — {synset_id}")
    print(f"  الكلمة المصدر : {anc.source_word}")
    print(f"  الجذر         : {anc.root}   [{anc.lookup_status}]")
    print(f"  متحقق مقاييس  : {'✓' if anc.root_verified else '✗'}")
    print(sep)

    print(f"\n  ① وجود    : {anc.wujud[:80] + '…' if len(anc.wujud) > 80 else anc.wujud or '—'}")
    print(f"\n  ② ذات     : {anc.dhat or '—'}")

    print(f"\n  ③ ماهية   ({len(anc.mahiyya)}) :")
    for ax in anc.mahiyya:
        print(f"      → {ax}")

    print(f"\n  ④ خواص    ({len(anc.khawass)}) :")
    for kh in anc.khawass:
        print(f"      • {kh}")

    print(f"\n  ⑤ صفات    :")
    for k, v in anc.sifat.items():
        label = {"ism_faail": "اسم فاعل", "ism_mafuul": "اسم مفعول",
                 "ism_makan": "اسم مكان",  "ism_zaman":  "اسم زمان",
                 "ism_aala":  "اسم آلة"}.get(k, k)
        print(f"      {label:12s}: {v}")

    print(f"\n  ⑥ مصدر    : {' / '.join(anc.masdar) or '—'}")
    print(f"\n  ⑦ فعل     : {anc.fi3l or '—'}")
    print(f"\n  ⑧ وزن     : {anc.wazn or '—'}")

    print(f"\n  ⑨ مشتق    ({len(anc.mushtaqq)}) :")
    for m in anc.mushtaqq:
        print(f"      [{m['wazn']}] {m['verb']:12s}  مصدر: {m['masdar']:15s}"
              f"  معنى: {m['meaning']}")

    print(f"\n  ⑩ علاقة   ({len(anc.ilaqa)}) :")
    for sl in anc.ilaqa:
        opt = "?" if sl["optional"] else "!"
        prep = f"/{sl['preposition']}" if sl.get("preposition") else ""
        print(f"      {sl['name']:8s}{prep} : {sl['sem_type']}{opt}   مثال: {sl['example']}")

    print(f"\n  ⑪ حكم     : {anc.hokm}")

    # ── جودة ─────────────────────────────────────────────────────────────
    print(f"\n  استمرارية السلسلة : {'✓ مكتملة' if anc.chain_continuity else '✗ ناقصة'}")
    if anc.open_nodes:
        print(f"  عقد مفتوحة       : {' / '.join(anc.open_nodes)}")
    if anc.warnings:
        print(f"\n  تحذيرات ({len(anc.warnings)}) :")
        for w in anc.warnings:
            print(f"    ⚠  {w}")
    print(f"{sep}\n")


# ══════════════════════════════════════════════════════════════════════════
# تشغيل مباشر — أمثلة
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    DB = "/root/maqayis_v2/maqayis.db"

    examples = [
        {
            "synset_id": "library.n.01",
            "words":     ["المكتبة", "library", "book collection"],
        },
        {
            "synset_id": "knowledge.n.01",
            "words":     ["العلم", "المعرفة", "knowledge"],
        },
        {
            "synset_id": "writing.n.01",
            "words":     ["الكتابة", "الخط", "writing"],
        },
    ]

    print("=" * 62)
    print("GRES-WAVE11 — طبقة النسب الاشتقاقي الوجودي")
    print("وجود → ذات → ماهية → خواص → صفات → مصدر → فعل → وزن → مشتق → علاقة → حكم")
    print("=" * 62)

    for ex in examples:
        anc = wave11_build(ex["words"], ex["synset_id"], DB)
        print_wave11(anc, ex["synset_id"])
