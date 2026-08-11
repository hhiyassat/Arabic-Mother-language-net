"""
اختبار محرك التوافق على الجذور العشرة التجريبية
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from word_tree.engines.compatibility_engine import (
    build_compatibility_map,
    parse_network_from_dict,
    parse_exceptions_from_dict,
    semantic_neighbors,
    RootCompatibilityMap,
    NetworkRelations,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_roots.json')


def main():
    print("=" * 60)
    print("   اختبار محرك التوافق — الجذور العشر التجريبية")
    print("=" * 60)

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    roots_data = data["roots"]

    # ── الشبكة الدلالية لكل جذر ────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  الشبكة الدلالية:")
    networks: dict[str, NetworkRelations] = {}
    for rd in roots_data:
        net = parse_network_from_dict(rd)
        networks[rd["letters"]] = net
        exc = parse_exceptions_from_dict(rd)

        print(f"\n  ● {rd['display']} ({rd['letters']})")
        if net.yushbih:   print(f"      يشبه   : {', '.join(net.yushbih)}")
        if net.yuaakis:   print(f"      يعاكس  : {', '.join(net.yuaakis)}")
        if net.yastlzim:  print(f"      يستلزم : {', '.join(net.yastlzim)}")
        if net.aamma:     print(f"      أعمّ    : {', '.join(net.aamma)}")
        if net.akhass:    print(f"      أخصّ    : {', '.join(net.akhass)}")
        if exc:
            for e in exc:
                print(f"      استثناء: [{e.slot}] → {e.override_type}  ({e.note})")

    # ── بناء خريطة التوافق ──────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  بناء خريطة التوافق الكاملة...")
    rcm = build_compatibility_map(roots_data)
    print(f"  تم حساب {len(rcm.results)} زوج من {len(rcm.roots)} جذر")

    # ── التسلسلات البنيوية ──────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  التسلسلات البنيوية (خرج A → دخل B):")
    chains = rcm.chains()
    if chains:
        for a, b in chains:
            print(f"    {a} → {b}")
    else:
        print("    (لا تسلسلات مباشرة)")

    # ── أعلى الأزواج توافقاً ────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  أعلى 5 أزواج من حيث درجة التوافق:")
    for res in rcm.top_pairs(5):
        print(f"    {res.root_a} ↔ {res.root_b}  :  {res.summary()}")

    # ── التوافق لكل جذر ─────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  أكثر جذر متوافقاً مع غيره:")
    root_scores: dict[str, float] = {}
    for r in rcm.roots:
        compatible = rcm.compatible_with(r, min_score=0.3)
        total = sum(x.score for x in compatible)
        root_scores[r] = total
    for root, total in sorted(root_scores.items(), key=lambda x: -x[1]):
        count = len(rcm.compatible_with(root, min_score=0.3))
        print(f"    {root:6}  مجموع الدرجات: {total:.2f}  ({count} جذر متوافق)")

    # ── الجذور المتعاكسة ────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("  الجذور التي لها تعاكس صريح:")
    for (a, b), res in rcm.results.items():
        if res.net_relation_ab == "يعاكس" or res.net_relation_ba == "يعاكس":
            print(f"    {a} ↔ {b}  (درجة: {res.score:.2f})")

    print(f"\n{'═'*60}")
    print("  اكتمل الاختبار ✓")


if __name__ == "__main__":
    main()
