"""المسلك الثالث T: التعدية بالهمزة والتضعيف — الفعل اللازم يصير متعدّياً فيكتسب المفعولُ صفةَ اللازم.

السند:
  سيبويه، الكتاب (sibawayhi.txt:16436–16440) «هذا باب افتراق فعلت وأفعلت في الفعل للمعنى: تقول دخل وخرج وجلس
     فإذا أخبرت أن غيره صيره إلى شيء من هذا قلت أخرجه وأدخله وأجلسه … فأكثر ما يكون على فعل إذا أردت أن غيره
     أدخله في ذلك يبنى الفعل منه على أفعلت».
  وفيه (16451–16455) عن الخليل: أحزنته = جعلته حزيناً (تغيير «حزن»)، وحزّنته = جعلت فيه حزناً.
  الكفوي، الكليات:27591 «والتعدية بالهمزة قياسية»، و30845–30846 «والحق أنه قياسي في القاصر، سماعي في غيره.
     وهو ظاهر قول سيبويه».
المانع:
  أفعل الذي ليس للتعدية: الكليات:17176 «وسرى، وأسرى: بمعنى … لازمان، والهمزة ليست للتعدية»؛
  وسيبويه:16449 «وشرقت بدت وأشرقت أضاءت وأسرع عجل وأبطأ احتبس». فيُشترط أن يكون أفعل نفسه متعدّياً.
الشرط: اللازم لازمٌ في الوسيط (جدول wazn-net المقيس 0.92)، وأفعل مسموع في معجمين فأكثر.

المخرَج لكلّ زوج: اللازم، المتعدّي، صفة اللازم (من sifat.tsv المقيس، وإلا اسم فاعل اللازم)، واسم المفعول للمتعدّي.
"""
import csv
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ahdath as A  # noqa: E402
from ext import wasit_frames as WF  # noqa: E402
import json  # noqa: E402


def wasit_index():
    W = {}
    for line in open(WF.WASIT, encoding="utf-8"):
        r = json.loads(line)
        k = WF.bare(r["root"]["source_display"])
        for s in r["sources"].values():
            for c in s.get("claims") or []:
                if c.get("headword"):
                    W.setdefault(k, []).append((c["headword"].strip(), c.get("text") or ""))
    return W


def sense_tags(W, root, verb):
    """وسوم معاني الفعل في الوسيط (متعدي/لازم/لازم_بحرف) بمنطق wazn-net المقيس."""
    vb, tags = WF.bare(verb), []
    for head, text in W.get(WF.bare(root), []):
        hw = head.split()[0] if head.split() else ""
        hb = WF.bare(hw)
        hobj = hb in (vb + "ه", vb + "ها")
        if (hb == vb or hobj) and WF.compatible(hw, verb):
            tags += [WF.frame_tag(fr, hobj)[0] for fr in WF.senses(text)]
    return tags

COLS = ["route", "base_event", "base", "base_form", "base_trans_wasit", "base_harf", "sifa", "sifa_kind", "sifa_src",
        "event_id", "verb", "form", "n_lex", "verb_trans_hfn", "verb_senses_wasit", "fail", "maful", "maful_src", "rank"]


def tsv(p):
    return list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))


JAL = r"جعل(?:ه|ها)?\s*(?:ي|ت)?{b}\S*|جعل(?:ه|ها)\s+\S*{b}\S*"


def jaala(W, root, verb, base):
    """نصّ الوسيط في أفعل يقول «جعله <اللازم>» — عبارة الخليل في الكتاب:16452 «جعلته حزيناً». يعيد العبارة أو ''."""
    import re
    vb, out = WF.bare(verb), []
    for head, text in W.get(WF.bare(root), []):
        hw = head.split()[0] if head.split() else ""
        if WF.bare(hw) in (vb, vb + "ه", vb + "ها") and WF.compatible(hw, verb):
            out.append(text)
    m = re.search(JAL.format(b=re.escape(WF.bare(base)[:2])), WF.bare(" ".join(out)))
    return m.group(0) if m else ""


def build_jal():
    """المسلك T_JAL: من حوض T كلّه (بلا مانع الوسيط) ما نصّ فيه الوسيط على «جعله <اللازم>». حُكم فيه حصراً (25/25)."""
    W = wasit_index()
    pool = tsv(os.path.join(HERE, "taadiya_T_pool_v1.tsv"))
    ev = {e["event_id"]: e for e in A.load()[0]}
    rows = []
    for r in pool:
        j = jaala(W, ev[r["event_id"]]["root_K"], r["verb"], r["base"])
        if j:
            rows.append(dict(r, route="T_JAL", jaala=j))
    with open(os.path.join(HERE, "taadiya_T_JAL.tsv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLS + ["jaala"], delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("T_JAL", len(rows))


def build():
    ev, lus = A.load()
    by_id = {e["event_id"]: e for e in ev}
    tw = {r["event_id"]: r for r in tsv(os.path.join(HERE, "ext", "transitivity_wasit.tsv"))}
    sif = {}
    for r in tsv(os.path.join(HERE, "ext", "sifat.tsv")):
        sif.setdefault(r["event_id"], r)
    rel = list(csv.DictReader(open(os.path.join(A.HFN, "event_relations.csv"), encoding="utf-8")))
    W = wasit_index()
    rows = []
    for r in rel:
        if r["fn_relation_type_candidate"] != "Causative_of":
            continue
        d, b = by_id.get(r["event_id"]), by_id.get(r["target"])
        if not d or not b or A.nlex(d) < 2:
            continue
        t = tw.get(b["event_id"])
        if not t or t["transitivity_wasit"] != "لازم":
            continue
        st = sense_tags(W, d["root_K"], d["verb"])
        if "متعدي" not in st:                     # المانع: أفعل لا معنى متعدّياً له في الوسيط (أسرى، أشرق، أخرف)
            continue
        p = A.participles(dict(d, transitivity="متعدي"), lus)
        bp = A.participles(dict(b, transitivity="لازم"), lus)
        s = sif.get(b["event_id"])
        rows.append(dict(route="T_IFAL", base_event=b["event_id"], base=b["verb"], base_form=b["form"].split(" ")[0],
                         base_trans_wasit=t["transitivity_wasit"], base_harf=t.get("harf", ""),
                         sifa=(s["word"] if s else bp["fail"]), sifa_kind=(s["kind"] if s else "HUDUTH"),
                         sifa_src=("WASIT_FAHUWA" if s else "ISM_FAIL"),
                         event_id=d["event_id"], verb=d["verb"], form=d["form"].split(" ")[0], n_lex=A.nlex(d),
                         verb_trans_hfn=d["transitivity"], verb_senses_wasit="·".join(st), fail=p["fail"], maful=p["maful"], maful_src=p["maful_src"],
                         rank="CANDIDATE"))
    rows.sort(key=lambda x: (x["base"], x["verb"]))
    write(os.path.join(HERE, "taadiya_T_pool.tsv"), rows)
    old = {r["event_id"] for r in tsv(os.path.join(HERE, "taadiya_T_sample_v1.tsv"))} if os.path.exists(os.path.join(HERE, "taadiya_T_sample_v1.tsv")) else set()
    rng = random.Random(f"{A.SEED}:AHDATH_T_v2")
    cand = [x for x in rows if x["event_id"] not in old]
    sample = rng.sample(cand, min(A.N_SAMPLE, len(cand)))
    write(os.path.join(HERE, "taadiya_T_sample.tsv"), sample)
    print("pool", len(rows), Counter(r["sifa_src"] for r in rows), "sample", len(sample))


def write(p, rows):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def score(name="taadiya_T_gold.tsv"):
    rows = tsv(os.path.join(HERE, name))
    lab = Counter(r["label"] for r in rows)
    judged = sum(v for k, v in lab.items() if k != "DEFER")
    ok = lab["TAADIYA"]
    lo = A.wilson(ok, judged)
    print(dict(lab), f"judged={judged} ok={ok} precision={ok / judged:.3f} wilson_low={lo:.3f} →",
          "ACCEPT" if lo >= A.THRESH else "BLOCK")


if __name__ == "__main__":
    {"score": score, "jal": build_jal}.get(sys.argv[1] if len(sys.argv) > 1 else "", build)()
