"""
slots_engine.py — محرك الفتحات
يُحلِّل البنية المسندية للجذر ويوفِّر أدوات الاستعلام والتحقق الدلالي
المبدأ الثالث: التوافق = فحص النوع (Type Check على الفتحات الدلالية)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.types import SemanticType, PrimaryPredicate


# ══════════════════════════════════════════════════════════════════════
# هياكل البيانات
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Slot:
    """فتحة دلالية واحدة في البنية المسندية"""
    name:        str                    # اسم الحالة (فاعل، مفعول، في، بـ ...)
    sem_type:    SemanticType           # النوع الدلالي من الأنواع الخمسة عشر
    example:     str                    # مثال تطبيقي
    optional:    bool                   # اختياري / إلزامي
    preposition: Optional[str] = None   # حرف الجر إن وُجد

    def is_oblique(self) -> bool:
        """هل الفتحة شبه جملة (مُقيَّدة بحرف جر)؟"""
        return self.preposition is not None

    def __repr__(self) -> str:
        tag = "?" if self.optional else "!"
        prep = f"[{self.preposition}]" if self.preposition else ""
        return f"Slot({self.name}{prep}:{self.sem_type.value}{tag})"


@dataclass
class PredicateStructure:
    """البنية المسندية الكاملة للجذر"""
    root:               str
    primary_predicate:  PrimaryPredicate
    slots:              list[Slot] = field(default_factory=list)
    raw_text:           str = ""

    # ── استعلامات الفتحات ─────────────────────────────────────────────

    def get_slot(self, name: str) -> Optional[Slot]:
        """ابحث عن فتحة باسمها"""
        for s in self.slots:
            if s.name == name:
                return s
        return None

    def get_by_type(self, sem_type: SemanticType) -> list[Slot]:
        """أرجع جميع الفتحات ذات النوع الدلالي المُحدَّد"""
        return [s for s in self.slots if s.sem_type == sem_type]

    def mandatory(self) -> list[Slot]:
        """الفتحات الإلزامية"""
        return [s for s in self.slots if not s.optional]

    def optional_slots(self) -> list[Slot]:
        """الفتحات الاختيارية"""
        return [s for s in self.slots if s.optional]

    def signature(self) -> tuple[SemanticType, ...]:
        """
        توقيع الفتحات الإلزامية — يُستخدم في فحص التوافق (المبدأ الثالث).
        الترتيب: الفتحات الإلزامية أولاً، مُرتَّبة بترتيبها في القائمة.
        """
        return tuple(s.sem_type for s in self.mandatory())

    def accepts_type(self, position: int, sem_type: SemanticType) -> bool:
        """
        هل الفتحة في الموضع (position) تقبل النوع الدلالي (sem_type)؟
        يُستخدم لفحص التوافق التركيبي.
        """
        mand = self.mandatory()
        if position < 0 or position >= len(mand):
            return False
        return mand[position].sem_type == sem_type

    def shares_argument_type(self, other: "PredicateStructure") -> bool:
        """
        هل يتشارك هذا الجذر والجذر الآخر نوعاً دلالياً واحداً على الأقل
        في فتحاتهما الإلزامية؟
        """
        my_types    = {s.sem_type for s in self.mandatory()}
        other_types = {s.sem_type for s in other.mandatory()}
        return bool(my_types & other_types)

    def can_chain_to(self, other: "PredicateStructure") -> bool:
        """
        هل يمكن ربط هذا الجذر بالجذر الآخر بحيث يصبح
        خرج أحدهما (مُتأثِّر / موضوع) دخلاً للآخر (مُنجِز / مُجرِّب)؟
        """
        my_outputs   = {SemanticType.MUTAATHIR, SemanticType.MAWDUU}
        other_inputs = {SemanticType.MUNJIZ, SemanticType.MUJARRIB, SemanticType.MUDRIK}
        my_out_types   = {s.sem_type for s in self.mandatory()} & my_outputs
        other_in_types = {s.sem_type for s in other.mandatory()} & other_inputs
        return bool(my_out_types) and bool(other_in_types)

    def summary(self) -> str:
        """ملخص نصي للبنية المسندية"""
        parts = [f"[{self.primary_predicate.value}]"]
        for s in self.slots:
            tag = "?" if s.optional else ""
            prep = f"/{s.preposition}" if s.preposition else ""
            parts.append(f"{s.name}{prep}:{s.sem_type.value}{tag}")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"PredicateStructure({self.root!r}, {self.summary()})"


# ══════════════════════════════════════════════════════════════════════
# التحليل: من البيانات المخزَّنة إلى PredicateStructure
# ══════════════════════════════════════════════════════════════════════

# خريطة تطبيع أسماء الأنواع الدلالية (تقبل الكتابة بلا تشكيل أيضاً)
_SEM_TYPE_MAP: dict[str, SemanticType] = {st.value: st for st in SemanticType}
_SEM_TYPE_MAP.update({
    "منجز":    SemanticType.MUNJIZ,
    "متأثر":   SemanticType.MUTAATHIR,
    "مدرك":    SemanticType.MUDRIK,
    "مجرب":    SemanticType.MUJARRIB,
    "محتوى":   SemanticType.MUHTAWA,
    "موضوع":   SemanticType.MAWDUU,
    "مصدر":    SemanticType.MASDAR,
    "غاية":    SemanticType.GHAYA,
    "مكان":    SemanticType.MAKAN,
    "زمان":    SemanticType.ZAMAN,
    "أداة":    SemanticType.ADAA,
    "مستفيد":  SemanticType.MUSTAFID,
    "مقدار":   SemanticType.MIQDAAR,
    "هيئة":    SemanticType.HAYAA,
    "سبب":     SemanticType.SABAB,
    # without shadda / diacritics variants
    "مُنجِز":  SemanticType.MUNJIZ,
    "مُتأثِّر":SemanticType.MUTAATHIR,
    "مُدرِك":  SemanticType.MUDRIK,
    "مُجرِّب": SemanticType.MUJARRIB,
    "مُدرك":   SemanticType.MUDRIK,
    "مُجرب":   SemanticType.MUJARRIB,
    "مُستفيد": SemanticType.MUSTAFID,
})

_PRED_MAP: dict[str, PrimaryPredicate] = {pp.value: pp for pp in PrimaryPredicate}


def _resolve_sem_type(raw: str) -> SemanticType:
    """حوِّل سلسلة نصية إلى SemanticType (مع دعم الأشكال غير المُشكَّلة)"""
    raw = raw.strip()
    if raw in _SEM_TYPE_MAP:
        return _SEM_TYPE_MAP[raw]
    # بحث تقريبي: استخدم أول مُطابَقة جزئية
    for key, val in _SEM_TYPE_MAP.items():
        if raw in key or key in raw:
            return val
    raise ValueError(f"نوع دلالي غير معروف: {raw!r}")


def _resolve_predicate(raw: str) -> PrimaryPredicate:
    """حوِّل سلسلة نصية إلى PrimaryPredicate"""
    raw = raw.strip()
    if raw in _PRED_MAP:
        return _PRED_MAP[raw]
    for key, val in _PRED_MAP.items():
        if raw == key or raw in key:
            return val
    raise ValueError(f"مسند أولي غير معروف: {raw!r}")


def parse_predicate(root: str, predicate_data: dict) -> PredicateStructure:
    """
    حوِّل قاموس البيانات (من pilot_roots.json) إلى PredicateStructure.

    predicate_data يجب أن يحتوي على:
        primary_predicate : str
        slots             : list[dict]  (name, type, example, optional, preposition?)
        raw_text          : str         (اختياري)
    """
    primary = _resolve_predicate(predicate_data["primary_predicate"])
    raw     = predicate_data.get("raw_text", "")

    slots: list[Slot] = []
    for sd in predicate_data.get("slots", []):
        sem_type = _resolve_sem_type(sd["type"])
        slots.append(Slot(
            name        = sd["name"],
            sem_type    = sem_type,
            example     = sd.get("example", ""),
            optional    = sd.get("optional", False),
            preposition = sd.get("preposition"),
        ))

    return PredicateStructure(
        root              = root,
        primary_predicate = primary,
        slots             = slots,
        raw_text          = raw,
    )


def parse_predicate_from_dict(root_data: dict) -> PredicateStructure:
    """واجهة مُيسَّرة — تستقبل قاموس الجذر الكامل من pilot_roots.json"""
    return parse_predicate(
        root           = root_data["letters"],
        predicate_data = root_data["predicate"],
    )


# ══════════════════════════════════════════════════════════════════════
# أدوات مقارنة متعددة الجذور
# ══════════════════════════════════════════════════════════════════════

def find_compatible_pairs(
    structures: list[PredicateStructure],
) -> list[tuple[PredicateStructure, PredicateStructure]]:
    """
    ابحث في قائمة البنى المسندية عن الأزواج المتوافقة:
    جذر A يمكن ربطه تركيبياً بجذر B (خرج A = دخل B).
    """
    pairs = []
    for i, a in enumerate(structures):
        for b in structures[i + 1:]:
            if a.can_chain_to(b):
                pairs.append((a, b))
            elif b.can_chain_to(a):
                pairs.append((b, a))
    return pairs


def group_by_predicate(
    structures: list[PredicateStructure],
) -> dict[PrimaryPredicate, list[PredicateStructure]]:
    """صنِّف البنى المسندية بحسب المسند الأولي"""
    groups: dict[PrimaryPredicate, list[PredicateStructure]] = {}
    for s in structures:
        groups.setdefault(s.primary_predicate, []).append(s)
    return groups


def group_by_signature(
    structures: list[PredicateStructure],
) -> dict[tuple, list[PredicateStructure]]:
    """صنِّف البنى المسندية بحسب توقيع الفتحات الإلزامية"""
    groups: dict[tuple, list[PredicateStructure]] = {}
    for s in structures:
        sig = s.signature()
        groups.setdefault(sig, []).append(s)
    return groups
