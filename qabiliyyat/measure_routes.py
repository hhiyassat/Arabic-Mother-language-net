#!/usr/bin/env python3
"""
measure_routes.py — قياس ثلاثة مسالك صرفيّة تُرشِّح القابليات والخواصّ (CANDIDATE، قراءة فقط)

قرار المالك 2026-11-05 «Yes, measure it» على السؤال ٣ من REPORT_QABILIYYAT_v1.md.

  R1_MUTAWAA  : جذرٌ له «فَعَلَ/أَفْعَلَ» متعدٍّ و«انْفَعَلَ» مشهودٌ في معجمين فأكثر
                ← قابليةٌ منفعلة «قبول الفعل»   (سيبويه: «كسرته فانكسر» ، الكتاب 4/65)
  R2_FACULA   : «فَعُلَ» مشهودٌ في معجمين فأكثر
                ← خاصيّةٌ ثابتة (خصلة)           (سيبويه: «الخصال التي تكون في الأشياء» ، 4/28)
  R3_FACUL    : رأسُ مادّةٍ على «فَعُول» في الوسيط/المصباح
                ← قابلية (طَهور = طاهر مطهِّر ؛ ناقة حَلوب/رَكوب)  (اللسان: طهر)

المصادر: HusseinFrameNet events.csv من أحدث إصدار (hfn_release.py؛ قيست أوّلاً على release_v36، والفرق في audit/hfn_v45_migration) (n_lex_v33) ، ~/roots/{wasit,misbah}_out/*.jsonl
المخرَج: candidates_<route>.tsv (كلّ المرشّحين) و sample_<route>.tsv (عيّنة عشوائية ببذرة ثابتة للحكم اليدوي).

    python3 measure_routes.py extract          # يبني المرشّحين والعيّنات
    python3 measure_routes.py score            # يقرأ gold_<route>.tsv ويحسب الدقّة و Wilson
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
from hfn_release import hfn_release_dir  # noqa: E402  (AMLN_HFN_RELEASE أو أحدث إصدار)
HFN_EVENTS = os.path.join(hfn_release_dir(), "events.csv")
LEX = {k: os.path.expanduser(f"~/roots/{k}_out/{k}-root-meanings-v2.jsonl") for k in ("wasit", "misbah")}
SEED = 20261105
N_SAMPLE = 60
THRESH = 0.78

H = "ًٌٍَُِّْٰـ"
FATHA, DAMMA, SHADDA, SUKUN = "َ", "ُ", "ّ", "ْ"


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def strip(s):
    # ٱ (همزة الوصل برسم المصحف، HFN v44) = ا في المطابقة، وإلا ضاع شرح الوسيط لكل مطاوع على v45
    return "".join(c for c in nfc(s) if c not in H).replace("ٱ", "ا")


def fold_root(s):
    return strip(s).translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء", "ى": "ي"}))


def lex_glosses():
    """رأس المادة المجرّد ← [(المعجم ، الرأس كما هو ، النصّ)]"""
    idx = defaultdict(list)
    for name, p in LEX.items():
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            for body in d["sources"].values():
                for c in body.get("claims", []):
                    hw = nfc(c.get("headword", "")).strip(" :،.")
                    if hw:
                        idx[strip(hw)].append((name, hw, (c.get("text") or "")[:160], d["root"]["source_display"]))
    return idx


def hfn_events():
    return list(csv.DictReader(open(HFN_EVENTS, encoding="utf-8")))


def nlex(e):
    try:
        return int(e.get("n_lex_v33") or e.get("n_lex") or 0)
    except ValueError:
        return 0


def gloss_for(idx, verb):
    hits = idx.get(strip(verb), [])
    return " ‖ ".join(f"{n}:{t}" for n, _, t, _ in hits[:2])


# ── المسالك ───────────────────────────────────────────────────────────────────
def r1_mutawaa(ev, idx):
    by_root = defaultdict(list)
    for e in ev:
        by_root[e["root_K"]].append(e)
    out = []
    for root, es in by_root.items():
        inf = [e for e in es if e["form"].startswith("انْفَعَلَ") and nlex(e) >= 2
               and not e.get("event_review_v36")]
        base = [e for e in es if e["form"].split(" ")[0] in ("فَعَلَ", "فَعِلَ", "أَفْعَلَ", "فَعَلَ/فَعِلَ")
                and e["transitivity"] in ("متعدي", "مشترك")]
        for e in inf:
            if base:
                b = base[0]
                out.append({"root": root, "candidate": e["verb"], "base": b["verb"], "n_lex": nlex(e),
                            "lexicons": e.get("lexicons_v33", ""), "event_id": e["event_id"],
                            "gloss": gloss_for(idx, e["verb"])})
    return out


def r2_facula(ev, idx):
    out = []
    for e in ev:
        if e["form"].startswith("فَعُلَ") and nlex(e) >= 2 and not e.get("event_review_v36"):
            out.append({"root": e["root_K"], "candidate": e["verb"], "base": "", "n_lex": nlex(e),
                        "lexicons": e.get("lexicons_v33", ""), "event_id": e["event_id"],
                        "gloss": gloss_for(idx, e["verb"])})
    return out


_FACUL = re.compile(r"^(?:ال)?([^\s" + H + r"])" + FATHA + r"([^\s" + H + r"])" + DAMMA + r"و([^\s" + H + r"])[" + H + r"]*$")


def r3_facul(idx):
    seen, out = set(), []
    for key, hits in idx.items():
        for name, hw, text, root in hits:
            w = re.sub(r"[\s()\[\]«»0-9٠-٩]+", "", hw)
            m = _FACUL.match(w)
            if not m:
                continue
            k = strip(w).removeprefix("ال")
            if k in seen:
                continue
            seen.add(k)
            out.append({"root": root, "candidate": w, "base": "", "n_lex": 1, "lexicons": name,
                        "event_id": "", "gloss": text})
    return out


ROUTES = {"R1_MUTAWAA": r1_mutawaa, "R2_FACULA": r2_facula, "R3_FACUL": None}
COLS = ["route", "root", "candidate", "base", "n_lex", "lexicons", "event_id", "gloss"]


def extract():
    idx = lex_glosses()
    ev = hfn_events()
    res = {"R1_MUTAWAA": r1_mutawaa(ev, idx), "R2_FACULA": r2_facula(ev, idx), "R3_FACUL": r3_facul(idx)}
    for r, rows in res.items():
        rows.sort(key=lambda x: (x["root"], x["candidate"]))
        with open(os.path.join(HERE, f"candidates_{r}.tsv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for x in rows:
                w.writerow(dict(x, route=r))
        rng = random.Random(f"{SEED}:{r}")
        sample = rng.sample(rows, min(N_SAMPLE, len(rows)))
        with open(os.path.join(HERE, f"sample_{r}.tsv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for x in sample:
                w.writerow(dict(x, route=r))
        print(f"{r}: candidates={len(rows)} sample={len(sample)}")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d


# الأحكام المقبولة لكلّ مسلك (ما سواها خطأ ، و DEFER لا يُحسب)
OK = {"R1_MUTAWAA": {"PHYS", "NAFS"}, "R2_FACULA": {"KHASSA_JINS", "KHASLA_NAFS", "BOTH"},
      "R3_FACUL": {"QABIL_FAIL", "QABIL_MUNFAIL"}}


def score():
    out = {}
    for r in OK:
        p = os.path.join(HERE, f"gold_{r}.tsv")
        if not os.path.exists(p):
            print(f"{r}: لا gold")
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))
        lab = Counter(x["label"] for x in rows)
        judged = sum(v for k, v in lab.items() if k != "DEFER")
        ok = sum(lab[k] for k in OK[r])
        prec = ok / judged if judged else 0
        lo = wilson(ok, judged)
        verdict = "ACCEPT" if lo >= THRESH else ("PRECISION_OK_LOW_N" if prec >= THRESH else "BLOCK")
        out[r] = {"labels": dict(lab), "judged": judged, "ok": ok, "precision": round(prec, 3),
                  "wilson_low": round(lo, 3), "verdict": verdict}
        print(r, json.dumps(out[r], ensure_ascii=False))
    json.dump(out, open(os.path.join(HERE, "SCORES_v1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    {"extract": extract, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "extract"]()
