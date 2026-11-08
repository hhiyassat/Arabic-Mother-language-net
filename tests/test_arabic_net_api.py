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
    assert f["mutawaa"][0]["value"] == "ٱنْكَسَرَ" and f["mutawaa"][0]["status"] == "MEASURED_ACCEPTED"
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


def test_r1w_mutawi_takes_hfn_vowelling():
    """فحص الجذور 1: مطاوع R1W كان بتشكيل الوسيط («انقلب»)؛ يؤخذ من حدث HFN المربوط ويُحفظ النصّ."""
    from word_tree import ahdath as A
    rows = [x for x in A._table() if x["route"] == "R1W"]
    if not A._hfn_verbs() or not rows:
        pytest.skip("HFN release or R1W pool not available")
    q = [x for x in rows if x["verb"] == "قَلَبَ"]
    assert q and q[0]["mutawi"] == "ٱنْقَلَبَ" and q[0]["mutawi_text"] == "انقلب"          # HFN v44+: همزة الوصل ٱ
    import unicodedata
    nfc = lambda s: unicodedata.normalize("NFC", s)
    assert sum(nfc(x["mutawi"]).replace("ٱ", "ا") != nfc(x["mutawi_text"]) for x in rows) == 27


def test_maqayis_fallback_finds_doubled_and_naqis_keys(monkeypatch):
    """فحص الجذور 1: المقاييس تكتب المضعّف حرفين (رب) والناقص بالألف المقصورة (دنى)؛ الاحتياط كان لا يجدهما."""
    from arabic_net_api import roots as R
    if not R._maqayis():
        pytest.skip("maqayis_all_roots.json not available")
    monkeypatch.setattr(R, "_root_meaning", lambda: (lambda r: {}))
    for root, key in (("ربب", "رب"), ("حقق", "حق"), ("دنو", "دني")):          # K يوحّد ى→ي
        m = R.meaning(root)
        assert m and m[0]["evidence"].endswith(f"key={key}"), root
    assert R.key_variants("يدي")[:2] == ["يدى", "يدو"] and "يد" not in R.key_variants("يدي")          # الثنائي الملتبس (يد) لا تسترجع به الواجهة
    assert R.key_variants("يدي", biliteral_naqis=True)[-1] == "يد"


def test_r1w_mutawi_flags_text_only_forms():
    """فحص الجذور، الدفعة 2: مطاوعٌ من نصّ الوسيط بلا حدث HFN يُعلَّم ولا يُغيَّر."""
    import unicodedata
    from word_tree import ahdath as A
    n = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
    rows = {(x["root"], n(x["mutawi"])): x for x in A._table() if x["route"] == "R1W"}
    assert rows[("صوب", n("تصوَّبَ"))]["mutawi_flags"] == ["PARTIAL_VOWELLING"]
    assert rows[("صوب", n("تصوَّبَ"))]["mutawi_src"] == "WASIT_TEXT"
    assert "ROOT_LETTERS_MISSING" in rows[("طبع", n("انْعَلَبَعَ"))]["mutawi_flags"]
    # المضعّف: الشدّة تُسقط تكرار الحرف — اصْطَفَّ من صفف ليس تالفاً
    assert "ROOT_LETTERS_MISSING" not in rows[("صفف", n("اصْطَفَّ"))]["mutawi_flags"]
    assert all(not x["mutawi_flags"] for x in rows.values() if x["mutawi_src"] == "HFN")


def test_audit_form_is_accepts_hfn_naqis_label():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audit"))
    import roots_audit as RA
    assert RA.form_is("أَفْعَى (أفعل ناقص)", "أَفْعَلَ")
    assert RA.form_is("أَفْعَلَ", "أَفْعَلَ")
    assert not RA.form_is("فَعَّلَ", "أَفْعَلَ")


def test_wazn_skips_unresolved_mutawaa_base():
    """فحص الجذور، الدفعة 3: base_of يعيد base فارغاً لـBASE_UNRESOLVED — لا تُعرض قيمةٌ فارغة."""
    from arabic_net_api import wazn as W
    fs = [f for f in W.features("تَطَهَّرَ") if f["feature"] == "mutawaa_base"]
    assert all(f["value"] for f in fs)
    assert all(f["source"] == "mutawaa_v7.tsv" for f in W.features("انْكَسَرَ"))


def test_maqayis_combined_naqis_hamza_entries():
    """فحص الجذور، الدفعة 4: ابن فارس يجمع المعتلّ والمهموز في مادّة (خطوأ) والواويّ واليائيّ في مادّة (بروى)."""
    from arabic_net_api import roots as R
    t = R._maqayis()
    pick = lambda r: next((v for v in [r] + R.key_variants(r) if v in t), None)  # noqa: E731
    assert pick("خطء") == pick("خطو") == "خطوء"
    assert pick("بري") == "بروي"
    assert pick("برء") is None          # برأ مادّة مهموزة مستقلّة: لا تُحمل على «بروى» المعتلّة


def test_maqayis_embedded_roots_from_full_text():
    """فحص الجذور، الدفعة 5: مادّةٌ قطّعها الاستخراج في سجلّ غيرها تُسترجع من body_text الكامل."""
    from unittest import mock
    from arabic_net_api import roots as R
    if not R._embedded():
        import pytest
        pytest.skip("data/maqayis_embedded.tsv غائب")
    with mock.patch.object(R, "_root_meaning", lambda: (lambda r: {})):
        for root, host in (("يوم", "يوح"), ("سخر", "سخد"), ("برر", "بذ"), ("قرأ", "قري")):
            m = R.meaning(root)
            assert m and f"«{host}»" in m[0]["evidence"], root
        assert R.meaning("يوم")[0]["value"][0].startswith("الياء والواو والميم")


def test_meaning_alt_reduplicated_and_naqis():
    """فحص كلّ الجذور: الرباعي المضاعف يُذكر في مادّة الثلاثي المضاعف (زلزل في زلل)، والناقص و/ي مادّة واحدة (دمو/دمي)."""
    from arabic_net_api import roots as R
    assert R.alt_roots("زلزل") == [("زلل", "REDUPLICATED_UNDER_GEMINATE", True)]
    assert ("دمي", "NAQIS_WAW_YA", False) in R.alt_roots("دمو")
    m = R.meaning("زلزل")
    if m:   # البنك حاضر
        assert all(x["match"] in ("ROOT", "ROOT_ALT") for x in m)


def test_maqayis_hamza_in_naqis_entry():
    """فحص كلّ الجذور: «وأمّا المهموز …» في مادّة المعتلّ (درأ في درى، فتأ في فتى) — بنصّ ابن فارس."""
    from arabic_net_api import roots as R
    e = R._embedded()
    if not e:
        import pytest
        pytest.skip("data/maqayis_embedded.tsv غائب")
    assert e["درء"]["host_display"] == "درى" and e["درء"]["how"] == "SAME_ENTRY_HAMZ"
    assert e["حرق"]["host_display"] == "حرف"          # «الحاء ولراء والقاف»: الألف ساقطة في OCR


def test_maqayis_absent_in_book_from_editor_notes():
    """عون وعوم وعول وعوق أهملها ابن فارس، ورتل ورتق سقطت من الأصل (حاشية هارون): غيابها من الكتاب لا من الاستخراج."""
    from arabic_net_api import roots as R
    a = R.absent_in_book()
    assert a["عون"]["kind"] == "OMITTED_BY_AUTHOR" and a["رتل"]["kind"] == "MANUSCRIPT_LACUNA"
    assert "عون" not in R._maqayis() and "عوض" in R._maqayis()


def test_withdrawn_events_not_served():
    """HFN-D067: أحداث v42 المسحوبة (الحق = أَلْحَقَ، فءخذ = فَأَخَذَ) لا تُخدَم بالجذر ولا بالكلمة، وevent() يحذّر."""
    from arabic_net_api import hfn
    h = hfn.api()
    w = [i for i, e in h.events.items() if e.get("event_review_v36", "").startswith("WITHDRAWN")]
    if not w:
        import pytest
        pytest.skip("release without withdrawn events")
    assert not h.lookup_root("الحق")["payload"]["events"]
    assert not h.lookup_root("فءخذ")["payload"]["events"]
    assert all(i not in {b["event_id"] for b in h.lookup_word(h.events[i]["verb"])["payload"]["events"]} for i in w)
    assert any(r.startswith("EVENT_WITHDRAWN") for r in h.event(w[0])["residuals"])


def test_wasl_mushaf_matches_engine_spelling():
    """HFN-D068: همزة الوصل ٱ في HFN (رسم المصحف بحكم المالك) تطابق اِ في wazn-net وا في الإصدارات السابقة."""
    from arabic_net_api._common import K, match_kind, wasl
    assert K("ٱسْتَعْلَمَ") == K("اسْتَعْلَمَ") == "استعلم"
    assert match_kind("ٱسْتَعْلَمَ", "اِسْتَعْلَمَ") == "EXACT"
    assert match_kind("ٱنْطِلَاق", "انْطِلَاق") == "EXACT"
    assert match_kind("ٱتَّبَعَ", "اِتَّبَعَ") == "EXACT"          # الافتعال المدغم: الحرف مشدّد لا ساكن
    assert wasl("أَكْرَمَ") == "أَكْرَمَ"              # همزة القطع لا تُمسّ
    assert match_kind("ٱسْتَعْلَمَ", "أَعْلَمَ") == "LETTERS"
