"""المسلك T_TAD: التعدية بالتضعيف بنصّ الوسيط — فَعَّلَ من لازمٍ، ونصّ الوسيط فيه «جعله/صيّره <اللازم>».

السند:
  سيبويه، الكتاب (sibawayhi.txt:16451–16455) عن الخليل: «أحزنته: جعلته حزيناً، وحزّنته: جعلت فيه حزناً» —
     فالتضعيف يجعل في المفعول ما كان للفاعل في اللازم.
  الكليات:30845–30846 «والحق أنه قياسي في القاصر، سماعي في غيره» — ولذلك لا يُقبل التضعيف بالصيغة وحدها
     (كما سقط T بالصيغة: 0.623)، بل بنصّ المعجم على «جعله/صيّره» كما في T_JAL (25/25).
الشرط:
  - فَعَّلَ مسموع في معجمين فأكثر (n_lex ≥ 2).
  - له في الجذر نفسه مجرّدٌ بالحروف نفسها لازمٌ في الوسيط (جدول wazn-net المقيس 0.92).
  - نصّ الوسيط في فَعَّلَ: «جعله» أو «صيّره» يليها لفظٌ من حروف اللازم أو صفته.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ahdath as A  # noqa: E402
import taadiya as TD  # noqa: E402

WF = TD.WF
MUJ = ("فَعَلَ", "فَعِلَ", "فَعُلَ", "فَعَلَ/فَعِلَ")
CAUS = r"(?:جعل|صير)(?:ه|ها)?\s*(?:ي|ت)?\S*{b}\S*|(?:جعل|صير)(?:ه|ها)\s+\S*{b}\S*"
COLS = TD.COLS + ["text_phrase", "text_src"]


def phrase(W, root, verb, keys):
    """عبارة «جعله/صيّره …» في نصّ الوسيط لفَعَّلَ نفسه (بشكله: compatible)، بأحد المفاتيح (حروف اللازم أو صفته)."""
    vb, out = WF.bare(verb), []
    for head, text in W.get(WF.bare(root), []):
        hw = head.split()[0] if head.split() else ""
        if WF.bare(hw) in (vb, vb + "ه", vb + "ها") and WF.compatible(hw, verb):
            out.append(text)
    blob = WF.bare(" ".join(out))
    for k in keys:
        if len(k) < 2:
            continue
        m = re.search(CAUS.format(b=re.escape(k)), blob)
        if m:
            return m.group(0), k
    return "", ""


def build():
    ev, lus = A.load()
    W = TD.wasit_index()
    tw = {r["event_id"]: r for r in TD.tsv(os.path.join(HERE, "ext", "transitivity_wasit.tsv"))}
    sif = {}
    for r in TD.tsv(os.path.join(HERE, "ext", "sifat.tsv")):
        sif.setdefault(r["event_id"], r)
    by_root = {}
    for e in ev:
        by_root.setdefault(WF.bare(e["root_K"]), []).append(e)
    pool, rows = [], []
    for d in ev:
        if d["form"].split(" ")[0] != "فَعَّلَ" or A.nlex(d) < 2:
            continue
        for b in by_root.get(WF.bare(d["root_K"]), []):
            if b["form"].split(" ")[0] not in MUJ or WF.bare(b["verb"]) != WF.bare(d["verb"]):
                continue
            t = tw.get(b["event_id"])
            if not t or t["transitivity_wasit"] != "لازم":
                continue
            s = sif.get(b["event_id"])
            sifa = s["word"] if s else A.participles(b, lus)["fail"]
            p = A.participles(dict(d, transitivity="متعدي"), lus)
            keys = [WF.bare(b["verb"])[:2]] + ([WF.bare(sifa)[:3]] if sifa else [])
            ph, k = phrase(W, d["root_K"], d["verb"], keys)
            row = dict(route="T_TAD", base_event=b["event_id"], base=b["verb"], base_form=b["form"].split(" ")[0],
                       base_trans_wasit=t["transitivity_wasit"], base_harf=t.get("harf", ""), sifa=sifa,
                       sifa_kind=(s["kind"] if s else "FAIL"), sifa_src=("SIFAT" if s else "QIYAS"),
                       event_id=d["event_id"], verb=d["verb"], form="فَعَّلَ", n_lex=A.nlex(d),
                       verb_trans_hfn=d.get("transitivity", ""), verb_senses_wasit="", fail=p["fail"],
                       maful=p["maful"], maful_src="QIYAS", rank="CANDIDATE", text_phrase=ph,
                       text_src=("WASIT_JAL_SAYR" if ph else ""))
            pool.append(row)
            if ph:
                rows.append(row)
    for name, data in (("taadiya_TAD_pool.tsv", pool), ("taadiya_T_TAD.tsv", rows)):
        with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
    print("pool", len(pool), "T_TAD (نصّ جعله/صيّره)", len(rows))


def score():
    rows = TD.tsv(os.path.join(HERE, "taadiya_T_TAD_gold.tsv"))
    lab = {}
    for r in rows:
        lab[r["label"]] = lab.get(r["label"], 0) + 1
    judged = sum(v for k, v in lab.items() if k != "DEFER")
    ok = lab.get("TAADIYA", 0)
    lo = A.wilson(ok, judged)
    print(lab, f"judged={judged} ok={ok} p={ok / judged:.3f} wilson_low={lo:.3f}", "ACCEPT" if lo >= A.THRESH else "BLOCK")


if __name__ == "__main__":
    (score if sys.argv[1:2] == ["score"] else build)()
