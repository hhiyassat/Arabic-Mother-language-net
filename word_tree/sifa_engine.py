"""
sifa_engine.py — محرك الصيغ الوصفية والاشتقاقية
ARABIC INTRINSIC WORD IDENTITY PROGRAM — المكون الثالث

يُحدد الصيغة الاشتقاقية للكلمة السطحية بالمقارنة مع الجذر:
  • صفة مشبهة (SIFA_MUSHABBAHA)  — فَعِيل من FAU_YAF_U
  • اسم فاعل (ISM_FAAIL)
  • اسم مفعول (ISM_MAFUUL)
  • اسم مكان/زمان/آلة
  • مصدر
  • جمع تكسير (تشخيص أولي)
  • صيغة مبالغة

المبادئ:
  • derivation_engine يُولِّد اسم الفاعل (كَارِم) لا الصفة المشبهة (كَرِيم)
  • هذا المحرك يسد الفجوة: يُولِّد الصفة المشبهة مباشرة من الجذر + الباب
  • كل قرار مرفق بدليل
"""
from __future__ import annotations
import re
from typing import Optional

from word_tree.word_identity_types import (
    DerivedFormType, MorphologicalIdentity, DerivationalIdentity,
    EvidenceRef, EvidenceSource
)


# ══════════════════════════════════════════════════════════════════════
# التطبيع الداخلي
# ══════════════════════════════════════════════════════════════════════

_DIACRITICS = "ًٌٍَُِّْٕٓٔ"

def _strip(s: str) -> str:
    return "".join(c for c in s if c not in _DIACRITICS)

def _norm(s: str) -> str:
    s = _strip(s)
    s = re.sub(r'[أإآ]', 'ا', s)
    return s


# ══════════════════════════════════════════════════════════════════════
# أوزان الصفة المشبهة
# ══════════════════════════════════════════════════════════════════════
# الصفة المشبهة: صفة ثابتة مستمرة من فعل لازم.
# أشهر أوزانها:

# فَعِيل (FAIIL) — أكثر الأوزان إنتاجية: كريم، جميل، شريف
_FAIIL = re.compile(r'^(.)(.)(.)ِيل$')   # مع تشكيل
_FAIIL_BARE = re.compile(r'^(.)(.)يل$')  # بدون (ثلاثة أحرف + يل)

# فَعَل / فَعِل (FAL/FIL) — ثلاثي قصير: حسن، بطل، نجس
_FAL_BARE = re.compile(r'^(.)(.)(.)$')    # ثلاثة أحرف بالضبط

# أَفْعَل (AFAL) — ألوان وعيوب: أحمر، أسود
_AFAL = re.compile(r'^[أا](.)ْ?(.)َ?([^\n])$')   # مع/بدون تشكيل
_AFAL_BARE = re.compile(r'^ا(.)(.)(.)$')

# فَعْلَان (FALAAN) — حالة عارضة: غضبان، ريان
_FALAAN = re.compile(r'^(.)(.)(.)ان$')

# فَعُول (FUUL) — شدة ودوام: صبور، غفور
_FUUL_BARE = re.compile(r'^(.)(.)(.)ول$')   # صبور، غفور، كفور

# مَفْعُول — اسم مفعول: مكتوب، محبوب
_MAFUUL_BARE = re.compile(r'^م(.)(.)(.)وب?$')   # مكتوب
_MAFUUL2 = re.compile(r'^م(.)ْ?(.)ُ?و?ل$')

# فَاعِل — اسم فاعل: كاتب، ذاهب
_FAAIL_BARE = re.compile(r'^(.)ا(.)ِ?(.)$')     # كاتب، ذاهب، شارب

# مَفْعَل/مَفْعِل — اسم مكان/زمان: مكتب، مجلس
_MAFAL_BARE = re.compile(r'^م(.)(.)(.)$')


# ══════════════════════════════════════════════════════════════════════
# الصفة المشبهة — التوليد والفحص
# ══════════════════════════════════════════════════════════════════════

# أوزان الصفة المشبهة الشائعة المولَّدة (بدون تشكيل)
def _gen_sifa_mushabbaha_forms(r1: str, r2: str, r3: str) -> list[tuple[str, str]]:
    """
    ولِّد أشكال الصفة المشبهة الممكنة للجذر (r1, r2, r3).
    أرجع: قائمة (الشكل, اسم الوزن)
    """
    forms = []
    # فَعِيل — الأشيع: كريم، حليم، رحيم، كفيل
    forms.append((f"{r1}{r2}ي{r3}", "فَعِيل"))
    # فَعَل — الثلاثي: حسن، بطل
    forms.append((f"{r1}{r2}{r3}", "فَعَل"))
    # فَعِل — كسر العين: نجس، فطن
    forms.append((f"{r1}{r2}{r3}", "فَعِل"))   # بدون تشكيل نفس الشكل
    # فَعُول — شدة: صبور، كفور
    forms.append((f"{r1}{r2}{r3}ول" if r3 != 'و' else f"{r1}{r2}ول", "فَعُول"))
    # أَفْعَل — ألوان: أحمر
    forms.append((f"ا{r1}{r2}{r3}", "أَفْعَل"))
    # فَعْلَان — حالة: غضبان
    forms.append((f"{r1}{r2}{r3}ان", "فَعْلَان"))
    return forms


def _sifa_matches_surface(surface_stripped: str, r1: str, r2: str, r3: str) -> Optional[str]:
    """
    هل surface تطابق إحدى صيغ الصفة المشبهة للجذر (r1,r2,r3)?
    أرجع اسم الوزن إن طابقت، وإلا None.
    """
    forms = _gen_sifa_mushabbaha_forms(r1, r2, r3)
    for form, wazn_name in forms:
        if surface_stripped == form:
            return wazn_name
    return None


# ══════════════════════════════════════════════════════════════════════
# تحليل الصيغة الاشتقاقية
# ══════════════════════════════════════════════════════════════════════

def analyze_derived_form(
    surface: str,
    resolved_root: Optional[str],
    root_baab: Optional[str],          # "FAU_YAF_U" | "FAA_YAF_U" | ...
    fau_yaf_u_roots: Optional[set[str]] = None,
) -> tuple[DerivedFormType, list[EvidenceRef]]:
    """
    حدد صيغة الكلمة الاشتقاقية.

    المدخلات:
        surface          — الكلمة السطحية
        resolved_root    — الجذر المحسوم (قد يكون None)
        root_baab        — الباب الصرفي من audited_roots.csv (قد يكون None)
        fau_yaf_u_roots  — مجموعة الجذور ذات الباب FAU_YAF_U (من CSV)

    المخرج:
        (DerivedFormType, evidence_list)
    """
    evidence: list[EvidenceRef] = []
    stripped = _strip(surface)
    normed   = _norm(surface)

    # ── 0. الكلمة هي الجذر نفسه (MUJARRAD) — الأولوية القصوى ─────────
    # يجب فحص هذا قبل الصفة المشبهة لأن الجذور الثلاثية قد تطابق أوزانها
    if resolved_root and normed == _norm(resolved_root):
        evidence.append(EvidenceRef(
            source=EvidenceSource.PATTERN_MATCH,
            detail=f"'{stripped}' تطابق الجذر نفسه",
            value="MUJARRAD",
            weight=1.0,
        ))
        return DerivedFormType.MUJARRAD, evidence

    # ── 1. صفة مشبهة (الأولوية) ────────────────────────────────────
    # الدليل الأقوى: الجذر + الباب FAU_YAF_U + مطابقة الوزن
    # شرط: الكلمة السطحية أطول من الجذر (فَعِيل=4 من جذر=3)
    if resolved_root and len(resolved_root) >= 3:
        r1, r2, r3 = list(resolved_root)[0], list(resolved_root)[1], list(resolved_root)[2]
        # الصفة المشبهة تزيد عن الجذر بحرف على الأقل (أو تساويه لكن بشكل مختلف)
        # استثناء: فَعَل (حسن=3 حروف = جذر) — نتحقق أنه ليس MUJARRAD أولاً (تم أعلاه)
        matched_wazn = _sifa_matches_surface(normed, r1, r2, r3)

        if matched_wazn:
            is_fau = (
                root_baab == "FAU_YAF_U"
                or (fau_yaf_u_roots is not None and resolved_root in fau_yaf_u_roots)
            )
            if is_fau:
                evidence.append(EvidenceRef(
                    source=EvidenceSource.AUDITED_ROOTS_CSV,
                    detail=f"جذر {resolved_root} ذو باب FAU_YAF_U (ضم ضم) في audited_roots.csv",
                    value=f"وزن:{matched_wazn}",
                    weight=0.95,
                ))
                evidence.append(EvidenceRef(
                    source=EvidenceSource.PATTERN_MATCH,
                    detail=f"السطح '{stripped}' يطابق وزن {matched_wazn} للجذر {resolved_root}",
                    value=matched_wazn,
                    weight=0.90,
                ))
                return DerivedFormType.SIFA_MUSHABBAHA, evidence
            elif len(normed) > len(_norm(resolved_root)):
                # مطابقة الوزن ولكن بدون FAU_YAF_U — نقبلها إذا الكلمة أطول من الجذر
                evidence.append(EvidenceRef(
                    source=EvidenceSource.PATTERN_MATCH,
                    detail=(
                        f"السطح '{stripped}' يطابق وزن {matched_wazn} — "
                        f"باب الجذر {root_baab or 'غير معروف'} "
                        f"{'ليس' if not is_fau else 'هو'} FAU_YAF_U"
                    ),
                    value=f"SIFA_PROBABLE:{matched_wazn}",
                    weight=0.6,
                ))
                return DerivedFormType.SIFA_MUSHABBAHA, evidence

    # ── 2. اسم فاعل (فَاعِل) ────────────────────────────────────────
    # كاتب، شارب، ذاهب — حرف ألف في الموضع الثاني
    if len(normed) == 4 and normed[1] == 'ا':
        evidence.append(EvidenceRef(
            source=EvidenceSource.PATTERN_MATCH,
            detail=f"'{stripped}' على وزن فَاعِل (حرف ألف ثانياً في رباعي)",
            value="ISM_FAAIL",
            weight=0.85,
        ))
        return DerivedFormType.ISM_FAAIL, evidence

    # اسم فاعل مزيد: مُفاعِل، مُفَعِّل ...
    if normed.startswith('م') and len(normed) >= 5:
        # تحقق: مُكاتِب، مُعلِّم ...
        # هذا فحص بسيط — نُرجع MUSHTAQQ_OTHER لمزيد الدقة
        pass

    # ── 3. اسم مفعول (مَفْعُول) ─────────────────────────────────────
    if normed.startswith('م') and len(normed) >= 4:
        # مكتوب: م + ك + ت + و + ب
        # مطابقة: م + ر1 + (حرف وسيط) + و + ر3
        # أو: م + ر1 + ر2 + ول
        rest = normed[1:]
        if 'و' in rest:
            idx_w = rest.index('و')
            if idx_w == len(rest) - 2:   # الواو قبل الأخير: مَفعول
                evidence.append(EvidenceRef(
                    source=EvidenceSource.PATTERN_MATCH,
                    detail=f"'{stripped}' على وزن مَفْعُول (م...و...)",
                    value="ISM_MAFUUL",
                    weight=0.85,
                ))
                return DerivedFormType.ISM_MAFUUL, evidence

    # ── 4. اسم مكان / زمان (مَفْعَل / مَفْعِل) ───────────────────────
    if normed.startswith('م') and 4 <= len(normed) <= 6:
        evidence.append(EvidenceRef(
            source=EvidenceSource.PATTERN_MATCH,
            detail=f"'{stripped}' يبدأ بـ م — محتمل اسم مكان/زمان",
            value="ISM_MAKAN_OR_ZAMAN",
            weight=0.55,
        ))
        # لا نُرجع مكان/زمان بدون تأكيد إضافي — نُرجع MUSHTAQQ_OTHER
        # (يحتاج سياق صرفي أعمق)
        return DerivedFormType.MUSHTAQQ_OTHER, evidence

    # ── 5. مصدر (masdar): تُعرَف بالكسرة أو بـ (فِعَال، تَفْعِيل...) ─
    # أوزان شائعة: كتابة، رسالة، سفر، علم
    # فحص بسيط — المصدر يحتاج الجذر + الباب لتأكيده
    if (normed.endswith('ة') or normed.endswith('ه')) and len(normed) >= 4:
        if resolved_root and normed.startswith(list(resolved_root)[0]):
            evidence.append(EvidenceRef(
                source=EvidenceSource.PATTERN_MATCH,
                detail=f"'{stripped}' ينتهي بتاء التأنيث ويبدأ بحرف الجذر — محتمل مصدر",
                value="MASDAR_PROBABLE",
                weight=0.6,
            ))
            return DerivedFormType.MASDAR, evidence

    # ── 6. جمع تكسير (أوزان شائعة) ─────────────────────────────────
    # أوزان: أَفعال (أقلام، أرجل)، فُعُول (بيوت)
    # تنبيه: فِعَال مشترك بين الجمع (رجال) والمصدر (كتاب) — لا ندخله هنا
    _JAM_PATTERNS = [
        # أَفعال: يبدأ بـ أ/ا + 4 أو 5 أحرف وليس ميماً (ليس مكان/مصدر)
        (lambda n: n.startswith('ا') and 4 <= len(n) <= 6
                   and not n.startswith('ام'), "أَفعال"),
        # فُعُول: ينتهي بـ ول + 4 أحرف إجمالاً
        (lambda n: len(n) == 4 and n.endswith('ول') and n[0] not in 'ام', "فُعُول"),
        # فِعَال المجموع: 4 أحرف، الثالث ألف، ومعروف أن الجذر ≠ الكلمة
        # نستخدم فقط إذا كان الجذر مختلفاً عن أول 2 أحرف + ا + حرف
        (lambda n: (len(n) == 4 and n[2] == 'ا' and n[3] not in 'اوي'
                    and resolved_root is not None
                    and len(resolved_root) >= 2
                    # تأكيد: الكلمة ليست بداية م (مصدر) ولا ت (مصدر)
                    and n[0] not in 'مت'
                    # تأكيد إضافي: الجذر ≠ الكلمة
                    and n != _norm(resolved_root or '')),
         "فِعَال"),
    ]
    for pat_fn, wazn_name in _JAM_PATTERNS:
        try:
            if pat_fn(normed):
                evidence.append(EvidenceRef(
                    source=EvidenceSource.PATTERN_MATCH,
                    detail=f"'{stripped}' يطابق وزن الجمع {wazn_name}",
                    value=f"JAM_TAKSIR:{wazn_name}",
                    weight=0.6,
                ))
                return DerivedFormType.JAM_TAKSIR, evidence
        except Exception:
            pass

    # ── 7. غير محدد ──────────────────────────────────────────────────
    # §9: UNRESOLVED ref يجب أن يتضمن FIRST_MISSING_OWNER + FAILED_EVIDENCE
    evidence.append(EvidenceRef(
        source=EvidenceSource.UNRESOLVED,
        detail=f"لم يُعرَّف وزن '{stripped}' بشكل قاطع",
        value=(
            "FIRST_MISSING_OWNER=sifa_engine/derivation_engine (توسيع الأوزان)"
            f" | FAILED_EVIDENCE=لا وزن صرفي مطابق لـ '{stripped}'"
        ),
        weight=0.0,
    ))
    return DerivedFormType.UNKNOWN, evidence


# ══════════════════════════════════════════════════════════════════════
# الصيغة الصرفية الكاملة
# ══════════════════════════════════════════════════════════════════════

def build_morphological_identity(
    surface: str,
    derived_form: DerivedFormType,
    evidence: list[EvidenceRef],
) -> MorphologicalIdentity:
    """
    أنشئ MorphologicalIdentity من الصيغة الاشتقاقية.
    يُضيف الجنس والعدد حيثما يمكن استنتاجهما.
    """
    stripped = _strip(surface)
    gender = None
    number = None
    definiteness = None

    # تأنيث
    if stripped.endswith('ة') or stripped.endswith('ه') or stripped.endswith('ت'):
        gender = "مؤنث"
    elif stripped.endswith('ى') or stripped.endswith('اء'):
        gender = "مؤنث"
    else:
        gender = "مذكر"   # الأصل في الأسماء المجردة

    # عدد: مثنى
    if stripped.endswith('ان') or stripped.endswith('ين'):
        if not stripped.endswith('ون') and len(stripped) > 4:
            number = "مثنى"
    # جمع مذكر سالم
    elif stripped.endswith('ون') or stripped.endswith('ين'):
        number = "جمع"
        gender = "مذكر"
    # جمع مؤنث سالم
    elif stripped.endswith('ات'):
        number = "جمع"
        gender = "مؤنث"
    else:
        number = "مفرد"

    # تعريف
    if stripped.startswith('ال'):
        definiteness = "معرفة"
    else:
        definiteness = "نكرة"

    return MorphologicalIdentity(
        derived_form=derived_form,
        gender=gender,
        number=number,
        definiteness=definiteness,
        base_pattern=None,   # يمكن توليده لاحقاً
        evidence=evidence,
    )


# ══════════════════════════════════════════════════════════════════════
# الهوية الاشتقاقية الكاملة
# ══════════════════════════════════════════════════════════════════════

def build_derivational_identity(
    surface: str,
    resolved_root: Optional[str],
    root_baab: Optional[str],
    derived_form: DerivedFormType,
    form_evidence: list[EvidenceRef],
    fau_yaf_u_roots: Optional[set[str]] = None,
) -> DerivationalIdentity:
    """
    أنشئ DerivationalIdentity — تصف المسار الاشتقاقي بالكامل.
    """
    stripped = _strip(surface)
    normed = _norm(surface)

    derivation_path: list[str] = []
    generated_form: Optional[str] = None
    surface_matches = False
    confidence = 0.0

    if resolved_root:
        derivation_path.append(f"جذر:{resolved_root}")
        if root_baab:
            derivation_path.append(f"باب:{root_baab}")

    # §4: confidence contract — HEURISTIC_SCORE, not CALIBRATED_PROBABILITY
    confidence_kind  = "HEURISTIC_SCORE"
    confidence_basis = "UNCOMPUTED"

    if derived_form == DerivedFormType.SIFA_MUSHABBAHA:
        derivation_path.append("صيغة:صفة_مشبهة")
        confidence_basis = "PATTERN_MATCH_AND_BAAB_LOOKUP"
        if resolved_root and len(resolved_root) >= 3:
            r1, r2, r3 = list(resolved_root)[0], list(resolved_root)[1], list(resolved_root)[2]
            generated_form = f"{r1}{r2}ي{r3}"   # فَعِيل (الأشيع)
            surface_matches = (normed == generated_form or normed == f"{r1}{r2}{r3}ان"
                               or normed == f"{r1}{r2}{r3}ول")
            is_fau = (
                root_baab == "FAU_YAF_U"
                or (fau_yaf_u_roots is not None and resolved_root in fau_yaf_u_roots)
            )
            confidence = 0.92 if is_fau else 0.65

    elif derived_form == DerivedFormType.ISM_FAAIL:
        derivation_path.append("صيغة:اسم_فاعل")
        confidence_basis = "PATTERN_MATCH_AND_BAAB_LOOKUP"
        if resolved_root and len(resolved_root) >= 3:
            r1, r2, r3 = list(resolved_root)[0], list(resolved_root)[1], list(resolved_root)[2]
            generated_form = f"{r1}ا{r2}{r3}"
            surface_matches = (normed == generated_form)
            confidence = 0.80

    elif derived_form == DerivedFormType.ISM_MAFUUL:
        derivation_path.append("صيغة:اسم_مفعول")
        confidence_basis = "PATTERN_MATCH_AND_BAAB_LOOKUP"
        if resolved_root and len(resolved_root) >= 3:
            r1, r2, r3 = list(resolved_root)[0], list(resolved_root)[1], list(resolved_root)[2]
            generated_form = f"م{r1}{r2}و{r3}"
            surface_matches = (normed == generated_form or normed == f"م{r1}{r2}و{r3}ة")
            confidence = 0.82

    elif derived_form == DerivedFormType.MUJARRAD:
        derivation_path.append("صيغة:مجرد")
        confidence_basis = "STATIC_LIST"
        generated_form = resolved_root
        surface_matches = True
        confidence = 1.0

    else:
        confidence_basis = "UNCOMPUTED"
        confidence = 0.3

    return DerivationalIdentity(
        root=resolved_root,
        baab=root_baab,
        derivation_path=derivation_path,
        generated_form=generated_form,
        surface_matches=surface_matches,
        confidence=confidence,
        confidence_kind=confidence_kind,    # §4
        confidence_basis=confidence_basis,  # §4
        evidence=form_evidence,
    )
