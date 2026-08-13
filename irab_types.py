"""
irab_types.py
━━━━━━━━━━━━━
LAYER 6 — IrabJudgmentKernel: أنواع البيانات

النطاق الوحيد: حكم إعرابي / تركيبي نحوي.
لا حكم فقهي. لا فتوى. لا تفسير.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# ── الثابت الجامد لـ LAYER 5 (يجب أن يطابق layer5_frozen في Layer6Handoff) ──
LAYER5_FROZEN_TOKEN = "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF"

# ── الحكم الختامي لـ LAYER 6 ─────────────────────────────────────────────────
LAYER6_VERDICT_TOKEN = "IRAB_JUDGMENT_KERNEL_LAYER6_BUILT_READY_FOR_HOKOM_HANDOFF"

# ── الثابت الجامد لـ LAYER 6 حين يُسلَّم إلى LAYER 7 (يطابق layer6_frozen) ──
#   LAYER 7 (HokomKernel) يستقبل Layer7Handoff ويتحقق من هذا الختم في GUARD_L7_00.
LAYER6_FROZEN_TOKEN = LAYER6_VERDICT_TOKEN


# ══════════════════════════════════════════════════════════════════════════════
# الأدوار الإعرابية
# ══════════════════════════════════════════════════════════════════════════════

class IrabRole:
    """أدوار إعرابية ثابتة — لا يُضاف إليها بدون مراجعة."""
    FI3L          = "فعل"
    FAAIL         = "فاعل"
    MAF3OOL       = "مفعول به"
    MUBTADA       = "مبتدأ"
    KHABAR        = "خبر"
    QAYD_JAR      = "جار ومجرور"
    QAYD_ZARF     = "ظرف"
    QAYD_HAL      = "حال"
    QAYD_MUTTASIL = "قيد متصل"
    UNKNOWN       = "غير محدد"


# ══════════════════════════════════════════════════════════════════════════════
# حالات الإعراب
# ══════════════════════════════════════════════════════════════════════════════

class IrabCase:
    """حالات الإعراب الثلاث + المبني."""
    MARFOO3  = "مرفوع"
    MANSOOB  = "منصوب"
    MAJROOR  = "مجرور"
    MABNI    = "مبني"
    UNKNOWN  = "غير محدد"


# ══════════════════════════════════════════════════════════════════════════════
# علامات الإعراب
# ══════════════════════════════════════════════════════════════════════════════

class IrabSign:
    """علامات الإعراب المعيارية."""
    DAMMA   = "الضمة"
    FATHA   = "الفتحة"
    KASRA   = "الكسرة"
    SUKOON  = "السكون"
    MABNI_FATH = "مبني على الفتح"
    MABNI_SUKOON = "مبني على السكون"
    MABNI_KASRA = "مبني على الكسر"
    NUN_DEL = "حذف النون"
    UNKNOWN = "غير محدد"


# ══════════════════════════════════════════════════════════════════════════════
# مدخل إعرابي واحد (لكلمة أو عنصر واحد)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IrabEntry:
    """حكم إعرابي لعنصر واحد في الجملة."""

    word: str
    """الكلمة أو العنصر (قد يكون متعدد الكلمات مثل جار ومجرور)."""

    position: int
    """الموقع في الجملة — 0 للفعل أو المبتدأ، 1 للفاعل أو الخبر، إلخ."""

    irab_role: str
    """الدور الإعرابي: IrabRole.FAAIL / MAF3OOL / MUBTADA / KHABAR / ..."""

    irab_case: str
    """حالة الإعراب: IrabCase.MARFOO3 / MANSOOB / MAJROOR / MABNI."""

    irab_sign: str
    """علامة الإعراب: IrabSign.DAMMA / FATHA / KASRA / ..."""

    irab_reason: str
    """السبب النحوي — جملة واحدة مختصرة."""

    muttasil: str = ""
    """المتعلَّق به إن وُجد (مثل الفعل الذي يتعلق به الجار والمجرور)، وإلا فارغ."""

    def to_dict(self) -> dict:
        return {
            "word":        self.word,
            "position":    self.position,
            "irab_role":   self.irab_role,
            "irab_case":   self.irab_case,
            "irab_sign":   self.irab_sign,
            "irab_reason": self.irab_reason,
            "muttasil":    self.muttasil,
        }


# ══════════════════════════════════════════════════════════════════════════════
# نتيجة الحكم الإعرابي الكاملة (مخرج LAYER 6)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IrabJudgmentResult:
    """مخرج LAYER 6 — الأحكام الإعرابية لجملة كاملة."""

    root: str
    """الجذر (مثل: كتب)."""

    synset_id: str
    """معرف المجموعة الدلالية (مثل: library.n.01)."""

    sentence: str
    """الجملة الكاملة كما وردت."""

    sentence_type: str
    """نوع الجملة: فعلية / اسمية / وصفية."""

    entries: List[IrabEntry] = field(default_factory=list)
    """الأحكام الإعرابية — حكم لكل عنصر."""

    verdict: str = "PENDING"
    """IRAB_COMPLETE إذا اكتمل الإعراب، أو BLOCKED إذا فشل الحارس."""

    block_reasons: List[str] = field(default_factory=list)
    """أسباب الحجب إن وُجدت."""

    layer6_frozen: str = LAYER6_VERDICT_TOKEN
    """ختم LAYER 6 — لا يُعدَّل."""

    @property
    def is_complete(self) -> bool:
        return self.verdict == "IRAB_COMPLETE" and bool(self.entries)

    @property
    def is_blocked(self) -> bool:
        return self.verdict == "BLOCKED"

    def to_dict(self) -> dict:
        return {
            "root":           self.root,
            "synset_id":      self.synset_id,
            "sentence":       self.sentence,
            "sentence_type":  self.sentence_type,
            "entries":        [e.to_dict() for e in self.entries],
            "verdict":        self.verdict,
            "block_reasons":  self.block_reasons,
            "layer6_frozen":  self.layer6_frozen,
        }

    def to_layer7_handoff(self) -> "Layer7Handoff":
        """يُنتج حزمة الـ handoff الرسمية لـ LAYER 7 (HokomKernel).

        LAYER 7 يستقبل هذا فقط — لا يُعيد فتح Wave11 ولا IfadahResult ولا IrabJudgmentResult.
        """
        return Layer7Handoff(
            root          = self.root,
            synset_id     = self.synset_id,
            sentence      = self.sentence,
            sentence_type = self.sentence_type,
            entries       = tuple(self.entries),
            irab_verdict  = self.verdict,
            layer6_frozen = self.layer6_frozen,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Handoff إلى LAYER 7 (HokomKernel)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Layer7Handoff:
    """
    ما يُسلَّم إلى LAYER 7 (HokomKernel) حصراً.

    LAYER 7 يحكم على سلامة الجملة تركيبياً (حكم لغوي) — لا حكم فقهي ولا فتوى.
    يستقبل هذا فقط، ولا يُعيد فتح أي طبقة سابقة.
    """
    root:           str
    synset_id:      str
    sentence:       str               # الجملة الكاملة كما وردت
    sentence_type:  str               # SentenceType.*
    entries:        tuple             # tuple[IrabEntry] — أحكام LAYER 6 الإعرابية
    irab_verdict:   str               # حكم LAYER 6: "IRAB_COMPLETE" / "BLOCKED"
    layer6_frozen:  str = LAYER6_VERDICT_TOKEN


# ══════════════════════════════════════════════════════════════════════════════
# ثوابت الحراس (للمطابقة النصية في الاختبارات)
# ══════════════════════════════════════════════════════════════════════════════

GUARD_L6_LABELS = {
    "GUARD_L6_00": "layer5_frozen ≠ LAYER5_FROZEN_TOKEN",
    "GUARD_L6_01": "raw_sentence فارغة",
    "GUARD_L6_02": "musnad فارغ",
    "GUARD_L6_03": "musnad_ilayh فارغ",
    "GUARD_L6_04": "جملة فعلية بلا فاعل",
    "GUARD_L6_05": "جملة اسمية بلا مبتدأ أو خبر",
    "GUARD_L6_06": "لا حكم إعرابي ممكن الاستنتاج",
}

# ── ثوابت التحقق ──────────────────────────────────────────────────────────────
assert isinstance(LAYER5_FROZEN_TOKEN, str) and LAYER5_FROZEN_TOKEN
assert isinstance(LAYER6_VERDICT_TOKEN, str) and LAYER6_VERDICT_TOKEN
assert len(GUARD_L6_LABELS) == 7
