"""
اختبار محرك التكسير على الجذور العشرة التجريبية
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from word_tree.engines.plural_engine import (
    build_plural_set_from_dict,
    wazn_frequency,
    PluralSet,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_roots.json')


def test_root(root_data: dict) -> tuple[bool, PluralSet | None]:
    label   = root_data["display"]
    letters = root_data["letters"]
    rt      = root_data["root_type"]

    print(f"\n{'═'*60}")
    print(f"الجذر: {label}  ({letters})  |  النوع: {rt}")
    print(f"{'─'*60}")

    try:
        ps = build_plural_set_from_dict(root_data)
    except Exception as e:
        print(f"  ❌ خطأ: {e}")
        import traceback; traceback.print_exc()
        return False, None

    stored    = ps.stored()
    generated = ps.generated()

    if stored:
        print(f"  جموع سماعية ({len(stored)}):")
        for p in stored:
            print(f"    {p.form:20}  وزن: {p.wazn}")
    else:
        print("  (لا جموع سماعية مخزَّنة)")

    if generated:
        print(f"  جموع قياسية ({len(generated)}):")
        for p in generated:
            print(f"    {p.form:20}  وزن: {p.wazn}  [قياس]")

    if not stored and not generated:
        print("  ∅ لا جموع")

    return True, ps


def main():
    print("=" * 60)
    print("   اختبار محرك التكسير — الجذور العشر التجريبية")
    print("=" * 60)

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    roots = data["roots"]
    all_sets: list[PluralSet] = []
    passed = 0

    for rd in roots:
        ok, ps = test_root(rd)
        if ok:
            passed += 1
            if ps:
                all_sets.append(ps)

    # ── إحصاء الأوزان ─────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"النتيجة: {passed}/{len(roots)} جذور اجتازت الاختبار")

    freq = wazn_frequency(all_sets)
    if freq:
        print(f"\n{'─'*60}")
        print("  تكرار الأوزان (الجموع السماعية والقياسية):")
        for wazn, count in freq.items():
            print(f"    {wazn:20}  ×{count}")


if __name__ == "__main__":
    main()
