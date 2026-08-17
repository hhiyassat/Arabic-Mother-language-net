"""
fi3l_engine.py — محرك أنماط الفعل العربي الجوهري
ARABIC INTRINSIC WORD IDENTITY PROGRAM — مكون الفعل الجوهري

المبادئ:
  • الاستدلال الصرفي الخالص فقط — لا سياق إعرابي
  • CONTEXT_USED_FOR_INTRINSIC_FI3L = 0
  • الغموض الجوهري محفوظ: MISSING_INTRINSIC_VERB_PATTERN ≠ NEEDS_CONTEXT
  • كل نمط يُصنَّف: FI3L | ISM | AMBIGUOUS — لا ISM_DEFAULT لما هو صرفياً مشترك

أصناف الأفعال المعالَجة:
  STRONG    — سالم (كَتَبَ، قَتَلَ): نمط CaCaCa
  HOLLOW    — أجوف (قَامَ، بَاعَ، قَالَ، صَامَ): وسطه ا في الماضي (CāC)
  DEFECTIVE — ناقص (دَعَا، رَمَى، سَعَى): آخره ا أو ى (CCā / CCى)
  HAMZATED  — مهموز (جَاءَ، شَاءَ): أجوف + لام همزة (CāCء)
  DOUBLED   — مضعَّف (مَدَّ، رَدَّ): شدة على الحرف الأخير

مصدر الدليل: MORPHOLOGICAL_ENGINE (لا مقاييس، لا سياق)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re

from word_tree.word_identity_types import (
    Fi3lFamily, EvidenceRef, EvidenceSource,
    RadicalHealth, HamzaFeature, GeminationFeature, VerbFeatureVector,
)


# ══════════════════════════════════════════════════════════════════════
# تعريف أصناف الحروف
# ══════════════════════════════════════════════════════════════════════

# حروف صحيحة مؤكدة (لا تلتبس بحروف المد)
_STRONG_CONS = frozenset("بتثجحخدذرزسشصضطظعغفقكلمنه")

# حروف علة
_WEAK_LETTERS = frozenset("اوي")

# حروف الهمزة
_HAMZA_LETTERS = frozenset("ءأإئؤ")

# جميع الحروف الصحيحة المحتملة (بما فيها الهمزة)
_NON_VOWEL_CONS = _STRONG_CONS | _HAMZA_LETTERS

# جميع الحروف العربية
_ALL_ARABIC = _STRONG_CONS | _WEAK_LETTERS | _HAMZA_LETTERS | frozenset("ى")

# التشكيل (الحركات)
_DIACRITICS = frozenset("ًٌٍَُِّْٕٓٔ")

# حرف الفتحة والكسرة والضمة والشدة
_FATHA  = 'َ'   # َ
_KASRA  = 'ِ'   # ِ
_DAMMA  = 'ُ'   # ُ
_SHADDA = 'ّ'   # ّ


# ══════════════════════════════════════════════════════════════════════
# نمط Regex للأوزان المشكَّلة
# ══════════════════════════════════════════════════════════════════════

_CONS_CLASS = "[بتثجحخدذرزسشصضطظعغفقكلمنهوي]"
_VOWEL_SHORT = f"[{_FATHA}{_KASRA}{_DAMMA}]"

# فَعَلَ / فَعِلَ / فَعُلَ — ماضي ثلاثي سالم مشكَّل
_STRONG_PAST_DIACRITIZED = re.compile(
    rf'^{_CONS_CLASS}{_VOWEL_SHORT}{_CONS_CLASS}{_VOWEL_SHORT}{_CONS_CLASS}{_VOWEL_SHORT}?$'
)

# فَاعَ / فَالَ — ماضي أجوف مشكَّل (C + fatha + ا + C + fatha?)
_HOLLOW_PAST_DIACRITIZED = re.compile(
    rf'^{_CONS_CLASS}[َ]ا{_CONS_CLASS}[َ]?$'
)

# فَعَى / فَعَلَ (last ى) — ماضي ناقص بالألف المقصورة
_DEFECTIVE_YA_DIACRITIZED = re.compile(
    rf'^{_CONS_CLASS}{_VOWEL_SHORT}{_CONS_CLASS}{_VOWEL_SHORT}[ى]$'
)

# فَعَا — ماضي ناقص بالألف الممدودة
_DEFECTIVE_ALEF_DIACRITIZED = re.compile(
    rf'^{_CONS_CLASS}{_VOWEL_SHORT}{_CONS_CLASS}{_VOWEL_SHORT}[ا]$'
)


# ══════════════════════════════════════════════════════════════════════
# هيكل النتيجة
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Fi3lPatternAnalysis:
    """
    نتيجة تحليل نمط الفعل العربي — استدلال صرفي خالص.

    CONTEXT_USED_FOR_INTRINSIC_FI3L = 0:
      لا يوجد في هذا الهيكل أي إشارة إلى سياق إعرابي أو نحوي أو Hokom.

    الغموض محفوظ:
      word_class_vote = "AMBIGUOUS" يعني غموضاً جوهرياً صادقاً،
      لا فجوة معلومات تُحل بالسياق.
    """
    fi3l_family:       Fi3lFamily       # الصنف الصرفي للفعل
    word_class_vote:   str              # "FI3L" | "AMBIGUOUS" | "NONE"
    intrinsic_score:   float            # 0.0 – 1.0: قوة الإشارة الصرفية
    is_fi3l_candidate: bool             # True = النمط يتوافق مع فعل
    pattern_label:     str = ""         # وسم النمط: "CāC"، "CCى"، "CaCaCa"...
    confidence_kind:   str = "HEURISTIC_SCORE"
    confidence_basis:  str = "PATTERN_MATCH"
    evidence:          list[EvidenceRef] = field(default_factory=list)
    not_owned:         list[str] = field(default_factory=list)
    # أعلام القراءة السريعة
    has_diacritics_used: bool = False    # True = التشخيص اعتمد على التشكيل
    # §A: النموذج المتعامد الكامل — لا خاصية تُلغي أخرى
    verb_features:     Optional[VerbFeatureVector] = None
    # §B: أول دليل مفقود أوقف الاستدلال (للحالات التي لا نمط فيها)
    first_missing_evidence: str = ""


# ══════════════════════════════════════════════════════════════════════
# الدوال المساعدة
# ══════════════════════════════════════════════════════════════════════

def _strip_diacritics(text: str) -> str:
    return "".join(c for c in text if c not in _DIACRITICS)


def _has_diacritics(text: str) -> bool:
    return any(c in _DIACRITICS for c in text)


def _no_pattern(
    evidence: list,
    not_owned: list,
    first_missing_evidence: str = "",
) -> Fi3lPatternAnalysis:
    """لا نمط فعلي مكتشف — ليس من مهمة هذا المحرك"""
    return Fi3lPatternAnalysis(
        fi3l_family=Fi3lFamily.UNKNOWN,
        word_class_vote="NONE",
        intrinsic_score=0.0,
        is_fi3l_candidate=False,
        pattern_label="",
        evidence=evidence,
        not_owned=not_owned,
        first_missing_evidence=first_missing_evidence,
    )


def _infer_first_missing_evidence(stripped: str) -> str:
    """
    §B: استنتج أول دليل مفقود حقيقي — بحسب البنية السطحية.

    FALSE_RESIDUAL_CAUSALITY = 0:
      الكلمة ذات الحروف السالمة (كتب) لا تُشير إلى الشدة.
      الشدة مفقودة فقط في حال الثنائي السطحي (مد/رد).
    """
    n = len(stripped)
    if n == 0:
        return "سطح فارغ — لا نمط قابل للاستدلال"
    # حرفان: يُشير إلى مضعَّف بدون شدة (مد/رد بلا مَدَّ/رَدَّ)
    if n == 2 and all(c in (_NON_VOWEL_CONS | _STRONG_CONS) for c in stripped):
        return (
            "الشدة — الثنائي السطحي يُرجَّح أنه مضعَّف (مَدَّ/رَدَّ)"
            " لكن الشدة مفقودة لتأكيد التضعيف"
        )
    if n >= 3:
        c0, c1, c2 = stripped[0], stripped[1], stripped[2]
        # مهموز العين (سأل، رأى)
        if c1 in _HAMZA_LETTERS:
            return (
                "تشكيل الماضي — مهموز العين (فَعَلَ/فَعِلَ بهمزة وسط)"
                " يحتاج فتحتين للتمييز من ISM بلا نمط جوهري بدون تشكيل"
            )
        # مهموز اللام بهمزة على الألف (قرأ) — ليس 'ء' التي تُعالجها CāCء
        if c2 in _HAMZA_LETTERS and c2 != 'ء':
            return (
                "تشكيل الماضي — مهموز اللام (فَعَلَ بهمزة نهاية)"
                " يحتاج تشكيلاً للتمييز من ISM بلا نمط جوهري بدون تشكيل"
            )
        # مثال: فاء علة (وعد، يسر)
        if c0 in _WEAK_LETTERS:
            return (
                "تشكيل الماضي — المثال (فاء علة: و/ي) يحتاج فَعَلَ"
                " للتمييز من ISM بلا نمط جوهري بدون تشكيل"
            )
        # مهموز الفاء (أخذ، أكل)
        if c0 in _HAMZA_LETTERS:
            return (
                "تشكيل الماضي — مهموز الفاء (أَفعَل) يحتاج فَعَلَ"
                " للتمييز من ISM بلا نمط جوهري بدون تشكيل"
            )
        # ثلاثي سالم الظاهر (كتب، قتل، درس)
        return (
            "تشكيل الفعل الماضي — الثلاثي السالم (فَعَلَ/فَعِلَ/فَعُلَ)"
            " يحتاج فتحتين+حركة للتمييز من ISM بلا نمط جوهري بدون تشكيل"
        )
    return "نمط غير مطابق لأي وزن فعلي ثلاثي معروف"


# ══════════════════════════════════════════════════════════════════════
# تحليل الأنماط المشكَّلة (دياكريتيكس — ثقة عالية)
# ══════════════════════════════════════════════════════════════════════

def _classify_diacritized(
    surface: str,
    stripped: str,
    evidence: list[EvidenceRef],
    not_owned: list[str],
) -> Optional[Fi3lPatternAnalysis]:
    """
    تحليل الأوزان حين يكون السطح مشكَّلاً.
    الثقة هنا أعلى لأن التشكيل يُزيل كثيراً من الغموض.
    """

    # — مضعَّف: شدة على آخر حرف (مَدَّ، رَدَّ) ─────────────────────────
    if _SHADDA in surface:
        # بعد حذف التشكيل: مد = حرفان، رد = حرفان
        if len(stripped) == 2 and all(c in _NON_VOWEL_CONS | _STRONG_CONS for c in stripped):
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=f"'{surface}' يحتوي شدة مع حرفين في السطح → وزن المضعَّف (مَدَّ، رَدَّ)",
                value="FI3L_DOUBLED_CERTAIN",
                weight=0.85,
            ))
            return Fi3lPatternAnalysis(
                fi3l_family=Fi3lFamily.DOUBLED,
                word_class_vote="FI3L",
                intrinsic_score=0.85,
                is_fi3l_candidate=True,
                pattern_label="CaCCa",
                confidence_basis="PATTERN_MATCH",
                has_diacritics_used=True,
                evidence=evidence,
                not_owned=not_owned,
                verb_features=VerbFeatureVector(
                    radical_health=RadicalHealth.SOUND,
                    hamza_feature=HamzaFeature.NONE,
                    gemination=GeminationFeature.DOUBLED,
                ),
            )

    # — أجوف مشكَّل: C + فتحة + ا + C ──────────────────────────────
    if _HOLLOW_PAST_DIACRITIZED.match(surface):
        evidence.append(EvidenceRef(
            source=EvidenceSource.MORPHOLOGICAL_ENGINE,
            detail=f"'{surface}' يطابق وزن فَاعَ/فَالَ المشكَّل → ماضي أجوف",
            value="FI3L_HOLLOW_DIACRITIZED",
            weight=0.88,
        ))
        not_owned.append(
            "NOT_OWNED: إثبات الجذر الأجوف (عين و/ي) → noun_root_corrector / Maqayis"
        )
        return Fi3lPatternAnalysis(
            fi3l_family=Fi3lFamily.HOLLOW,
            word_class_vote="FI3L",
            intrinsic_score=0.88,
            is_fi3l_candidate=True,
            pattern_label="CāC_diacritized",
            confidence_basis="PATTERN_MATCH",
            has_diacritics_used=True,
            evidence=evidence,
            not_owned=not_owned,
            verb_features=VerbFeatureVector(
                radical_health=RadicalHealth.HOLLOW,
                hamza_feature=HamzaFeature.NONE,
                gemination=GeminationFeature.NONE,
            ),
        )

    # — ناقص مشكَّل ى: C + v + C + v + ى ──────────────────────────
    if _DEFECTIVE_YA_DIACRITIZED.match(surface):
        evidence.append(EvidenceRef(
            source=EvidenceSource.MORPHOLOGICAL_ENGINE,
            detail=f"'{surface}' وزن مشكَّل ينتهي بـ ى → ماضي ناقص بالألف المقصورة",
            value="FI3L_DEFECTIVE_YA_DIACRITIZED",
            weight=0.88,
        ))
        return Fi3lPatternAnalysis(
            fi3l_family=Fi3lFamily.DEFECTIVE,
            word_class_vote="FI3L",
            intrinsic_score=0.88,
            is_fi3l_candidate=True,
            pattern_label="CaCā_ya_diacritized",
            confidence_basis="PATTERN_MATCH",
            has_diacritics_used=True,
            evidence=evidence,
            not_owned=not_owned,
            verb_features=VerbFeatureVector(
                radical_health=RadicalHealth.DEFECTIVE,
                hamza_feature=HamzaFeature.NONE,
                gemination=GeminationFeature.NONE,
            ),
        )

    # — ناقص مشكَّل ا: C + v + C + v + ا ──────────────────────────
    if _DEFECTIVE_ALEF_DIACRITIZED.match(surface):
        evidence.append(EvidenceRef(
            source=EvidenceSource.MORPHOLOGICAL_ENGINE,
            detail=f"'{surface}' وزن مشكَّل ينتهي بـ ا → ماضي ناقص بالألف الممدودة",
            value="FI3L_DEFECTIVE_ALEF_DIACRITIZED",
            weight=0.88,
        ))
        return Fi3lPatternAnalysis(
            fi3l_family=Fi3lFamily.DEFECTIVE,
            word_class_vote="FI3L",
            intrinsic_score=0.88,
            is_fi3l_candidate=True,
            pattern_label="CaCā_alef_diacritized",
            confidence_basis="PATTERN_MATCH",
            has_diacritics_used=True,
            evidence=evidence,
            not_owned=not_owned,
            verb_features=VerbFeatureVector(
                radical_health=RadicalHealth.DEFECTIVE,
                hamza_feature=HamzaFeature.NONE,
                gemination=GeminationFeature.NONE,
            ),
        )

    # — سالم مشكَّل: C + فتحة/كسرة + C + فتحة/كسرة + C ────────────
    if _STRONG_PAST_DIACRITIZED.match(surface):
        evidence.append(EvidenceRef(
            source=EvidenceSource.MORPHOLOGICAL_ENGINE,
            detail=f"'{surface}' يطابق وزن فَعَلَ/فَعِلَ/فَعُلَ المشكَّل → ماضي سالم",
            value="FI3L_STRONG_DIACRITIZED",
            weight=0.90,
        ))
        not_owned.append(
            "NOT_OWNED: التمييز من ISM (فَعَل/فِعَال) بالتشكيل المختلف → Layer 6 أو قاموس"
        )
        return Fi3lPatternAnalysis(
            fi3l_family=Fi3lFamily.STRONG,
            word_class_vote="FI3L",
            intrinsic_score=0.90,
            is_fi3l_candidate=True,
            pattern_label="CaCaCa",
            confidence_basis="PATTERN_MATCH",
            has_diacritics_used=True,
            evidence=evidence,
            not_owned=not_owned,
            verb_features=VerbFeatureVector(
                radical_health=RadicalHealth.SOUND,
                hamza_feature=HamzaFeature.NONE,
                gemination=GeminationFeature.NONE,
            ),
        )

    return None


# ══════════════════════════════════════════════════════════════════════
# تحليل الأنماط بدون تشكيل (ثقة أقل — غموض جوهري محفوظ)
# ══════════════════════════════════════════════════════════════════════

def _classify_unvoweled(
    stripped: str,
    evidence: list[EvidenceRef],
    not_owned: list[str],
) -> Fi3lPatternAnalysis:
    """
    تحليل السطح بدون تشكيل.
    الغموض الجوهري هنا صادق — ليس فجوة معلومات.
    MISSING_INTRINSIC_VERB_PATTERN ≠ NEEDS_CONTEXT
    """
    n = len(stripped)

    # ── نمط ناقص بـ ى: CCى (رمى، سعى، مشى) ─────────────────────────
    # هذا النمط هو الأقوى: الألف المقصورة في نهاية ثلاثي = فعل ناقص بنسبة عالية
    if n == 3 and stripped.endswith('ى'):
        c0, c1 = stripped[0], stripped[1]
        if c0 in _NON_VOWEL_CONS and c1 in (_NON_VOWEL_CONS | _WEAK_LETTERS):
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"'{stripped}' = CCى (ألف مقصورة في الآخر) → نمط ماضي ناقص قوي"
                    " | أمثلة: رمى، سعى، مشى، دنا، عدا"
                ),
                value="FI3L_DEFECTIVE_YA_CANDIDATE",
                weight=0.70,
            ))
            not_owned.append(
                "NOT_OWNED: التحقق من الجذر الناقص (ي/و) → noun_root_corrector / Maqayis"
            )
            not_owned.append(
                "NOT_OWNED: أمثلة غموض ISM بنمط CCى: فتى، ندى، مدى — تُحسم بالمعجم"
            )
            return Fi3lPatternAnalysis(
                fi3l_family=Fi3lFamily.DEFECTIVE,
                word_class_vote="FI3L",
                intrinsic_score=0.70,
                is_fi3l_candidate=True,
                pattern_label="CCى",
                evidence=evidence,
                not_owned=not_owned,
                verb_features=VerbFeatureVector(
                    radical_health=RadicalHealth.DEFECTIVE,
                    hamza_feature=HamzaFeature.NONE,
                    gemination=GeminationFeature.NONE,
                ),
            )

    # ── نمط مهموز أجوف: CāCء (جاء، شاء) ────────────────────────────
    # الأجوف المهموز اللام: ثلاثي، وسطه ا، آخره ء
    # §A: Fi3lFamily.HAMZATED هو الوسم المختصر الأبرز.
    #     VerbFeatureVector يحفظ كلا البُعدين: HOLLOW (عينه مد) + FINAL (لامه همزة)
    #     ORTHOGONAL_VERB_FEATURE_LOSS = 0: HAMZATED لا يُلغي HOLLOW
    if n == 3 and stripped[1] == 'ا' and stripped[2] == 'ء':
        c0 = stripped[0]
        if c0 in _NON_VOWEL_CONS:
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"'{stripped}' = CāCء → نمط الأجوف المهموز اللام — FI3L مرشح"
                    " | أمثلة FI3L: جاء، شاء"
                ),
                value="FI3L_HOLLOW_HAMZATED_CANDIDATE",
                weight=0.65,
            ))
            # Law: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
            # نمط CāCء مشترك مع ISM (ماء) على مستوى النمط — لكن ذلك لا يُسبب
            # غموضاً على مستوى الرمز لجاء/شاء التي ليس لها تحليل ISM مرخَّص.
            # الغموض على مستوى النمط مُوثَّق في not_owned، لا في evidence.
            not_owned.append(
                "NOT_OWNED: حسم الغموض FI3L↔ISM (جاء/ماء) → معجم مقاييس أو دياكريتيكس"
            )
            not_owned.append(
                "NOT_OWNED: PATTERN_CLASS_NOTE: نمط CāCء مشترك مع ISM (ماء) على مستوى"
                " النمط فقط — لا يُسبب غموضاً لرموز مثل جاء/شاء التي ليس لها"
                " تحليل ISM مرخَّص مستقل"
            )
            return Fi3lPatternAnalysis(
                fi3l_family=Fi3lFamily.HAMZATED,
                word_class_vote="FI3L",
                intrinsic_score=0.65,
                is_fi3l_candidate=True,
                pattern_label="CāCء",
                evidence=evidence,
                not_owned=not_owned,
                # §A: البُعدان محفوظان بشكل متعامد:
                #   radical_health=HOLLOW  ← العين حرف مد (جاء/شاء = ج/ش + ا + ء)
                #   hamza_feature=FINAL    ← اللام همزة
                verb_features=VerbFeatureVector(
                    radical_health=RadicalHealth.HOLLOW,
                    hamza_feature=HamzaFeature.FINAL,
                    gemination=GeminationFeature.NONE,
                ),
            )

    # ── نمط أجوف: CāC (قام، باع، قال، صام) ─────────────────────────
    # ثلاثي، وسطه ا، آخره ليس ء
    if n == 3 and stripped[1] == 'ا' and stripped[2] not in ('ا', 'ء', 'ى'):
        c0, c2 = stripped[0], stripped[2]
        if c0 in _NON_VOWEL_CONS and c2 in (_NON_VOWEL_CONS | _WEAK_LETTERS):
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"'{stripped}' = CāC → نمط ماضي الأجوف — FI3L مرشح"
                    " | أمثلة: قام، باع، قال، صام"
                ),
                value="FI3L_HOLLOW_CANDIDATE",
                weight=0.60,
            ))
            # Law: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
            # نمط CāC مشترك مع ISM (باب، دار) على مستوى النمط — لكن ذلك لا يُسبب
            # غموضاً على مستوى الرمز لقام/باع التي ليس لها تحليل ISM مرخَّص مستقل.
            # الغموض على مستوى النمط مُوثَّق في not_owned، لا في evidence.
            not_owned.append(
                "NOT_OWNED: حسم الغموض FI3L↔ISM (قام/باب) → دياكريتيكس أو معجم مقاييس"
            )
            not_owned.append(
                "NOT_OWNED: PATTERN_CLASS_NOTE: نمط CāC مشترك مع ISM (باب، دار) على"
                " مستوى النمط فقط — لا يُسبب غموضاً على مستوى الرمز إلا بوجود"
                " تحليلين مرخَّصين لنفس الرمز"
            )
            return Fi3lPatternAnalysis(
                fi3l_family=Fi3lFamily.HOLLOW,
                word_class_vote="FI3L",
                intrinsic_score=0.60,
                is_fi3l_candidate=True,
                pattern_label="CāC",
                evidence=evidence,
                not_owned=not_owned,
                verb_features=VerbFeatureVector(
                    radical_health=RadicalHealth.HOLLOW,
                    hamza_feature=HamzaFeature.NONE,
                    gemination=GeminationFeature.NONE,
                ),
            )

    # ── نمط ناقص بـ ا: CCا (دعا، بكا، نجا) ──────────────────────────
    # ثلاثي ينتهي بـ ا، ووسطه ليس ا (لتمييزه عن CāC)
    if n == 3 and stripped.endswith('ا') and stripped[1] != 'ا':
        c0, c1 = stripped[0], stripped[1]
        if c0 in _NON_VOWEL_CONS and c1 in (_NON_VOWEL_CONS | _WEAK_LETTERS):
            evidence.append(EvidenceRef(
                source=EvidenceSource.MORPHOLOGICAL_ENGINE,
                detail=(
                    f"'{stripped}' = CCا → نمط ماضي ناقص بالألف الممدودة — FI3L مرشح"
                    " | أمثلة FI3L: دعا، بكا، نجا"
                ),
                value="FI3L_DEFECTIVE_ALEF_CANDIDATE",
                weight=0.55,
            ))
            # Law: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
            not_owned.append(
                "NOT_OWNED: حسم الغموض FI3L↔ISM (دعا/غدا) → معجم أو سياق تركيبي"
            )
            not_owned.append(
                "NOT_OWNED: PATTERN_CLASS_NOTE: نمط CCا مشترك مع ISM (غدا، سما) على"
                " مستوى النمط فقط — لا يُسبب غموضاً على مستوى الرمز إلا بوجود"
                " تحليلين مرخَّصين لنفس الرمز"
            )
            return Fi3lPatternAnalysis(
                fi3l_family=Fi3lFamily.DEFECTIVE,
                word_class_vote="FI3L",
                intrinsic_score=0.55,
                is_fi3l_candidate=True,
                pattern_label="CCا",
                evidence=evidence,
                not_owned=not_owned,
                verb_features=VerbFeatureVector(
                    radical_health=RadicalHealth.DEFECTIVE,
                    hamza_feature=HamzaFeature.NONE,
                    gemination=GeminationFeature.NONE,
                ),
            )

    # لا نمط مكتشف — §B: احسب أول دليل مفقود حقيقي
    fme = _infer_first_missing_evidence(stripped)
    return _no_pattern(evidence, not_owned, first_missing_evidence=fme)


# ══════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية
# ══════════════════════════════════════════════════════════════════════

def classify_fi3l_pattern(surface: str) -> Fi3lPatternAnalysis:
    """
    افحص إذا كان السطح يحمل نمط فعل عربي جوهري.

    المدخل:
        surface — الكلمة (مشكَّلة أو غير مشكَّلة)

    المخرج:
        Fi3lPatternAnalysis
            .fi3l_family        — الصنف الصرفي
            .word_class_vote    — "FI3L" | "AMBIGUOUS" | "NONE"
            .is_fi3l_candidate  — True إذا وُجد نمط فعلي
            .intrinsic_score    — 0.0–1.0 (HEURISTIC_SCORE)

    ضمانات:
        CONTEXT_USED_FOR_INTRINSIC_FI3L = 0
          لا يُستخدم سياق إعرابي أو مخرجات Hokom/Irab.

        الغموض الجوهري محفوظ:
          "AMBIGUOUS" = النمط مشترك مع ISM صرفياً
          ليس "يحتاج سياقاً" — بل "لا يحسمه صرف الكلمة المنفردة"
    """
    evidence: list[EvidenceRef] = []
    not_owned: list[str] = []

    if not surface or not surface.strip():
        return _no_pattern(evidence, not_owned)

    surface = surface.strip()
    has_diacs = _has_diacritics(surface)
    stripped = _strip_diacritics(surface)

    if not stripped:
        return _no_pattern(evidence, not_owned)

    # ── 1. تحليل بالتشكيل إن وُجد (ثقة عالية) ───────────────────────
    if has_diacs:
        result = _classify_diacritized(surface, stripped, evidence, not_owned)
        if result is not None:
            return result
        # إذا وُجد تشكيل لكن لم يطابق الأنماط → ننتقل للتحليل بدون تشكيل

    # ── 2. تحليل بدون تشكيل (ثقة متوسطة — غموض محفوظ) ─────────────
    return _classify_unvoweled(stripped, evidence, not_owned)


def is_fi3l_candidate(surface: str) -> bool:
    """اختبار سريع: هل الكلمة مرشحة لأن تكون فعلاً؟"""
    return classify_fi3l_pattern(surface).is_fi3l_candidate


def get_fi3l_family(surface: str) -> Fi3lFamily:
    """اختبار سريع: أعطِ صنف الفعل (UNKNOWN إذا لم يُعرَّف)"""
    return classify_fi3l_pattern(surface).fi3l_family
