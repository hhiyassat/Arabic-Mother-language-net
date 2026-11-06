"""المسلك R1W: نصّ الوسيط «X: مطاوع Yه» ← Y مؤثّر في مفعوله، وX مطاوعه، ومصدر X اسم الأثر.

السند: الكليات:27626–27627 «والمطاوع يجيء مما كان فيه علاج … بل يأتي من المجرد أيضا تقول: ضاعفت الحساب
فتضاعف، وعلمته فتعلم»؛ وكشف الأسرار:9670 (انفعل) «إلا حيث يكون علاج وتأثير».
تنبيه: الكفوي يجعل «علّمته فتعلّم» مطاوعة، والعلم ليس تأثيراً في المحلّ؛ فالمطاوعة على غير انفعل
دليلُ علاجٍ لا دليلُ تأثير — ولذلك يُقاس هذا المسلك ولا يُقبل بالنصّ وحده.
"""
import csv
import os
import random
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ahdath as A  # noqa: E402
import taadiya as TD  # noqa: E402

PAT = re.compile(r"مطاوع(?:ة)?\s+([^\s.،:؛)]+)")
COLS = ["route", "root", "mutawi", "mutawi_event", "base_text", "base", "base_event", "base_form", "n_lex",
        "mani", "fail", "maful", "athar", "rank", "base_match"]

# صيغة الأصل من صيغة المطاوع (سيبويه، باب المطاوعة؛ الكليات:27626): تفعّل←فعّل، تفاعل←فاعل، تفعلل←فعلل،
# انفعل/افتعل ← المجرّد (وافتعل قد يطاوع أفعل).
MUT2BASE = {
    "تَفَعَّلَ": ("فَعَّلَ",),
    "تَفَاعَلَ": ("فَاعَلَ",),
    "تَفَعْلَلَ": ("فَعْلَلَ",),
    "انْفَعَلَ": ("فَعَلَ", "فَعِلَ", "فَعُلَ", "فَعَلَ/فَعِلَ"),
    "افْتَعَلَ": ("فَعَلَ", "فَعِلَ", "فَعُلَ", "فَعَلَ/فَعِلَ", "أَفْعَلَ"),
}


SHADDA, FATHA, KASRA, DAMMA = "\u0651", "\u064e", "\u0650", "\u064f"
_H = "[\u064b-\u0652]*"
RAW = re.compile("م" + _H + "ط" + _H + "ا" + _H + "و" + _H + "ع" + _H + "(?:ة" + _H + ")?\\s+([^\\s.،:؛)]+)")


def text_forms(raw):
    """صيغة الأصل من شكل كلمته في نصّ الوسيط نفسه (دفَّقه ← فَعَّلَ؛ دفَقَه ← فَعَلَ). None إن لم يُشكَل."""
    tok = re.sub(r"(ه|ها|هم)[\u064b-\u0652]*$", "", A.nfc(raw))
    letters = []
    for ch in tok:
        if "\u064b" <= ch <= "\u0652":
            if letters:
                letters[-1][1].append(ch)
        else:
            letters.append([ch, []])
    n = len(letters)
    if any(SHADDA in m for _, m in letters) and n == 3:
        return ("فَعَّلَ",)
    if n == 4 and letters[0][0] in "أاإ":
        return ("أَفْعَلَ",)
    if n == 4 and letters[1][0] == "ا":
        return ("فَاعَلَ",)
    if n == 4:
        return ("فَعْلَلَ",)
    if n == 3:
        v = letters[1][1]
        if FATHA in v:
            return ("فَعَلَ", "فَعَلَ/فَعِلَ")
        if KASRA in v:
            return ("فَعِلَ", "فَعَلَ/فَعِلَ")
        if DAMMA in v:
            return ("فَعُلَ",)
    return None


def want_forms(head, mut):
    """الصيغ المقبولة للأصل: من صيغة المطاوع في HFN إن عُرفت، وإلا من شكل الكلمة."""
    if mut and mut["form"].split(" ")[0] in MUT2BASE:
        return MUT2BASE[mut["form"].split(" ")[0]]
    hw = A.nfc(head)
    if hw.startswith("ت") and "ّ" in hw:
        return MUT2BASE["تَفَعَّلَ"]
    if hw.startswith("ت") and len(TD.WF.bare(hw)) == 5 and TD.WF.bare(hw)[2] == "ا":
        return MUT2BASE["تَفَاعَلَ"]
    if hw.startswith("ت"):
        return MUT2BASE["تَفَعْلَلَ"]
    return ("فَعَلَ", "فَعِلَ", "فَعُلَ", "فَعَلَ/فَعِلَ", "أَفْعَلَ")


def build():
    ev, lus = A.load()
    W = TD.wasit_index()
    WF = TD.WF
    by_root = {}
    for e in ev:
        by_root.setdefault(WF.bare(e["root_K"]), []).append(e)
    rows, st = [], Counter()
    for root, items in W.items():
        for head, text in items:
            for m in PAT.finditer(WF.bare(text)):
                bt = m.group(1)
                b = re.sub(r"(ه|ها|هم)$", "", bt)
                evs = by_root.get(root, [])
                mut = next((e for e in evs if WF.bare(e["verb"]) == WF.bare(head.split()[0])), None)
                base = [e for e in evs if WF.bare(e["verb"]) == b and A.nlex(e) >= 2]
                if not base:
                    st["no_base"] += 1
                    continue
                raws = RAW.findall(A.nfc(text))
                tf = next((text_forms(r) for r in raws if WF.bare(re.sub(r"(ه|ها|هم)[\u064b-\u0652]*$", "", r)) == b), None)
                want = tf or want_forms(head.split()[0], mut)
                if tf and not any(e["form"].split(" ")[0] in tf for e in base):
                    st["base_form_absent_in_hfn"] += 1   # النصّ يسمّي صيغةً ليست في HFN: لا إبدال بغيرها
                    continue
                pref = [e for e in base if e["form"].split(" ")[0] in want]
                if not pref and len({e["form"].split(" ")[0] for e in base}) > 1:
                    st["ambiguous_base"] += 1      # لا صيغة مطابقة وأكثر من صيغة: لا ترجيح بلا سند
                    continue
                bse = sorted(pref or base, key=lambda e: (-A.nlex(e), e["event_id"]))[0]
                p = A.participles(dict(bse, transitivity="متعدي"), lus)
                rows.append(dict(route="R1W", root=root, mutawi=head.split()[0], mutawi_event=mut["event_id"] if mut else "",
                                 base_text=bt, base=bse["verb"], base_event=bse["event_id"], base_form=bse["form"].split(" ")[0],
                                 n_lex=A.nlex(bse), mani=A.mani(bse["verb"]), fail=p["fail"], maful=p["maful"],
                                 athar=(mut["masdar"] if mut else ""), rank="CANDIDATE",
                                 base_match=("TEXT" if tf else "MUT_FORM") if pref else "ONLY_FORM"))
                st["ok"] += 1
    seen, uniq = set(), []
    for r in rows:
        k = (r["base_event"], WF.bare(r["mutawi"]))
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    with open(os.path.join(HERE, "mutawaa_R1W_pool.tsv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(uniq)
    cand = [r for r in uniq if not r["mani"]]
    s = random.Random(f"{A.SEED}:AHDATH_R1W").sample(cand, min(A.N_SAMPLE, len(cand)))
    with open(os.path.join(HERE, "mutawaa_R1W_sample.tsv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(s)
    print(dict(st), "unique", len(uniq), "mani", len(uniq) - len(cand), "sample", len(s))


def score():
    rows = list(csv.DictReader(open(os.path.join(HERE, "mutawaa_R1W_gold.tsv"), encoding="utf-8"), delimiter="\t"))
    lab = Counter(r["label"] for r in rows)
    judged = sum(v for k, v in lab.items() if k != "DEFER")
    ok = lab["MUATHTHIR"]
    lo = A.wilson(ok, judged)
    print(dict(lab), f"judged={judged} ok={ok} p={ok / judged:.3f} wilson_low={lo:.3f}", "ACCEPT" if lo >= A.THRESH else "BLOCK")


if __name__ == "__main__":
    (score if sys.argv[1:2] == ["score"] else build)()
