"""جهة الفاعل — هل فاعل الفعل محدِثٌ له أم محلٌّ قام به الحدث؟ (CANDIDATE، قراءة فقط من HFN)

الأصل: الفاعل يُعرَف بالإسناد لا بالإيجاد —
  الصبّان، حاشية على الأشموني (sabban.txt:2228–2229): «الدالة بالمطابقة على من وجد منه الفعل أو قام به …
  كضربت ومت». فـ«مات الرجل»: الرجل فاعل لأنّ الموت قام به، لا لأنّه أوجده.

القيم:
  MAHALL   الفاعل محلٌّ قام به الحدث (صفة، لون، داء، انفعال، حدوث بالطبع) — ليس محدِثاً مريداً له.
  MUHDITH  الفاعل يوجِد الحدث باختياره في الاستعمال الغالب (انطلق، لعِب).
  DEFER    المعنى غير بيّن من نصّ الوسيط.

المسالك (كلّ مسلك فرضيّة: «فاعل هذا الوزن MAHALL») — يُقبل منها ما بلغ حدّ ويلسون الأدنى ≥ 0.78:
  J_LAWN     افْعَلَّ (احمرّ، اخضرّ، اصفرّ). سيبويه، الكتاب (sibawayhi.txt:16108–16116)
             «أما الألوان فإنها تبنى على أفعل … ازراق واخضار واصفار واحمار».
  J_SAJIYYA  فَعُلَ (كرُم، حسُن، قبُح). الكتاب (sibawayhi.txt:16143–16144)
             «باب ايضا في الخصال التي تكون في الأشياء: أما ما كان حسنا أو قبحا فإنه مما يبنى فعله على فعُل يفعُل».
  J_DAA      فَعِلَ لازم في الوسيط وصفته على فَعِل أو أفعل أو فعلان (وجِع فهو وجِع، عمِش فهو أعمش، عطِش فهو عطشان).
             الكتاب (sibawayhi.txt:16016) «باب ما جاء من الأدواء على مثال وجع يوجع وجعا وهو وجع»،
             و(16108) الألوان على أفعل.
  J_MUTAWAA  انْفَعَلَ (انكسر، انشقّ). الكتاب (sibawayhi.txt:16543) «باب ما طاوع الذي فعله على فعل وهو يكون على انفعل».

المسبِّب المحذوف: إن كان للفعل في T_JAL المقبول «أفعله: جعله <اللازم>» أو أصلٌ في R1/R1W (كسره ← انكسر)
  ذُكر في عمود musabbib_verb — وهو الفعل الذي يُظهر المسبِّب فاعلاً.

    python3 ahdath/jiha.py build    # jiha_pool.tsv + jiha_sample_<route>.tsv
    python3 ahdath/jiha.py score    # يقيس كلّ مسلك من jiha_gold_<route>.tsv
"""
import csv
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ahdath as A  # noqa: E402
import taadiya as TD  # noqa: E402

WF = TD.WF
N = 40
SEED = 20261106
ROUTES = {
    "J_LAWN": "sibawayhi.txt:16108–16116",
    "J_SAJIYYA": "sibawayhi.txt:16143–16144",
    "J_DAA": "sibawayhi.txt:16016؛ 16108",
    "J_MUTAWAA": "sibawayhi.txt:16543",
}
DAA_TEMPLATES = ("فعل3", "أفعل", "فعلان", "فعلاء")
COLS = ["route", "event_id", "root", "verb", "form", "n_lex", "trans_wasit", "sifa", "sifa_template",
        "jiha", "musabbib_verb", "musabbib_route", "src", "rank"]


def gloss(W, root, verb, n=160):
    """أوّل نصّ الوسيط للفعل نفسه — للحكم باليد."""
    vb = WF.bare(verb)
    for head, text in W.get(WF.bare(root), []):
        hw = head.split()[0] if head.split() else ""
        if WF.bare(hw) == vb and WF.compatible(hw, verb):
            return re.sub(r"\s+", " ", text)[:n]
    for head, text in W.get(WF.bare(root), []):  # بلا شرط الشكل: الوسيط قد يورد الفعل بلا حركات
        hw = head.split()[0] if head.split() else ""
        if WF.bare(hw) == vb:
            return re.sub(r"\s+", " ", text)[:n]
    return ""


def musabbib():
    """اللازم/المطاوع ← الفعل الذي يُظهر المسبِّب، من المسالك المقبولة وحدها."""
    m = {}
    for r in TD.tsv(os.path.join(HERE, "taadiya_T_JAL.tsv")):
        m.setdefault(WF.bare(r["base"]), (r["verb"], "T_JAL"))
    for r in TD.tsv(os.path.join(HERE, "rules_R1.tsv")):
        if not r.get("mani"):
            m.setdefault(WF.bare(r["mutawaa"]), (r["verb"], "R1"))
    for r in TD.tsv(os.path.join(HERE, "mutawaa_R1W_pool.tsv")):
        if not r.get("mani"):
            m.setdefault(WF.bare(r["mutawi"]), (r["base"], "R1W"))
    return m


def route_of(e, tw, sif):
    f = e["form"].split(" ")[0]
    if f == "افْعَلَّ":
        return "J_LAWN"
    if f == "فَعُلَ":
        return "J_SAJIYYA"
    if f == "انْفَعَلَ":
        return "J_MUTAWAA"
    if f == "فَعِلَ":
        t = tw.get(e["event_id"])
        s = sif.get(e["event_id"])
        if t and t["transitivity_wasit"] == "لازم" and s and s["template"] in DAA_TEMPLATES:
            return "J_DAA"
    return ""


def build():
    ev, _ = A.load()
    tw = {r["event_id"]: r for r in TD.tsv(os.path.join(HERE, "ext", "transitivity_wasit.tsv"))}
    sif = {}
    for r in TD.tsv(os.path.join(HERE, "ext", "sifat.tsv")):
        sif.setdefault(r["event_id"], r)
    mus = musabbib()
    pool = []
    for e in ev:
        rt = route_of(e, tw, sif)
        if not rt or A.nlex(e) < 2:
            continue
        s = sif.get(e["event_id"]) or {}
        mv, mr = mus.get(WF.bare(e["verb"]), ("", ""))
        pool.append(dict(route=rt, event_id=e["event_id"], root=e["root_K"], verb=e["verb"],
                         form=e["form"].split(" ")[0], n_lex=A.nlex(e),
                         trans_wasit=(tw.get(e["event_id"]) or {}).get("transitivity_wasit", ""),
                         sifa=s.get("word", ""), sifa_template=s.get("template", ""), jiha="MAHALL",
                         musabbib_verb=mv, musabbib_route=mr, src=ROUTES[rt], rank="CANDIDATE"))
    _write(os.path.join(HERE, "jiha_pool.tsv"), COLS, pool)
    W = TD.wasit_index()
    rnd = random.Random(SEED)
    for rt in ROUTES:
        xs = [p for p in pool if p["route"] == rt]
        smp = rnd.sample(xs, min(N, len(xs)))
        for p in smp:
            p["gloss"] = gloss(W, p["root"], p["verb"])
        _write(os.path.join(HERE, f"jiha_sample_{rt}.tsv"), ["route", "event_id", "verb", "sifa", "gloss"], smp)
        print(rt, "pool", len(xs), "sample", len(smp))


def _write(p, cols, rows):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def score():
    out = {}
    for rt in ROUTES:
        p = os.path.join(HERE, f"jiha_gold_{rt}.tsv")
        if not os.path.exists(p):
            continue
        lab = {}
        for r in TD.tsv(p):
            lab[r["label"]] = lab.get(r["label"], 0) + 1
        judged = lab.get("MAHALL", 0) + lab.get("MUHDITH", 0)
        ok = lab.get("MAHALL", 0)
        lo = A.wilson(ok, judged)
        out[rt] = dict(lab=lab, judged=judged, ok=ok, p=ok / judged if judged else 0, wilson_low=lo,
                       verdict="ACCEPT" if lo >= A.THRESH else "BLOCK")
        print(rt, lab, f"p={out[rt]['p']:.3f} wilson_low={lo:.3f}", out[rt]["verdict"])
    return out


if __name__ == "__main__":
    (score if sys.argv[1:2] == ["score"] else build)()
