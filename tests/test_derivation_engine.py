"""
اختبار المحرك الاشتقاقي على الجذور العشرة التجريبية
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from word_tree.engines.derivation_engine import derive_from_dict, DerivationSet


DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_roots.json')


def test_root(root_data: dict) -> bool:
    label = root_data["display"]
    letters = root_data["letters"]
    rt = root_data["root_type"]

    print(f"\n{'═'*60}")
    print(f"الجذر: {label}  ({letters})  |  النوع: {rt}")
    print(f"{'─'*60}")

    try:
        ds: DerivationSet = derive_from_dict(root_data)
    except Exception as e:
        print(f"  ❌ خطأ في التوليد: {e}")
        import traceback; traceback.print_exc()
        return False

    # ── باب I ─────────────────────────────────────────────────────────
    print("  ■ باب I — المشتقات الأساسية:")
    if ds.masadir_samiyya:
        print(f"    مصادر سماعية : {' / '.join(ds.masadir_samiyya)}")
    if ds.masdar_qiyasi:
        print(f"    مصدر قياسي   : {ds.masdar_qiyasi}")
    print(f"    اسم الفاعل   : {ds.ism_faail  or '—'}")
    print(f"    اسم المفعول  : {ds.ism_mafuul or '—'}")
    print(f"    اسم المكان   : {ds.ism_makan  or '—'}")
    print(f"    اسم الزمان   : {ds.ism_zaman  or '—'}")
    print(f"    اسم الآلة    : {ds.ism_aala   or '—'}")

    # ── مزيدات II–X ───────────────────────────────────────────────────
    if ds.mazidaat:
        print(f"\n  ■ الأوزان المزيدة ({len(ds.mazidaat)} أوزان):")
        for m in ds.mazidaat:
            print(f"    [{m.wazn}] {m.wazn_op}")
            print(f"      فعل      : {m.verb}")
            print(f"      مصدر     : {m.masdar}")
            print(f"      اسم فاعل : {m.ism_faail}")
            print(f"      اسم مفعول: {m.ism_mafuul}")
            print(f"      الدلالة  : {m.meaning}")
    else:
        print("  (لا أوزان مزيدة)")

    return True


def main():
    print("=" * 60)
    print("   اختبار المحرك الاشتقاقي — الجذور العشر التجريبية")
    print("=" * 60)

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    roots = data["roots"]
    passed = 0
    for root_data in roots:
        ok = test_root(root_data)
        if ok:
            passed += 1

    print(f"\n{'═'*60}")
    print(f"النتيجة: {passed}/{len(roots)} جذور اجتازت الاختبار")


if __name__ == "__main__":
    main()
