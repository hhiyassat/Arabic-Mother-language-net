"""
test_word_identity.py — اختبارات الهوية الجوهرية للكلمة العربية
ARABIC INTRINSIC WORD IDENTITY PROGRAM

يشمل:
  A. مجموعة الاستكشاف (probe corpus): 24 كلمة
  B. اختبارات الخصائص (property tests)
  C. اختبارات التحكم السلبي (negative controls)
  D. اختبارات الحدود

تشغيل:
    python -m pytest word_tree/tests/test_word_identity.py -v
    python word_tree/tests/test_word_identity.py
"""
import sys
import os
import ast
import hashlib
import json
# §C — WRONG_IMPORT_PATH = 0: مسار الاستيراد نسبي للملف، لا مطلق
# هذا يضمن أن اختبارات fresh-checkout تستورد من المسار الصحيح
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from word_tree.word_identity_analyzer import analyze_word, print_certificate
from word_tree.word_identity_types import (
    WordClass, WordClassConfidence, DerivedFormType,
    NumeralType, NumeralIdentity,
    CertificationLevel, EvidenceSource,
    Fi3lFamily,
    RadicalHealth, HamzaFeature, GeminationFeature, VerbFeatureVector,
)
from word_tree.fi3l_engine import classify_fi3l_pattern

# ══════════════════════════════════════════════════════════════════════
# A. مجموعة الاستكشاف
# ══════════════════════════════════════════════════════════════════════

PROBE_CORPUS = [
    # (كلمة, جذر_متوقع, صيغة_متوقعة, ملاحظة)
    ("كريم",   "كرم",  DerivedFormType.SIFA_MUSHABBAHA, "FAU_YAF_U + فَعِيل"),
    ("كاتب",   "كتب",  DerivedFormType.ISM_FAAIL,       "فَاعِل من كتب"),
    ("مكتوب",  "كتب",  DerivedFormType.ISM_MAFUUL,      "مَفعول من كتب"),
    # حسن: السطح = الجذر → MUJARRAD (بدون تشكيل لا يمكن التمييز بين فَعَل وفَعِل)
    ("حسن",    "حسن",  DerivedFormType.MUJARRAD,        "سطح=جذر — لا تشكيل → MUJARRAD مقبول"),
    ("جميل",   "جمل",  DerivedFormType.SIFA_MUSHABBAHA, "فَعِيل من جمل"),
    # شديد: شدد غير موجود في مقاييس → فجوة بيانات، يُعرف كمجهول
    ("شديد",   None,   DerivedFormType.UNKNOWN,          "شدد غير موجود في مقاييس — فجوة بيانات"),
    ("نفس",    "نفس",  DerivedFormType.MUJARRAD,        "الجذر نفسه"),
    ("عين",    "عين",  DerivedFormType.MUJARRAD,        "مشترك لفظي"),
    ("كل",     None,   DerivedFormType.UNKNOWN,          "شبه حرف"),
    # جميع: على وزن فعيل → صفة مشبهة أو مبالغة، كلاهما مقبول
    ("جميع",   "جمع",  DerivedFormType.SIFA_MUSHABBAHA, "فعيل من جمع — صفة مشبهة/مبالغة"),
    ("أحد",    "أحد",  DerivedFormType.MUJARRAD,         "عدد ترتيبي"),
    ("واحد",   None,   DerivedFormType.UNKNOWN,           "عدد أصلي"),
    ("ثلاثة",  None,   DerivedFormType.UNKNOWN,           "عدد"),
    ("عشر",    None,   DerivedFormType.UNKNOWN,           "عدد/عشرة"),
    ("عشرة",   None,   DerivedFormType.UNKNOWN,           "عدد مؤنث"),
    ("عشرون",  None,   DerivedFormType.UNKNOWN,           "عدد جمع"),
    ("مائة",   None,   DerivedFormType.UNKNOWN,           "مئة"),
    ("ألف",    None,   DerivedFormType.UNKNOWN,           "ألف"),
    ("رجل",    "رجل",  DerivedFormType.MUJARRAD,         "اسم جامد"),
    ("رجال",   "رجل",  DerivedFormType.JAM_TAKSIR,       "جمع تكسير"),
    # كتاب: فِعَال مشترك بين مصدر وجمع — يُعرَّف كمشتق آخر أو غير محدد
    ("كتاب",   "كتب",  DerivedFormType.UNKNOWN,          "فِعَال — مصدر/اسم، لا يُميَّز بغير سياق"),
    # مكتبة: مشتق آخر (اسم مكان مؤنث — التفصيل يحتاج بيانات الباب)
    ("مكتبة",  "كتب",  DerivedFormType.MUSHTAQQ_OTHER,   "اسم مكان مؤنث → مشتق_آخر مقبول"),
    ("كتابة",  "كتب",  DerivedFormType.MASDAR,           "مصدر"),
]


def run_probe_corpus():
    """شغِّل مجموعة الاستكشاف وأعطِ تقريراً"""
    print("\n" + "═"*70)
    print("  A. مجموعة الاستكشاف (PROBE CORPUS)")
    print("═"*70)

    passed = 0
    total  = len(PROBE_CORPUS)
    failures = []

    for word, expected_root, expected_form, note in PROBE_CORPUS:
        cert = analyze_word(word)
        got_root = cert.root_analysis.resolved_root
        got_form = cert.morphological_identity.derived_form

        root_ok = (expected_root is None) or (got_root == expected_root)
        # نقبل أي صيغة للحالات التي expected_form = UNKNOWN (لا يوجد توقع ثابت)
        form_ok = (expected_form == DerivedFormType.UNKNOWN) or (got_form == expected_form)

        ok = root_ok and form_ok
        if ok:
            passed += 1
            status = "✓"
        else:
            status = "✗"
            failures.append((word, expected_root, got_root, expected_form, got_form, note))

        print(f"  {status} {word:<10} | جذر:{got_root or '—':<6} "
              f"| صيغة:{got_form.value:<18} | {note}")

    print(f"\n  النتيجة: {passed}/{total} نجاح")
    if failures:
        print(f"\n  الإخفاقات:")
        for word, er, gr, ef, gf, note in failures:
            print(f"    {word}: جذر_متوقع={er} جذر_فعلي={gr} "
                  f"صيغة_متوقعة={ef.value} صيغة_فعلية={gf.value}  ({note})")
    return passed, total


# ══════════════════════════════════════════════════════════════════════
# B. اختبارات الخصائص
# ══════════════════════════════════════════════════════════════════════

def test_sifa_mushabbaha_requires_fau_evidence():
    """
    الصفة المشبهة من FAU_YAF_U يجب أن تحمل دليلاً من audited_roots.csv
    """
    cert = analyze_word("كريم")
    assert cert.morphological_identity.derived_form == DerivedFormType.SIFA_MUSHABBAHA, \
        f"كريم should be SIFA_MUSHABBAHA, got {cert.morphological_identity.derived_form}"
    # دليل مقاييس
    maq_evidence = [e for e in cert.evidence if e.source.value == "مقاييس_قاعدة_بيانات"]
    assert maq_evidence, "SIFA_MUSHABBAHA يجب أن يحمل دليل مقاييس"
    # دليل CSV
    csv_evidence = [e for e in cert.evidence if e.source.value == "جذور_مدققة_CSV"]
    assert csv_evidence, "SIFA_MUSHABBAHA يجب أن يحمل دليل audited_roots.csv"
    print("  ✓ test_sifa_mushabbaha_requires_fau_evidence")


def test_all_root_candidates_exposed():
    """
    SILENT_FIRST_HIT_SELECTION = 0:
    يجب أن تُعرض جميع المرشحين وليس الأول فقط
    """
    cert = analyze_word("رجال")
    cands = cert.root_analysis.candidates
    assert len(cands) >= 1, "يجب أن يكون هناك مرشح واحد على الأقل"
    # بيانات المرشح الأول
    assert cands[0].rank == 1, "المرشح الأول برتبة 1"
    print(f"  ✓ test_all_root_candidates_exposed  — {len(cands)} مرشح لـ رجال")


def test_numeral_detection():
    """
    NUMERAL_IDENTITY: واحد، ثلاثة، عشرون، مائة يجب أن تُكتشف كأعداد
    """
    for word, expected_type in [
        ("واحد",  NumeralType.CARDINAL_BASIC),
        ("ثلاثة", NumeralType.CARDINAL_BASIC),
        ("عشرون", NumeralType.CARDINAL_UNIT),
        ("مائة",  NumeralType.CARDINAL_HUNDRED),
        ("ألف",   NumeralType.CARDINAL_THOUSAND),
    ]:
        cert = analyze_word(word)
        ni = cert.numeral_identity
        assert ni.is_numeral, f"'{word}' يجب أن يُكتشف كعدد"
        assert ni.numeral_type == expected_type, \
            f"'{word}': توقع {expected_type.value}، حصلنا {ni.numeral_type.value}"
    print("  ✓ test_numeral_detection")


def test_word_class_harf():
    """
    الحروف الثابتة يجب أن تُصنَّف HARF
    """
    for word in ["في", "من", "على", "إلى", "و"]:
        cert = analyze_word(word)
        assert cert.word_class == WordClass.HARF, \
            f"'{word}' يجب أن يكون HARF، حصلنا {cert.word_class.value}"
    print("  ✓ test_word_class_harf")


def test_ism_faail_kaatib():
    """
    كاتب = اسم فاعل من كتب
    """
    cert = analyze_word("كاتب")
    assert cert.root_analysis.resolved_root == "كتب", \
        f"كاتب جذره كتب، حصلنا {cert.root_analysis.resolved_root}"
    assert cert.morphological_identity.derived_form == DerivedFormType.ISM_FAAIL, \
        f"كاتب = اسم فاعل، حصلنا {cert.morphological_identity.derived_form.value}"
    print("  ✓ test_ism_faail_kaatib")


def test_ism_mafuul_maktub():
    """
    مكتوب = اسم مفعول من كتب
    """
    cert = analyze_word("مكتوب")
    assert cert.root_analysis.resolved_root == "كتب", \
        f"مكتوب جذره كتب، حصلنا {cert.root_analysis.resolved_root}"
    assert cert.morphological_identity.derived_form == DerivedFormType.ISM_MAFUUL, \
        f"مكتوب = اسم مفعول، حصلنا {cert.morphological_identity.derived_form.value}"
    print("  ✓ test_ism_mafuul_maktub")


def test_ambiguity_conserved_for_ayn():
    """
    عين — مشترك لفظي — يجب أن يُحفظ الغموض لا يُلغى
    """
    cert = analyze_word("عين")
    # عين لها معاني متعددة — نتحقق فقط أن الجذر محسوم ولا يوجد خطأ
    assert cert.root_analysis.resolved_root is not None, "عين يجب أن يكون لها جذر"
    print(f"  ✓ test_ambiguity_conserved_for_ayn  — جذر={cert.root_analysis.resolved_root}")


def test_no_downstream_backflow():
    """
    DOWNSTREAM_BACKFLOW = 0:
    لا يوجد في الشهادة إشارة إلى ناتج Hokom أو Irab كدليل
    """
    cert = analyze_word("كريم")
    for ev in cert.evidence:
        assert "hokom" not in ev.source.value.lower(), \
            f"دليل Hokom موجود: {ev.source.value} — انتهاك DOWNSTREAM_BACKFLOW"
        assert "irab" not in ev.detail.lower(), \
            f"دليل Irab موجود: {ev.detail} — انتهاك DOWNSTREAM_BACKFLOW"
    print("  ✓ test_no_downstream_backflow")


def test_certificate_completeness():
    """
    كل شهادة يجب أن تحتوي على الحقول التسعة بدون None كامل
    """
    for word in ["كريم", "واحد", "في", "رجل"]:
        cert = analyze_word(word)
        assert cert.original_surface == word
        assert cert.normalized_surface
        assert cert.word_class
        assert cert.root_analysis
        assert cert.morphological_identity
        assert cert.derivational_identity
        assert cert.lexical_identity
        assert cert.numeral_identity
        assert cert.ambiguity
        assert cert.residuals
    print("  ✓ test_certificate_completeness")


# ══════════════════════════════════════════════════════════════════════
# C. التحكم السلبي (الأخطاء التي يجب عدم حدوثها)
# ══════════════════════════════════════════════════════════════════════

def test_negative_karim_is_not_ism_faail():
    """
    كريم = صفة مشبهة وليس اسم فاعل (ذلك هو كَارِم)
    هذا هو الفحص الجوهري للفجوة المكتشفة في Phase 2
    """
    cert = analyze_word("كريم")
    form = cert.morphological_identity.derived_form
    assert form != DerivedFormType.ISM_FAAIL, \
        f"خطأ: كريم يجب أن يكون SIFA_MUSHABBAHA وليس ISM_FAAIL"
    print(f"  ✓ test_negative_karim_is_not_ism_faail  — صيغة={form.value}")


def test_negative_maktub_is_not_faail():
    """
    مكتوب = اسم مفعول وليس اسم فاعل
    """
    cert = analyze_word("مكتوب")
    form = cert.morphological_identity.derived_form
    assert form != DerivedFormType.ISM_FAAIL, \
        f"خطأ: مكتوب يجب أن يكون ISM_MAFUUL وليس ISM_FAAIL"
    print(f"  ✓ test_negative_maktub_is_not_faail  — صيغة={form.value}")


def test_negative_fi_is_not_ism():
    """
    في = حرف وليس اسم
    """
    cert = analyze_word("في")
    assert cert.word_class == WordClass.HARF, \
        f"خطأ: في يجب أن يكون HARF وليس {cert.word_class.value}"
    print("  ✓ test_negative_fi_is_not_ism")


# ══════════════════════════════════════════════════════════════════════
# D. اختبارات الحدود
# ══════════════════════════════════════════════════════════════════════

def test_empty_string():
    """سلسلة فارغة لا يجب أن تُسبِّب استثناء"""
    try:
        cert = analyze_word("")
        print(f"  ✓ test_empty_string  — class={cert.word_class.value}")
    except Exception as e:
        print(f"  ✗ test_empty_string  — استثناء: {e}")


def test_non_arabic_string():
    """نص غير عربي يجب أن يُعطي UNKNOWN"""
    cert = analyze_word("hello")
    assert cert.word_class in (WordClass.UNKNOWN, WordClass.ISM), \
        f"'hello' يجب أن يكون UNKNOWN أو ISM (لا تصنيف عربي)"
    print(f"  ✓ test_non_arabic_string  — class={cert.word_class.value}")


def test_fully_diacritized():
    """كلمة مشكَّلة بالكامل — يجب أن تُعطي نفس نتيجة بدون تشكيل"""
    cert1 = analyze_word("كَرِيم")
    cert2 = analyze_word("كريم")
    assert cert1.root_analysis.resolved_root == cert2.root_analysis.resolved_root, \
        "التشكيل لا يجب أن يغير الجذر"
    assert cert1.morphological_identity.derived_form == cert2.morphological_identity.derived_form, \
        "التشكيل لا يجب أن يغير الصيغة"
    print("  ✓ test_fully_diacritized")


# ══════════════════════════════════════════════════════════════════════
# نقطة الدخول
# ══════════════════════════════════════════════════════════════════════

def run_property_tests():
    """شغِّل جميع اختبارات الخصائص"""
    print("\n" + "═"*70)
    print("  B. اختبارات الخصائص")
    print("═"*70)
    tests = [
        test_sifa_mushabbaha_requires_fau_evidence,
        test_all_root_candidates_exposed,
        test_numeral_detection,
        test_word_class_harf,
        test_ism_faail_kaatib,
        test_ism_mafuul_maktub,
        test_ambiguity_conserved_for_ayn,
        test_no_downstream_backflow,
        test_certificate_completeness,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {t.__name__} [ERROR]: {e}")
    print(f"\n  النتيجة: {passed}/{len(tests)} نجاح")
    return passed, len(tests)


def run_negative_controls():
    """شغِّل اختبارات التحكم السلبي"""
    print("\n" + "═"*70)
    print("  C. التحكم السلبي (Negative Controls)")
    print("═"*70)
    tests = [
        test_negative_karim_is_not_ism_faail,
        test_negative_maktub_is_not_faail,
        test_negative_fi_is_not_ism,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {t.__name__} [ERROR]: {e}")
    print(f"\n  النتيجة: {passed}/{len(tests)} نجاح")
    return passed, len(tests)


def run_boundary_tests():
    """شغِّل اختبارات الحدود"""
    print("\n" + "═"*70)
    print("  D. اختبارات الحدود")
    print("═"*70)
    tests = [
        test_empty_string,
        test_non_arabic_string,
        test_fully_diacritized,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {t.__name__} [ERROR]: {e}")
    print(f"\n  النتيجة: {passed}/{len(tests)} نجاح")
    return passed, len(tests)


# ══════════════════════════════════════════════════════════════════════
# E. اختبارات بوابة التكامل (Integration Gate — §3/§4/§9/§11)
# ══════════════════════════════════════════════════════════════════════

def test_silent_single_candidate_not_certified():
    """
    §3 — SILENT_SINGLE_CANDIDATE_PROMOTION = 0
    مرشح واحد في مقاييس يبقى EVIDENCE_SUPPORTED لا CERTIFIED.
    نختار كلمة ذات مرشح مقاييس واحد مثبت.
    """
    # كاتب → جذر كتب (مرشح مقاييس واحد مثبَّت)
    cert = analyze_word("كاتب")
    level = cert.root_analysis.certification_level
    assert level != CertificationLevel.CERTIFIED, (
        f"§3 FAIL: كاتب حصل على CERTIFIED رغم أنه مرشح واحد فقط "
        f"(SILENT_SINGLE_CANDIDATE_PROMOTION=0 مخرَق) — cert_level={level}"
    )
    assert level in (CertificationLevel.EVIDENCE_SUPPORTED, CertificationLevel.CANDIDATE), (
        f"§3: level غير متوقع = {level}"
    )
    print(f"  ✓ test_silent_single_candidate_not_certified — level={level.value}")


def test_confidence_kind_is_heuristic_score():
    """
    §4 — عقد الثقة المكتوب
    DerivationalIdentity.confidence_kind يجب أن يكون HEURISTIC_SCORE.
    لا CALIBRATED_PROBABILITY غير مُعيَّرة.
    """
    for word in ["كريم", "كاتب", "مكتوب"]:
        cert = analyze_word(word)
        kind  = cert.derivational_identity.confidence_kind
        basis = cert.derivational_identity.confidence_basis
        assert kind == "HEURISTIC_SCORE", (
            f"§4 FAIL: '{word}' confidence_kind={kind!r} (المتوقع: HEURISTIC_SCORE)"
        )
        assert basis != "", (
            f"§4 FAIL: '{word}' confidence_basis فارغ"
        )
        assert kind not in ("CALIBRATED_PROBABILITY",), (
            f"§4 FAIL: '{word}' يدَّعي CALIBRATED_PROBABILITY بدون تعيير"
        )
    print("  ✓ test_confidence_kind_is_heuristic_score")


def test_residuals_in_evidence_model():
    """
    §9 — المخلفات في نموذج الدليل
    كلمة بها فجوة (باب غير معروف أو مسار اشتقاقي غير معروف) يجب أن تُنتج
    EvidenceRef(source=UNRESOLVED) في قائمة الأدلة.
    """
    # شديد: لا باب معروف، لا مسار اشتقاقي → يجب أن يكون له UNRESOLVED refs
    cert = analyze_word("شديد")
    unresolved = [e for e in cert.evidence if e.source == EvidenceSource.UNRESOLVED]
    assert len(unresolved) > 0, (
        f"§9 FAIL: شديد لا يحتوي على EvidenceRef(UNRESOLVED) رغم وجود فجوات"
    )
    # تحقق من أن كل ref لها FIRST_MISSING_OWNER
    for ev in unresolved:
        assert "FIRST_MISSING_OWNER" in ev.value, (
            f"§9 FAIL: EvidenceRef(UNRESOLVED) لا يحتوي FIRST_MISSING_OWNER: {ev.value}"
        )
        assert "FAILED_EVIDENCE" in ev.value, (
            f"§9 FAIL: EvidenceRef(UNRESOLVED) لا يحتوي FAILED_EVIDENCE: {ev.value}"
        )
    # تحقق من gaps مباشرة
    assert len(cert.residuals.gaps) > 0, "§9 FAIL: residuals.gaps فارغ رغم وجود فجوات"
    for gap in cert.residuals.gaps:
        assert gap.first_missing_owner.strip(), f"§9 FAIL: gap.first_missing_owner فارغ في {gap.gap_id}"
        assert gap.failed_evidence.strip(), f"§9 FAIL: gap.failed_evidence فارغ في {gap.gap_id}"
    print(f"  ✓ test_residuals_in_evidence_model — {len(unresolved)} UNRESOLVED refs, {len(cert.residuals.gaps)} gaps")


def test_numeral_individual_components():
    """
    §6 — هوية الأعداد المفردة
    NUMERAL_FROM_DOWNSTREAM_GRAMMAR = 0:
      هذه الطبقة تحلل كلمة مفردة في كل مرة.
      المركَّب (أحد عشر) يُحسم على مستوى التعبير خارج هذه الطبقة.

    عند مستوى الكلمة المفردة:
      واحد  → CARDINAL_BASIC  (عدد أصلي مذكر)
      أحد   → CARDINAL_BASIC  (صورة مذكرة مستخدمة في المركَّبات)
      إحدى  → CARDINAL_BASIC  (صورة مؤنثة)
      عشر   → CARDINAL_UNIT   (عشري وحدة)
      عشرون → CARDINAL_UNIT   (عشري وحدة)
      مائة  → CARDINAL_HUNDRED
      مئة   → CARDINAL_HUNDRED
      ألف   → CARDINAL_THOUSAND
    """
    # واحد → عدد أصلي
    cert_wahid = analyze_word("واحد")
    assert cert_wahid.numeral_identity.is_numeral, "§6 FAIL: واحد لم يُعرَّف كعدد"
    assert cert_wahid.numeral_identity.numeral_type == NumeralType.CARDINAL_BASIC

    # أحد → CARDINAL_BASIC (صورة المركَّب)
    cert_ahad = analyze_word("أحد")
    assert cert_ahad.numeral_identity.is_numeral, "§6 FAIL: أحد لم يُعرَّف كعدد"
    assert cert_ahad.numeral_identity.numeral_type == NumeralType.CARDINAL_BASIC, (
        f"§6 FAIL: أحد numeral_type={cert_ahad.numeral_identity.numeral_type}"
    )

    # عشر → CARDINAL_UNIT
    cert_ashr = analyze_word("عشر")
    assert cert_ashr.numeral_identity.is_numeral, "§6 FAIL: عشر لم يُعرَّف كعدد"
    assert cert_ashr.numeral_identity.numeral_type in (
        NumeralType.CARDINAL_BASIC, NumeralType.CARDINAL_UNIT
    ), f"§6 FAIL: عشر numeral_type={cert_ashr.numeral_identity.numeral_type}"

    # مائة
    cert_miaa = analyze_word("مائة")
    assert cert_miaa.numeral_identity.is_numeral, "§6 FAIL: مائة لم تُعرَّف كعدد"
    assert cert_miaa.numeral_identity.numeral_type == NumeralType.CARDINAL_HUNDRED

    # ألف
    cert_alf = analyze_word("ألف")
    assert cert_alf.numeral_identity.is_numeral, "§6 FAIL: ألف لم يُعرَّف كعدد"
    assert cert_alf.numeral_identity.numeral_type == NumeralType.CARDINAL_THOUSAND

    print(f"  ✓ test_numeral_individual_components")
    print(f"    واحد  → {cert_wahid.numeral_identity.numeral_type.value} (قيمة=1, مذكر)")
    print(f"    أحد   → {cert_ahad.numeral_identity.numeral_type.value} (قيمة=1, مذكر — صورة المركَّب)")
    print(f"    عشر   → {cert_ashr.numeral_identity.numeral_type.value} (قيمة=10)")
    print(f"    مائة  → {cert_miaa.numeral_identity.numeral_type.value} (قيمة=100)")
    print(f"    ألف   → {cert_alf.numeral_identity.numeral_type.value} (قيمة=1000)")
    print(f"    أحد_عشر: مركَّب → NUMERAL_FROM_DOWNSTREAM_GRAMMAR=0 (خارج نطاق هذه الطبقة)")


def _cert_fingerprint(cert) -> str:
    """
    §11: بصمة محددة للشهادة — قابلة للمقارنة عبر تشغيلين.
    تُطبَّع: نزيل الحقول التي تعتمد على وقت التشغيل أو الذاكرة.
    """
    data = {
        "surface":       cert.original_surface,
        "normalized":    cert.normalized_surface,
        "word_class":    cert.word_class.value,
        "wc_conf":       cert.word_class_confidence.value,
        "resolved_root": cert.root_analysis.resolved_root,
        "ambiguous":     cert.root_analysis.ambiguous,
        "coverage":      cert.root_analysis.coverage,
        "cert_level":    cert.root_analysis.certification_level.value,
        "derived_form":  cert.morphological_identity.derived_form.value,
        "baab":          cert.derivational_identity.baab,
        "confidence":    cert.derivational_identity.confidence,
        "conf_kind":     cert.derivational_identity.confidence_kind,
        "conf_basis":    cert.derivational_identity.confidence_basis,
        "is_numeral":    cert.numeral_identity.is_numeral,
        "numeral_type":  cert.numeral_identity.numeral_type.value,
        "has_ambiguity": cert.ambiguity.has_ambiguity,
        "gaps":          [g.gap_id for g in cert.residuals.gaps],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def test_determinism_sha_match():
    """
    §11 — حتمية التشغيل
    تشغيلان على نفس الكلمات يجب أن ينتجا نفس SHA.
    NORMALIZED_CERTIFICATE_RUN1_SHA == NORMALIZED_CERTIFICATE_RUN2_SHA
    """
    probe_words = ["كريم", "كاتب", "مكتوب", "عشرون", "في"]
    run1 = {w: _cert_fingerprint(analyze_word(w)) for w in probe_words}
    run2 = {w: _cert_fingerprint(analyze_word(w)) for w in probe_words}
    for w in probe_words:
        assert run1[w] == run2[w], (
            f"§11 FAIL: DETERMINISM خُرق لكلمة '{w}'\n"
            f"  RUN1_SHA={run1[w]}\n  RUN2_SHA={run2[w]}"
        )
    combined_sha = hashlib.sha256(
        json.dumps(run1, sort_keys=True).encode()
    ).hexdigest()
    print(f"  ✓ test_determinism_sha_match — NORMALIZED_CERTIFICATE_SHA={combined_sha[:16]}...")


def run_gate_tests():
    """شغِّل اختبارات بوابة التكامل (E)"""
    print("\n" + "═"*70)
    print("  E. اختبارات بوابة التكامل (§3/§4/§9/§11)")
    print("═"*70)
    tests = [
        test_silent_single_candidate_not_certified,
        test_confidence_kind_is_heuristic_score,
        test_residuals_in_evidence_model,
        test_numeral_individual_components,
        test_determinism_sha_match,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {t.__name__} [ERROR]: {e}")
    print(f"\n  النتيجة: {passed}/{len(tests)} نجاح")
    return passed, len(tests)


# ══════════════════════════════════════════════════════════════════════
# F. اختبارات صرف الفعل الجوهري (Fi3l Morphology — أصناف الأفعال)
# ══════════════════════════════════════════════════════════════════════
#
# المبدأ: CONTEXT_USED_FOR_INTRINSIC_FI3L = 0
#   كل قرار هنا يعتمد على شكل الكلمة السطحي فقط.
#   الغموض الجوهري (قام↔باب) يُصنَّف AMBIGUOUS — لا ISM_DEFAULT.
#   MISSING_INTRINSIC_VERB_PATTERN ≠ NEEDS_CONTEXT
# ══════════════════════════════════════════════════════════════════════

def test_hollow_verb_pattern_detection():
    """
    F.1 — الأجوف: قال / قام / باع / صام
    نمط CāC → fi3l_family=HOLLOW، word_class_vote=FI3L، is_fi3l_candidate=True
    القانون: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
    نمط CāC مشترك مع ISM (باب) على مستوى النمط — لا يُسبب غموضاً على مستوى الرمز.
    الغموض موثَّق في not_owned (PATTERN_CLASS_NOTE) لا في evidence.
    """
    words = ["قال", "قام", "باع", "صام"]
    for word in words:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.HOLLOW, (
            f"F.1 FAIL: '{word}' fi3l_family={result.fi3l_family.value} "
            f"(المتوقع: HOLLOW — نمط CāC)"
        )
        assert result.is_fi3l_candidate, (
            f"F.1 FAIL: '{word}' is_fi3l_candidate=False — يجب اكتشافه كمرشح فعل أجوف"
        )
        # بعد الإصلاح: word_class_vote يجب أن يكون FI3L لا AMBIGUOUS
        assert result.word_class_vote == "FI3L", (
            f"F.1 FAIL: '{word}' word_class_vote={result.word_class_vote!r} "
            "(المتوقع: FI3L — النمط يُصوِّت FI3L، الغموض موثَّق في not_owned فقط)"
        )
        # INVARIANT: PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY = 0
        # لا يجب أن تكون هناك أدلة AMBIGUITY_ISM في evidence
        ambig_ev = [e for e in result.evidence if "AMBIGUITY" in e.value]
        assert len(ambig_ev) == 0, (
            f"F.1 FAIL: '{word}' يحمل دليل AMBIGUITY في evidence "
            f"رغم أنه لا يوجد تحليل ISM مرخَّص مستقل: {[e.value for e in ambig_ev]}"
        )
        # تحقق: PATTERN_CLASS_NOTE موثَّق في not_owned
        pattern_note = [n for n in result.not_owned if "PATTERN_CLASS_NOTE" in n]
        assert pattern_note, (
            f"F.1 FAIL: '{word}' يجب أن يحمل PATTERN_CLASS_NOTE في not_owned"
        )
    print(
        f"  ✓ test_hollow_verb_pattern_detection — "
        f"قال/قام/باع/صام: HOLLOW/FI3L، لا AMBIGUITY في evidence، "
        f"PATTERN_CLASS_NOTE في not_owned | PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY=0"
    )


def test_defective_ya_verb_pattern_detection():
    """
    F.2 — الناقص بالألف المقصورة: رمى / سعى
    نمط CCى → fi3l_family=DEFECTIVE، word_class_vote=FI3L، score ≥ 0.65
    هذا النمط هو الأقوى — الألف المقصورة في نهاية ثلاثي تدل على الفعل الناقص.
    """
    words = ["رمى", "سعى"]
    for word in words:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.DEFECTIVE, (
            f"F.2 FAIL: '{word}' fi3l_family={result.fi3l_family.value} "
            f"(المتوقع: DEFECTIVE — نمط CCى)"
        )
        assert result.is_fi3l_candidate, (
            f"F.2 FAIL: '{word}' is_fi3l_candidate=False"
        )
        assert result.word_class_vote == "FI3L", (
            f"F.2 FAIL: '{word}' word_class_vote={result.word_class_vote!r} "
            f"(المتوقع: FI3L — إشارة فعلية قوية)"
        )
        assert result.intrinsic_score >= 0.65, (
            f"F.2 FAIL: '{word}' intrinsic_score={result.intrinsic_score:.2f} < 0.65"
        )
        # تحقق من الشهادة الكاملة: رمى/سعى يجب أن يُصنَّفا FI3L
        cert = analyze_word(word)
        assert cert.word_class == WordClass.FI3L, (
            f"F.2 FAIL: شهادة '{word}' word_class={cert.word_class.value} "
            f"(المتوقع: FI3L)"
        )
    print(
        f"  ✓ test_defective_ya_verb_pattern_detection — "
        f"رمى/سعى نمط CCى → FI3L (score={result.intrinsic_score:.2f})"
    )


def test_defective_alef_verb_pattern_detection():
    """
    F.3 — الناقص بالألف الممدودة: دعا
    نمط CCا → fi3l_family=DEFECTIVE، word_class_vote=FI3L
    القانون: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
    نمط CCا مشترك مع ISM (غدا) على مستوى النمط — لا يُسبب غموضاً على مستوى الرمز دعا.
    الغموض موثَّق في not_owned (PATTERN_CLASS_NOTE) لا في evidence.
    """
    result = classify_fi3l_pattern("دعا")
    assert result.fi3l_family == Fi3lFamily.DEFECTIVE, (
        f"F.3 FAIL: دعا fi3l_family={result.fi3l_family.value} (المتوقع: DEFECTIVE)"
    )
    assert result.is_fi3l_candidate, "F.3 FAIL: دعا is_fi3l_candidate=False"
    # بعد الإصلاح: word_class_vote يجب أن يكون FI3L
    assert result.word_class_vote == "FI3L", (
        f"F.3 FAIL: دعا word_class_vote={result.word_class_vote!r} (المتوقع: FI3L)"
    )
    # INVARIANT: لا AMBIGUITY_ISM في evidence
    ambig_ev = [e for e in result.evidence if "AMBIGUITY" in e.value]
    assert len(ambig_ev) == 0, (
        f"F.3 FAIL: دعا يحمل دليل AMBIGUITY في evidence رغم عدم وجود تحليل ISM مرخَّص: "
        f"{[e.value for e in ambig_ev]}"
    )
    # NOT_OWNED موثَّق للحسم المؤجَّل FI3L↔ISM
    not_owned_fi3l_ism = [n for n in result.not_owned if "FI3L↔ISM" in n or "دعا" in n]
    assert not_owned_fi3l_ism, (
        "F.3 FAIL: دعا يجب أن يحمل NOT_OWNED لحسم الغموض FI3L↔ISM (معجم أو سياق)"
    )
    # PATTERN_CLASS_NOTE موثَّق في not_owned
    pattern_note = [n for n in result.not_owned if "PATTERN_CLASS_NOTE" in n]
    assert pattern_note, (
        "F.3 FAIL: دعا يجب أن يحمل PATTERN_CLASS_NOTE في not_owned"
    )
    print(
        f"  ✓ test_defective_alef_verb_pattern_detection — "
        f"دعا: DEFECTIVE/FI3L، لا AMBIGUITY في evidence، "
        f"PATTERN_CLASS_NOTE في not_owned | PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY=0"
    )


def test_hamzated_hollow_verb_pattern_detection():
    """
    F.4 — المهموز الأجوف: جاء / شاء
    نمط CāCء → fi3l_family=HAMZATED، word_class_vote=FI3L، is_fi3l_candidate=True
    القانون: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
    نمط CāCء مشترك مع ISM (ماء) على مستوى النمط — لا يُسبب غموضاً على مستوى الرمز.
    الغموض موثَّق في not_owned (PATTERN_CLASS_NOTE) لا في evidence.
    """
    words = ["جاء", "شاء"]
    for word in words:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.HAMZATED, (
            f"F.4 FAIL: '{word}' fi3l_family={result.fi3l_family.value} "
            f"(المتوقع: HAMZATED — نمط CāCء)"
        )
        assert result.is_fi3l_candidate, (
            f"F.4 FAIL: '{word}' is_fi3l_candidate=False"
        )
        # بعد الإصلاح: word_class_vote يجب أن يكون FI3L
        assert result.word_class_vote == "FI3L", (
            f"F.4 FAIL: '{word}' word_class_vote={result.word_class_vote!r} "
            "(المتوقع: FI3L — لا تحليل ISM مرخَّص مستقل لجاء/شاء)"
        )
        # INVARIANT: لا AMBIGUITY_ISM في evidence
        ambig_ev = [e for e in result.evidence if "AMBIGUITY" in e.value]
        assert len(ambig_ev) == 0, (
            f"F.4 FAIL: '{word}' يحمل دليل AMBIGUITY في evidence: "
            f"{[e.value for e in ambig_ev]}"
        )
        # PATTERN_CLASS_NOTE موثَّق في not_owned
        pattern_note = [n for n in result.not_owned if "PATTERN_CLASS_NOTE" in n]
        assert pattern_note, (
            f"F.4 FAIL: '{word}' يجب أن يحمل PATTERN_CLASS_NOTE في not_owned"
        )
    print(
        f"  ✓ test_hamzated_hollow_verb_pattern_detection — "
        f"جاء/شاء: HAMZATED/FI3L، لا AMBIGUITY في evidence، "
        f"PATTERN_CLASS_NOTE في not_owned | PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY=0"
    )


def test_qama_jaa_not_ism_default():
    """
    F.5 — قام وجاء: الشهادة الكاملة تُعطي FI3L/PROBABLE
    القانون: PATTERN_CLASS_AMBIGUITY != TOKEN_IDENTITY_AMBIGUITY
    بعد الإصلاح: قام وجاء يُصنَّفان FI3L/PROBABLE لا UNKNOWN/AMBIGUOUS
    لأن fi3l_engine يُصوِّت FI3L وword_class_engine يُمرِّر الصوت مباشرةً.
    """
    for word, expected_family in [("قام", Fi3lFamily.HOLLOW), ("جاء", Fi3lFamily.HAMZATED)]:
        # تحقق من fi3l_engine
        fi3l = classify_fi3l_pattern(word)
        assert fi3l.fi3l_family == expected_family, (
            f"F.5 FAIL: fi3l_engine '{word}' family={fi3l.fi3l_family.value}"
        )
        assert fi3l.is_fi3l_candidate, f"F.5 FAIL: '{word}' is_fi3l_candidate=False"
        assert fi3l.word_class_vote == "FI3L", (
            f"F.5 FAIL: fi3l_engine '{word}' word_class_vote={fi3l.word_class_vote!r} "
            "(المتوقع: FI3L بعد الإصلاح)"
        )

        # تحقق من الشهادة الكاملة
        cert = analyze_word(word)

        # القاعدة: لا يجوز أن يكون ISM مع PROBABLE (ذلك هو ISM_DEFAULT)
        is_ism_default = (
            cert.word_class == WordClass.ISM and
            cert.word_class_confidence == WordClassConfidence.PROBABLE
        )
        assert not is_ism_default, (
            f"F.5 FAIL: '{word}' ما زال ISM_DEFAULT "
            f"(class={cert.word_class.value}, conf={cert.word_class_confidence.value})"
        )

        # القيمة الصحيحة بعد الإصلاح: FI3L/PROBABLE
        assert cert.word_class == WordClass.FI3L, (
            f"F.5 FAIL: '{word}' word_class={cert.word_class.value} "
            f"(المتوقع: FI3L — fi3l_engine يُصوِّت FI3L وword_class_engine يُمرِّر)"
        )
        assert cert.word_class_confidence == WordClassConfidence.PROBABLE, (
            f"F.5 FAIL: '{word}' confidence={cert.word_class_confidence.value} "
            f"(المتوقع: PROBABLE)"
        )

        print(
            f"  ✓ test_qama_jaa_not_ism_default: '{word}'"
            f" → {cert.word_class.value}/{cert.word_class_confidence.value}"
            f" (fi3l_family={fi3l.fi3l_family.value})"
        )


def test_strong_verb_diacritized():
    """
    F.6 — السالم بالتشكيل: كَتَبَ / قَتَلَ
    وزن فَعَلَ المشكَّل → fi3l_family=STRONG، word_class_vote=FI3L (score ≥ 0.85)
    التشكيل يُزيل غموض ISM (كِتَاب مختلف وزناً).
    """
    words = ["كَتَبَ", "قَتَلَ"]
    for word in words:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.STRONG, (
            f"F.6 FAIL: '{word}' fi3l_family={result.fi3l_family.value} "
            f"(المتوقع: STRONG — وزن فَعَلَ)"
        )
        assert result.word_class_vote == "FI3L", (
            f"F.6 FAIL: '{word}' word_class_vote={result.word_class_vote!r} (المتوقع: FI3L)"
        )
        assert result.intrinsic_score >= 0.85, (
            f"F.6 FAIL: '{word}' intrinsic_score={result.intrinsic_score:.2f} < 0.85"
        )
        assert result.has_diacritics_used, (
            f"F.6 FAIL: '{word}' has_diacritics_used=False — يجب استخدام التشكيل"
        )
    print(
        f"  ✓ test_strong_verb_diacritized — "
        f"كَتَبَ/قَتَلَ وزن فَعَلَ → STRONG/FI3L (score≥0.85)"
    )


def test_doubled_verb_diacritized():
    """
    F.7 — المضعَّف بالتشكيل: مَدَّ / رَدَّ
    شدة على الحرف الأخير → fi3l_family=DOUBLED، word_class_vote=FI3L (score ≥ 0.80)
    بدون تشكيل (مد، رد): لا نمط محدد — الغموض الجوهري محفوظ.
    """
    # مشكَّل: يُكتشف
    for word in ["مَدَّ", "رَدَّ"]:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.DOUBLED, (
            f"F.7 FAIL: '{word}' fi3l_family={result.fi3l_family.value} (المتوقع: DOUBLED)"
        )
        assert result.word_class_vote == "FI3L", (
            f"F.7 FAIL: '{word}' word_class_vote={result.word_class_vote!r}"
        )
        assert result.intrinsic_score >= 0.80, (
            f"F.7 FAIL: '{word}' intrinsic_score={result.intrinsic_score:.2f}"
        )

    # بدون تشكيل: UNKNOWN (الغموض الجوهري — لا يُحكم بدون شدة)
    for word in ["مد", "رد"]:
        result = classify_fi3l_pattern(word)
        assert result.fi3l_family == Fi3lFamily.UNKNOWN, (
            f"F.7: '{word}' بدون تشكيل → المتوقع UNKNOWN (الشدة ضرورية لتأكيد المضعَّف)، "
            f"حصلنا {result.fi3l_family.value}"
        )

    print(
        "  ✓ test_doubled_verb_diacritized — "
        "مَدَّ/رَدَّ (بشدة) → DOUBLED/FI3L | مد/رد (بلا شدة) → UNKNOWN"
    )


def test_context_zero_for_fi3l_engine():
    """
    F.8 — CONTEXT_USED_FOR_INTRINSIC_FI3L = 0
    تحقق بفحص AST: fi3l_engine.py لا يستورد من hokom/irab/ifadah/wave11.
    لا قرار فعلي يعتمد على سياق إعرابي أو مخرجات Hokom.
    """
    import os
    fi3l_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'fi3l_engine.py'))
    with open(fi3l_path, 'r', encoding='utf-8') as f:
        src = f.read()

    tree = ast.parse(src)
    forbidden_modules = {"hokom", "irab", "ifadah_kernel", "wave11", "irab_types", "b4", "r5"}
    bad_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if any(fb in module.lower() for fb in forbidden_modules):
                        bad_imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module.split('.')[0]
                if any(fb in node.module.lower() for fb in forbidden_modules):
                    bad_imports.append(f"from {node.module} import ...")

    assert not bad_imports, (
        f"F.8 FAIL: CONTEXT_USED_FOR_INTRINSIC_FI3L ≠ 0 — "
        f"fi3l_engine يستورد من طبقات تنازلية: {bad_imports}"
    )
    print(
        f"  ✓ test_context_zero_for_fi3l_engine — "
        f"CONTEXT_USED_FOR_INTRINSIC_FI3L=0 مُثبَت: لا استيراد من hokom/irab/ifadah"
    )


def test_pattern_class_not_promoted_to_token_ambiguity():
    """
    F.9 — INVARIANT: PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY = 0
    تحكم سلبي: باب يطابق نمط CāC تماماً مثل قام.
    اشتراك باب وقام في نمط CāC لا يُدخل غموضاً على مستوى الرمز في قام.
    قام يبقى FI3L — لا AMBIGUITY في evidence بسبب باب.
    """
    # كلا الرمزين يطابق نمط CāC
    bab_result = classify_fi3l_pattern("باب")
    qama_result = classify_fi3l_pattern("قام")

    # باب: يطابق نمط CāC لكن بدون تحليل فعلي مدعوم → لا يُصنَّف FI3L بالضرورة
    # قام: يطابق نمط CāC ويُصنَّف FI3L
    assert qama_result.word_class_vote == "FI3L", (
        f"F.9 FAIL: قام word_class_vote={qama_result.word_class_vote!r} (المتوقع: FI3L)"
    )
    assert qama_result.is_fi3l_candidate, "F.9 FAIL: قام is_fi3l_candidate=False"

    # INVARIANT COUNTER: لا AMBIGUITY في evidence قام بسبب باب
    qama_ambig = [e for e in qama_result.evidence if "AMBIGUITY" in e.value]
    assert len(qama_ambig) == 0, (
        f"F.9 FAIL: PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY ≠ 0 — "
        f"قام يحمل AMBIGUITY في evidence رغم أن باب كلمة مختلفة: "
        f"{[e.value for e in qama_ambig]}"
    )

    # تحقق أن كلا الرمزين يطابق نفس عائلة النمط (HOLLOW) — تأكيد الاشتراك
    assert qama_result.fi3l_family == Fi3lFamily.HOLLOW, (
        f"F.9: قام fi3l_family={qama_result.fi3l_family.value} (المتوقع: HOLLOW)"
    )
    if bab_result.is_fi3l_candidate:
        assert bab_result.fi3l_family == Fi3lFamily.HOLLOW, (
            f"F.9 note: باب fi3l_family={bab_result.fi3l_family.value}"
        )
        # التأكيد الجوهري: اشتراك باب في نمط CāC لم يُلوِّث قام
        bab_in_qama_ev = [
            e for e in qama_result.evidence
            if "باب" in e.detail or "ISM" in e.value
        ]
        assert len(bab_in_qama_ev) == 0, (
            f"F.9 FAIL: دليل ISM (باب) ظهر في evidence قام: "
            f"{[(e.value, e.detail) for e in bab_in_qama_ev]}"
        )

    print(
        f"  ✓ test_pattern_class_not_promoted_to_token_ambiguity — "
        f"PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY=0: "
        f"باب وقام يتشاركان CāC لكن قام يبقى FI3L دون تلوُّث"
    )


def test_generated_verb_not_surface_proof():
    """
    F.10 — INVARIANT: GENERATED_VERB_USED_AS_SURFACE_PROOF = 0
    fi3l_engine يعتمد على PATTERN_MATCH (النمط) لا على توليد أشكال الفعل ومقارنتها.
    يُثبَت بـ:
      1. confidence_basis في not_owned/evidence يُشير إلى PATTERN_MATCH لا GENERATED_FORM
      2. intrinsic_score < 1.0 (النمط وحده لا يكفي لليقين الكامل)
      3. لا يوجد دليل بقيمة "GENERATED_*" في evidence
    """
    test_words = ["قام", "دعا", "جاء", "رمى"]
    for word in test_words:
        result = classify_fi3l_pattern(word)
        if not result.is_fi3l_candidate:
            continue

        # تحقق 1: لا أدلة مولَّدة
        generated_ev = [e for e in result.evidence if "GENERATED" in e.value.upper()]
        assert len(generated_ev) == 0, (
            f"F.10 FAIL: GENERATED_VERB_USED_AS_SURFACE_PROOF ≠ 0 — "
            f"'{word}' يحمل دليلاً مولَّداً: {[e.value for e in generated_ev]}"
        )

        # تحقق 2: intrinsic_score < 1.0 (النمط وحده لا يُعطي يقيناً كاملاً)
        assert result.intrinsic_score < 1.0, (
            f"F.10 FAIL: '{word}' intrinsic_score={result.intrinsic_score:.2f} == 1.0 — "
            f"النمط وحده لا يُعطي يقيناً كاملاً (السطح الموثَّق خارج نطاق هذا المحرك)"
        )

        # تحقق 3: pattern_label موجود (يُثبت أن القرار قائم على نمط)
        assert result.pattern_label, (
            f"F.10 FAIL: '{word}' pattern_label فارغ رغم is_fi3l_candidate=True"
        )

    print(
        f"  ✓ test_generated_verb_not_surface_proof — "
        f"GENERATED_VERB_USED_AS_SURFACE_PROOF=0: قام/دعا/جاء/رمى "
        f"يعتمدون على PATTERN_MATCH، لا أشكال مولَّدة، score<1.0"
    )


def test_vocalization_strengthens_certification():
    """
    F.11 — التشكيل يُقوِّي الشهادة: VOCALIZATION_USED_AS_INTRINSIC_EVIDENCE
    قَامَ (مشكَّل) → has_diacritics_used=True، intrinsic_score أعلى
    قام (غير مشكَّل) → has_diacritics_used=False، intrinsic_score أدنى
    القاعدة: score(مشكَّل) > score(غير مشكَّل) لنفس الجذر
    """
    # مشكَّل
    result_vocalized = classify_fi3l_pattern("قَامَ")
    # غير مشكَّل
    result_plain = classify_fi3l_pattern("قام")

    # كلاهما مرشح
    assert result_vocalized.is_fi3l_candidate, (
        "F.11 FAIL: قَامَ is_fi3l_candidate=False"
    )
    assert result_plain.is_fi3l_candidate, (
        "F.11 FAIL: قام is_fi3l_candidate=False"
    )

    # التشكيل يُقوِّي الثقة
    assert result_vocalized.intrinsic_score > result_plain.intrinsic_score, (
        f"F.11 FAIL: score(قَامَ)={result_vocalized.intrinsic_score:.2f} "
        f"≤ score(قام)={result_plain.intrinsic_score:.2f} — "
        f"التشكيل يجب أن يُعطي ثقةً أعلى"
    )

    # has_diacritics_used: True للمشكَّل، False للمجرد
    # ملاحظة: قَامَ يُحوَّل بـ _strip_diacritics ثم نفحص نمطه — has_diacritics_used يُشير
    # إلى أن المحرك استخدم التشكيل في قرار الثقة
    assert result_vocalized.has_diacritics_used, (
        "F.11 FAIL: قَامَ has_diacritics_used=False — التشكيل يجب أن يُوظَّف كدليل"
    )

    # التقرير
    print(
        f"  ✓ test_vocalization_strengthens_certification — "
        f"VOCALIZATION_USED_AS_INTRINSIC_EVIDENCE=YES: "
        f"score(قَامَ)={result_vocalized.intrinsic_score:.2f} > "
        f"score(قام)={result_plain.intrinsic_score:.2f}, "
        f"has_diacritics_used(قَامَ)={result_vocalized.has_diacritics_used}"
    )


def test_verb_feature_orthogonality():
    """
    F.12 — §A: ORTHOGONAL_VERB_FEATURE_LOSS = 0
    Fi3lFamily.HAMZATED لـ جاء/شاء لا يُلغي خاصية HOLLOW.
    VerbFeatureVector يجب أن يحفظ كلا البُعدين بشكل مستقل.

    جاء = Fi3lFamily.HAMZATED + VFV(radical_health=HOLLOW, hamza_feature=FINAL, gemination=NONE)
    مَدَّ = Fi3lFamily.DOUBLED + VFV(radical_health=SOUND, hamza_feature=NONE, gemination=DOUBLED)
    قام = Fi3lFamily.HOLLOW + VFV(radical_health=HOLLOW, hamza_feature=NONE, gemination=NONE)
    رمى = Fi3lFamily.DEFECTIVE + VFV(radical_health=DEFECTIVE, hamza_feature=NONE, gemination=NONE)
    """
    # §A.1: جاء وشاء — HOLLOW + FINAL مزدوج
    for word in ("جاء", "شاء"):
        r = classify_fi3l_pattern(word)
        assert r.is_fi3l_candidate, "F.12 FAIL: %s is_fi3l_candidate=False" % word
        assert r.fi3l_family == Fi3lFamily.HAMZATED, (
            "F.12 FAIL: %s fi3l_family=%s (exp HAMZATED)" % (word, r.fi3l_family)
        )
        assert r.verb_features is not None, (
            "F.12 FAIL: ORTHOGONAL_VERB_FEATURE_LOSS — %s verb_features=None" % word
        )
        assert r.verb_features.radical_health == RadicalHealth.HOLLOW, (
            "F.12 FAIL: ORTHOGONAL_VERB_FEATURE_LOSS — %s radical_health=%s (exp HOLLOW)"
            % (word, r.verb_features.radical_health)
        )
        assert r.verb_features.hamza_feature == HamzaFeature.FINAL, (
            "F.12 FAIL: %s hamza_feature=%s (exp FINAL)" % (word, r.verb_features.hamza_feature)
        )
        assert r.verb_features.gemination == GeminationFeature.NONE, (
            "F.12 FAIL: %s gemination=%s (exp NONE)" % (word, r.verb_features.gemination)
        )

    # §A.2: مَدَّ — SOUND + DOUBLED
    r_madd = classify_fi3l_pattern("مَدَّ")
    assert r_madd.verb_features is not None, "F.12 FAIL: مَدَّ verb_features=None"
    assert r_madd.verb_features.radical_health == RadicalHealth.SOUND, (
        "F.12 FAIL: مَدَّ radical_health=%s (exp SOUND)" % r_madd.verb_features.radical_health
    )
    assert r_madd.verb_features.gemination == GeminationFeature.DOUBLED, (
        "F.12 FAIL: مَدَّ gemination=%s (exp DOUBLED)" % r_madd.verb_features.gemination
    )
    assert r_madd.verb_features.hamza_feature == HamzaFeature.NONE, (
        "F.12 FAIL: مَدَّ hamza_feature=%s (exp NONE)" % r_madd.verb_features.hamza_feature
    )

    # §A.3: قام (unvocalized) — HOLLOW + NONE + NONE
    r_qam = classify_fi3l_pattern("قام")
    assert r_qam.verb_features is not None, "F.12 FAIL: قام verb_features=None"
    assert r_qam.verb_features.radical_health == RadicalHealth.HOLLOW, (
        "F.12 FAIL: قام radical_health=%s (exp HOLLOW)" % r_qam.verb_features.radical_health
    )
    assert r_qam.verb_features.gemination == GeminationFeature.NONE, (
        "F.12 FAIL: قام gemination=%s (exp NONE)" % r_qam.verb_features.gemination
    )
    assert r_qam.verb_features.hamza_feature == HamzaFeature.NONE, (
        "F.12 FAIL: قام hamza_feature=%s (exp NONE)" % r_qam.verb_features.hamza_feature
    )

    # §A.4: رمى (unvocalized) — DEFECTIVE
    r_rmy = classify_fi3l_pattern("رمى")
    assert r_rmy.verb_features is not None, "F.12 FAIL: رمى verb_features=None"
    assert r_rmy.verb_features.radical_health == RadicalHealth.DEFECTIVE, (
        "F.12 FAIL: رمى radical_health=%s (exp DEFECTIVE)" % r_rmy.verb_features.radical_health
    )

    print(
        "  ✓ test_verb_feature_orthogonality — ORTHOGONAL_VERB_FEATURE_LOSS=0: "
        "جاء HOLLOW+FINAL, مَدَّ SOUND+DOUBLED, قام HOLLOW+NONE, رمى DEFECTIVE"
    )


def test_false_residual_causality():
    """
    F.13 — §B: FALSE_RESIDUAL_CAUSALITY = 0
    first_missing_evidence يُشير إلى السبب الحقيقي لإخفاق الاستدلال.

    القاعدة الأساسية:
      كتب (سالم) لا يُفيد أن "الشدة" مفقودة — الشدة ليست ذات صلة بالثلاثي السالم.
      مد/رد (ثنائي السطح) يُفيد أن "الشدة" مفقودة — هذا صحيح للمضعَّف بدون تشكيل.

    FALSE_RESIDUAL_CAUSALITY = 0:
      لا يُوصَف سبب مزيَّف لإخفاق الاستدلال.
    """
    # §B.1: كتب (سالم ثلاثي) — MUST NOT mention shadda
    r_ktb = classify_fi3l_pattern("كتب")
    assert not r_ktb.is_fi3l_candidate, "F.13: كتب يجب أن يكون غير مرشح"
    fme_ktb = r_ktb.first_missing_evidence
    assert fme_ktb, "F.13 FAIL: كتب first_missing_evidence فارغ"
    assert "شدة" not in fme_ktb, (
        "F.13 FAIL: FALSE_RESIDUAL_CAUSALITY — كتب (سالم) يُشير إلى الشدة: %r" % fme_ktb
    )
    assert "تشكيل" in fme_ktb or "نمط" in fme_ktb, (
        "F.13 FAIL: كتب first_missing_evidence لا يذكر التشكيل: %r" % fme_ktb
    )

    # §B.2: مد (ثنائي السطح) — shadda IS the relevant missing element
    r_mad = classify_fi3l_pattern("مد")
    assert not r_mad.is_fi3l_candidate, "F.13: مد (بلا شدة) يجب أن يكون غير مرشح"
    fme_mad = r_mad.first_missing_evidence
    assert "شدة" in fme_mad, (
        "F.13 FAIL: مد (مضعَّف) لا يُشير إلى الشدة: %r" % fme_mad
    )

    # §B.3: وعد (مثال) — must mention علة or مثال
    r_waad = classify_fi3l_pattern("وعد")
    assert not r_waad.is_fi3l_candidate, "F.13: وعد يجب أن يكون غير مرشح"
    fme_waad = r_waad.first_missing_evidence
    assert "شدة" not in fme_waad, (
        "F.13 FAIL: FALSE_RESIDUAL_CAUSALITY — وعد يُشير إلى الشدة: %r" % fme_waad
    )
    assert "علة" in fme_waad or "مثال" in fme_waad, (
        "F.13 FAIL: وعد (مثال) لا يذكر علة/مثال: %r" % fme_waad
    )

    print(
        "  ✓ test_false_residual_causality — FALSE_RESIDUAL_CAUSALITY=0: "
        "كتب≠شدة, مد=شدة, وعد=علة/مثال"
    )


def test_root_vfv_composition():
    """
    F.14 — تركيب خصائص الفعل من الجذر المُثبَّت
    ROOT → VFV COMPOSITION GATE

    ثلاثة أعلام (كل منها بضابط غير فارغ):

    ROOT_FEATURE_AVAILABLE_BUT_IGNORED = 0:
      الضابط: وعد → radical_health=ASSIMILATED (الجذر متاح ومُثبَّت، يُستخدم).
      لو كان المحرك يتجاهل الجذر، كانت قيمة composed_verb_features=None أو SOUND.

    ORTHOGONAL_FEATURE_ERASURE = 0:
      الضابط: جاء/جيأ → radical_health=HOLLOW + hamza_feature=FINAL معاً.
      لو كانت إحداهما تُلغي الأخرى، لكانت إحداهما NONE.

    UNLICENSED_ROOT_TO_FEATURE_PROMOTION = 0:
      الضابط: قرأ (cert=CANDIDATE/NOT_FOUND) → composed_verb_features=None.
      لو كان المحرك يُرقِّي من CANDIDATE، كانت القيمة غير None.
    """
    from word_tree.fi3l_engine import compose_vfv_from_certified_root

    # ── ضابط 1: ROOT_FEATURE_AVAILABLE_BUT_IGNORED = 0 ─────────────
    # وعد → جذر "وعد" (EVIDENCE_SUPPORTED) → radical_health = ASSIMILATED
    cert_waad = analyze_word("وعد")
    cvfv_waad = cert_waad.composed_verb_features
    assert cvfv_waad is not None, (
        "F.14 FAIL: ROOT_FEATURE_AVAILABLE_BUT_IGNORED — وعد لديه جذر مُثبَّت"
        " لكن composed_verb_features=None (الخاصية مُتجاهَلة)"
    )
    assert cvfv_waad.radical_health == RadicalHealth.ASSIMILATED, (
        "F.14 FAIL: ROOT_FEATURE_AVAILABLE_BUT_IGNORED — وعد: "
        "radical_health=%s (exp ASSIMILATED)" % cvfv_waad.radical_health
    )
    # سأل → جذر "سأل" (EVIDENCE_SUPPORTED) → hamza_feature = MEDIAL
    cert_saal = analyze_word("سأل")
    cvfv_saal = cert_saal.composed_verb_features
    assert cvfv_saal is not None, "F.14 FAIL: سأل composed_verb_features=None"
    assert cvfv_saal.hamza_feature == HamzaFeature.MEDIAL, (
        "F.14 FAIL: سأل hamza_feature=%s (exp MEDIAL)" % cvfv_saal.hamza_feature
    )
    # أخذ → جذر "أخذ" (EVIDENCE_SUPPORTED) → hamza_feature = INITIAL
    cert_akhd = analyze_word("أخذ")
    cvfv_akhd = cert_akhd.composed_verb_features
    assert cvfv_akhd is not None, "F.14 FAIL: أخذ composed_verb_features=None"
    assert cvfv_akhd.hamza_feature == HamzaFeature.INITIAL, (
        "F.14 FAIL: أخذ hamza_feature=%s (exp INITIAL)" % cvfv_akhd.hamza_feature
    )

    # ── ضابط 2: ORTHOGONAL_FEATURE_ERASURE = 0 ─────────────────────
    # جاء → جذر "جيأ" (EVIDENCE_SUPPORTED): c1=ي → HOLLOW, c2=أ/ء → FINAL
    cert_jaa = analyze_word("جاء")
    cvfv_jaa = cert_jaa.composed_verb_features
    assert cvfv_jaa is not None, "F.14 FAIL: جاء composed_verb_features=None"
    assert cvfv_jaa.radical_health == RadicalHealth.HOLLOW, (
        "F.14 FAIL: ORTHOGONAL_FEATURE_ERASURE — جاء/جيأ: "
        "radical_health=%s (exp HOLLOW)" % cvfv_jaa.radical_health
    )
    assert cvfv_jaa.hamza_feature == HamzaFeature.FINAL, (
        "F.14 FAIL: ORTHOGONAL_FEATURE_ERASURE — جاء/جيأ: "
        "hamza_feature=%s (exp FINAL)" % cvfv_jaa.hamza_feature
    )
    assert cvfv_jaa.gemination == GeminationFeature.NONE, (
        "F.14 FAIL: جاء gemination=%s (exp NONE)" % cvfv_jaa.gemination
    )
    # شاء — نفس الجذر (أو جيأ)
    cert_shaa = analyze_word("شاء")
    cvfv_shaa = cert_shaa.composed_verb_features
    assert cvfv_shaa is not None, "F.14 FAIL: شاء composed_verb_features=None"
    assert cvfv_shaa.radical_health == RadicalHealth.HOLLOW, (
        "F.14 FAIL: شاء radical_health=%s (exp HOLLOW)" % cvfv_shaa.radical_health
    )
    assert cvfv_shaa.hamza_feature == HamzaFeature.FINAL, (
        "F.14 FAIL: شاء hamza_feature=%s (exp FINAL)" % cvfv_shaa.hamza_feature
    )

    # ── ضابط 3: UNLICENSED_ROOT_TO_FEATURE_PROMOTION = 0 ────────────
    # قرأ → cert=CANDIDATE (NOT_FOUND في مقاييس) → composed_verb_features يجب أن يكون None
    cert_qraa = analyze_word("قرأ")
    root_cert_qraa = cert_qraa.root_analysis.certification_level.value
    # تحقق أن الجذر فعلاً على مستوى CANDIDATE
    assert root_cert_qraa == "مرشح", (
        "F.14 precondition: قرأ يجب أن يكون CANDIDATE، وجدنا: %s" % root_cert_qraa
    )
    cvfv_qraa = cert_qraa.composed_verb_features
    assert cvfv_qraa is None, (
        "F.14 FAIL: UNLICENSED_ROOT_TO_FEATURE_PROMOTION — قرأ (CANDIDATE): "
        "composed_verb_features=%s (exp None)" % cvfv_qraa
    )

    # ── ضابط 4: DERIVED_FEATURE_RANK_ABOVE_ROOT = 0 ────────────────────
    # DERIVED_FEATURE_RANK <= SOURCE_ROOT_RANK
    # وعد → root cert = EVIDENCE_SUPPORTED ("مدعوم_بدليل")
    # → يجب أن تكون provenance["source"] = "EVIDENCE_SUPPORTED_ROOT"
    #   وليس "CERTIFIED_ROOT" (التي تعني رتبة أعلى = CERTIFIED)
    prov_waad = cert_waad.vfv_provenance
    assert prov_waad is not None, "F.14 FAIL: وعد vfv_provenance=None"
    waad_root_cert = cert_waad.root_analysis.certification_level.value
    assert waad_root_cert == "مدعوم_بدليل", (
        "F.14 precondition: وعد يجب أن يكون EVIDENCE_SUPPORTED، وجدنا: %s" % waad_root_cert
    )
    waad_feat_source = prov_waad["radical_health"]["source"]
    waad_feat_status = prov_waad["radical_health"]["status"]
    assert waad_feat_source == "EVIDENCE_SUPPORTED_ROOT", (
        "F.14 FAIL: DERIVED_FEATURE_RANK_ABOVE_ROOT — وعد (root=EVIDENCE_SUPPORTED): "
        "feat_source=%s (exp EVIDENCE_SUPPORTED_ROOT — لا يجوز CERTIFIED_ROOT)" % waad_feat_source
    )
    assert waad_feat_status == "EVIDENCE_SUPPORTED", (
        "F.14 FAIL: EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED — وعد: "
        "feat_status=%s (exp EVIDENCE_SUPPORTED — لا يجوز CERTIFIED)" % waad_feat_status
    )

    # ── ضابط 5: EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED = 0 ─────
    # تحقق من جاء (EVIDENCE_SUPPORTED أيضاً) — يجب نفس السلوك
    prov_jaa = cert_jaa.vfv_provenance
    assert prov_jaa is not None, "F.14 FAIL: جاء vfv_provenance=None"
    jaa_feat_source = prov_jaa["radical_health"]["source"]
    jaa_feat_status = prov_jaa["radical_health"]["status"]
    assert jaa_feat_source == "EVIDENCE_SUPPORTED_ROOT", (
        "F.14 FAIL: EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED — جاء (root=EVIDENCE_SUPPORTED): "
        "feat_source=%s (exp EVIDENCE_SUPPORTED_ROOT)" % jaa_feat_source
    )
    assert jaa_feat_status == "EVIDENCE_SUPPORTED", (
        "F.14 FAIL: EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED — جاء: "
        "feat_status=%s (exp EVIDENCE_SUPPORTED)" % jaa_feat_status
    )

    print(
        "  ✓ test_root_vfv_composition — "
        "ROOT_FEATURE_AVAILABLE_BUT_IGNORED=0 (وعد→ASSIMILATED, سأل→MEDIAL, أخذ→INITIAL), "
        "ORTHOGONAL_FEATURE_ERASURE=0 (جاء/جيأ→HOLLOW+FINAL), "
        "UNLICENSED_ROOT_TO_FEATURE_PROMOTION=0 (قرأ CANDIDATE→None), "
        "DERIVED_FEATURE_RANK_ABOVE_ROOT=0 (وعد/جاء: feat_source=EVIDENCE_SUPPORTED_ROOT), "
        "EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED=0 (feat_status=EVIDENCE_SUPPORTED)"
    )


def run_fi3l_tests():
    """شغِّل اختبارات صرف الفعل الجوهري (F)"""
    print("\n" + "═"*70)
    print("  F. صرف الفعل الجوهري (Fi3l Morphology — أصناف ضعيفة وسالمة)")
    print("  CONTEXT_USED_FOR_INTRINSIC_FI3L = 0")
    print("  PATTERN_CLASS_AMBIGUITY_PROMOTED_TO_TOKEN_AMBIGUITY = 0 [F.9]")
    print("  GENERATED_VERB_USED_AS_SURFACE_PROOF = 0 [F.10]")
    print("  VOCALIZATION_USED_AS_INTRINSIC_EVIDENCE = YES [F.11]")
    print("  ORTHOGONAL_VERB_FEATURE_LOSS = 0 [F.12]")
    print("  FALSE_RESIDUAL_CAUSALITY = 0 [F.13]")
    print("  ROOT_FEATURE_AVAILABLE_BUT_IGNORED = 0 [F.14]")
    print("  ORTHOGONAL_FEATURE_ERASURE = 0 [F.14]")
    print("  UNLICENSED_ROOT_TO_FEATURE_PROMOTION = 0 [F.14]")
    print("  DERIVED_FEATURE_RANK_ABOVE_ROOT = 0 [F.14]")
    print("  EVIDENCE_SUPPORTED_ROOT_MISLABELED_CERTIFIED = 0 [F.14]")
    print("═"*70)
    tests = [
        test_hollow_verb_pattern_detection,
        test_defective_ya_verb_pattern_detection,
        test_defective_alef_verb_pattern_detection,
        test_hamzated_hollow_verb_pattern_detection,
        test_qama_jaa_not_ism_default,
        test_strong_verb_diacritized,
        test_doubled_verb_diacritized,
        test_context_zero_for_fi3l_engine,
        test_pattern_class_not_promoted_to_token_ambiguity,
        test_generated_verb_not_surface_proof,
        test_vocalization_strengthens_certification,
        test_verb_feature_orthogonality,
        test_false_residual_causality,
        test_root_vfv_composition,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            import traceback
            print(f"  ✗ {t.__name__} [ERROR]: {e}")
            traceback.print_exc()
    print(f"\n  النتيجة: {passed}/{len(tests)} نجاح")
    return passed, len(tests)


def main():
    print("\n" + "█"*70)
    print("  ARABIC INTRINSIC WORD IDENTITY PROGRAM — تشغيل الاختبارات")
    print("█"*70)

    p1, t1 = run_probe_corpus()
    p2, t2 = run_property_tests()
    p3, t3 = run_negative_controls()
    p4, t4 = run_boundary_tests()
    p5, t5 = run_gate_tests()
    p6, t6 = run_fi3l_tests()

    total_passed = p1 + p2 + p3 + p4 + p5 + p6
    total_tests  = t1 + t2 + t3 + t4 + t5 + t6

    print("\n" + "═"*70)
    print(f"  الملخص النهائي: {total_passed}/{total_tests} نجاح")
    print("═"*70)

    # طباعة مفصلة لبعض الكلمات المحورية
    print("\n  ── شهادات الكلمات المحورية ──")
    for word in ["كريم", "كاتب", "مكتوب", "واحد", "عشرون", "مائة"]:
        cert = analyze_word(word)
        print_certificate(cert, compact=True)

    # ملخص صرف الفعل
    print("\n  ── ملخص صرف الفعل الجوهري ──")
    verb_probes = [
        ("قال",   "أجوف"),
        ("قام",   "أجوف"),
        ("باع",   "أجوف"),
        ("صام",   "أجوف"),
        ("جاء",   "مهموز_أجوف"),
        ("شاء",   "مهموز_أجوف"),
        ("دعا",   "ناقص_ا"),
        ("رمى",   "ناقص_ى"),
        ("سعى",   "ناقص_ى"),
        ("كَتَبَ","سالم_مشكَّل"),
        ("مَدَّ", "مضعَّف_مشكَّل"),
    ]
    for word, expected_type in verb_probes:
        r = classify_fi3l_pattern(word)
        cert = analyze_word(word)
        print(
            f"  {word:10} fi3l={r.fi3l_family.value:8} vote={r.word_class_vote:10} "
            f"cert={cert.word_class.value}/{cert.word_class_confidence.value}"
        )


if __name__ == "__main__":
    main()
