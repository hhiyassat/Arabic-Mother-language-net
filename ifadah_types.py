"""
ifadah_types.py — أنواع LAYER 5: IfadahKernel
تعريفات البيانات المجمَّدة للطبقة الخامسة.

هذه الأنواع ثابتة ولا تتغيَّر بعد التجميد.
LAYER 6 يستقبل IfadahResult كمدخَل وحيد.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass   # wave11_ancestry في نفس المستوى — لا يحتاج import نوعي


# ══════════════════════════════════════════════════════════════════════════
# أنواع الجملة
# ══════════════════════════════════════════════════════════════════════════

class SentenceType:
    FI3LIYYA = "فعلية"    # فعل + فاعل (+ مفعول + قيود)
    ISMIYYA  = "اسمية"    # مبتدأ + خبر
    WASF     = "وصفية"    # اسم + صفة (نعت) — لا تُرفع إلى جملة كاملة بغير دليل


class IsnadType:
    HAQIQI  = "حقيقي"    # إسناد الفعل إلى صاحبه الحقيقي
    MAJAZI  = "مجازي"    # إسناد الفعل إلى غير صاحبه
    INSHAII = "إنشائي"   # أمر / نهي / استفهام


# ══════════════════════════════════════════════════════════════════════════
# الفتحة المُفعَّلة
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FilledSlot:
    """فتحة دلالية مُملوءة بقيمة ملموسة من السياق."""
    slot_name:   str
    sem_type:    str
    value:       str
    optional:    bool
    preposition: Optional[str] = None

    def surface(self) -> str:
        if self.preposition:
            return f"{self.preposition} {self.value}"
        return self.value


# ══════════════════════════════════════════════════════════════════════════
# Handoff إلى LAYER 6
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Layer6Handoff:
    """
    ما يُسلَّم إلى LAYER 6 (IrabJudgmentKernel) حصراً.

    LAYER 6 يستقبل هذا فقط — لا يُعيد فتح Wave11 ولا IfadahResult.
    """
    root:           str
    synset_id:      str
    sentence_type:  str          # SentenceType.*
    isnad_type:     str          # IsnadType.*
    musnad:         str          # المسند (فعل أو خبر)
    musnad_ilayh:   str          # المسند إليه (فاعل أو مبتدأ)
    qayd:           tuple        # القيود (مفعول، جار، حال...)
    raw_sentence:   str          # الجملة الكاملة للتحليل
    layer5_frozen:  str = "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF"


# ══════════════════════════════════════════════════════════════════════════
# مخرج LAYER 5 الكامل
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class IfadahResult:
    """
    مخرج LAYER 5 — الجملة المفيدة + handoff لـ LAYER 6.

    القواعد الصارمة:
      1. jumlah_fi3liyya لا يُملأ بدون musnad + musnad_ilayh.
      2. jumlah_ismiyya لا يُملأ بدون mubtada + khabar.
      3. jumlah_wasfiyya لا تُرفع إلى جملة كاملة بغير دليل.
      4. hokm_placeholder = OPEN → LAYER 6 دائماً (لا حكم هنا).
    """
    root:       str
    synset_id:  str

    # ── الجمل الثلاث ───────────────────────────────────────────────────
    jumlah_fi3liyya:  str = ""
    jumlah_ismiyya:   str = ""
    jumlah_wasfiyya:  str = ""

    # ── تفاصيل الإسناد ────────────────────────────────────────────────
    sentence_type:    str = SentenceType.FI3LIYYA
    isnad_type:       str = IsnadType.HAQIQI
    musnad:           str = ""
    musnad_ilayh:     str = ""
    qayd:             list = field(default_factory=list)
    filled_slots:     list = field(default_factory=list)

    # ── حكم الطبقة (ثابت لا يتغيَّر) ─────────────────────────────────
    hokm_placeholder: str = "OPEN → LAYER 6"

    # ── Wave11 مرجع (للقراءة فقط — لا يُعاد فتحه) ────────────────────
    wave11_ref: Optional[object] = field(default=None, repr=False)

    # ── حالة التجميد ──────────────────────────────────────────────────
    freeze_status: str = "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF"
    block_reasons: list = field(default_factory=list)

    def to_layer6_handoff(self) -> Layer6Handoff:
        """يُنتج حزمة الـ handoff الرسمية لـ LAYER 6."""
        return Layer6Handoff(
            root          = self.root,
            synset_id     = self.synset_id,
            sentence_type = self.sentence_type,
            isnad_type    = self.isnad_type,
            musnad        = self.musnad,
            musnad_ilayh  = self.musnad_ilayh,
            qayd          = tuple(self.qayd),
            raw_sentence  = self.jumlah_fi3liyya or self.jumlah_ismiyya,
        )

    @property
    def is_frozen(self) -> bool:
        return (
            self.freeze_status == "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF"
            and not self.block_reasons
        )
