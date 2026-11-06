"""arabic_net_api: الواجهة الجامعة فوق HFN وwazn-net وAMLN والجذور (قراءة فقط)."""
import os

import pytest

HOME = os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net"))
need = pytest.mark.skipif(not all(os.path.isdir(os.path.join(HOME, d)) for d in
                                  ("HusseinFrameNet", "Arabic-Mother-language-wazn-net")),
                          reason="arabic-net repos not present")


@need
def test_verb_all_providers():
    from arabic_net_api import verb
    r = verb("كَسَرَ", root="كسر")
    f = r["features"]
    assert r["missing"] == [] and r["rank"] == "CANDIDATE"
    assert f["masdar"][0]["value"] == "كَسْر" and f["ism_fail"][0]["value"] == "كَاسِر"
    assert f["mutawaa"][0]["value"] == "انْكَسَرَ" and f["mutawaa"][0]["status"] == "MEASURED_ACCEPTED"
    assert {x["route"] for x in f["ahdath_effect"]} >= {"R1"}
    assert all(x["match"] == "EXACT" and x["is_fact"] is False for v in f.values() for x in v)


@need
def test_exact_match_is_default_and_nothing_dropped_silently():
    from arabic_net_api import verb
    r = verb("كسر")  # بلا حركات (كما يرد من WordNet): لا مقبول ولا مرفوض — كلّه في pending بسببه
    assert r["features"] == {} and not r["excluded"] and r["pending"]
    assert all("pending_reason" in x and x["match"] == "UNVOWELLED_QUERY" for x in r["pending"])
    r2 = verb("كسر", match="letters")
    assert r2["features"] and not r2["excluded"] and not r2["pending"]


@need
def test_taadiya_and_jiha():
    from arabic_net_api import verb
    f = verb("ضَجِرَ")["features"]
    assert f["taadiya"][0]["value"] == "أَضْجَرَ" and f["taadiya"][0]["route"] == "T_JAL"
    assert f["fail_jiha"][0]["value"] == "MAHALL" and f["fail_jiha"][0]["musabbib_verb"] == "أَضْجَرَ"
    assert verb("حَسُنَ")["features"]["fail_jiha"][0]["route"] == "J_SAJIYYA"


@need
def test_root_and_sources():
    from arabic_net_api import root, sources
    r = root("كسر")
    assert r["features"]["root_meaning"] and all(x["status"] == "UNVERIFIED_OCR" for x in r["features"]["root_meaning"])
    assert r["features"]["hfn_event"]
    s = sources()
    assert s["hfn"]["release"].startswith("HFN_release_v") and len(s["hfn"]["manifest_sha256"]) == 64
    assert all(s[k]["commit"] for k in ("hfn", "wazn", "amln", "maqayis"))


@need
def test_failing_provider_reported_not_raised(monkeypatch):
    import arabic_net_api as A

    def boom(v):
        raise RuntimeError("down")
    monkeypatch.setattr(A.wazn, "features", boom)
    r = A.verb("كَسَرَ")
    assert any(m["provider"] == "wazn" for m in r["missing"]) and "masdar" in r["features"]


@need
def test_different_vowelling_rejected_only_with_evidence():
    """ضَرَبَ لا يأخذ جهة ضَرُبَ (HFN: حدثان مستقلّان)؛ والتشكيل المخالف بلا دليل لا يُرفض."""
    from arabic_net_api import verb
    from word_tree import ahdath as W
    from word_tree import vowel_evidence as V
    assert W.jiha("ضَرَبَ") == []
    rej = W.jiha("ضَرَبَ", keep_rejected=True)
    assert rej and rej[0]["match"] == "DIFFERENT_VERB" and rej[0]["vowel_evidence"][0]["source"] == "HFN"
    assert W.jiha("ضَرُبَ")[0]["match"] == "EXACT"
    assert W.jiha("ضرب")[0]["match"] == "UNVOWELLED_QUERY"          # من WordNet بلا حركات: يُبقى معلَّماً
    r = verb("ضَرَبَ")
    assert "fail_jiha" not in r["features"]
    assert any(x["feature"] == "fail_jiha" and "HFN" in x["excluded_reason"] for x in r["excluded"])
    # الوسيط يكتب «اصْفَرَ» بلا شدّة: لا يشهد له HFN حدثاً مستقلاً → لا دليل → لا يُرفض
    j = V.judge("اصْفَرَّ", "اصْفَرَ")
    assert j["match"] == "UNRESOLVED" and j["keep"] and j["evidence"][0]["source"] == "NONE"
    assert V.judge("عَلِمَ", "عَلَّمَ")["match"] == "DIFFERENT_VERB"
    assert V.judge("اَشْرَقَ", "أَشْرَقَ")["keep"]                       # رسم الهمزة رسمٌ لا دليل


@need
def test_english_translation_is_recorded_not_decisive():
    """الترجمة الإنجليزية دليلٌ يُسجَّل ويُعلَّم، ولا يَرفض وحده (قيس: 10/15، ويلسون 0.42 < 0.78)."""
    from word_tree import vowel_evidence as V
    if V.english("beat.v.02") is None:
        pytest.skip("nltk wordnet غير متاح")
    j = V.judge("ضرب", "ضَرُبَ", "لازم", synset="beat.v.02")
    assert j["keep"] and j["flags"] == ["en_conflict"] and j["evidence"][0]["source"] == "EN"
    assert j["evidence"][0]["en_trans"] == "متعدي"
    e = V.judge("ضَرُبَ", "ضَرُبَ", "لازم", synset="beat.v.02")
    assert e["match"] == "EXACT" and e["flags"] == ["en_conflict"]


def test_ahdath_loads_standalone():
    """عامل sarf يحمّل word_tree/ahdath.py منفرداً (importlib، python3 -I) — يجب أن يعمل بلا حزمة."""
    import subprocess
    import sys
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "word_tree", "ahdath.py")
    code = ("import importlib.util,sys\n"
            f"s=importlib.util.spec_from_file_location('_up_amln_ahdath',{p!r})\n"
            "m=importlib.util.module_from_spec(s);sys.modules['_up_amln_ahdath']=m;s.loader.exec_module(m)\n"
            "print(m.jiha('ضَرَبَ'), [x['match'] for x in m.jiha('ضَرُبَ')])")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd="/")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[] ['EXACT']"
