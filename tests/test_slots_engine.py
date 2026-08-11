"""
اختبار محرك الفتحات على الجذور العشرة التجريبية
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from word_tree.engines.slots_engine import (
    parse_predicate_from_dict,
    find_compatible_pairs,
    group_by_predicate,
    group_by_signature,
    PredicateStructure,
)
from word_tree.core.types import SemanticType

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_roots.json')


def test_root(root_data: dict) -> bool:
    label   = root_data["display"]
    letters = root_data["letters"]
    print(f"\n{'═'*60}")
    print(f"الجذر: {label}  ({letters})")
    print(f"{'─'*60}")

    try:
        ps = parse_predicate_from_dict(root_data)
    except Exception as e:
        print(f"  ❌ خطأ في التحليل: {e}")
        import traceback; traceback.print_exc()
        return False

    print(f"  المسند الأولي : {ps.primary_predicate.value}")
    print(f"  الملخص        : {ps.summary()}")
    print(f"  التوقيع       : {tuple(t.value for t in ps.signature())}")
    print(f"  الفتحات الإلزامية ({len(ps.mandatory())}):")
    for s in ps.mandatory():
        print(f"    {s.name:10} → {s.sem_type.value:10}  مثال: {s.example}")
    if ps.optional_slots():
        print(f"  الفتحات الاختيارية ({len(ps.optional_slots())}):")
        for s in ps.optional_slots():
            prep = f"[{s.preposition}] " if s.preposition else ""
            print(f"    {s.name:10} {prep}→ {s.sem_type.value:10}  مثال: {s.example}")
    return True


def main():
    print("=" * 60)
    print("   اختبار محرك الفتحات — الجذور العشر التجريبية")
    print("=" * 60)

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    roots = data["roots"]
    structures: list[PredicateStructure] = []
    passed = 0

    for rd in roots:
        ok = test_root(rd)
        if ok:
            passed += 1
            structures.append(parse_predicate_from_dict(rd))

    # ── تحليل جماعي ───────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"النتيجة: {passed}/{len(roots)} جذور اجتازت الاختبار")

    print(f"\n{'─'*60}")
    print("  التجميع بحسب التوقيع الدلالي:")
    groups = group_by_signature(structures)
    for sig, members in sorted(groups.items(), key=lambda x: -len(x[1])):
        sig_str = " + ".join(t.value for t in sig)
        roots_str = "، ".join(m.root for m in members)
        print(f"    [{sig_str}]  ← {roots_str}")

    print(f"\n{'─'*60}")
    print("  أزواج يمكن ربطها تركيبياً (A → B):")
    pairs = find_compatible_pairs(structures)
    if pairs:
        for a, b in pairs:
            print(f"    {a.root} → {b.root}")
    else:
        print("    (لا أزواج متوافقة مباشرة في هذه المجموعة)")

    print(f"\n{'─'*60}")
    print("  التجميع بحسب المسند الأولي:")
    by_pred = group_by_predicate(structures)
    for pred, members in by_pred.items():
        roots_str = "، ".join(m.root for m in members)
        print(f"    {pred.value:12} ← {roots_str}")


if __name__ == "__main__":
    main()
