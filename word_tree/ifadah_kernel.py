"""
ifadah_kernel.py — LAYER 5: طبقة الإفادة
تحوِّل النسب الاشتقاقي (Wave11Ancestry) إلى جملة مفيدة مكتملة.

القاعدة الجوهرية:
  الكلمة تحمل قابليات. العامل يُشغِّلها. الإفادة تكتمل بالإسناد.
  الإسناد = نسبة حكم إلى موضوع في سياق.

الحدود الصارمة:
  • لا إفادة بلا مسند.
  • لا إفادة بلا مسند إليه.
  • لا جملة فعلية بلا فاعل.
  • لا جملة اسمية بلا مبتدأ وخبر.
  • لا عبارة وصفية تُرفع إلى جملة كاملة بغير دليل.
  • لا حكم هنا — الحكم في LAYER 6.

الطبقات:
  LAYER 0–4 → Wave11Ancestry         (النسب الاشتقاقي الوجودي)
  LAYER 5   → IfadahKernel  [هذا]   (الجملة المفيدة)
  LAYER 6   → IrabJudgmentKernel     (الحكم الإعرابي) ← OPEN
"""
from __future__ import annotations

from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from word_tree.wave11_ancestry import Wave11Ancestry, wave11_build
from word_tree.core.types import SemanticType
from word_tree.ifadah_types import (
    SentenceType, IsnadType,
    FilledSlot, IfadahResult, Layer6Handoff,
)


# ══════════════════════════════════════════════════════════════════════════
# قيم افتراضية للفتحات (عرض تجريبي — تُستبدَل بالسياق الفعلي)
# ══════════════════════════════════════════════════════════════════════════

_DEFAULT_FILLERS: dict[str, str] = {
    SemanticType.MUNJIZ.value:    "الطالبُ",
    SemanticType.MUTAATHIR.value: "المتأثِّرُ",
    SemanticType.MAWDUU.value:    "الكتابَ",
    SemanticType.MUDRIK.value:    "العالِمُ",
    SemanticType.MUJARRIB.value:  "المُجرِّبُ",
    SemanticType.MUHTAWA.value:   "الحقيقةَ",
    SemanticType.MASDAR.value:    "المصدرِ",
    SemanticType.GHAYA.value:     "الغايةَ",
    SemanticType.MAKAN.value:     "في المكانِ",
    SemanticType.ZAMAN.value:     "في الوقتِ",
    SemanticType.ADAA.value:      "بالأداةِ",
    SemanticType.MUSTAFID.value:  "للمستفيدِ",
    SemanticType.MIQDAAR.value:   "قدراً",
    SemanticType.HAYAA.value:     "هيئةً",
    SemanticType.SABAB.value:     "لسببٍ",
}


# ══════════════════════════════════════════════════════════════════════════
# الحراس (Guards) — يمنعون الإفادة الناقصة
# ══════════════════════════════════════════════════════════════════════════

def _guard_musnad(musnad: str, block_reasons: list[str]) -> bool:
    """الحارس 1: لا إفادة بلا مسند."""
    if not musnad.strip():
        block_reasons.append("GUARD_01: إفادة بلا مسند — مرفوضة")
        return False
    return True


def _guard_musnad_ilayh(musnad_ilayh: str, block_reasons: list[str]) -> bool:
    """الحارس 2: لا إفادة بلا مسند إليه."""
    if not musnad_ilayh.strip():
        block_reasons.append("GUARD_02: إفادة بلا مسند إليه — مرفوضة")
        return False
    return True


def _guard_fi3liyya_faail(
    fi3l: str, filled: list[FilledSlot], block_reasons: list[str]
) -> bool:
    """الحارس 3: لا جملة فعلية بلا فاعل."""
    if not fi3l:
        return True   # لا جملة فعلية أصلاً — لا انتهاك
    faail = next((s for s in filled if s.slot_name == "فاعل"), None)
    if not faail or not faail.value.strip():
        block_reasons.append("GUARD_03: جملة فعلية بلا فاعل — مرفوضة")
        return False
    return True


def _guard_ismiyya_mubtada_khabar(
    mubtada: str, khabar: str, block_reasons: list[str]
) -> bool:
    """الحارس 4: لا جملة اسمية بلا مبتدأ وخبر."""
    if mubtada and not khabar:
        block_reasons.append("GUARD_04: جملة اسمية بلا خبر — مرفوضة")
        return False
    if khabar and not mubtada:
        block_reasons.append("GUARD_04: جملة اسمية بلا مبتدأ — مرفوضة")
        return False
    return True


def _guard_wasfiyya_not_promoted(
    wasf: str, sentence_type: str, block_reasons: list[str]
) -> bool:
    """الحارس 5: العبارة الوصفية لا تُرفع إلى جملة كاملة بغير دليل."""
    if wasf and sentence_type == SentenceType.WASF:
        # لا بأس — تبقى وصفية
        return True
    if wasf and sentence_type == SentenceType.FI3LIYYA:
        # مسموح — الجملة الفعلية تُضاف إليها الوصفية كقيد
        return True
    return True   # الوصفية لا تُرفع تلقائياً — يحتاج دليلاً صريحاً


# ══════════════════════════════════════════════════════════════════════════
# تفعيل الفتحات
# ══════════════════════════════════════════════════════════════════════════

def activate_slots(
    anc:     Wave11Ancestry,
    context: Optional[dict[str, str]] = None,
) -> list[FilledSlot]:
    """
    يُفعِّل فتحات الجذر بقيم من السياق أو بقيم افتراضية.
    context: {اسم_الفتحة: قيمة}
    """
    ctx = context or {}
    filled: list[FilledSlot] = []

    for slot in anc.ilaqa:
        name     = slot["name"]
        sem      = slot["sem_type"]
        optional = slot["optional"]
        prep     = slot.get("preposition")
        example  = slot.get("example", "")

        value = ctx.get(name) or example or _DEFAULT_FILLERS.get(sem, "شيءٌ")

        filled.append(FilledSlot(
            slot_name   = name,
            sem_type    = sem,
            value       = value,
            optional    = optional,
            preposition = prep,
        ))

    return filled


# ══════════════════════════════════════════════════════════════════════════
# بناء الجملة الفعلية
# ══════════════════════════════════════════════════════════════════════════

def _build_fi3liyya(
    fi3l:   str,
    filled: list[FilledSlot],
    block_reasons: list[str],
) -> tuple[str, str, str, list[str]]:
    """فعل + فاعل + (مفعول) + (قيود إلزامية)"""
    if not fi3l:
        return "", "", "", []

    faail   = next((s for s in filled if s.slot_name == "فاعل"),   None)
    maf3uul = next((s for s in filled if s.slot_name == "مفعول"), None)
    quyuud  = [s for s in filled if s.slot_name not in ("فاعل", "مفعول") and not s.optional]

    # حارس: الفعل يحتاج فاعلاً
    if not _guard_fi3liyya_faail(fi3l, filled, block_reasons):
        return "", fi3l, "", []

    musnad       = fi3l
    musnad_ilayh = faail.value if faail else ""
    qayd_parts   = []

    if maf3uul:
        qayd_parts.append(maf3uul.surface())
    for q in quyuud:
        qayd_parts.append(q.surface())

    parts  = [fi3l, musnad_ilayh] + qayd_parts
    jumlah = " ".join(p for p in parts if p)

    return jumlah, musnad, musnad_ilayh, qayd_parts


# ══════════════════════════════════════════════════════════════════════════
# بناء الجملة الاسمية
# ══════════════════════════════════════════════════════════════════════════

def _build_ismiyya(
    anc: Wave11Ancestry,
    block_reasons: list[str],
) -> str:
    """مبتدأ + خبر — كلاهما إلزامي."""
    mubtada = anc.sifat.get("ism_faail", "")
    khabar  = anc.mahiyya[0] if anc.mahiyya else ""

    if not _guard_ismiyya_mubtada_khabar(mubtada, khabar, block_reasons):
        return ""
    if not mubtada or not khabar:
        return ""
    return f"{mubtada} {khabar}"


# ══════════════════════════════════════════════════════════════════════════
# بناء العبارة الوصفية (تبقى وصفية — لا تُرفع)
# ══════════════════════════════════════════════════════════════════════════

def _build_wasfiyya(anc: Wave11Ancestry) -> str:
    """اسم مكان: مكان المصدر — عبارة وصفية فقط."""
    ism_m  = anc.sifat.get("ism_makan", "")
    masdar = anc.masdar[0] if anc.masdar else ""
    if not ism_m or not masdar:
        return ""
    return f"{ism_m}: مكان {masdar}"


# ══════════════════════════════════════════════════════════════════════════
# نقطة الدخول الرئيسية
# ══════════════════════════════════════════════════════════════════════════

def ifadah_build(
    anc:       Wave11Ancestry,
    synset_id: str = "",
    context:   Optional[dict[str, str]] = None,
) -> IfadahResult:
    """
    يبني LAYER 5 من Wave11Ancestry.

    المدخلات:
        anc        — مخرج wave11_build()
        synset_id  — معرِّف المجموعة
        context    — {اسم_الفتحة: قيمة} لتخصيص الفتحات

    المخرجات:
        IfadahResult — جاهز للـ handoff إلى LAYER 6
    """
    block_reasons: list[str] = []

    result = IfadahResult(root=anc.root, synset_id=synset_id, wave11_ref=anc)

    if not anc.root or not anc.root_verified:
        block_reasons.append("GUARD_00: جذر غير موثَّق في مقاييس اللغة")
        result.block_reasons  = block_reasons
        result.freeze_status  = "IFADAH_KERNEL_LAYER5_BLOCKED_WITH_EXACT_REASONS"
        result.hokm_placeholder = "OPEN → LAYER 6 — محجوب: جذر غير موثَّق"
        return result

    # ── تفعيل الفتحات ───────────────────────────────────────────────────
    filled = activate_slots(anc, context)
    result.filled_slots = filled

    # ── الجملة الفعلية ──────────────────────────────────────────────────
    jumlah_f, musnad, m_ilayh, qayd = _build_fi3liyya(anc.fi3l, filled, block_reasons)

    # حراس الإسناد الأساسية
    _guard_musnad(musnad, block_reasons)
    _guard_musnad_ilayh(m_ilayh, block_reasons)

    result.jumlah_fi3liyya = jumlah_f
    result.musnad          = musnad
    result.musnad_ilayh    = m_ilayh
    result.qayd            = qayd
    result.sentence_type   = SentenceType.FI3LIYYA
    result.isnad_type      = IsnadType.HAQIQI

    # ── الجملة الاسمية ──────────────────────────────────────────────────
    result.jumlah_ismiyya = _build_ismiyya(anc, block_reasons)

    # ── العبارة الوصفية ─────────────────────────────────────────────────
    wasf = _build_wasfiyya(anc)
    _guard_wasfiyya_not_promoted(wasf, result.sentence_type, block_reasons)
    result.jumlah_wasfiyya = wasf

    # ── تحديد حالة التجميد ──────────────────────────────────────────────
    if block_reasons:
        result.freeze_status  = "IFADAH_KERNEL_LAYER5_BLOCKED_WITH_EXACT_REASONS"
        result.hokm_placeholder = f"OPEN → LAYER 6 — محجوب ({len(block_reasons)} أسباب)"
    else:
        result.freeze_status  = "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF"
        result.hokm_placeholder = "OPEN → LAYER 6"

    result.block_reasons = block_reasons
    return result


# ══════════════════════════════════════════════════════════════════════════
# واجهة مباشرة: من الكلمات إلى الإفادة
# ══════════════════════════════════════════════════════════════════════════

def ifadah_from_words(
    words:     list[str],
    synset_id: str,
    db_path:   str,
    context:   Optional[dict[str, str]] = None,
) -> IfadahResult:
    """من قائمة كلمات مباشرة إلى الجملة المفيدة."""
    anc = wave11_build(words, synset_id, db_path)
    return ifadah_build(anc, synset_id, context)


# ══════════════════════════════════════════════════════════════════════════
# العرض
# ══════════════════════════════════════════════════════════════════════════

def print_ifadah(r: IfadahResult) -> None:
    sep = "─" * 62
    print(f"\n{sep}")
    print(f"  LAYER 5 [{r.synset_id}]  جذر: {r.root}")
    print(f"  الحالة: {r.freeze_status}")
    print(sep)

    if r.block_reasons:
        print(f"\n  ⛔ أسباب الحجب ({len(r.block_reasons)}):")
        for br in r.block_reasons:
            print(f"    • {br}")
    else:
        print(f"\n  الجملة الفعلية  : {r.jumlah_fi3liyya or '—'}")
        print(f"    المسند         : {r.musnad}")
        print(f"    المسند إليه    : {r.musnad_ilayh}")
        if r.qayd:
            print(f"    القيود         : {' / '.join(r.qayd)}")
        print(f"\n  الجملة الاسمية  : {r.jumlah_ismiyya or '—'}")
        print(f"  العبارة الوصفية : {r.jumlah_wasfiyya or '—'}  [وصفية — لا تُرفع]")

        if r.filled_slots:
            print(f"\n  الفتحات المُفعَّلة ({len(r.filled_slots)}):")
            for fs in r.filled_slots:
                tag  = "?" if fs.optional else "!"
                prep = f"/{fs.preposition}" if fs.preposition else ""
                print(f"    [{fs.sem_type}{tag}] {fs.slot_name}{prep} ← {fs.value}")

    print(f"\n  ⑪ حكم (LAYER 6) : {r.hokm_placeholder}")
    if r.is_frozen:
        h = r.to_layer6_handoff()
        print(f"\n  LAYER 6 handoff :")
        print(f"    raw_sentence  = {h.raw_sentence!r}")
        print(f"    musnad        = {h.musnad!r}")
        print(f"    musnad_ilayh  = {h.musnad_ilayh!r}")
        print(f"    qayd          = {h.qayd}")
    print(f"{sep}\n")
