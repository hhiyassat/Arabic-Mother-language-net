"""
word_class_engine.py — محرك تصنيف الكلمة العربية (ISM / FI3L / HARF)
ARABIC INTRINSIC WORD IDENTITY PROGRAM — المكون الأول

المبادئ:
  • الحروف قائمة ثابتة → CERTAIN
  • الأفعال: وجود ضمائر الفعل أو صيغة أمر → CERTAIN
  • الأسماء: ما تبقى بعد استبعاد الحروف والأفعال
  • الغموض يُحفظ ولا يُلغى
  • لا سياق إعرابي هنا (ذلك في Layer 6)
"""
from __future__ import annotations
from typing import Optional
import re

from word_tree.word_identity_types import (
    WordClass, WordClassConfidence, EvidenceRef, EvidenceSource
)
from word_tree.fi3l_engine import classify_fi3l_pattern


# ══════════════════════════════════════════════════════════════════════
# قائمة الحروف الثابتة (HARF_STATIC_LIST)
# ══════════════════════════════════════════════════════════════════════

# الحروف الأحادية الكتابة أو التي لا تقبل أي إسناد اسمي
_HUROOF_CERTAIN: set[str] = {
    # حروف الجر
    "في", "من", "إلى", "على", "عن", "مع", "ب", "ك", "ل", "لـ",
    "حتى", "منذ", "خلال", "عبر", "تجاه", "إزاء", "حيال",
    # حروف العطف
    "و", "أو", "أم", "بل", "لكن", "لكنه", "ثم", "فـ",
    # حروف النفي والاستفهام
    "لا", "لم", "لن", "ما", "لماذا",
    # حروف الشرط والجواب
    "إن", "إذا", "لو", "لولا", "لوما", "أما", "فإن",
    # حروف التوكيد والتنبيه
    "إن", "أن", "أنّ", "كأن", "ليت", "لعل",
    "ها", "أيها", "أيتها",
    # حروف الجواب
    "نعم", "بلى", "إي", "أجل", "لا",
    # حروف الاستثناء
    "إلا", "غير", "سوى",
    # حروف المصدرية
    "أن", "ما", "كي",
    # أخرى
    "قد", "سوف", "سـ",
}

# الحروف ذات الكتابة المشتركة مع الأسماء — يُعامَل غموضها بالتحفظ
_HUROOF_PROBABLE: set[str] = {
    "ما", "من", "أن", "إن", "لا", "غير", "سوى",
    # هذه قد تكون اسماً في سياقات معينة
}


# ══════════════════════════════════════════════════════════════════════
# أنماط الأفعال (FI3L)
# ══════════════════════════════════════════════════════════════════════

# مؤشرات الفعل المضارع: ي/ت/أ/ن + فعل
_FI3L_MUDAARI3_PREFIXES = re.compile(r'^[يتأن][؀-ۿ]{2,}$')

# صيغ الأمر الجازمة: خالية من المضارع، تبدأ بهمزة وصل + حرف ساكن
_FI3L_AMR_PATTERN = re.compile(
    r'^(اِ|ا)[^اويً-ْ][؀-ۿ]+$'
)

# مؤشرات الفعل الماضي البادية للعيان:
_FI3L_MADII_SUFFIXES = {
    "تُ", "تَ", "تِ", "نَا", "تُمْ", "تُنَّ", "تُمَا",
    "وا", "تَا", "نَ",
}

# أوزان الفعل المبني للمجهول في الماضي: فُعِلَ
_MAJHUL_MADII = re.compile(r'^[؀-ۿ][ُ][؀-ۿ][ِ][؀-ۿ]$')


# ══════════════════════════════════════════════════════════════════════
# التطبيع
# ══════════════════════════════════════════════════════════════════════

def _strip_diacritics(text: str) -> str:
    """أزل التشكيل (الحركات والسكون والشدة)"""
    diacritics = "ًٌٍَُِّْٕٓٔ"
    return "".join(c for c in text if c not in diacritics)


def _normalize(text: str) -> str:
    """
    تطبيع موحَّد: أزل التشكيل + وحِّد الهمزة + أزل التاء المربوطة الطرفية.
    لا تغيِّر بنية الكلمة.
    """
    text = _strip_diacritics(text)
    # توحيد الهمزات
    text = re.sub(r'[أإآ]', 'ا', text)
    text = text.replace('ة', 'ه')  # تاء مربوطة → هاء للمقارنة الداخلية
    return text.strip()


# ══════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════════════

def classify_word_class(
    surface: str,
    root_hint: Optional[str] = None,
) -> tuple[WordClass, WordClassConfidence, list[EvidenceRef]]:
    """
    صنِّف الكلمة إلى ISM / FI3L / HARF.

    المدخل:
        surface     — الكلمة كما وردت (مع تشكيل أو بدونه)
        root_hint   — الجذر المحسوم إن وُجد (يساعد في تمييز اسم الفاعل من الفعل)

    المخرج:
        (WordClass, WordClassConfidence, list[EvidenceRef])
    """
    evidence: list[EvidenceRef] = []
    stripped  = _strip_diacritics(surface).strip()
    normalized = _normalize(stripped)

    # ── 1. فحص قائمة الحروف الثابتة ─────────────────────────────────
    if stripped in _HUROOF_CERTAIN or normalized in _HUROOF_CERTAIN:
        # تحقق: هل في القائمة المشتركة (غموض محتمل)؟
        if stripped in _HUROOF_PROBABLE:
            evidence.append(EvidenceRef(
                source=EvidenceSource.HARF_STATIC_LIST,
                detail=f"'{stripped}' في قائمة الحروف المشتركة — غموض محتمل مع الاسم",
                value="HARF_PROBABLE",
                weight=0.7,
            ))
            return WordClass.HARF, WordClassConfidence.PROBABLE, evidence
        evidence.append(EvidenceRef(
            source=EvidenceSource.HARF_STATIC_LIST,
            detail=f"'{stripped}' في قائمة الحروف الثابتة",
            value="HARF_CERTAIN",
            weight=1.0,
        ))
        return WordClass.HARF, WordClassConfidence.CERTAIN, evidence

    # ── 2. فحص لواحق الفعل الماضي الصريحة ──────────────────────────
    for suffix in _FI3L_MADII_SUFFIXES:
        # نتحقق من السطح الأصلي (مع حركات) أو المجرَّد (بدون حركات)
        # §Gap1-FIX: بعض اللواحق مشكَّلة (تَ) والبحث يجب أن يشمل surface
        if (surface.endswith(suffix) or stripped.endswith(suffix)) and len(stripped) > len(suffix) + 1:
            evidence.append(EvidenceRef(
                source=EvidenceSource.PATTERN_MATCH,
                detail=f"ينتهي بـ '{suffix}' — لاحقة فعل ماضٍ",
                value="FI3L_MADII",
                weight=0.85,
            ))
            return WordClass.FI3L, WordClassConfidence.PROBABLE, evidence

    # ── 3. فحص الفعل المبني للمجهول (فُعِلَ) ───────────────────────
    if _MAJHUL_MADII.match(stripped):
        evidence.append(EvidenceRef(
            source=EvidenceSource.PATTERN_MATCH,
            detail="يطابق وزن فُعِلَ — فعل ماضٍ مبني للمجهول",
            value="FI3L_MAJHUL",
            weight=0.8,
        ))
        # لكن لاحظ: كلمات مثل "كُتِب" قد تكون فعلاً أو اسماً في سياق معين
        # نُعيد PROBABLE لا CERTAIN
        return WordClass.FI3L, WordClassConfidence.PROBABLE, evidence

    # ── 4. فحص صيغة الفعل المضارع ──────────────────────────────────
    if _FI3L_MUDAARI3_PREFIXES.match(stripped):
        # استثناء: "يد"، "يوم" — كلمات قصيرة تبدأ بـ ي وهي أسماء
        if len(stripped) <= 3 and not root_hint:
            evidence.append(EvidenceRef(
                source=EvidenceSource.PATTERN_MATCH,
                detail=f"'{stripped}' قصيرة جداً — كلمة مبدوءة بـي لكن محتملة الاسمية",
                value="AMBIGUOUS",
                weight=0.5,
            ))
        else:
            evidence.append(EvidenceRef(
                source=EvidenceSource.PATTERN_MATCH,
                detail=f"يبدأ بـ '{stripped[0]}' — سابقة الفعل المضارع",
                value="FI3L_MUDAARI3",
                weight=0.75,
            ))
            # ملاحظة: هذا الفحص ضعيف بدون سياق — كلمات مثل "يمين"، "يسار" أسماء
            # نُعيد PROBABLE
            return WordClass.FI3L, WordClassConfidence.PROBABLE, evidence

    # ── 5. فحص الأنماط الفعلية الجوهرية (fi3l_engine) ───────────────
    # قبل الحكم بالاستبعاد، نستشير محرك الفعل الصرفي.
    # CONTEXT_USED_FOR_INTRINSIC_FI3L = 0 — لا سياق هنا.
    # الغموض الجوهري (قام↔باب) يُعاد كـ UNKNOWN/AMBIGUOUS لا ISM_DEFAULT.
    fi3l_result = classify_fi3l_pattern(surface)
    if fi3l_result.is_fi3l_candidate:
        evidence.extend(fi3l_result.evidence)
        if fi3l_result.word_class_vote == "FI3L":
            # إشارة فعلية قوية (CCى أو نمط مشكَّل)
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"fi3l_engine: نمط '{fi3l_result.pattern_label}' → FI3L "
                    f"(score={fi3l_result.intrinsic_score:.2f}, "
                    f"fi3l_family={fi3l_result.fi3l_family.value})"
                ),
                value="FI3L_PATTERN_VOTE",
                weight=fi3l_result.intrinsic_score,
            ))
            return WordClass.FI3L, WordClassConfidence.PROBABLE, evidence
        elif fi3l_result.word_class_vote == "AMBIGUOUS":
            # غموض جوهري: النمط مشترك بين FI3L وISM
            # لا نقرر باستبعاد — نحفظ الغموض
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"fi3l_engine: نمط '{fi3l_result.pattern_label}' → غموض جوهري "
                    f"FI3L↔ISM (fi3l_family={fi3l_result.fi3l_family.value})"
                ),
                value="FI3L_ISM_AMBIGUOUS",
                weight=fi3l_result.intrinsic_score,
            ))
            return WordClass.UNKNOWN, WordClassConfidence.AMBIGUOUS, evidence

    # ── 6. ما تبقى = اسم بالاستبعاد ────────────────────────────────
    # وصلنا هنا فقط إذا لم يكتشف fi3l_engine أي نمط فعلي
    evidence.append(EvidenceRef(
        source=EvidenceSource.PATTERN_MATCH,
        detail="لا يطابق أي نمط حرف أو فعل أو صرف → اسم بالاستبعاد",
        value="ISM_DEFAULT",
        weight=0.7,
    ))
    return WordClass.ISM, WordClassConfidence.PROBABLE, evidence


# ══════════════════════════════════════════════════════════════════════
# تطبيع الكلمة (يُستخدم من خارج هذا الملف أيضاً)
# ══════════════════════════════════════════════════════════════════════

def normalize_surface(surface: str) -> str:
    """أرجع الشكل المطبَّع — بدون تشكيل وبهمزة موحَّدة"""
    return _normalize(_strip_diacritics(surface))


def strip_diacritics(text: str) -> str:
    """أزل التشكيل فقط"""
    return _strip_diacritics(text)
