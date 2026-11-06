"""
hokom_kernel.py
━━━━━━━━━━━━━━━
LAYER 7 — HokomKernel

النطاق الوحيد: حكم لغوي على سلامة الجملة تركيبياً.
لا حكم فقهي. لا فتوى. لا تفسير. لا إغلاق GRES-HUKM الفقهي.
لا يُعيد فتح Wave11 ولا IfadahResult ولا IrabJudgmentResult.

المدخل:  Layer7Handoff (من LAYER 6 المجمَّد)
المخرج:  HokomResult (حكم سلامة الجملة + الاختلالات إن وُجدت)

القواعد الثلاث (فحوص السلامة):
  R1 — ISNAD:     اكتمال الإسناد (فعلية: فعل+فاعل / اسمية: مبتدأ+خبر)
  R2 — AGREEMENT: مطابقة الحالة الإعرابية للدور (فاعل مرفوع، مفعول منصوب، ...)
  R3 — MUTTASIL:  كل متعلَّق غير فارغ يجب أن يُحيل إلى كلمة موجودة في الجملة

الحراس:
  GUARD_L7_00 — layer6_frozen غير صحيح
  GUARD_L7_01 — sentence فارغة
  GUARD_L7_02 — لا مدخلات إعرابية (entries فارغة)
  GUARD_L7_03 — نوع الجملة غير مدعوم
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from typing import List, Optional

from ifadah_types import SentenceType
from irab_types import (
    IrabCase,
    IrabRole,
    Layer7Handoff,
    LAYER6_FROZEN_TOKEN,
)
from hokom_types import (
    GUARD_L7_LABELS,
    HokomResult,
    HokomVerdict,
    SoundnessCheck,
)

# ── أنواع الجمل المدعومة ──────────────────────────────────────────────────────
_SUPPORTED_TYPES = {SentenceType.FI3LIYYA, SentenceType.ISMIYYA, SentenceType.WASF}

# ── القاعدة R2: الحالة الإعرابية المتوقَّعة لكل دور ────────────────────────────
_EXPECTED_CASE = {
    IrabRole.FI3L:      {IrabCase.MABNI, IrabCase.MARFOO3},
    IrabRole.FAAIL:     {IrabCase.MARFOO3},
    IrabRole.MAF3OOL:   {IrabCase.MANSOOB},
    IrabRole.MUBTADA:   {IrabCase.MARFOO3},
    IrabRole.KHABAR:    {IrabCase.MARFOO3},
    IrabRole.QAYD_JAR:  {IrabCase.MAJROOR},
    IrabRole.QAYD_ZARF: {IrabCase.MANSOOB},
    IrabRole.QAYD_HAL:  {IrabCase.MANSOOB},
}


# ══════════════════════════════════════════════════════════════════════════════
# الحراس (GUARD_L7_00 — GUARD_L7_03)
# ══════════════════════════════════════════════════════════════════════════════

def _guard_layer6_frozen(handoff: Layer7Handoff, reasons: List[str]) -> bool:
    """GUARD_L7_00: layer6_frozen يجب أن يكون LAYER6_FROZEN_TOKEN."""
    if handoff.layer6_frozen != LAYER6_FROZEN_TOKEN:
        reasons.append(
            f"GUARD_L7_00: layer6_frozen='{handoff.layer6_frozen}' ≠ '{LAYER6_FROZEN_TOKEN}'"
        )
        return False
    return True


def _guard_sentence(handoff: Layer7Handoff, reasons: List[str]) -> bool:
    """GUARD_L7_01: sentence لا يجوز أن تكون فارغة."""
    if not handoff.sentence or not handoff.sentence.strip():
        reasons.append("GUARD_L7_01: sentence فارغة — لا جملة للحكم")
        return False
    return True


def _guard_entries(handoff: Layer7Handoff, reasons: List[str]) -> bool:
    """GUARD_L7_02: entries لا يجوز أن تكون فارغة — لا حكم بلا إعراب."""
    if not handoff.entries:
        reasons.append("GUARD_L7_02: لا مدخلات إعرابية — تعذَّر الحكم")
        return False
    return True


def _guard_sentence_type(handoff: Layer7Handoff, reasons: List[str]) -> bool:
    """GUARD_L7_03: نوع الجملة يجب أن يكون مدعوماً."""
    if handoff.sentence_type not in _SUPPORTED_TYPES:
        reasons.append(
            f"GUARD_L7_03: نوع الجملة '{handoff.sentence_type}' غير مدعوم"
        )
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# فحوص السلامة (R1 — R3)
# ══════════════════════════════════════════════════════════════════════════════

def _check_isnad(handoff: Layer7Handoff) -> SoundnessCheck:
    """R1: اكتمال الإسناد بحسب نوع الجملة."""
    roles = {e.irab_role for e in handoff.entries}
    if handoff.sentence_type == SentenceType.FI3LIYYA:
        missing = [r for r in (IrabRole.FI3L, IrabRole.FAAIL) if r not in roles]
        label = "جملة فعلية"
    else:  # ISMIYYA أو WASF — كلاهما يُبنى مبتدأً وخبراً في LAYER 6
        missing = [r for r in (IrabRole.MUBTADA, IrabRole.KHABAR) if r not in roles]
        label = "جملة اسمية"
    if missing:
        return SoundnessCheck(
            name="ISNAD", passed=False,
            detail=f"{label} ناقصة الإسناد — مفقود: {' و'.join(missing)}",
        )
    return SoundnessCheck(name="ISNAD", passed=True, detail=f"{label} مكتملة الإسناد")


def _check_agreement(handoff: Layer7Handoff) -> SoundnessCheck:
    """R2: مطابقة الحالة الإعرابية للدور لكل عنصر."""
    mismatches: List[str] = []
    for e in handoff.entries:
        expected = _EXPECTED_CASE.get(e.irab_role)
        if expected is not None and e.irab_case not in expected:
            mismatches.append(
                f"«{e.word}» ({e.irab_role}) جاء {e.irab_case} والمتوقَّع {' أو '.join(sorted(expected))}"
            )
    if mismatches:
        return SoundnessCheck(
            name="AGREEMENT", passed=False,
            detail="اختلال في المطابقة الإعرابية: " + "؛ ".join(mismatches),
        )
    return SoundnessCheck(name="AGREEMENT", passed=True, detail="جميع الحالات الإعرابية مطابقة لأدوارها")


def _check_muttasil(handoff: Layer7Handoff) -> SoundnessCheck:
    """R3: كل متعلَّق (muttasil) غير فارغ يجب أن يُحيل إلى كلمة موجودة."""
    words = {e.word for e in handoff.entries}
    orphans: List[str] = []
    for e in handoff.entries:
        if e.muttasil and e.muttasil not in words:
            orphans.append(f"«{e.word}» يتعلَّق بـ «{e.muttasil}» غير الموجود في الجملة")
    if orphans:
        return SoundnessCheck(
            name="MUTTASIL", passed=False,
            detail="تعلُّق يتيم: " + "؛ ".join(orphans),
        )
    return SoundnessCheck(name="MUTTASIL", passed=True, detail="جميع التعلُّقات تُحيل إلى عناصر موجودة")


# ══════════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية — hokom_judge
# ══════════════════════════════════════════════════════════════════════════════

def hokom_judge(handoff: Layer7Handoff) -> HokomResult:
    """يستقبل Layer7Handoff وينتج HokomResult — حكم سلامة الجملة."""
    block_reasons: List[str] = []

    def _blocked() -> HokomResult:
        return HokomResult(
            root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.sentence, sentence_type=handoff.sentence_type,
            verdict=HokomVerdict.BLOCKED, checks=[], defects=[],
            block_reasons=block_reasons,
        )

    if not _guard_layer6_frozen(handoff, block_reasons):
        return _blocked()
    if not _guard_sentence(handoff, block_reasons):
        return _blocked()
    if not _guard_entries(handoff, block_reasons):
        return _blocked()
    if not _guard_sentence_type(handoff, block_reasons):
        return _blocked()

    checks = [
        _check_isnad(handoff),
        _check_agreement(handoff),
        _check_muttasil(handoff),
    ]
    defects = [c.detail for c in checks if not c.passed]
    verdict = HokomVerdict.SALEEM if not defects else HokomVerdict.MUKHTALL

    return HokomResult(
        root=handoff.root, synset_id=handoff.synset_id,
        sentence=handoff.sentence, sentence_type=handoff.sentence_type,
        verdict=verdict, checks=checks, defects=defects, block_reasons=[],
    )


def hokom_judge_from_irab(irab_result) -> Optional[HokomResult]:
    """طريق ملائم: يأخذ IrabJudgmentResult مكتملاً ويحكم على سلامته."""
    if not hasattr(irab_result, "is_complete") or not irab_result.is_complete:
        return None
    if not hasattr(irab_result, "to_layer7_handoff"):
        return None
    handoff = irab_result.to_layer7_handoff()
    if handoff is None:
        return None
    return hokom_judge(handoff)


assert callable(hokom_judge)
assert callable(hokom_judge_from_irab)
assert len(GUARD_L7_LABELS) == 4
