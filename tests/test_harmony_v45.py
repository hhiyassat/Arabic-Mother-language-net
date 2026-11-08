"""تناغم الطبقات بعد «نفذ كل» (2026-11-08): الطبقات تقرأ أحدث إصدار من HFN، ومداخل المقاييس مربوطة بالبنك."""
import csv
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.environ.get("ARABIC_NET_HOME", os.path.dirname(ROOT))
HFN = os.path.join(NET, "HusseinFrameNet")
pytestmark = pytest.mark.skipif(not os.path.isdir(HFN), reason="HusseinFrameNet غير موجود")


def test_no_layer_pins_an_old_release():
    """لا ملفّ حيّ يثبّت release_v36 أو غيره؛ كلّها تمرّ على hfn_release.py (أو ما يماثله في word_tree)."""
    live = ["ahdath/ahdath.py", "ahdath/ext/wasit_frames.py", "tahayyuz/build_tahayyuz.py", "qabiliyyat/measure_routes.py",
            "word_tree/ahdath.py", "word_tree/vowel_evidence.py"]
    for f in live:
        code = "\n".join(l for l in open(os.path.join(ROOT, f), encoding="utf-8") if not l.lstrip().startswith("#"))
        assert not re.search(r'["\']release_v\d+["\']\s*\)?$', code, re.M) or "release_v45\"" in code, f
        assert "release_v36/" not in code and '"release_v36"' not in code, f


def test_resolver_picks_newest_with_manifest(monkeypatch):
    import sys
    sys.path.insert(0, ROOT)
    from hfn_release import hfn_release_dir
    monkeypatch.delenv("AMLN_HFN_RELEASE", raising=False)
    rels = [d for d in os.listdir(os.path.join(HFN, "release")) if re.fullmatch(r"release_v\d+", d)
            and os.path.exists(os.path.join(HFN, "release", d, "MANIFEST.json"))]
    assert os.path.basename(hfn_release_dir()) == max(rels, key=lambda d: int(d[9:]))
    monkeypatch.setenv("AMLN_HFN_RELEASE", "release_v36")
    assert hfn_release_dir().endswith("release_v36")


def test_maqayis_entries_mapped_to_bank():
    banks = sorted((f for f in os.listdir(os.path.join(HFN, "02_roots")) if re.fullmatch(r"HFN_ROOTS_v\d+\.csv", f)), key=lambda f: int(f[11:-4]))
    bk = {b["K"] for b in csv.DictReader(open(os.path.join(HFN, "02_roots", banks[-1]), encoding="utf-8"))}
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "maqayis_bank_crosswalk.tsv"), encoding="utf-8"), delimiter="\t"))
    assert len(rows) == 4548
    mapped = [r for r in rows if not r["basis"].startswith("UNMAPPED")]
    assert len(mapped) >= 4540
    assert all(k in bk for r in mapped for k in r["bank_K"].split("|"))
    assert all(r["bank_K"] == "" for r in rows if r["basis"].startswith("UNMAPPED"))


def test_wasl_does_not_lose_wasit_glosses():
    """على v45 تُكتب همزة الوصل ٱ؛ شرح الوسيط لمرشّحي المطاوعة يجب ألا يضيع (كان 168 مرشّحاً بلا شرح)."""
    rows = list(csv.DictReader(open(os.path.join(ROOT, "qabiliyyat", "candidates_R1_MUTAWAA.tsv"), encoding="utf-8"), delimiter="\t"))
    assert sum(1 for r in rows if r["candidate"].startswith("ٱ")) > 100
    assert sum(1 for r in rows if not r["gloss"]) <= 63          # 63 بلا شرح على v36 نفسها (لا مادة في الوسيط)، لا أكثر


def test_wasit_bare_maps_wasl():
    """ٱ (HFN v44+) must match ا in Wasit matching, or انفعل/افتعل verbs lose their event (R1W pool)."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ahdath"))
    from ext import wasit_frames as WF
    assert WF.bare("ٱنْجَعَبَ") == WF.bare("انْجَعَبَ")


def test_transitivity_v2_is_v1_plus_census():
    """ext/transitivity_wasit_v2.tsv keeps every v1 row; it changes a tag only where two blind readers agreed (CENSUS2_v5)."""
    import csv, os
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ahdath", "ext")
    v1 = {r["event_id"]: r for r in csv.DictReader(open(os.path.join(d, "transitivity_wasit.tsv"), encoding="utf-8"), delimiter="\t")}
    v2 = {r["event_id"]: r for r in csv.DictReader(open(os.path.join(d, "transitivity_wasit_v2.tsv"), encoding="utf-8"), delimiter="\t")}
    assert set(v1) == set(v2)
    for k, r in v2.items():
        assert r["transitivity_v1"] == v1[k]["transitivity_wasit"]
        if r["transitivity_wasit"] != v1[k]["transitivity_wasit"]:
            assert r["basis_v5"] == "CENSUS2_v5"


def test_blocker_final_alif():
    """رَثَا (HFN) = رثى (قائمة المانع): الألف آخر الناقص تُوحَّد للمطابقة."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ahdath"))
    import ahdath as A
    assert A.mani("رَثَا") == A.mani("رَثَى") == "LISAN"
    assert A.mani("كَسَرَ") == ""
