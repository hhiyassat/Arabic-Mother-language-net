#!/usr/bin/env python3
# منسوخ قراءةً من Arabic-Mother-language-wazn-net@wazn-ahdath-fields-20261105:scripts/build_transitivity_wasit.py (مقيس 0.92).
# يُستعمل هنا لقراءة إطار المعنى في مادّة أَفْعَلَ؛ main() لا تُستدعى.
"""build_transitivity_wasit.py — التعدّي من تركيب شرح المعجم الوسيط (ملاحظة ahdath ٣، المالك 2026-11-05).

لكل حدث ثلاثي مجرّد في HFN v36 تُطلب مادّته في الوسيط (~/roots/wasit_out، المرجع M11) برأس يطابق الفعل
(الهيكل، والتشكيل إن وُجد؛ أو الفعل + ضمير المفعول «أَجَاعَهُ»). يُقسَم الشرح معانيَ على «و -»، ويُقرأ إطار كل معنى (ما قبل «:»):
  مفعول منصوب من قائمة مغلقة (فلانًا، الشيءَ…) أو ضمير مفعول في الرأس  → متعدي
  حرف جرّ بعد الفاعل (عن، على، في، إلى، من، ب، ل…)                     → لازم + الحرف
  لا مفعول ولا حرف (فاعل فقط أو لا شيء)                                  → لازم
تجميع المعاني: كلها متعدي → متعدي · كلها لازم بلا حرف → لازم · لازم وفيها حرف → لازم+الحرف الأغلب ·
مختلفة → مشترك. لا رأس مطابق أو لا إطار مقروء → غير معلوم (لا يُخمَّن).
المخرَج جدول جانبي data/transitivity_wasit.tsv بسنده؛ لا يُكتب فوق وسم HFN. CANDIDATE. يرفض الكتابة فوق ملف قائم.
"""
import csv, json, os, re, sys, unicodedata, collections as C

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(H, "data", "transitivity_wasit.tsv")
EV = os.path.expanduser("~/arabic-net/HusseinFrameNet/release/release_v36/events.csv")
WASIT = os.path.expanduser("~/roots/wasit_out/wasit-root-meanings-v2.jsonl")
HAR = re.compile("[ً-ْٰـ]")
SEATS = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء", "ى": "ي"})

OBJ = {"فلانا", "فلانً", "الشيء", "الشىء", "الشيءَ", "فلانة", "القوم", "غيره", "اياه", "إياه", "الامر"}
HARF_TOK = {"عن": "عن", "على": "على", "علي": "على", "في": "في", "فى": "في", "الى": "إلى", "إلى": "إلى", "إلي": "إلى",
            "من": "من", "به": "ب", "بها": "ب", "بهم": "ب", "له": "ل", "لها": "ل", "عليه": "على", "عليها": "على",
            "فيه": "في", "فيها": "في", "عنه": "عن", "عنها": "عن", "منه": "من", "منها": "من", "إليه": "إلى", "اليه": "إلى",
            "مع": "مع", "معه": "مع"}
SPLIT = re.compile(r"(?:^|[.،؛]\s*|\s)و\s*[-_ـ–]\s*")


def bare(s):
    return HAR.sub("", unicodedata.normalize("NFC", s or "")).translate(SEATS).strip(" :،.-_")


def acc_obj(tok_raw):
    """مفعول منصوب: فلانًا/فلاناً، أو الشيءَ (بفتحة ظاهرة)."""
    b = bare(tok_raw)
    if b in ("فلانا",) or (b == "فلان" and ("ً" in tok_raw or tok_raw.endswith("ا"))):
        return True
    if b in ("الشيء", "الشء") and "َ" in tok_raw[-2:]:
        return True
    # معرَّف منصوب بفتحة ظاهرة (السائرَ، الأشباحَ)؛ النكرة المنوّنة مصدرٌ غالباً فلا تُعدّ
    t = unicodedata.normalize("NFC", tok_raw).rstrip(".،:؛)")
    if b.startswith("ال") and len(b) > 3 and t.endswith("َ") and "ً" not in t:
        return True
    return b in ("غيره", "اياه", "ءياه")


def frame_tag(frame, head_has_obj):
    toks = frame.replace("-", " ").replace("_", " ").split()
    harf = None
    for i, t in enumerate(toks):
        b = bare(t)
        if acc_obj(t):
            return "متعدي", None
        if b in HARF_TOK or b.translate(SEATS) in HARF_TOK:
            harf = harf or HARF_TOK.get(b) or HARF_TOK.get(b.translate(SEATS))
        elif len(b) > 2 and b[0] in "بل" and b[1:3] == "ال":
            harf = harf or b[0]
    if head_has_obj:
        return "متعدي", None
    if harf:
        return "لازم_بحرف", harf
    return "لازم", None


def senses(text):
    parts = [p for p in SPLIT.split(" " + text) if p.strip()]
    out = []
    for p in parts:
        if ":" not in p:
            continue
        fr = p.split(":", 1)[0]
        if len(fr.split()) > 8:      # إطار طويل = نثر لا تركيب: لا يُقرأ
            continue
        out.append(fr.strip())
    return out


def compatible(head, verb):
    h, v = unicodedata.normalize("NFC", head), unicodedata.normalize("NFC", verb)
    if ("ّ" in h) != ("ّ" in v) and len(HAR.findall(h)) >= 2:
        return False                       # الشدّة تفرّق فَعَلَ من فَعَّلَ (حَصَنَ ≠ حَصَّنَ)
    hm, vm = re.findall("[ً-ّ]", h), re.findall("[ً-ّ]", v)
    if len(hm) < 2:
        return True
    return HAR.sub("", h) and [m for m in hm if m != "ْ"][:2] == [m for m in vm if m != "ْ"][:2]


def main():
    if os.path.exists(OUT):
        sys.exit(OUT + " exists — not overwritten")
    W = C.defaultdict(list)
    for line in open(WASIT, encoding="utf-8"):
        r = json.loads(line)
        k = bare(r["root"]["source_display"])
        for s in r["sources"].values():
            for c in s.get("claims") or []:
                if c.get("headword"):
                    W[k].append((c["headword"].strip(), c.get("text") or ""))
    rows, st = [], C.Counter()
    for e in csv.DictReader(open(EV, encoding="utf-8")):
        if e["layer"] not in ("الثلاثي", "المجرد"):
            continue
        vb = bare(e["verb"])
        hits = []
        for head, text in W.get(bare(e["root_K"]), []):
            hb = bare(head.split()[0]) if head.split() else ""
            if hb == vb and compatible(head.split()[0], e["verb"]):
                hits.append((head, text, False))
            elif hb in (vb + "ه", vb + "ها") and compatible(head.split()[0], e["verb"]):
                hits.append((head, text, True))
        tags, ev = [], []
        for head, text, hobj in hits:
            for fr in senses(text):
                t, h = frame_tag(fr, hobj)
                tags.append((t, h))
                if len(ev) < 3:
                    ev.append(f"{head} | {fr[:40]} → {t}{'/' + h if h else ''}")
        kinds = {t for t, _ in tags}
        if not tags:
            tr, harf = "غير معلوم", ""
        elif kinds == {"متعدي"}:
            tr, harf = "متعدي", ""
        elif kinds == {"لازم"}:
            tr, harf = "لازم", ""
        elif kinds <= {"لازم", "لازم_بحرف"}:
            tr = "لازم"
            harf = C.Counter(h for t, h in tags if h).most_common(1)[0][0]
        else:
            tr, harf = "مشترك", ""
        st[tr + ("+حرف" if harf else "")] += 1
        rows.append(dict(event_id=e["event_id"], root=e["root_K"], verb=e["verb"], form=e["form"], hfn_transitivity=e["transitivity"],
                         transitivity_wasit=tr, harf=harf, n_senses=len(tags),
                         sense_tags="·".join(t + ("/" + h if h else "") for t, h in tags), evidence=" ‖ ".join(ev), rank="CANDIDATE"))
    with open(OUT, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    print(len(rows), dict(st))
    x = C.Counter((r["hfn_transitivity"] or "فارغ", r["transitivity_wasit"]) for r in rows)
    for k, v in sorted(x.items(), key=lambda z: -z[1])[:16]:
        print(" ", k, v)


if __name__ == "__main__":
    main()
