"""
numeral_engine.py — محرك الهوية العددية
ARABIC INTRINSIC WORD IDENTITY PROGRAM — المكون الثاني

المبادئ:
  • القائمة الثابتة هي الدليل الأول والأقوى
  • الأعداد المركبة (أحد عشر...) تُحسم في مستوى التعبير لا الكلمة المفردة
  • NUMERAL_IDENTITY_PRODUCER = هذا الملف فقط
  • يشمل: المذكر والمؤنث لكل عدد
"""
from __future__ import annotations
from typing import Optional

from word_tree.word_identity_types import (
    NumeralType, NumeralIdentity, EvidenceRef, EvidenceSource
)


# ══════════════════════════════════════════════════════════════════════
# جداول الأعداد الثابتة
# ══════════════════════════════════════════════════════════════════════

# الأعداد الأصلية 1–9 (مفرد، مذكر ومؤنث)
_CARDINAL_BASIC: dict[str, tuple[Optional[int], Optional[str]]] = {
    # مذكر              # القيمة  # الجنس
    "واحد":     (1, "مذكر"),
    "واحدة":    (1, "مؤنث"),
    # أحد: الصورة المذكرة المستخدمة في المركَّبات (أحد عشر) وبعض السياقات المفردة
    "أحد":      (1, "مذكر"),
    "إحدى":     (1, "مؤنث"),
    "اثنان":    (2, "مذكر"),
    "اثنين":    (2, "مذكر"),
    "اثنتان":   (2, "مؤنث"),
    "اثنتين":   (2, "مؤنث"),
    "ثلاثة":    (3, "مؤنث"),    # العدد يخالف المعدود: ثلاثة كتب (مفرد مذكر)
    "ثلاث":     (3, "مذكر"),
    "اربعة":    (4, "مؤنث"),
    "اربع":     (4, "مذكر"),
    "أربعة":    (4, "مؤنث"),
    "أربع":     (4, "مذكر"),
    "خمسة":     (5, "مؤنث"),
    "خمس":      (5, "مذكر"),
    "ستة":      (6, "مؤنث"),
    "ست":       (6, "مذكر"),
    "سبعة":     (7, "مؤنث"),
    "سبع":      (7, "مذكر"),
    "ثمانية":   (8, "مؤنث"),
    "ثمان":     (8, "مذكر"),
    "ثمانٍ":    (8, "مذكر"),
    "تسعة":     (9, "مؤنث"),
    "تسع":      (9, "مذكر"),
}

# الأعداد 10 و العشرات
_CARDINAL_UNIT: dict[str, tuple[Optional[int], Optional[str]]] = {
    "عشرة":    (10, "مؤنث"),
    "عشر":     (10, "مذكر"),
    "عشرون":   (20, None),
    "عشرين":   (20, None),
    "ثلاثون":  (30, None),
    "ثلاثين":  (30, None),
    "أربعون":  (40, None),
    "أربعين":  (40, None),
    "خمسون":   (50, None),
    "خمسين":   (50, None),
    "ستون":    (60, None),
    "ستين":    (60, None),
    "سبعون":   (70, None),
    "سبعين":   (70, None),
    "ثمانون":  (80, None),
    "ثمانين":  (80, None),
    "تسعون":   (90, None),
    "تسعين":   (90, None),
}

# المئات
_CARDINAL_HUNDRED: dict[str, tuple[Optional[int], Optional[str]]] = {
    "مئة":      (100, None),
    "مائة":     (100, None),
    "مئتان":    (200, None),
    "مئتين":    (200, None),
    "مائتان":   (200, None),
    "مائتين":   (200, None),
    "ثلاثمئة":  (300, None),
    "ثلاثمائة": (300, None),
    "أربعمئة":  (400, None),
    "أربعمائة": (400, None),
    "خمسمئة":   (500, None),
    "خمسمائة":  (500, None),
    "ستمئة":    (600, None),
    "ستمائة":   (600, None),
    "سبعمئة":   (700, None),
    "سبعمائة":  (700, None),
    "ثمانمئة":  (800, None),
    "ثمانمائة": (800, None),
    "تسعمئة":   (900, None),
    "تسعمائة":  (900, None),
}

# الآلاف والملايين
_CARDINAL_THOUSAND: dict[str, tuple[Optional[int], Optional[str]]] = {
    "ألف":     (1000, None),
    "ألفان":   (2000, None),
    "ألفين":   (2000, None),
    "آلاف":    (None, None),   # جمع
    "ألوف":    (None, None),   # جمع
}

_CARDINAL_MILLION: dict[str, tuple[Optional[int], Optional[str]]] = {
    "مليون":   (1_000_000, None),
    "مليونان": (2_000_000, None),
    "ملايين":  (None, None),
    "مليار":   (1_000_000_000, None),
    "مليارين": (2_000_000_000, None),
    "مليارات": (None, None),
    "تريليون": (1_000_000_000_000, None),
}

# الأعداد الترتيبية (مفرد مذكر فقط — المؤنث بإضافة تاء)
_ORDINAL: dict[str, int] = {
    "أول":    1, "أولى":  1,
    "ثانٍ":   2, "ثانية": 2, "ثان": 2,
    "ثالث":   3, "ثالثة": 3,
    "رابع":   4, "رابعة": 4,
    "خامس":   5, "خامسة": 5,
    "سادس":   6, "سادسة": 6,
    "سابع":   7, "سابعة": 7,
    "ثامن":   8, "ثامنة": 8,
    "تاسع":   9, "تاسعة": 9,
    "عاشر":  10, "عاشرة":10,
    "حادي عشر": 11,
    "ثاني عشر": 12,
    "عشرون":  None,  # يُستخدم عدداً وترتيبياً
}

# الكسور
_FRACTION: dict[str, tuple[Optional[int], int]] = {
    "نصف":      (1, 2),
    "ثلث":      (1, 3),
    "ربع":      (1, 4),
    "خمس":      (1, 5),   # تعارض مع العدد 5 مذكر → غموض، لكن الكسر أغلب في سياق الكسر
    "سدس":      (1, 6),
    "سبع":      (1, 7),   # تعارض أيضاً
    "ثمن":      (1, 8),
    "تسع":      (1, 9),   # تعارض
    "عشر":      (1, 10),  # تعارض
}


# ══════════════════════════════════════════════════════════════════════
# دمج الجداول للبحث السريع
# ══════════════════════════════════════════════════════════════════════

_ALL_NUMERALS: dict[str, tuple[NumeralType, Optional[int], Optional[str]]] = {}

for word, (val, gender) in _CARDINAL_BASIC.items():
    _ALL_NUMERALS[word] = (NumeralType.CARDINAL_BASIC, val, gender)

for word, (val, gender) in _CARDINAL_UNIT.items():
    _ALL_NUMERALS[word] = (NumeralType.CARDINAL_UNIT, val, gender)

for word, (val, gender) in _CARDINAL_HUNDRED.items():
    _ALL_NUMERALS[word] = (NumeralType.CARDINAL_HUNDRED, val, gender)

for word, (val, gender) in _CARDINAL_THOUSAND.items():
    _ALL_NUMERALS[word] = (NumeralType.CARDINAL_THOUSAND, val, gender)

for word, (val, gender) in _CARDINAL_MILLION.items():
    _ALL_NUMERALS[word] = (NumeralType.CARDINAL_MILLION, val, gender)

for word, val in _ORDINAL.items():
    if word not in _ALL_NUMERALS:   # لا نكتب فوق العدد الأصلي
        _ALL_NUMERALS[word] = (NumeralType.ORDINAL, val, None)

for word, (num, den) in _FRACTION.items():
    # الكسور لها تعارض مع العدد — لا نكتب فوق
    if word not in _ALL_NUMERALS:
        _ALL_NUMERALS[word] = (NumeralType.FRACTION, None, None)


# ══════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════════════

def classify_numeral(surface: str) -> NumeralIdentity:
    """
    افحص إذا كانت الكلمة عدداً وأعطِ هويتها.

    المدخل:
        surface — الكلمة (مشكَّلة أو غير مشكَّلة)

    المخرج:
        NumeralIdentity — is_numeral=False إذا لم تكن عدداً
    """
    from word_tree.word_class_engine import strip_diacritics
    stripped = strip_diacritics(surface).strip()

    # توحيد الهمزة للمقارنة
    import re
    normalized = re.sub(r'[أإآ]', 'ا', stripped)

    # ابحث في الجدول
    entry = _ALL_NUMERALS.get(stripped) or _ALL_NUMERALS.get(normalized)

    if entry is None:
        return NumeralIdentity(
            is_numeral=False,
            numeral_type=NumeralType.NONE,
            numeric_value=None,
            gender_form=None,
            evidence=[],
        )

    numeral_type, numeric_value, gender = entry
    evidence = [EvidenceRef(
        source=EvidenceSource.NUMERAL_STATIC_LIST,
        detail=f"'{stripped}' موجودة في قائمة الأعداد الثابتة → {numeral_type.value}",
        value=str(numeric_value) if numeric_value is not None else "متغير",
        weight=1.0,
    )]

    return NumeralIdentity(
        is_numeral=True,
        numeral_type=numeral_type,
        numeric_value=numeric_value,
        gender_form=gender,
        evidence=evidence,
    )


def is_numeral(surface: str) -> bool:
    """اختبار سريع: هل الكلمة عدد؟"""
    return classify_numeral(surface).is_numeral
