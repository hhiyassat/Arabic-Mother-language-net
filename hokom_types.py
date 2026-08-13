"""
hokom_types.py
━━━━━━━━━━━━━━
LAYER 7 — HokomKernel: أنواع البيانات

النطاق الوحيد: حكم لغوي على سلامة الجملة تركيبياً (حكم لغوي / نحوي نهائي).
لا حكم فقهي. لا فتوى. لا تفسير. لا إغلاق GRES-HUKM الفقهي.

المدخل:  Layer7Handoff (من LAYER 6 المجمَّد)
المخرج:  HokomResult — حكم سلامة الجملة + قائمة الاختلالات إن وُجدت.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from irab_types import LAYER6_FROZEN_TOKEN

# ── الثابت الجامد لـ LAYER 6 (يجب أن يطابق layer6_frozen في Layer7Handoff) ──
#   يُعاد تصديره هنا لراحة الاستيراد في الكيرنل والاختبارات.
LAYER6_FROZEN_TOKEN = LAYER6_FROZEN_TOKEN  # noqa: PLW0127 (re-export مقصود)

# ── الحكم الختامي لـ LAYER 7 ─────────────────────────────────────────────────
LAYER7_VERDICT_TOKEN = "HOKM_KERNEL_LAYER7_BUILT_READY_FOR_LAYER8_HANDOFF"


# ══════════════════════════════════════════════════════════════════════════════
# الأحكام الختامية الممكنة
# ══════════════════════════════════════════════════════════════════════════════

class HokomVerdict:
    """أحكام سلامة الجملة — لا يُضاف إليها بدون مراجعة."""
    SALEEM   = "HOKM_SALEEM"     # الجملة سليمة تركيبياً
    MUKHTALL = "HOKM_MUKHTALL"   # الجملة مختلَّة تركيبياً (اختلال واحد فأكثر)
    BLOCKED  = "BLOCKED"         # تعذَّر الحكم (فشل حارس)


# ══════════════════════════════════════════════════════════════════════════════
# نتيجة فحص سلامة واحد
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SoundnessCheck:
    """نتيجة فحص سلامة واحد (قاعدة واحدة من قواعد LAYER 7)."""

    name:   str
    """اسم الفحص: ISNAD / AGREEMENT / MUTTASIL."""

    passed: bool
    """هل نجح الفحص؟"""

    detail: str
    """تفصيل نصي — سبب النجاح أو وصف الاختلال."""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


# ══════════════════════════════════════════════════════════════════════════════
# نتيجة الحكم اللغوي الكاملة (مخرج LAYER 7)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HokomResult:
    """مخرج LAYER 7 — حكم سلامة الجملة."""

    root: str
    """الجذر (مثل: كتب)."""

    synset_id: str
    """معرف المجموعة الدلالية (مثل: library.n.01)."""

    sentence: str
    """الجملة الكاملة كما وردت."""

    sentence_type: str
    """نوع الجملة: فعلية / اسمية / وصفية."""

    verdict: str = HokomVerdict.BLOCKED
    """HOKM_SALEEM / HOKM_MUKHTALL / BLOCKED."""

    checks: List[SoundnessCheck] = field(default_factory=list)
    """نتائج فحوص السلامة الثلاثة (isnad / agreement / muttasil)."""

    defects: List[str] = field(default_factory=list)
    """قائمة الاختلالات — تكون فارغة إذا كان الحكم SALEEM."""

    block_reasons: List[str] = field(default_factory=list)
    """أسباب الحجب إن وُجدت (فشل حارس)."""

    layer7_frozen: str = LAYER7_VERDICT_TOKEN
    """ختم LAYER 7 — لا يُعدَّل."""

    @property
    def is_saleem(self) -> bool:
        return self.verdict == HokomVerdict.SALEEM and not self.defects

    @property
    def is_mukhtall(self) -> bool:
        return self.verdict == HokomVerdict.MUKHTALL

    @property
    def is_blocked(self) -> bool:
        return self.verdict == HokomVerdict.BLOCKED

    def to_dict(self) -> dict:
        return {
            "root":          self.root,
            "synset_id":     self.synset_id,
            "sentence":      self.sentence,
            "sentence_type": self.sentence_type,
            "verdict":       self.verdict,
            "checks":        [c.to_dict() for c in self.checks],
            "defects":       self.defects,
            "block_reasons": self.block_reasons,
            "layer7_frozen": self.layer7_frozen,
        }


# ══════════════════════════════════════════════════════════════════════════════
# ثوابت الحراس (للمطابقة النصية في الاختبارات)
# ══════════════════════════════════════════════════════════════════════════════

GUARD_L7_LABELS = {
    "GUARD_L7_00": "layer6_frozen ≠ LAYER6_FROZEN_TOKEN",
    "GUARD_L7_01": "sentence فارغة",
    "GUARD_L7_02": "لا مدخلات إعرابية (entries فارغة)",
    "GUARD_L7_03": "نوع الجملة غير مدعوم",
}

# ── ثوابت التحقق ──────────────────────────────────────────────────────────────
assert isinstance(LAYER6_FROZEN_TOKEN, str) and LAYER6_FROZEN_TOKEN
assert isinstance(LAYER7_VERDICT_TOKEN, str) and LAYER7_VERDICT_TOKEN
assert len(GUARD_L7_LABELS) == 4
