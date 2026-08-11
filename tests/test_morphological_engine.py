"""
اختبار المحرك الصرفي على الجذور العشرة التجريبية
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from word_tree.engines.morphological_engine import conjugate
from word_tree.core.types import RootType, Baab


# الجذور العشر مع حروفها الأصلية الصحيحة (ثلاثة أحرف)
PILOT_ROOTS = [
    # (مفتاح، حروف أصلية، نوع، باب، أمثلة متوقعة)
    ("كتب",  "كتب", RootType.SAHIH,      Baab.FAA_YAF_U,
     {"ماضٍ_هو": "كَتَبَ", "مضارع_هو": "يَكْتُبُ", "أمر_أنت": "اِكْتُبْ"}),

    ("علم",  "علم", RootType.SAHIH,      Baab.FAI_YAF_A,
     {"ماضٍ_هو": "عَلِمَ", "مضارع_هو": "يَعْلَمُ"}),

    ("كرم",  "كرم", RootType.SAHIH,      Baab.FAU_YAF_U,
     {"ماضٍ_هو": "كَرُمَ", "مضارع_هو": "يَكْرُمُ"}),

    ("حكم",  "حكم", RootType.SAHIH,      Baab.FAA_YAF_I,
     {"ماضٍ_هو": "حَكَمَ", "مضارع_هو": "يَحْكِمُ"}),

    ("ردد",  "ردد", RootType.MUDAAF,     Baab.FAA_YAF_U,
     {"ماضٍ_هو": "رَدَّ"}),

    ("وصل",  "وصل", RootType.MITHAL_WAW, Baab.FAA_YAF_I,
     {"ماضٍ_هو": "وَصَلَ", "مضارع_هو": "يَصِلُ"}),

    ("قول",  "قول", RootType.AJWAF_WAW,  Baab.FAA_YAF_U,
     {"ماضٍ_هو": "قَالَ", "مضارع_هو": "يَقُولُ", "أمر_أنت": "قُلْ"}),

    ("بيع",  "بيع", RootType.AJWAF_YAA,  Baab.FAA_YAF_I,
     {"ماضٍ_هو": "بَاعَ", "مضارع_هو": "يَبِيعُ"}),

    ("رمي",  "رمي", RootType.NAQIS_YAA,  Baab.FAA_YAF_I,
     {"ماضٍ_هو": "رَمَى", "مضارع_هو": "يَرْمِيُ"}),

    ("دعو",  "دعو", RootType.NAQIS_WAW,  Baab.FAA_YAF_U,
     {"ماضٍ_هو": "دَعَا", "مضارع_هو": "يَدْعُوُ"}),
]


def test_root(label, letters, root_type, baab, expected):
    print(f"\n{'═'*60}")
    print(f"الجذر: {label}  |  النوع: {root_type.value}  |  الباب: {baab.value}")
    print(f"{'─'*60}")

    try:
        p = conjugate(letters, root_type, baab)
    except Exception as e:
        print(f"  ❌ خطأ في التوليد: {e}")
        return False

    print(f"  ✅ عدد الخلايا المُولَّدة: {len(p.cells)}")

    # طباعة الماضي المعلوم
    print("\n  الماضي (معلوم):")
    past = p.filter(mood="ماضٍ", voice="معلوم")
    for c in past[:6]:   # أول ٦ (الغائب)
        print(f"    {c.person} {c.number} {c.gender}: {c.form}")

    # طباعة المضارع المرفوع
    print("\n  المضارع المرفوع (معلوم):")
    present = p.filter(mood="مضارع مرفوع", voice="معلوم")
    for c in present[:6]:
        print(f"    {c.person} {c.number} {c.gender}: {c.form}")

    # طباعة الأمر
    print("\n  الأمر:")
    imp = p.filter(mood="أمر")
    for c in imp:
        print(f"    {c.person} {c.number} {c.gender}: {c.form}")

    return True


def main():
    print("=" * 60)
    print("   اختبار المحرك الصرفي — الجذور العشر التجريبية")
    print("=" * 60)

    passed = 0
    for entry in PILOT_ROOTS:
        ok = test_root(*entry)
        if ok:
            passed += 1

    print(f"\n{'═'*60}")
    print(f"النتيجة: {passed}/{len(PILOT_ROOTS)} جذور اجتازت الاختبار")


if __name__ == "__main__":
    main()
