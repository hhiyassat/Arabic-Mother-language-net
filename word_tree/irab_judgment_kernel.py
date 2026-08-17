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

from typing import List, Optional

from word_tree.ifadah_types import Layer6Handoff, SentenceType
from word_tree.irab_types import (
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

def _fi3l_sign(musnad: str) -> tuple[str, str, str]:
    """
    القاعدة A: تحديد حكم الفعل وعلامته وسببه.

    المضارع يبدأ بـ يَ/يُ/تَ/تُ/أَ/نَ.
    الماضي مبني على الفتح عادةً.
    """
    stripped = musnad.strip()
    # أبسط فحص: إذا بدأ بـ يـ أو تـ أو أ أو ن → مضارع
    first = stripped[0] if stripped else ""
    if first in ("ي", "ت", "أ", "ن"):
        return (IrabCase.MARFOO3, IrabSign.DAMMA, "فعل مضارع مرفوع بالضمة لتجرده من الناصب والجازم")
    else:
        return (IrabCase.MABNI, IrabSign.MABNI_FATH, "فعل ماضٍ مبني على الفتح")


# ══════════════════════════════════════════════════════════════════════════════
# القاعدة F — تصنيف القيد
# ══════════════════════════════════════════════════════════════════════════════

def _classify_qayd(qayd_word: str, musnad: str) -> IrabEntry:
    """القاعدة F: الحكم الإعرابي للقيود (ظرف / جار ومجرور / حال / مفعول به ثانٍ)."""
    w = qayd_word.strip()
    # فحص بسيط: إذا بدأ بحرف جر معروف → جار ومجرور
    first_token = w.split()[0] if w.split() else w
    if first_token in _JAR_PREFIXES or any(w.startswith(p) for p in ("بـ", "لـ", "كـ")):
        return IrabEntry(
            word=w,
            position=2,
            irab_role=IrabRole.QAYD_JAR,
            irab_case=IrabCase.MAJROOR,
            irab_sign=IrabSign.KASRA,
            irab_reason="جار ومجرور — الاسم مجرور بحرف الجر",
            muttasil=musnad,
        )
    # إذا انتهى بـ ًا (فتحتان) → مفعول به أو ظرف
    if w.endswith("اً") or w.endswith("ًا"):
        return IrabEntry(
            word=w,
            position=2,
            irab_role=IrabRole.QAYD_ZARF,
            irab_case=IrabCase.MANSOOB,
            irab_sign=IrabSign.FATHA,
            irab_reason="منصوب على الظرفية أو المفعولية",
            muttasil=musnad,
        )
    # الافتراضي: مفعول به ثانٍ منصوب
    return IrabEntry(
        word=w,
        position=2,
        irab_role=IrabRole.MAF3OOL,
        irab_case=IrabCase.MANSOOB,
        irab_sign=IrabSign.FATHA,
        irab_reason="مفعول به منصوب وعلامة نصبه الفتحة",
        muttasil="",
    )


# ══════════════════════════════════════════════════════════════════════════════
# بناء أحكام الجملة الفعلية (القواعد A + B + C + F)
# ══════════════════════════════════════════════════════════════════════════════

def _build_fi3liyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    """القواعد A/B/C/F — الجملة الفعلية."""
    entries: List[IrabEntry] = []

    # القاعدة A — الفعل
    fi3l_case, fi3l_sign, fi3l_reason = _fi3l_sign(handoff.musnad)
    entries.append(IrabEntry(
        word=handoff.musnad,
        position=0,
        irab_role=IrabRole.FI3L,
        irab_case=fi3l_case,
        irab_sign=fi3l_sign,
        irab_reason=fi3l_reason,
        muttasil="",
    ))

    # القاعدة B — الفاعل
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh,
        position=1,
        irab_role=IrabRole.FAAIL,
        irab_case=IrabCase.MARFOO3,
        irab_sign=IrabSign.DAMMA,
        irab_reason="فاعل مرفوع — الفعل رفع فاعله وجوباً",
        muttasil=handoff.musnad,
    ))

    # القاعدة C — المفعول به (أول قيد)
    if handoff.qayd:
        first_qayd = handoff.qayd[0]
        entries.append(IrabEntry(
            word=first_qayd,
            position=2,
            irab_role=IrabRole.MAF3OOL,
            irab_case=IrabCase.MANSOOB,
            irab_sign=IrabSign.FATHA,
            irab_reason="مفعول به منصوب وعلامة نصبه الفتحة",
            muttasil=handoff.musnad,
        ))

        # القاعدة F — القيود الباقية
        for idx, qw in enumerate(handoff.qayd[1:], start=3):
            entry = _classify_qayd(qw, handoff.musnad)
            # تحديث الموقع
            entries.append(IrabEntry(
                word=entry.word,
                position=idx,
                irab_role=entry.irab_role,
                irab_case=entry.irab_case,
                irab_sign=entry.irab_sign,
                irab_reason=entry.irab_reason,
                muttasil=entry.muttasil,
            ))

    return entries


# ══════════════════════════════════════════════════════════════════════════════
# بناء أحكام الجملة الاسمية (القواعد D + E + F)
# ══════════════════════════════════════════════════════════════════════════════

def _build_ismiyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    """القواعد D/E/F — الجملة الاسمية."""
    entries: List[IrabEntry] = []

    # القاعدة D — المبتدأ
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh,
        position=0,
        irab_role=IrabRole.MUBTADA,
        irab_case=IrabCase.MARFOO3,
        irab_sign=IrabSign.DAMMA,
        irab_reason="مبتدأ مرفوع وعلامة رفعه الضمة",
        muttasil="",
    ))

    # القاعدة E — الخبر
    entries.append(IrabEntry(
        word=handoff.musnad,
        position=1,
        irab_role=IrabRole.KHABAR,
        irab_case=IrabCase.MARFOO3,
        irab_sign=IrabSign.DAMMA,
        irab_reason="خبر مرفوع وعلامة رفعه الضمة",
        muttasil=handoff.musnad_ilayh,
    ))

    # القاعدة F — القيود
    for idx, qw in enumerate(handoff.qayd, start=2):
        entry = _classify_qayd(qw, handoff.musnad)
        entries.append(IrabEntry(
            word=entry.word,
            position=idx,
            irab_role=entry.irab_role,
            irab_case=entry.irab_case,
            irab_sign=entry.irab_sign,
            irab_reason=entry.irab_reason,
            muttasil=entry.muttasil,
        ))

    return entries


# ══════════════════════════════════════════════════════════════════════════════
# بناء أحكام الجملة الوصفية (نعتية — مبسَّطة)
# ══════════════════════════════════════════════════════════════════════════════

def _build_wasfiyya_entries(handoff: Layer6Handoff) -> List[IrabEntry]:
    """القاعدة D/E + نعت — الجملة الوصفية."""
    entries: List[IrabEntry] = []

    # الاسم الموصوف → مبتدأ (أو معمول)
    entries.append(IrabEntry(
        word=handoff.musnad_ilayh,
        position=0,
        irab_role=IrabRole.MUBTADA,
        irab_case=IrabCase.MARFOO3,
        irab_sign=IrabSign.DAMMA,
        irab_reason="اسم موصوف — مرفوع وعلامة رفعه الضمة",
        muttasil="",
    ))

    # الصفة / الخبر الوصفي
    entries.append(IrabEntry(
        word=handoff.musnad,
        position=1,
        irab_role=IrabRole.KHABAR,
        irab_case=IrabCase.MARFOO3,
        irab_sign=IrabSign.DAMMA,
        irab_reason="خبر وصفي مرفوع أو نعت تابع لموصوفه في الإعراب",
        muttasil=handoff.musnad_ilayh,
    ))

    return entries


# ══════════════════════════════════════════════════════════════════════════════
# الدالة الرئيسية — irab_judge
# ══════════════════════════════════════════════════════════════════════════════

def irab_judge(handoff: Layer6Handoff) -> IrabJudgmentResult:
    """
    يستقبل Layer6Handoff وينتج IrabJudgmentResult.

    المراحل:
      1. تشغيل الحراس (GUARD_L6_00 → GUARD_L6_06)
      2. بناء الأحكام الإعرابية حسب نوع الجملة
      3. إعادة الحكم الكامل أو BLOCKED
    """
    block_reasons: List[str] = []

    # ─── الحراس (يُوقف أول فشل) ────────────────────────────────────────────
    if not _guard_layer5_frozen(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    if not _guard_raw_sentence(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    if not _guard_musnad(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    if not _guard_musnad_ilayh(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    if not _guard_fi3liyya_faail(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    if not _guard_ismiyya_mubtada_khabar(handoff, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=handoff.sentence_type,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    # ─── بناء الأحكام حسب نوع الجملة ───────────────────────────────────────
    stype = handoff.sentence_type
    if stype == SentenceType.FI3LIYYA:
        entries = _build_fi3liyya_entries(handoff)
    elif stype == SentenceType.ISMIYYA:
        entries = _build_ismiyya_entries(handoff)
    elif stype == SentenceType.WASF:
        entries = _build_wasfiyya_entries(handoff)
    else:
        # نوع مجهول → نحاول الجملة الفعلية كافتراضي
        entries = _build_fi3liyya_entries(handoff)

    # ─── GUARD_L6_06: هل نتج حكم واحد على الأقل؟ ───────────────────────────
    if not _guard_irab_producible(entries, block_reasons):
        return IrabJudgmentResult(
            root=handoff.root,
            synset_id=handoff.synset_id,
            sentence=handoff.raw_sentence,
            sentence_type=stype,
            entries=[],
            verdict="BLOCKED",
            block_reasons=block_reasons,
        )

    return IrabJudgmentResult(
        root=handoff.root,
        synset_id=handoff.synset_id,
        sentence=handoff.raw_sentence,
        sentence_type=stype,
        entries=entries,
        verdict="IRAB_COMPLETE",
        block_reasons=[],
    )


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة — irab_judge_from_ifadah
# ══════════════════════════════════════════════════════════════════════════════

def irab_judge_from_ifadah(ifadah_result) -> Optional[IrabJudgmentResult]:
    """
    تحويل IfadahResult مباشرةً إلى IrabJudgmentResult.
    تُعيد None إذا لم يكن IfadahResult مجمَّداً.
    """
    if not hasattr(ifadah_result, "is_frozen") or not ifadah_result.is_frozen:
        return None
    if not hasattr(ifadah_result, "to_layer6_handoff"):
        return None
    handoff = ifadah_result.to_layer6_handoff()
    if handoff is None:
        return None
    return irab_judge(handoff)


# ── ثوابت التحقق ──────────────────────────────────────────────────────────────
assert callable(irab_judge)
assert callable(irab_judge_from_ifadah)
