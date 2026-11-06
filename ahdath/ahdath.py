#!/usr/bin/env python3
"""
ahdath.py — الحدث يغيّر صفة من وقع منه ومن وقع عليه (CANDIDATE، قراءة فقط من HFN)

الأساس النظري: ASAS_NAZARI.md «ثانياً» (وافق عليه المالك 2026-11-05).

    python3 ahdath/ahdath.py build     # يبني rules_R1 و pool_R2 و sample_R2
    python3 ahdath/ahdath.py score     # يقيس R2 من gold_R2.tsv

المسلكان:
  R1  فعلٌ له مطاوع «انْفَعَلَ» مشهود (مسلك قابليات R1 المقيس 0.964) ← مؤثّر بنصّ الزمخشري
      «ولا يقع أي: انفعل حيث لا علاج ولا تأثير» (التاج:348191).
  R2  فعلٌ متعدٍّ لا مطاوع له على انفعل ← يُحكم فيه باليد على عيّنة ثم يُقاس.
المانع: أفعال القلوب في الألفيّة (alfiyya.txt:287–289) «أعني رأى خال علمت وجدا…»،
  و«العلم تابع للمعلوم غير مؤثر فيه» (عبد الجبار، شرح الأصول الخمسة:9910).
"""
from __future__ import annotations

import csv
import math
import os
import random
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HFN = os.path.expanduser("~/arabic-net/HusseinFrameNet/release/release_v36")
R1_FILE = os.path.join(HERE, "..", "qabiliyyat", "candidates_R1_MUTAWAA.tsv")
SEED = 20261105
N_SAMPLE = 60
THRESH = 0.78
# v2 بقرار المالك 2026-11-05 «نعم، أعد القياس»: R2 مقصور على «متعدي» (كان: متعدي + مشترك)
R2_TRANS = ("متعدي",)

FATHA, DAMMA, KASRA, SUKUN, SHADDA = "َ", "ُ", "ِ", "ْ", "ّ"
TANWIN_K = "ٍ"
HARAKAT = set("ًٌٍَُِّْٰـ")
WEAK = set("وي")
HAMZA = set("ءأإؤئآ")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def bare(s):
    return "".join(c for c in nfc(s) if c not in HARAKAT)


# ── المانع: أفعال القلوب (ابن مالك) ─────────────────────────────────────────────
# «انصب بفعل القلب جزأي ابتدا … أعني رأى خال علمت وجدا / ظن حسبت وزعمت مع عد … حجا درى وجعل الذ كاعتقد / وهب تعلم»
QULUB = {"رأى", "خال", "علم", "وجد", "ظن", "حسب", "زعم", "عد", "حجا", "درى", "هب", "تعلم"}
# ── توسيع المانع (v2، 2026-11-05) ─────────────────────────────────────────────
# النصّ:
#  الجرجاني، التعريفات:3342–3343: «الفعل العلاجي: ما يحتاج حدوثه إلى تحريك عضو، كالضرب، والشتم.
#     الفعل الغير العلاجي: ما لا يحتاج إليه، كالعلم».
#  الكفوي، الكليات:27620–27623: «علاجا وهو ما يفتقر في إيجاده إلى إعمال جارحة ظاهرة نحو: قمت، وقعدت،
#     وقطعته، ورأيته / وغير علاج نحو: حسن، وقبح، وعدمته، وفقدته، وعلمته، وفهمته، وهويته، وذكرته، والمراد ذكر القلب».
#  كشف الأسرار:9670 والتاج:348191: انفعل لا يقع «إلا حيث يكون علاج وتأثير».
# فالمانع قسمان: (أ) غير علاج أصلاً؛ (ب) علاج في جارحة الفاعل لا تأثير له في المحلّ
# (الرؤية عند الكفوي علاج، والشتم عند الجرجاني علاج، ولا أثر لهما في المرئيّ والمشتوم).
# كلّ مجموعة: (الأفعال مجرّدةً من الحركات، مصدرها: NASS = منصوص بعينه، ISTINBAT = مُلحق بالمعنى).
MANI_GROUPS = {
    "QULUB":     ({"رأى", "خال", "علم", "وجد", "ظن", "حسب", "زعم", "عد", "حجا", "درى", "هب", "تعلم"}, "NASS"),  # الألفيّة
    "GHAYR_ILAJ": ({"فهم", "هوي", "ذكر", "عدم", "فقد"}, "NASS"),                                       # الكليات:27622
    "QALB":      ({"عرف", "يقن", "أيقن", "فقه", "جهل", "نسي", "أحب", "حب", "ود", "كره", "بغض", "أبغض", "مقت",
                   "خشي", "خاف", "هاب", "رهب", "حذر", "رجا", "أمل", "اشتهى", "حسد", "رحم"}, "ISTINBAT"),  # في معنى علم/هوي
    "IDRAK":     ({"سمع", "أبصر", "بصر", "شم", "ذاق", "أحس", "نظر", "لمح", "أدرك", "رمق", "لحظ", "استمع", "شاهد"}, "ISTINBAT"),
    "LISAN":     ({"قال", "قرأ", "تلا", "خطب", "نادى", "دعا", "سأل", "طلب", "استفتى", "أمر", "نهى", "أخبر", "خبر", "حدث",
                   "كلم", "شكر", "حمد", "مدح", "ذم", "هجا", "رثى", "سب", "شتم", "لعن", "ودع", "سلم", "بشر", "أنذر",
                   "وعد", "أوعد", "نصح", "ألك", "أبلغ", "بلغ", "لام", "عذل", "عاتب", "ناجى", "سمى", "وصف", "روى",
                   "أنشد", "فسر", "كذب", "صدق", "أقر", "جحد", "أنكر", "استغفر", "سبح", "كبر", "هلل"}, "ISTINBAT"),
    "MASIR":     ({"تبع", "اتبع", "ردف", "لحق", "قصد", "أتى", "جاء", "زار", "حضر", "شهد", "أم", "تلا", "قفا",
                   "جاور", "صاحب", "رافق", "لازم", "انتظر", "رقب", "رصد", "واجه", "استقبل"}, "ISTINBAT"),
}
QULUB = MANI_GROUPS["QULUB"][0]
IDRAK = MANI_GROUPS["IDRAK"][0]


# أفعال يوافق رسمها المجرّد فعلاً في القائمة ومعناها تأثير في المحلّ (فتُستثنى بالشكل التامّ):
# عَلَمَ الشفة: شقّها؛ كَلَمَه: جرحه؛ سَلَمَ الجلد: دبغه؛ أَمَّه: شجّه آمّة؛ حَسَبَ: عدّ (ليس حَسِبَ الظنّ)
MANI_EXCLUDE = {nfc(v) for v in ("عَلَمَ", "كَلَمَ", "سَلَمَ", "أَمَّ", "حَسَبَ")}


def mani(verb: str) -> str:
    if nfc(verb) in MANI_EXCLUDE:
        return ""
    b = bare(verb)
    for g, (vs, _) in MANI_GROUPS.items():
        if b in vs:
            return g
    return ""


def mani_src(group: str) -> str:
    return MANI_GROUPS[group][1] if group else ""


# ── اسم الفاعل واسم المفعول ───────────────────────────────────────────────────
def _letters(root):
    r = bare(root).replace("أ", "ء").replace("إ", "ء").replace("ؤ", "ء").replace("ئ", "ء").replace("ى", "ي")
    return list(r) if len(r) == 3 else None


def derive_thulathi(root: str, transitive: bool, verb: str = ""):
    """قياس سيبويه في الثلاثيّ: فاعِل ومَفْعُول. يعيد (فاعل، مفعول، نوع الجذر) أو None فيما لم يُقَس.
    الإعلال يُعرف من لفظ الفعل لا من الجذر وحده: عَوِرَ صحيح العين لفظاً، وقالَ أجوف."""
    L = _letters(root)
    if not L:
        return None
    a, b, c = L
    vb = bare(verb)
    if a in WEAK and (b in WEAK or c in WEAK) or (b in WEAK and c in WEAK):
        return None  # لفيف: لا يُشتقّ آليّاً
    if "ء" in L and (b == c or b in WEAK or c in WEAK):
        return None  # مهموز مع إعلال أو تضعيف: رسم الهمزة لا يُقاس آليّاً
    if vb and b in WEAK and not (len(vb) == 3 and vb[1] == "ا"):
        b_weak = False  # العين حرف علّة صحيح في اللفظ: عَوِرَ ، صَيِدَ
    else:
        b_weak = b in WEAK
    if vb and c in WEAK and vb[-1] not in "اىي":
        c_weak = False
    else:
        c_weak = c in WEAK
    if b == c:  # مضعّف: مَرَّ ← مَارّ ، مَمْرُور
        f = a + FATHA + "ا" + b + SHADDA
        m = "مَ" + a + SUKUN + b + DAMMA + "و" + b
        kind = "MUDAAF"
    elif b_weak:  # أجوف: قال ← قائل ، مقول / باع ← بائع ، مبيع
        f = a + FATHA + "ا" + "ئ" + KASRA + c
        m = "مَ" + a + (DAMMA + "و" if b == "و" else KASRA + "ي") + c
        kind = "AJWAF"
    elif c_weak:  # ناقص: رمى ← رامٍ ، مرميّ / دعا ← داعٍ ، مدعوّ
        f = a + FATHA + "ا" + b + TANWIN_K
        m = "مَ" + a + SUKUN + b + (DAMMA + "و" + SHADDA if c == "و" else KASRA + "ي" + SHADDA)
        kind = "NAQIS"
    else:
        if a == "ء":  # أكل ← آكِل ، مَأْكُول
            f = "آ" + b + KASRA + c
            m = "مَ" + "أ" + SUKUN + b + DAMMA + "و" + c
        elif b == "ء":  # سأل ← سائِل ، مَسْؤُول
            f = a + FATHA + "ا" + "ئ" + KASRA + c
            m = "مَ" + a + SUKUN + "ؤ" + DAMMA + "و" + c
        elif c == "ء":  # قرأ ← قارِئ ، مَقْرُوء
            f = a + FATHA + "ا" + b + KASRA + "ئ"
            m = "مَ" + a + SUKUN + b + DAMMA + "و" + "ء"
        else:
            f = a + FATHA + "ا" + b + KASRA + c
            m = "مَ" + a + SUKUN + b + DAMMA + "و" + c
        kind = "SAHIH" if "ء" not in L else "MAHMUZ"
    return nfc(f), (nfc(m) if transitive else ""), kind


def derive_mazid(verb: str, root: str, transitive: bool, form: str = ""):
    """المزيد الصحيح: «مُ» مكان حرف المضارعة وكسر ما قبل الآخر (للفاعل) أو فتحه (للمفعول). المعتلّ والمضعّف لا يُقاس آليّاً."""
    L = _letters(root)
    if not L or set(L) & (WEAK | {"ء"}) or L[1] == L[2]:
        return None
    v = nfc(verb)
    if not v.endswith(FATHA):
        return None
    if v.startswith("أَ"):
        stem = "مُ" + v[2:]
    elif v.startswith("ا"):
        stem = "مُ" + v[1:]
    elif form in ("فَعَّلَ", "فَاعَلَ", "فَعْلَلَ", "تَفَعَّلَ", "تَفَاعَلَ", "تَفَعْلَلَ") or len(bare(v)) == 4 or SHADDA in v:
        stem = "مُ" + v
    else:
        return None
    stem = stem[:-1]  # حذف فتحة الآخر
    # حركة ما قبل الآخر: آخر حرف حركة قبل الحرف الأخير
    last = len(stem) - 1
    i = last - 1
    while i >= 0 and stem[i] not in (FATHA, KASRA, DAMMA):
        if stem[i] not in HARAKAT:
            return None  # لا حركة على ما قبل الآخر
        i -= 1
    f = stem[:i] + KASRA + stem[i + 1:]
    m = stem[:i] + FATHA + stem[i + 1:]
    return nfc(f), (nfc(m) if transitive else ""), "MAZID_SAHIH"


THULATHI = {"فَعَلَ", "فَعِلَ", "فَعَلَ/فَعِلَ"}


def participles(ev: dict, lus: dict):
    """المسموع من معاجم HFN أوّلاً (PARTICIPLE_*LEX)، ثم القياس. يعيد dict."""
    trans = ev["transitivity"] in ("متعدي", "مشترك")
    att = lus.get(ev["event_id"], {})
    f_att = att.get("اسم فاعل", [""])[0]
    m_att = att.get("اسم مفعول", [""])[0]
    form = ev["form"].split(" ")[0]
    if form in THULATHI:
        q = derive_thulathi(ev["root_K"], trans, ev["verb"])
    elif form == "فَعُلَ":
        q = None  # فَعُلَ: صفة مشبّهة للثبوت، لا اسم فاعل للحدوث (التعريفات:470)
    else:
        q = derive_mazid(ev["verb"], ev["root_K"], trans, form)
    out = {"fail": f_att, "fail_src": "SAMAI" if f_att else "",
           "maful": m_att, "maful_src": "SAMAI" if m_att else "",
           "qiyas_kind": q[2] if q else ""}
    if q:
        if not f_att:
            out["fail"], out["fail_src"] = q[0], "QIYAS"
        if not m_att and q[1]:
            out["maful"], out["maful_src"] = q[1], "QIYAS"
    if not trans:
        out["maful"], out["maful_src"] = "", "LAZIM"
    return out


# ── الأدوار ─────────────────────────────────────────────────────────────────
MUKHTAR_LEX = {"noun.person", "noun.animal"}  # «الحيوان: الجسم النامي الحساس المتحرك بالإرادة» (التعريفات:1937)


def ikhtiyar(lexname: str) -> str:
    if not lexname:
        return "DEFER"
    return "مختار" if lexname in MUKHTAR_LEX else "غير مختار"


def roles(form: str, voice: str, effect: str):
    """effect: MUATHTHIR | LA_ATHAR | DEFER — من المسلك.
    يعيد دور كلّ موضع نحويّ في الحقيقة، ولا يُستنتج أحدهما من الآخر."""
    form = form.split(" ")[0]
    if form.startswith("انْفَعَلَ"):  # المطاوع: فاعله النحويّ هو المحلّ المنفعل
        return {"فاعل": "متأثّر"}
    if voice == "majhul":
        return {"نائب فاعل": "متأثّر" if effect == "MUATHTHIR" else ("لا أثر" if effect == "LA_ATHAR" else "DEFER")}
    if effect == "MUATHTHIR":
        return {"فاعل": "مؤثّر", "مفعول به": "متأثّر"}
    if effect == "LA_ATHAR":
        return {"فاعل": "لا أثر في المفعول", "مفعول به": "لا أثر"}
    return {"فاعل": "DEFER", "مفعول به": "DEFER"}


# ── مراتب الزمن ───────────────────────────────────────────────────────────────
def time_rank(when: str, baqi: bool = True, repeated: bool = False):
    """when: HAL | MADI | ISTIQBAL. baqi=False للفعل الذي لا يبقى كالحركة والكلام."""
    if repeated:
        return {"rank": "MALAKA", "hukm": "صفة ثابتة", "src": "التعريفات:4647–4650"}
    if when == "HAL":
        return {"rank": "HAL", "hukm": "حقيقة", "khilaf": "", "src": "الكلّيات:2601"}
    if when == "ISTIQBAL":
        return {"rank": "ISTIQBAL", "hukm": "مجاز", "khilaf": "اتفاقاً", "src": "الكلّيات:2602"}
    if when == "MADI":
        return {"rank": "MADI", "hukm": "مجاز",
                "khilaf": ("قيل حقيقة؛ وعلى القول الثالث حقيقة لأنه مما لا يبقى" if not baqi else "قيل حقيقة"),
                "src": "الكلّيات:2601–2604؛ الفروق:17284"}
    raise ValueError(when)


# ── التحميل ─────────────────────────────────────────────────────────────────
def load():
    ev = list(csv.DictReader(open(os.path.join(HFN, "events.csv"), encoding="utf-8")))
    lus = defaultdict(dict)
    for x in csv.DictReader(open(os.path.join(HFN, "lexical_units.csv"), encoding="utf-8")):
        lus[x["event_id"]].setdefault(x["pos_ar"], []).append(x["lemma"])
    return ev, lus


def nlex(e):
    try:
        return int(e.get("n_lex_v33") or e.get("n_lex") or 0)
    except ValueError:
        return 0


def is_mutawaa_form(form):
    return form.startswith("انْفَعَلَ")


COLS = ["route", "event_id", "root", "verb", "form", "transitivity", "n_lex",
        "fail", "fail_src", "maful", "maful_src", "qiyas_kind",
        "mutawaa", "mutawaa_event", "athar", "mani", "effect", "rank"]


def build():
    ev, lus = load()
    by_id = {e["event_id"]: e for e in ev}
    by_root = defaultdict(list)
    for e in ev:
        by_root[e["root_K"]].append(e)
    # R1
    r1 = list(csv.DictReader(open(R1_FILE, encoding="utf-8"), delimiter="\t"))
    rows1 = []
    for x in r1:
        inf = by_id[x["event_id"]]
        base = next((e for e in by_root[x["root"]] if e["verb"] == x["base"]), None)
        if not base:
            continue
        p = participles(base, lus)
        rows1.append(dict(route="R1", event_id=base["event_id"], root=x["root"], verb=base["verb"],
                          form=base["form"].split(" ")[0], transitivity=base["transitivity"], n_lex=nlex(base),
                          mutawaa=inf["verb"], mutawaa_event=inf["event_id"], athar=inf["masdar"],
                          mani=mani(base["verb"]), effect="MUATHTHIR" if not mani(base["verb"]) else "DEFER",
                          rank="CANDIDATE", **p))
    # R2
    roots_inf = {e["root_K"] for e in ev if is_mutawaa_form(e["form"]) and nlex(e) >= 2}
    pool = [e for e in ev if e["transitivity"] in R2_TRANS and nlex(e) >= 2
            and e["root_K"] not in roots_inf and not e.get("event_review_v36")]
    rows2 = []
    for e in pool:
        p = participles(e, lus)
        m = mani(e["verb"])
        rows2.append(dict(route="R2", event_id=e["event_id"], root=e["root_K"], verb=e["verb"],
                          form=e["form"].split(" ")[0], transitivity=e["transitivity"], n_lex=nlex(e),
                          mutawaa="", mutawaa_event="", athar="", mani=m,
                          effect="LA_ATHAR" if m else "DEFER", rank="CANDIDATE", **p))
    for name, rows in (("rules_R1.tsv", rows1), ("pool_R2.tsv", rows2)):
        rows.sort(key=lambda r: (r["root"], r["verb"]))
        write(os.path.join(HERE, name), rows)
    # العيّنة v2: بذرة جديدة، وتُستثنى عيّنة v1 حتى لا يُقاس على ما بُني منه المانع
    old = set()
    p1 = os.path.join(HERE, "sample_R2_v1.tsv")
    if os.path.exists(p1):
        old = {r["event_id"] for r in csv.DictReader(open(p1, encoding="utf-8"), delimiter="\t")}
    rng = random.Random(f"{SEED}:AHDATH_R2_v2")
    cand = [r for r in rows2 if not r["mani"] and r["event_id"] not in old]
    sample = rng.sample(cand, N_SAMPLE)
    write(os.path.join(HERE, "sample_R2_v2.tsv"), sample)
    st = Counter(r["fail_src"] for r in rows1 + rows2)
    print(f"R1 rules={len(rows1)}  R2 pool={len(rows2)} (mani={sum(1 for r in rows2 if r['mani'])})  sample={len(sample)}")
    print("fail_src", dict(st), " maful_src", dict(Counter(r["maful_src"] for r in rows1 + rows2)))


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d


def score(name="gold_R2_v2.tsv"):
    p = os.path.join(HERE, name)
    rows = list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))
    lab = Counter(r["label"] for r in rows)
    judged = sum(v for k, v in lab.items() if k != "DEFER")
    ok = lab["MUATHTHIR"]
    prec = ok / judged if judged else 0
    lo = wilson(ok, judged)
    verdict = "ACCEPT" if lo >= THRESH else ("PRECISION_OK_LOW_N" if prec >= THRESH else "BLOCK")
    print(dict(lab), f"judged={judged} ok={ok} precision={prec:.3f} wilson_low={lo:.3f} → {verdict}")


# ── R2 v3 (2026-11-06): التعدّي من الوسيط (wazn-net، مقيس 0.92) بدل وسم HFN (0.576) ──
def build_r2_wasit():
    ev, lus = load()
    tw = {r["event_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "ext", "transitivity_wasit.tsv"),
                                                        encoding="utf-8"), delimiter="\t")}
    roots_inf = {e["root_K"] for e in ev if is_mutawaa_form(e["form"]) and nlex(e) >= 2}
    rows = []
    for e in ev:
        t = tw.get(e["event_id"])
        if not t or t["transitivity_wasit"] != "متعدي" or nlex(e) < 2 or e["root_K"] in roots_inf:
            continue
        p = participles(dict(e, transitivity="متعدي"), lus)
        m = mani(e["verb"])
        rows.append(dict(route="R2w", event_id=e["event_id"], root=e["root_K"], verb=e["verb"],
                         form=e["form"].split(" ")[0], transitivity="متعدي(الوسيط)", n_lex=nlex(e),
                         mutawaa="", mutawaa_event="", athar="", mani=m,
                         effect="LA_ATHAR" if m else "DEFER", rank="CANDIDATE", **p))
    rows.sort(key=lambda r: (r["root"], r["verb"]))
    write(os.path.join(HERE, "pool_R2_v3.tsv"), rows)
    seen = set()
    for n in ("sample_R2_v1.tsv", "sample_R2_v2.tsv"):
        seen |= {r["event_id"] for r in csv.DictReader(open(os.path.join(HERE, n), encoding="utf-8"), delimiter="\t")}
    cand = [r for r in rows if not r["mani"] and r["event_id"] not in seen]
    sample = random.Random(f"{SEED}:AHDATH_R2_v3").sample(cand, min(N_SAMPLE, len(cand)))
    write(os.path.join(HERE, "sample_R2_v3.tsv"), sample)
    print("R2w pool", len(rows), "mani", sum(1 for r in rows if r["mani"]), "sample", len(sample))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "score" and len(sys.argv) > 2:
        score(sys.argv[2])
    else:
        {"build": build, "score": score, "r2w": build_r2_wasit}[cmd]()
