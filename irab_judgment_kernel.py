"""
irab_judgment_kernel.py
━━━━━━━━━━━━━━━━━━━━━━━
LAYER 6 — IrabJudgmentKernel

النطاق الوحيد: حكم إعرابي / تركيبي نحوي.
لا حكم فقهي. لا فتوى. لا تفسير. لا GRES-HUKM فقهي.

المدخل:  Layer6Handoff (من LAYER 5 المجمَّد)
المخرج:  IrabJudgmentResult (أحكام إعرابية لكل عنصر)

القواعد:
  A — الفعل (مسند فعلية)
  B — الفاعل (مسند إليه في فعلية)
  C — المفعول به (قيد أول في فعلية)
  D — المبتدأ (مسند إليه في اسمية)
  E — الخبر (مسند في اسمية)
  F — القيد العام (جار ومجرور / ظرف / حال)

الحراس:
  GUARD_L6_00 — layer5_frozen غير صحيح
  GUARD_L6_01 — raw_sentence فارغة
  GUARD_L6_02 — musnad فارغ
  GUARD_L6_03 — musnad_ilayh فارغ
  GUARD_L6_04 — جملة فعلية بلا فاعل
  GUARD_L6_05 — جملة اسمية بلا مبتدأ أو خبر
  GUARD_L6_06 — لا حكم إعرابي ممكن الاستنتاج
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from typing import List, Optional

from ifadah_types import Layer6Handoff, SentenceType
from irab_types import (
    IrabCase,
    IrabEntry,
    IrabJudgmentResult,
    IrabRole,
    IrabSign,
    LAYER5_FROZEN_TOKEN,
    LAYER6_VERDICT_TOKEN,
)

# ── ثوابت داخلية ──────────────────────────────────────────────────────────────
_LAYER6_FROZEN = LAYER6_VERDICT_TOKEN

# بادئات الجار (بسيطة — تكفي للحكم التركيبي)
_JAR_PREFIXES = {"في", "من", "إلى", "على", "عن", "ب", "ك", "ل", "بـ", "لـ"}

# ══════════════════════════════════════════════════════════════════════════════
# الحراس (GUARD_L6_00 — GUARD_L6_06)
# ══════════════════════════════════════════════════════════════════════════════

def _guard_layer5_frozen(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_00: layer5_frozen يجب أن يكون LAYER5_FROZEN_TOKEN."""
    if handoff.layer5_frozen != LAYER5_FROZEN_TOKEN:
        reasons.append(
            f"GUARD_L6_00: layer5_frozen='{handoff.layer5_frozen}' ≠ '{LAYER5_FROZEN_TOKEN}'"
        )
        return False
    return True


def _guard_raw_sentence(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_01: raw_sentence لا يجوز أن تكون فارغة."""
    if not handoff.raw_sentence or not handoff.raw_sentence.strip():
        reasons.append("GUARD_L6_01: raw_sentence فارغة — لا جملة للإعراب")
        return False
    return True


def _guard_musnad(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_02: musnad لا يجوز أن يكون فارغاً."""
    if not handoff.musnad or not handoff.musnad.strip():
        reasons.append("GUARD_L6_02: musnad فارغ — لا مسند للحكم")
        return False
    return True


def _guard_musnad_ilayh(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_03: musnad_ilayh لا يجوز أن يكون فارغاً."""
    if not handoff.musnad_ilayh or not handoff.musnad_ilayh.strip():
        reasons.append("GUARD_L6_03: musnad_ilayh فارغ — لا مسند إليه")
        return False
    return True


def _guard_fi3liyya_faail(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_04: الجملة الفعلية يجب أن يكون لها فاعل (musnad_ilayh)."""
    if handoff.sentence_type == SentenceType.FI3LIYYA:
        if not handoff.musnad_ilayh or not handoff.musnad_ilayh.strip():
            reasons.append("GUARD_L6_04: جملة فعلية بلا فاعل — مرفوض")
            return False
    return True


def _guard_ismiyya_mubtada_khabar(handoff: Layer6Handoff, reasons: List[str]) -> bool:
    """GUARD_L6_05: الجملة الاسمية تحتاج مبتدأ (musnad_ilayh) وخبر (musnad)."""
    if handoff.sentence_type == SentenceType.ISMIYYA:
        missing = []
        if not handoff.musnad_ilayh or not handoff.musnad_ilayh.strip():
            missing.append("مبتدأ")
        if not handoff.musnad or not handoff.musnad.strip():
            missing.append("خبر")
        if missing:
            reasons.append(
                f"GUARD_L6_05: جملة اسمية ناقصة — مفقود: {' و'.join(missing)}"
            )
            return False
    return True


def _guard_irab_producible(entries: List[IrabEntry], reasons: List[str]) -> bool:
    """GUARD_L6_06: يجب أن يُنتج الكيرنل حكماً واحداً على الأقل."""
    if not entries:
        reasons.append("GUARD_L6_06: لا حكم إعرابي واحد أمكن الاستنتاج")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# تحديد نوع الفعل (القاعدة A)
# ══════════════════════════════════════════════════════════════════════════════

def _fi3l_sign(musnad: str) -> tuple:
    """القاعدة A: تحديد حكم الفعل وعلامته وسببه."""
    stripped = musnad.strip()
    first = stripped[0] if stripped else ""
    if first in ("ي", "ت", "أ", "ن"):
        return (IrabCase.MARFOO3, IrabSign.DAMMA, "فعل مضارع مرفوع بالضمة لتجرده من الناصب والجازم")
    else:
        return (IrabCase.MABNI, IrabSign.MABNI_FATH, "فعل ماضٍ مبني على الفتح")


# ══════════════════════════════════════════════════════════════════════════════
# القاعدة F — تصنيف القيد
# ══════════════════════════════════════════════════════════════════════════════

def _classify_qayd(qayd_word: str, musnad: str) -> IrabEntry:
    """القاعدة F: الحكم الإعرابي للقيود."""
    w = qayd_word.strip()
    first_token = w.split()[0] if w.split() else w
    if first_token in _JAR_PREFIXES or any(w.startswith(p) for p in ("بـ", "لـ", "كـ")):
        return IrabEntry(
            word=w, position=2, irab_role=IrabRole.QAYD_JAR,
            irab_case=IrabCase.MAJROOR, irab_sign=IrabSign.KASRA,
            irab_reason="جار ومجرور — الاسم مجرور بحرف الجر", muttasil=musnad,
        )
    if w.endswith("اً") or w.endswith("ًا"):
        return IrabEntry(
            word=w, position=2, irab_role=IrabRole.QAYD_ZARF,
            irab_case=IrabCase.MANSOOB, irab_sign=IrabSign.FATHA,
            irab_reason="منصوب على الظرفية أو المفعولية", muttasil=musnad,
        )
    return IrabEntry(
        word=w, position=2, irab_role=IrabRole.MAF3OOL,
        irab_case=IrabCase.MANSOOB, irab_sign=IrabSign.FATHA,
        irab_reason="مفعول به منصوب وعلامة نصبه الفتحة", muttasil="",
    )


# ══════════════════════════════════════════════════════════════════════════════
# بناء الأحكام
# ══════════════════════════════════════════════════════════════════════════════

def _build_fi3liyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    entries: List[IrabEntry] = []
    fi3l_case, fi3l_sign, fi3l_reason = _fi3l_sign(handoff.musnad)
    entries.append(IrabEntry(
        word=handoff.musnad, position=0, irab_role=IrabRole.FI3L,
        irab_case=fi3l_case, irab_sign=fi3l_sign, irab_reason=fi3l_reason, muttasil="",
    ))
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh, position=1, irab_role=IrabRole.FAAIL,
        irab_case=IrabCase.MARFOO3, irab_sign=IrabSign.DAMMA,
        irab_reason="فاعل مرفوع — الفعل رفع فاعله وجوباً", muttasil=handoff.musnad,
    ))
    if handoff.qayd:
        first_qayd = handoff.qayd[0]
        entries.append(IrabEntry(
            word=first_qayd, position=2, irab_role=IrabRole.MAF3OOL,
            irab_case=IrabCase.MANSOOB, irab_sign=IrabSign.FATHA,
            irab_reason="مفعول به منصوب وعلامة نصبه الفتحة", muttasil=handoff.musnad,
        ))
        for idx, qw in enumerate(handoff.qayd[1:], start=3):
            entry = _classify_qayd(qw, handoff.musnad)
            entries.append(IrabEntry(
                word=entry.word, position=idx, irab_role=entry.irab_role,
                irab_case=entry.irab_case, irab_sign=entry.irab_sign,
                irab_reason=entry.irab_reason, muttasil=entry.muttasil,
            ))
    return entries


def _build_ismiyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    entries: List[IrabEntry] = []
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh, position=0, irab_role=IrabRole.MUBTADA,
        irab_case=IrabCase.MARFOO3, irab_sign=IrabSign.DAMMA,
        irab_reason="مبتدأ مرفوع وعلامة رفعه الضمة", muttasil="",
    ))
    entries.append(IrabEntry(
        word=handoff.musnad, position=1, irab_role=IrabRole.KHABAR,
        irab_case=IrabCase.MARFOO3, irab_sign=IrabSign.DAMMA,
        irab_reason="خبر مرفوع وعلامة رفعه الضمة", muttasil=handoff.musnad_ilayh,
    ))
    for idx, qw in enumerate(handoff.qayd, start=2):
        entry = _classify_qayd(qw, handoff.musnad)
        entries.append(IrabEntry(
            word=entry.word, position=idx, irab_role=entry.irab_role,
            irab_case=entry.irab_case, irab_sign=entry.irab_sign,
            irab_reason=entry.irab_reason, muttasil=entry.muttasil,
        ))
    return entries


def _build_wasfiyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    entries: List[IrabEntry] = []
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh, position=0, irab_role=IrabRole.MUBTADA,
        irab_case=IrabCase.MARFOO3, irab_sign=IrabSign.DAMMA,
        irab_reason="اسم موصوف — مرفوع وعلامة رفعه الضمة", muttasil="",
    ))
    entries.append(IrabEntry(
        word=handoff.musnad, position=1, irab_role=IrabRole.KHABAR,
        irab_case=IrabCase.MARFOO3, irab_sign=IrabSign.DAMMA,
        irab_reason="خبر وصفي مرفوع أو نعت تابع لموصوفه في الإعراب",
        muttasil=handoff.musnad_ilayh,
    ))
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية — irab_judge
# ══════════════════════════════════════════════════════════════════════════════

def irab_judge(handoff: Layer6Handoff) -> IrabJudgmentResult:
    """يستقبل Layer6Handoff وينتج IrabJudgmentResult."""
    block_reasons: List[str] = []

    if not _guard_layer5_frozen(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)
    if not _guard_raw_sentence(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)
    if not _guard_musnad(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)
    if not _guard_musnad_ilayh(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)
    if not _guard_fi3liyya_faail(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)
    if not _guard_ismiyya_mubtada_khabar(handoff, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=handoff.sentence_type,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)

    stype = handoff.sentence_type
    if stype == SentenceType.FI3LIYYA:
        entries = _build_fi3liyya_entries(handoff)
    elif stype == SentenceType.ISMIYYA:
        entries = _build_ismiyya_entries(handoff)
    elif stype == SentenceType.WASF:
        entries = _build_wasfiyya_entries(handoff)
    else:
        entries = _build_fi3liyya_entries(handoff)

    if not _guard_irab_producible(entries, block_reasons):
        return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence, sentence_type=stype,
            entries=[], verdict="BLOCKED", block_reasons=block_reasons)

    return IrabJudgmentResult(root=handoff.root, synset_id=handoff.synset_id,
        sentence=handoff.raw_sentence, sentence_type=stype,
        entries=entries, verdict="IRAB_COMPLETE", block_reasons=[])


def irab_judge_from_ifadah(ifadah_result) -> Optional[IrabJudgmentResult]:
    if not hasattr(ifadah_result, "is_frozen") or not ifadah_result.is_frozen:
        return None
    if not hasattr(ifadah_result, "to_layer6_handoff"):
        return None
    handoff = ifadah_result.to_layer6_handoff()
    if handoff is None:
        return None
    return irab_judge(handoff)


assert callable(irab_judge)
assert callable(irab_judge_from_ifadah)
