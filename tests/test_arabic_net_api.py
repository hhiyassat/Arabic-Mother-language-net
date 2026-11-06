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
    r = verb("كسر")  # بلا حركات: لا شيء مطابق مشكولاً، وكلّه في excluded بسببه
    assert r["features"] == {} and r["excluded"]
    assert all("excluded_reason" in x for x in r["excluded"])
    r2 = verb("كسر", match="letters")
    assert r2["features"] and not r2["excluded"]


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
