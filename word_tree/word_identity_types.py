"""
word_identity_types.py — أنواع طبقة الهوية الجوهرية للكلمة العربية
ARABIC INTRINSIC WORD IDENTITY PROGRAM — هياكل البيانات

مبادئ التصميم:
 • الغموض محفوظ حتى يُحسمه دليل مُرخَّص
 • لا قرار صرفي بدون مصدر دليل
 • لا تدفق للخلف: لا يُستخدم ناتج Hokom كدليل هنا
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════════════
# مستوى الإثبات (CERTIFICATION_LEVEL)  — §3
# ══════════════════════════════════════════════════════════════════════

class CertificationLevel(str, Enum):
    """
    مستوى إثبات المرشح أو القرار.

    SILENT_SINGLE_CANDIDATE_PROMOTION = 0:
      وجود مرشح واحد فقط لا يرقِّيه تلقائياً إلى CERTIFIED.
      المرشح الوحيد يبقى EVIDENCE_SUPPORTED حتى يأتي دليل مستقل ثانٍ.

    التدرج:
      CANDIDATE         — مرشح خوارزمي أو أول وصول، بلا تحقق من مقاييس
      EVIDENCE_SUPPORTED — موجود في مقاييس، أو دليل واحد مستقل
      CERTIFIED         — دليلان مستقلان يُثبتانه (مقاييس + مطابقة وزن مثلاً)
      REJECTED          — مستبعَد بدليل نقيض
      UNRESOLVED        — لا دليل كافٍ، يُحال للطبقة التالية
    """
    CANDIDATE          = "مرشح"
    EVIDENCE_SUPPORTED = "مدعوم_بدليل"
    CERTIFIED          = "مُثبَت"
    REJECTED           = "مستبعَد"
    UNRESOLVED         = "غير_محسوم"


# ══════════════════════════════════════════════════════════════════════
# صنف الفعل العربي (FI3L_FAMILY)  — محرك الفعل الجوهري
# ══════════════════════════════════════════════════════════════════════

class Fi3lFamily(str, Enum):
    """
    صنف الفعل العربي — يحدده البنية الصرفية الجوهرية للسطح.

    CONTEXT_USED_FOR_INTRINSIC_FI3L = 0:
      لا يُستخدم سياق إعرابي أو نحوي في تحديد هذا الصنف.
      القرارات هنا تعتمد على شكل الكلمة السطحي فقط.

    الغموض الجوهري محفوظ:
      MISSING_INTRINSIC_VERB_PATTERN ≠ NEEDS_CONTEXT
      النمط CāC (قام، باع) مشترك مع ISM (باب، دار) → AMBIGUOUS صادق

    ملاحظة التعامد (ORTHOGONALITY_NOTE):
      Fi3lFamily هو وسم مختصر للخاصية الأبرز — لا يُلغي الخصائص الأخرى.
      استخدم VerbFeatureVector للنموذج الكامل المتعامد.
      مثال: جاء → Fi3lFamily.HAMZATED + VerbFeatureVector(HOLLOW, FINAL, NONE)
    """
    STRONG    = "سالم"       # فعل سالم: جميع حروف الجذر صحيحة (كَتَبَ، قَتَلَ)
    HOLLOW    = "أجوف"       # فعل أجوف: العين و أو ي (قَامَ، بَاعَ، قَالَ، صَامَ)
    DEFECTIVE = "ناقص"       # فعل ناقص: اللام و أو ي (دَعَا، رَمَى، سَعَى)
    HAMZATED  = "مهموز"      # فعل مهموز: أحد حروفه همزة (جَاءَ، شَاءَ، أَخَذَ)
    DOUBLED   = "مضعَّف"     # فعل مضعَّف: العين = اللام (مَدَّ، رَدَّ)
    MIXED     = "مختلط"      # مزيج: مهموز + أجوف (جاء = أجوف مهموز اللام)
    UNKNOWN   = "غير_محدد"   # لم يُعرَّف النمط بدليل جوهري


# ══════════════════════════════════════════════════════════════════════
# متجه الخصائص الفعلية المتعامدة (VERB_FEATURE_VECTOR)  — §A
# ══════════════════════════════════════════════════════════════════════

class RadicalHealth(str, Enum):
    """
    صحة حروف الجذر الثلاثي — بُعد مستقل.

    ORTHOGONAL_TO_HAMZA_AND_GEMINATION = True:
      جاء = HOLLOW (عينه حرف مد) + همزة في اللام → لا تُلغي إحداهما الأخرى.
    """
    SOUND      = "سالم"       # جميع حروف الجذر صحيحة: كَتَبَ، قَتَلَ، سَأَلَ
    ASSIMILATED = "مثال"      # الفاء حرف علة: وَعَدَ، يَسَرَ
    HOLLOW     = "أجوف"       # العين حرف علة: قَامَ، بَاعَ، جَاءَ (وسطه مد)
    DEFECTIVE  = "ناقص"       # اللام حرف علة: رَمَى، دَعَا
    LAFIF      = "لفيف"       # حرفا علة: وَقَى (مفروق)، طَوَى (مقرون)


class HamzaFeature(str, Enum):
    """
    موقع الهمزة في الجذر — بُعد مستقل عن RadicalHealth.

    NONE  = لا همزة في الجذر
    INITIAL / MEDIAL / FINAL = الهمزة في الفاء / العين / اللام
    """
    NONE    = "لا_همزة"
    INITIAL = "مهموز_الفاء"   # أَخَذَ، أَكَلَ
    MEDIAL  = "مهموز_العين"   # سَأَلَ، رَأَى
    FINAL   = "مهموز_اللام"   # قَرَأَ، جَاءَ، شَاءَ


class GeminationFeature(str, Enum):
    """
    تضعيف الجذر (العين = اللام) — بُعد مستقل.
    """
    NONE    = "غير_مضعَّف"
    DOUBLED = "مضعَّف"        # مَدَّ، رَدَّ، حَلَّ


@dataclass
class VerbFeatureVector:
    """
    النموذج الكامل المتعامد لخصائص الجذر الفعلي.

    ORTHOGONAL_VERB_FEATURE_LOSS = 0:
      لا خاصية تُلغي أخرى. كل بُعد مستقل.

    أمثلة:
      كَتَبَ → VFV(SOUND,   NONE,    NONE)
      قَامَ  → VFV(HOLLOW,  NONE,    NONE)
      جَاءَ  → VFV(HOLLOW,  FINAL,   NONE)   ← أجوف مهموز اللام
      شَاءَ  → VFV(HOLLOW,  FINAL,   NONE)   ← نفس جاء
      سَأَلَ  → VFV(SOUND,   MEDIAL,  NONE)
      أَخَذَ  → VFV(SOUND,   INITIAL, NONE)
      قَرَأَ  → VFV(SOUND,   FINAL,   NONE)
      مَدَّ  → VFV(SOUND,   NONE,    DOUBLED)
      رَدَّ  → VFV(SOUND,   NONE,    DOUBLED)
      وَعَدَ → VFV(ASSIMILATED, NONE, NONE)
      رَمَى  → VFV(DEFECTIVE, NONE,  NONE)
    """
    radical_health: RadicalHealth
    hamza_feature:  HamzaFeature
    gemination:     GeminationFeature


# ══════════════════════════════════════════════════════════════════════
# تصنيف الكلمة (WORD_CLASS)
# ══════════════════════════════════════════════════════════════════════

class WordClass(str, Enum):
    """التصنيف الثلاثي الكبير — لا وسط بينها"""
    ISM   = "اسم"    # الاسم: يقبل التنوين أو التعريف أو الإسناد الاسمي
    FI3L  = "فعل"    # الفعل: يتصرف بالزمن أو يبنى للمجهول
    HARF  = "حرف"   # الحرف: مبني، لا يُسند إليه
    UNKNOWN = "غير_محدد"  # لم يُحسم


class WordClassConfidence(str, Enum):
    """درجة اليقين في تصنيف WORD_CLASS"""
    CERTAIN  = "يقين"      # قائمة ثابتة (أحرف) أو برهان صرفي واضح
    PROBABLE = "غالب"      # غالبية الشواهد تدل عليه
    AMBIGUOUS = "متنازع"   # أكثر من تصنيف ممكن بغير سياق


# ══════════════════════════════════════════════════════════════════════
# نوع الصيغة الاشتقاقية (DERIVED_FORM_TYPE)
# ══════════════════════════════════════════════════════════════════════

class DerivedFormType(str, Enum):
    """
    صيغة الكلمة المشتقة — كلها داخل عائلة الاسم (ISM) أو الفعل (FI3L).
    UNKNOWN تعني: لم يُعرف، ليس: لا يوجد.
    """
    # ── مشتقات الأسماء ──────────────────────────────────────────────
    ISM_FAAIL        = "اسم_فاعل"          # كَاتِب
    ISM_MAFUUL       = "اسم_مفعول"         # مَكْتُوب
    ISM_MAKAN        = "اسم_مكان"          # مَكْتَبَة / مَكْتَب
    ISM_ZAMAN        = "اسم_زمان"          # مَوْسِم
    ISM_AALA         = "اسم_آلة"           # مِكْنَسَة
    SIFA_MUSHABBAHA  = "صفة_مشبهة"         # كَرِيم، جَمِيل، شَدِيد (ثابت + لازم)
    MASDAR           = "مصدر"              # كِتَابَة، كَتْب
    MASDAR_MIIMI     = "مصدر_ميمي"         # مَكْتَب (دلالة مصدرية)
    SIFA_MUBAALAGHA  = "صيغة_مبالغة"       # فَعَّال، مِفْعَال، فَعُول، فَعِيل
    ISM_TAFDIIL      = "اسم_تفضيل"         # أَفْعَل (أكبر، أفضل)
    JAM_TAKSIR       = "جمع_تكسير"         # رِجَال، كُتُب
    JAM_MUDHAKKAR    = "جمع_مذكر_سالم"     # مُعَلِّمُون
    JAM_MUANNATH     = "جمع_مؤنث_سالم"     # مُعَلِّمَات
    MUSHTAQQ_OTHER   = "مشتق_آخر"          # مشتق لم يُعرَّف بشكل أدق
    # ── صيغ الأفعال ─────────────────────────────────────────────────
    FI3L_MADII       = "فعل_ماض"
    FI3L_MUDAARI3    = "فعل_مضارع"
    FI3L_AMR         = "فعل_أمر"
    FI3L_MAJHUL      = "فعل_مبني_للمجهول"
    FI3L_MAZID_II    = "فعل_مزيد_II"       # فَعَّلَ
    FI3L_MAZID_III   = "فعل_مزيد_III"      # فَاعَلَ
    FI3L_MAZID_IV    = "فعل_مزيد_IV"       # أَفْعَلَ
    FI3L_MAZID_V     = "فعل_مزيد_V"        # تَفَعَّلَ
    FI3L_MAZID_VI    = "فعل_مزيد_VI"       # تَفَاعَلَ
    FI3L_MAZID_VII   = "فعل_مزيد_VII"      # اِنْفَعَلَ
    FI3L_MAZID_VIII  = "فعل_مزيد_VIII"     # اِفْتَعَلَ
    FI3L_MAZID_IX    = "فعل_مزيد_IX"       # اِفْعَلَّ
    FI3L_MAZID_X     = "فعل_مزيد_X"        # اِسْتَفْعَلَ
    # ── جامع ────────────────────────────────────────────────────────
    MUJARRAD         = "جذر_مجرد"          # الكلمة هي الجذر نفسه
    UNKNOWN          = "غير_محدد"


# ══════════════════════════════════════════════════════════════════════
# الهوية العددية (NUMERAL_IDENTITY)
# ══════════════════════════════════════════════════════════════════════

class NumeralType(str, Enum):
    """
    تصنيف الكلمة العددية.
    NONE = ليست عدداً.
    """
    NONE           = "ليس_عدداً"
    CARDINAL_BASIC  = "أصلي_مفرد"   # واحد، اثنان، ثلاثة...تسعة
    CARDINAL_UNIT   = "عشري_وحدة"   # عشرة، عشرون...تسعون
    CARDINAL_HUNDRED = "مئوي"        # مئة، مئتان
    CARDINAL_THOUSAND = "ألفي"       # ألف، ألفان، آلاف
    CARDINAL_MILLION  = "مليوني"     # مليون، مليار
    ORDINAL           = "ترتيبي"     # أول، ثانٍ، ثالث...
    FRACTION          = "كسري"       # نصف، ثلث، ربع
    MULTIPLICATIVE    = "تكراري"     # مرة، مرتان، ثلاث مرات (مركّب)


# ══════════════════════════════════════════════════════════════════════
# مصادر الدليل (EVIDENCE_REF)
# ══════════════════════════════════════════════════════════════════════

class EvidenceSource(str, Enum):
    """مصدر الدليل — يظهر في كل مطالبة"""
    MAQAYIS_DB         = "مقاييس_قاعدة_بيانات"
    AUDITED_ROOTS_CSV  = "جذور_مدققة_CSV"
    HARF_STATIC_LIST   = "قائمة_الحروف_الثابتة"
    NUMERAL_STATIC_LIST = "قائمة_الأعداد_الثابتة"
    DERIVATION_ENGINE  = "محرك_الاشتقاق"
    MORPHOLOGICAL_ENGINE = "محرك_الصرف"
    PATTERN_MATCH      = "مطابقة_وزن"
    NOUN_ROOT_CORRECTOR = "مصحح_جذر_الاسم"
    CORPUS_LOOKUP      = "بحث_في_المدونة"
    UNRESOLVED         = "غير_محسوم"


@dataclass
class EvidenceRef:
    """مرجع دليل واحد قابل للتتبع"""
    source:  EvidenceSource
    detail:  str                     # وصف المطابقة: مثلاً "باب FAU_YAF_U في audited_roots.csv"
    value:   str = ""                # القيمة الفعلية التي أنتجها الدليل
    weight:  float = 1.0             # الوزن النسبي (0–1)


# ══════════════════════════════════════════════════════════════════════
# مرشح الجذر (ROOT CANDIDATE)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RootCandidate:
    """
    مرشح جذر واحد — مع درجة الدليل.
    SILENT_FIRST_HIT_SELECTION = 0:
    نعرض جميع المرشحين، لا نختار الأول صمتاً.
    SILENT_SINGLE_CANDIDATE_PROMOTION = 0:
    المرشح الوحيد يبقى EVIDENCE_SUPPORTED لا CERTIFIED.
    """
    root:               str
    is_maqayis:         bool                       # موجود في مقاييس؟
    rank:               int                        # ترتيب الثقة (1 = الأقوى)
    algorithm_src:      str = ""                   # الخوارزمية التي أنتجته
    axes_count:         int = 0                    # عدد المحاور الدلالية في مقاييس
    baab:               Optional[str] = None       # الباب إن عُرف من audited_roots.csv
    certification_level: "CertificationLevel" = field(
        default_factory=lambda: CertificationLevel.CANDIDATE
    )
    evidence:           list[EvidenceRef] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# تحليل الجذر (ROOT ANALYSIS)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RootAnalysis:
    """
    نتيجة تحليل الجذر — تحفظ الغموض.
    إذا كان len(candidates) > 1 → ambiguity = True.
    SILENT_SINGLE_CANDIDATE_PROMOTION = 0:
      single maq candidate → EVIDENCE_SUPPORTED, لا CERTIFIED.
    """
    candidates:         list[RootCandidate]
    resolved_root:      Optional[str]      # الجذر المحسوم إن وُجد دليل واحد فقط
    ambiguous:          bool               # هل التعدد لم يُحسم؟
    coverage:           str                # "COVERED" | "NOT_FOUND" | "MISSING_VOLUME" | "NO_ARABIC"
    certification_level: "CertificationLevel" = field(
        default_factory=lambda: CertificationLevel.UNRESOLVED
    )


# ══════════════════════════════════════════════════════════════════════
# الهوية الصرفية (MORPHOLOGICAL_IDENTITY)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MorphologicalIdentity:
    """
    ما تُخبرنا به الصيغة الصرفية — بدون سياق إعرابي.
    (السياق الإعرابي في Layer 6 — ليس هنا)
    """
    derived_form:    DerivedFormType
    gender:          Optional[str] = None    # "مذكر" | "مؤنث" | None
    number:          Optional[str] = None    # "مفرد" | "مثنى" | "جمع" | None
    definiteness:    Optional[str] = None    # "معرفة" | "نكرة" | None
    base_pattern:    Optional[str] = None    # الوزن المجرد: فَعِيل، مَفْعُول...
    evidence:        list[EvidenceRef] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# الهوية الاشتقاقية (DERIVATIONAL_IDENTITY)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class DerivationalIdentity:
    """
    العلاقة بين السطح والجذر — عبر محرك الاشتقاق.
    هل الكلمة السطحية مولَّدة من الجذر المحسوم بخطوة اشتقاقية واضحة؟

    §4 — عقد الثقة المكتوب:
      confidence_kind  : نوع الرقم في 'confidence'
                         "HEURISTIC_SCORE"        — نقطة مرجَّحة يدوياً، لا احتمالية مُعيَّرة
                         "CALIBRATED_PROBABILITY" — احتمالية مُعيَّرة (غير مُنفَّذة بعد)
      confidence_basis : أساس الحساب
                         "PATTERN_MATCH_AND_BAAB_LOOKUP" — مطابقة وزن + باب CSV
                         "STATIC_LIST"                   — قائمة ثابتة
                         "UNCOMPUTED"                    — لا قيمة محسوبة
    """
    root:             Optional[str]          # الجذر المرجعي لهذه الهوية
    baab:             Optional[str]          # الباب الصرفي للجذر
    derivation_path:  list[str]              # مسار الاشتقاق: ["FAU_YAF_U", "SIFA_MUSHABBAHA"]
    generated_form:   Optional[str]          # الصيغة التي ولَّدها المحرك (قد تختلف عن السطح)
    surface_matches:  bool                   # هل الصيغة المولَّدة تطابق السطح؟
    confidence:       float                  # 0–1  (انظر confidence_kind)
    confidence_kind:  str = "HEURISTIC_SCORE"              # §4: نوع القيمة
    confidence_basis: str = "PATTERN_MATCH_AND_BAAB_LOOKUP"  # §4: أساس الحساب
    evidence:         list[EvidenceRef] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# الهوية المعجمية (LEXICAL_IDENTITY)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class LexicalIdentity:
    """
    ما يُعطيه المعجم المرجعي (مقاييس) عن الجذر.
    لا نستخرج هوية معجمية للكلمة السطحية مباشرة — فقط عبر الجذر.
    """
    root:            Optional[str]
    axes_texts:      list[str]       # المحاور الدلالية من مقاييس
    axes_count:      int
    body_snippet:    str             # مقتطف من نص مدخل المقاييس (أول 200 حرف)
    coverage_status: str             # "COVERED" | "MISSING_VOLUME" | "NOT_FOUND"
    evidence:        list[EvidenceRef] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# الهوية العددية (NUMERAL_IDENTITY)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class NumeralIdentity:
    """
    هوية الكلمة إذا كانت عدداً. is_numeral=False → ignore rest.
    """
    is_numeral:    bool
    numeral_type:  NumeralType
    numeric_value: Optional[int]      # القيمة الرقمية إن كانت قابلة للحساب
    gender_form:   Optional[str]      # "مذكر" | "مؤنث" للأعداد ذات الشكلين
    evidence:      list[EvidenceRef] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# حالة الغموض (AMBIGUITY)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class AmbiguityReport:
    """
    تقرير الغموض الكامل.
    الغموض محفوظ حتى يُحسمه دليل مُرخَّص — ولا يُحسم بالسياق هنا.
    """
    has_ambiguity:        bool
    ambiguity_sources:    list[str]       # "ROOT_AMBIGUITY", "WORD_CLASS_AMBIGUITY", ...
    candidate_roots:      list[str]       # جميع الجذور المرشحة
    candidate_classes:    list[WordClass] # جميع التصنيفات الممكنة
    resolution_available: bool            # هل يمكن حسمه بدليل موجود؟
    resolution_note:      str             # "يتطلب سياقاً إعرابياً" | "مدخل مزدوج في المقاييس"


# ══════════════════════════════════════════════════════════════════════
# المخلفات (RESIDUALS)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ResidualGap:
    """
    §9: فجوة موثَّقة كعنصر أول — مع المالك المفقود والدليل الفاشل.
    هذه البنية هي الإجابة على: من يملك إغلاق هذه الفجوة؟
    """
    gap_id:              str    # مُعرِّف قصير: "MISSING_ROOT", "UNKNOWN_BAAB", ...
    description:         str    # وصف الفجوة
    first_missing_owner: str    # الطبقة أو المكوِّن المسؤول عن الإغلاق
    failed_evidence:     str    # الدليل الذي حاولنا ولم نجده: "مقاييس: جذر غير موجود"
    severity:            str = "WARN"   # "WARN" | "BLOCK" | "INFO"


@dataclass
class Residuals:
    """
    كل ما لم يُحسم في هذه الطبقة.
    §9: المخلفات حقل أول في الشهادة — موثَّق بـ ResidualGap وEvidenceRef.

    يُحال للطبقة التالية (Hokom / Irab) أو يُعلَّق.
    """
    unresolved_root:     bool = False    # الجذر لم يُحسم
    unresolved_class:    bool = False    # التصنيف لم يُحسم
    unknown_baab:        bool = False    # الباب غير معروف
    missing_volume:      bool = False    # حرف أول من الأحرف الناقصة في مقاييس
    no_derivation_path:  bool = False    # لا مسار اشتقاقي واضح
    gaps:                list[ResidualGap] = field(default_factory=list)   # §9: تفصيل الفجوات
    notes:               list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# الشهادة الكاملة (WORD IDENTITY CERTIFICATE)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class WordIdentityCertificate:
    """
    الهوية الجوهرية الكاملة للكلمة العربية.
    المخرج الرئيسي لـ ARABIC INTRINSIC WORD IDENTITY PROGRAM.

    الحقول التسعة كما في المواصفة:
        original_surface    — الكلمة كما وردت
        normalized_surface  — بعد إزالة التشكيل وتوحيد الهمزة
        word_class          — ISM / FI3L / HARF / UNKNOWN
        root_analysis       — مرشحو الجذر مع الأدلة
        morphological_identity  — الصيغة الصرفية
        derivational_identity   — المسار الاشتقاقي
        lexical_identity        — ما يعطيه المقاييس عبر الجذر
        numeral_identity        — هل هي عدد؟
        ambiguity               — تقرير الغموض
        evidence                — قائمة الأدلة المجمَّعة
        residuals               — ما لم يُحسم
    """
    original_surface:       str
    normalized_surface:     str
    word_class:             WordClass
    word_class_confidence:  WordClassConfidence
    root_analysis:          RootAnalysis
    morphological_identity: MorphologicalIdentity
    derivational_identity:  DerivationalIdentity
    lexical_identity:       LexicalIdentity
    numeral_identity:       NumeralIdentity
    ambiguity:              AmbiguityReport
    evidence:               list[EvidenceRef]
    residuals:              Residuals
    # §ROOT-VFV COMPOSITION — النموذج المتعامد المُركَّب من جذر + نمط سطحي
    # composed_verb_features: مشتق من (SURFACE_PATTERN + ROOT_EVIDENCE) معاً.
    # None = ليس فعلاً، أو الجذر دون EVIDENCE_SUPPORTED.
    # UNLICENSED_ROOT_TO_FEATURE_PROMOTION = 0:
    #   لا تُشتق خصائص من جذر CANDIDATE — فقط من EVIDENCE_SUPPORTED فما فوق.
    # DERIVED_FEATURE_RANK <= SOURCE_ROOT_RANK:
    #   الخاصية المشتقة لا تكتسب رتبة أعلى من دليل الجذر.
    #   EVIDENCE_SUPPORTED root → feat_source="EVIDENCE_SUPPORTED_ROOT", feat_status="EVIDENCE_SUPPORTED"
    #   CERTIFIED root          → feat_source="CERTIFIED_ROOT",           feat_status="CERTIFIED"
    composed_verb_features: Optional["VerbFeatureVector"] = None
    # vfv_provenance: مصدر كل بُعد من أبعاد VerbFeatureVector الثلاثة.
    # مثال (EVIDENCE_SUPPORTED): {"radical_health": {"value":"مثال","source":"EVIDENCE_SUPPORTED_ROOT","status":"EVIDENCE_SUPPORTED"}}
    # مثال (CERTIFIED):          {"radical_health": {"value":"مثال","source":"CERTIFIED_ROOT","status":"CERTIFIED"}}
    vfv_provenance:         Optional[dict] = None

    def is_resolved(self) -> bool:
        """هل الهوية محسومة بالكامل؟"""
        return (
            self.word_class != WordClass.UNKNOWN
            and not self.ambiguity.has_ambiguity
            and self.root_analysis.resolved_root is not None
        )

    def summary_line(self) -> str:
        """سطر ملخص للطباعة السريعة"""
        root_str = self.root_analysis.resolved_root or "؟"
        if self.root_analysis.ambiguous:
            root_str = "/".join(self.root_analysis.candidates[i].root
                                for i in range(min(3, len(self.root_analysis.candidates))))
            root_str = f"[{root_str}]"
        class_str = self.word_class.value
        form_str = self.morphological_identity.derived_form.value
        num_str = f" عدد={self.numeral_identity.numeral_type.value}" if self.numeral_identity.is_numeral else ""
        return (
            f"{self.original_surface} → جذر:{root_str} "
            f"| تصنيف:{class_str} | صيغة:{form_str}{num_str}"
        )
