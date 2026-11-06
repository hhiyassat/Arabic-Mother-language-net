"""اختبارات «الحدث يغيّر صفة من وقع منه ومن وقع عليه» — من أمثلة ASAS_NAZARI.md §7.

المدخَل هنا بنيةٌ لا جملة: لا يوجد مُعرِب يحلّل الجملة، فكلّ مثال يُعطى فعله وصيغته وبناؤه
(معلوم/مجهول) وجنس فاعله، ويُختبر ما يخرج من القواعد.
تحتاج rules_R1.tsv و pool_R2.tsv (python3 ahdath/ahdath.py build) و HusseinFrameNet release_v36.
"""
import csv
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ahdath"))
import ahdath as A  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(A.HFN, "events.csv")),
                                reason="HusseinFrameNet release_v36 غير موجود")


def _tsv(name):
    return {r["verb"]: r for r in csv.DictReader(open(os.path.join(ROOT, "ahdath", name), encoding="utf-8"), delimiter="\t")}


@pytest.fixture(scope="module")
def R1():
    return _tsv("rules_R1.tsv")


@pytest.fixture(scope="module")
def R2():
    return _tsv("pool_R2.tsv")


# ── أ. الأدوار ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def HFN():
    ev, lus = A.load()
    return {e["verb"]: e for e in ev if e["form"].startswith("فَعَلَ") or e["form"].startswith("فَعِلَ")}, lus


def test_01_daraba_ustadh_talib(R2, HFN):
    """ضَرَبَ الأُسْتَاذُ الطَّالِبَ — والاسمان مسموعان.
    v2: ضَرَبَ موسوم «مشترك» في HFN، فخرج من R2 بعد قصره على «متعدي»؛ ولا يقع عليه المانع."""
    ev, lus = HFN
    assert "ضَرَبَ" not in R2 and ev["ضَرَبَ"]["transitivity"] == "مشترك"
    r = A.participles(ev["ضَرَبَ"], lus)
    assert (r["fail"], r["fail_src"], r["maful"], r["maful_src"]) == ("ضَارِب", "SAMAI", "مَضْرُوب", "SAMAI")
    assert A.mani("ضَرَبَ") == ""
    assert A.roles("فَعَلَ", "malum", "MUATHTHIR") == {"فاعل": "مؤثّر", "مفعول به": "متأثّر"}
    assert A.ikhtiyar("noun.person") == "مختار"


def test_02_kasara_fa_inkasara(R1):
    """كَسَرَ الوَلَدُ الإِنَاءَ فَانْكَسَرَ — المطاوعة دليل التأثير، ومصدر المطاوع اسم الأثر."""
    r = R1["كَسَرَ"]
    assert (r["mutawaa"], r["athar"], r["effect"]) == ("انْكَسَرَ", "انْكِسَار", "MUATHTHIR")
    assert (r["fail"], r["maful"]) == ("كَاسِر", "مَكْسُور")


def test_03_inkasara_al_inau():
    """انْكَسَرَ الإِنَاءُ — الفاعل النحويّ متأثّر، ولا يخرج «مؤثّر» (والحالة السلبية ٢٠)."""
    assert A.roles("انْفَعَلَ", "malum", "MUATHTHIR") == {"فاعل": "متأثّر"}
    assert "مؤثّر" not in A.roles("انْفَعَلَ", "malum", "MUATHTHIR").values()
    f, _, _ = A.derive_mazid("انْكَسَرَ", "كسر", False, "انْفَعَلَ")
    assert f == "مُنْكَسِر"


def test_04_qata_tu_al_habla(R1):
    """قَطَعْتُ الحَبْلَ فَانْقَطَعَ — مثال الجرجاني «القاطع ما دام قاطعاً»."""
    r = R1["قَطَعَ"]
    assert (r["fail"], r["maful"], r["mutawaa"], r["athar"]) == ("قَاطِع", "مَقْطُوع", "انْقَطَعَ", "انْقِطَاع")


def test_05_ahraqat_al_nar():
    """أَحْرَقَتِ النَّارُ الثَّوْبَ — فاعل غير مختار؛ والاسمان قياساً من أَفْعَلَ."""
    assert A.ikhtiyar("noun.phenomenon") == "غير مختار"
    assert A.derive_mazid("أَحْرَقَ", "حرق", True, "أَفْعَلَ")[:2] == ("مُحْرِق", "مُحْرَق")


def test_06_atfaa_hamza_not_guessed():
    """أَطْفَأَ — مهموز اللام في المزيد: لا يُقاس آليّاً (يبقى للمسموع أو للمراجعة)."""
    assert A.derive_mazid("أَطْفَأَ", "طفء", True, "أَفْعَلَ") is None


def test_07_duriba_al_talib():
    """ضُرِبَ الطَّالِبُ — نائب الفاعل متأثّر، ولا يُخترع للمؤثّر طرف."""
    assert A.roles("فَعَلَ", "majhul", "MUATHTHIR") == {"نائب فاعل": "متأثّر"}


def test_08_raaytu_al_hilal(R2):
    """رَأَيْتُ الهِلَالَ — متعدٍّ بلا علاج: المانع أفعال القلوب."""
    assert R2["رَأَى"]["mani"] == "QULUB" and R2["رَأَى"]["effect"] == "LA_ATHAR"
    assert A.roles("فَعَلَ", "malum", "LA_ATHAR")["مفعول به"] == "لا أثر"


def test_09_alima_zaydun_al_khabar(HFN):
    """عَلِمَ زَيْدٌ الخَبَرَ — «العلم تابع للمعلوم غير مؤثر فيه». (v2: عَلِمَ «مشترك» فليس في R2.)"""
    ev, lus = HFN
    assert A.mani("عَلِمَ") == "QULUB"
    assert A.participles(ev["عَلِمَ"], lus)["maful"] == "مَعْلُوم"


def test_09b_mani_groups():
    """توسيع المانع v2: النصّ (الكليات:27622) والاستنباط، والمستثنى بالشكل."""
    assert A.mani("فَهِمَ") == "GHAYR_ILAJ" and A.mani_src("GHAYR_ILAJ") == "NASS"
    assert A.mani("قَرَأَ") == "LISAN" and A.mani_src("LISAN") == "ISTINBAT"
    assert A.mani("خَشِيَ") == "QALB" and A.mani("تَبِعَ") == "MASIR"
    assert A.mani("كَلَمَ") == "" and A.mani("عَلَمَ") == ""   # كلمه: جرحه؛ علم الشفة: شقّها


def test_10_marartu_bi_zayd():
    """مَرَرْتُ بِزَيْدٍ — اللازم لا يُبنى منه اسم مفعول بلا حرف."""
    f, m, kind = A.derive_thulathi("مرر", False, "مَرَّ")
    assert (f, m, kind) == ("مَارّ", "", "MUDAAF")


def test_11_mata_zaydun():
    """مَاتَ زَيْدٌ — اسم الفاعل قياساً «مَائِت» للحدوث؛ و«مَيِّت» صفة مشبّهة لا تُشتقّ هنا."""
    f, m, kind = A.derive_thulathi("موت", False, "مَاتَ")
    assert (f, m, kind) == ("مَائِت", "", "AJWAF")


def test_12_hasuna_al_wajh():
    """حَسُنَ الوَجْهُ — فَعُلَ: صفة مشبّهة للثبوت، فلا اسم فاعل (التعريفات:470)."""
    ev = {"event_id": "x", "form": "فَعُلَ", "verb": "حَسُنَ", "root_K": "حسن", "transitivity": "لازم"}
    p = A.participles(ev, {})
    assert p["fail"] == "" and p["maful"] == ""


# ── ب. مراتب الزمن ──────────────────────────────────────────────────────────

def test_13_hal():
    assert A.time_rank("HAL")["hukm"] == "حقيقة"


def test_14_madi():
    t = A.time_rank("MADI")
    assert t["hukm"] == "مجاز" and t["khilaf"]


def test_15_mutakallim_la_yabqa():
    assert "القول الثالث" in A.time_rank("MADI", baqi=False)["khilaf"]


def test_16_istiqbal():
    t = A.time_rank("ISTIQBAL")
    assert (t["hukm"], t["khilaf"]) == ("مجاز", "اتفاقاً")


def test_17_darrab_malaka():
    assert A.time_rank("MADI", repeated=True)["rank"] == "MALAKA"


# ── ج. حالات يجب أن تُرفض ───────────────────────────────────────────────────

def test_18_alimtuhu_fa_inalama(R1):
    """عَلِمْتُهُ فَانْعَلَمَ — لا مطاوع لعَلِمَ في المسلك الأوّل."""
    assert "عَلِمَ" not in R1


def test_19_inadama_not_mutawaa(R1):
    """عَدِمْتُهُ فَانْعَدَمَ — «انعدم» في HFN بمعجم واحد، فلا يدخل المسلك الأوّل (خطأ عند الزمخشري)."""
    assert all(r["mutawaa"] != "انْعَدَمَ" for r in R1.values())


def test_20_roles_not_from_nahw():
    """لا يُستنتج role_wujudi من role_nahwi: الفاعل في المطاوع متأثّر لا مؤثّر."""
    assert A.roles("انْفَعَلَ", "malum", "MUATHTHIR")["فاعل"] != A.roles("فَعَلَ", "malum", "MUATHTHIR")["فاعل"]


# ── سلامة الاشتقاق ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("root,verb,trans,expect", [
    ("قول", "قَالَ", True, ("قَائِل", "مَقُول")),
    ("بيع", "بَاعَ", True, ("بَائِع", "مَبِيع")),
    ("رمي", "رَمَى", True, ("رَامٍ", "مَرْمِيّ")),
    ("دعو", "دَعَا", True, ("دَاعٍ", "مَدْعُوّ")),
    ("ءكل", "أَكَلَ", True, ("آكِل", "مَأْكُول")),
    ("سءل", "سَأَلَ", True, ("سَائِل", "مَسْؤُول")),
    ("وعد", "وَعَدَ", True, ("وَاعِد", "مَوْعُود")),
    ("عور", "عَوِرَ", False, ("عَاوِر", "")),
])
def test_derive_thulathi(root, verb, trans, expect):
    assert A.derive_thulathi(root, trans, verb)[:2] == expect


@pytest.mark.parametrize("verb,root,form,expect", [
    ("عَلَّمَ", "علم", "فَعَّلَ", ("مُعَلِّم", "مُعَلَّم")),
    ("قَاتَلَ", "قتل", "فَاعَلَ", ("مُقَاتِل", "مُقَاتَل")),
    ("اسْتَخْرَجَ", "خرج", "اسْتَفْعَلَ", ("مُسْتَخْرِج", "مُسْتَخْرَج")),
    ("تَكَسَّرَ", "كسر", "تَفَعَّلَ", ("مُتَكَسِّر", "مُتَكَسَّر")),
])
def test_derive_mazid(verb, root, form, expect):
    assert A.derive_mazid(verb, root, True, form)[:2] == expect


def test_weak_undecided():
    assert A.derive_thulathi("رءي", True, "رَأَى") is None   # مهموز معتلّ
    assert A.derive_thulathi("شوء", True, "شَاءَ") is None   # أجوف مهموز


# ── v3 (2026-11-06): التعدية وR2 بتعدّي الوسيط ──────────────────────────────────

def _rows(name):
    return list(csv.DictReader(open(os.path.join(ROOT, "ahdath", name), encoding="utf-8"), delimiter="\t"))


def test_21_ahzanahu_jaala():
    """أَمْرَضَهُ: الوسيط «جعله مريضاً» — عبارة الخليل «جعلته حزيناً» (الكتاب:16452)."""
    r = {x["verb"]: x for x in _rows("taadiya_T_JAL.tsv")}
    assert "أَمْرَضَ" in r and r["أَمْرَضَ"]["base"] == "مَرِضَ" and "مريض" in r["أَمْرَضَ"]["jaala"]
    assert all(x["route"] == "T_JAL" and x["rank"] == "CANDIDATE" for x in r.values())


def test_22_taadiya_mani_lazim_afal():
    """المانع: أفعل بلا معنى متعدٍّ في الوسيط لا يدخل حوض T (أَدْلَجَ: ساروا من أول الليل؛ أَغْفَى: نام)."""
    pool = {x["verb"] for x in _rows("taadiya_T_pool.tsv")}
    assert "أَدْلَجَ" not in pool and "أَغْفَى" not in pool


def test_23_r2w_from_wasit():
    """R2 v3: الحوض من تعدّي الوسيط، والعيّنة لا تتداخل مع v1 وv2."""
    pool = _rows("pool_R2_v3.tsv")
    assert pool and all(x["transitivity"] == "متعدي(الوسيط)" for x in pool)
    s3 = {x["event_id"] for x in _rows("sample_R2_v3.tsv")}
    old = {x["event_id"] for x in _rows("sample_R2_v1.tsv") + _rows("sample_R2_v2.tsv")}
    assert not (s3 & old)


def test_24_r1w_wasit_mutawaa():
    """R1W: نصّ الوسيط «مطاوع Yه» — المطاوع من غير انفعل (الكليات:27626)، وصيغة الأصل من شكل النصّ نفسه."""
    pool = _rows("mutawaa_R1W_pool.tsv")
    by = {(A.bare(x["mutawi"]), A.bare(x["base"])): x for x in pool}
    assert ("انكسر", "كسر") in by and ("انهشم", "هشم") in by
    # «تَطَهَّرَ: مطاوع طَهَّرَه» ← فَعَّلَ لا فَعُلَ (طَهُرَ لازم)
    assert A.nfc(by[("تطهر", "طهر")]["base"]) == A.nfc("طَهَّرَ")
    # «تَكَسَّرَ: مطاوع كسّرَه» و«تهشّم: مطاوع هشّمه»: فَعَّلَ غير موجود في HFN، فلا يُبدَل بفَعَلَ
    assert ("تكسر", "كسر") not in by and ("تهشم", "هشم") not in by
    assert all(x["route"] == "R1W" and x["rank"] == "CANDIDATE" for x in pool)
    assert {x["base_match"] for x in pool} <= {"TEXT", "MUT_FORM", "ONLY_FORM"}


def test_25_jiha_sitt():
    """الجهات الستّ «موضوعة لأمكنة مبهمة» (الكليات:25073): subtype=JIHA لا ZARF."""
    import json
    d = json.load(open(os.path.join(ROOT, "data", "wordnet", "wordnet_tahayyuz.json"), encoding="utf-8"))
    e = d[[k for k in d if k != "_meta"][0]]
    assert e["left.n.01"]["class"] == "HAYYIZ_MUBHAM" and e["left.n.01"]["subtype"] == "JIHA"


def test_26_t_tad_blocked():
    """T_TAD: فَعَّلَ بنصّ «جعله/صيّره» — كَبَّرَ ← كَبِرَ «جعله كبيرا»؛ والمسلك محجوب (0.643 < 0.78)."""
    rows = _rows("taadiya_T_TAD.tsv")
    assert any(A.bare(r["verb"]) == "كبر" and "كبير" in r["text_phrase"] for r in rows)
    gold = _rows("taadiya_T_TAD_gold.tsv")
    judged = [g for g in gold if g["label"] != "DEFER"]
    ok = sum(g["label"] == "TAADIYA" for g in judged)
    assert A.wilson(ok, len(judged)) < A.THRESH


def test_27_word_tree_adapter_accepted_only():
    """word_tree.ahdath يقرأ المقبول وحده (R1، R1W، T_JAL) ولا يقرأ المحجوب (R2، T، T_TAD)."""
    from word_tree import ahdath as WA
    s = WA.summary()
    assert set(s) == {"R1", "R1W", "T_JAL"} and all(v > 0 for v in s.values())
    k = WA.for_verb("كَسَرَ")
    assert any(x["route"] == "R1" and x["maful"] == "مَكْسُور" and x["athar"] == "انْكِسَار" for x in k)
    assert all(x["rank"] == "CANDIDATE" for x in WA._table())
