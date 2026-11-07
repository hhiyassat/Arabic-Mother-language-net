"""
build_maqayis_embedded.py — جذور المقاييس المدفونة في سجلّ جذرٍ آخر (فحص الجذور، الدفعة ٥).

الاستخراج (word_tree/maqayis.db، 4548 سجلّاً) قطّع بعض المواد في غير موضعها، فبقي عنوان المادّة
«الياء والواو والميم» في وسط سجلّ «يوح». هذا السكربت يمسح النصّ الكامل (body_text) بحثاً عن عناوين المواد
في وسط السجلّات، ويكتب لكلّ جذرٍ لا مفتاح له في الجدول: سجلّه المضيف وموضع العنوان فيه.

أنماط العنوان (مع تسامح OCR):
  «X وY وZ»            مسبوقاً برقم أو نقطة أو «أمّا» أو «اعلم أنّ» أو «*» (التاء * والراء والكاف)
  «* وY وZ»            الحرف الأول ساقط، فيُؤخذ من السجلّ المضيف (* والخاء والراء ← سخر في سخد)
  «X وY في المضاعف»    المضعّف (الباء والراء في المضاعف ← برر في بذ)؛ «وأمّا X وY فأصل» (أمم في أل)
«الصاء» تُقرأ صاداً (الصاء والياء والراء ← صير في صيد).

لا يُغيَّر شيء في المقاييس ولا في maqayis.db. الناتج data/maqayis_embedded.tsv: مؤشّر (المضيف، الموضع) لا نصّ.

    python3 audit/build_maqayis_embedded.py
"""
from __future__ import annotations

import csv
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AMLN = os.path.dirname(HERE)
sys.path.insert(0, AMLN)
from arabic_net_api import roots as R  # noqa: E402
from arabic_net_api._common import K  # noqa: E402

DB = os.path.join(AMLN, "word_tree", "maqayis.db")
OUT = os.path.join(AMLN, "data", "maqayis_embedded.tsv")
HAR = re.compile(r"[ً-ْٰ]")
N = {"الهمزة": "ء", "الباء": "ب", "التاء": "ت", "الثاء": "ث", "الجيم": "ج", "الحاء": "ح", "الخاء": "خ",
     "الدال": "د", "الذال": "ذ", "الراء": "ر", "الزاء": "ز", "الزاي": "ز", "السين": "س", "الشين": "ش",
     "الصاد": "ص", "الصاء": "ص", "الضاد": "ض", "الطاء": "ط", "الظاء": "ظ", "العين": "ع", "الغين": "غ",
     "الفاء": "ف", "القاف": "ق", "الكاف": "ك", "اللام": "ل", "الميم": "م", "النون": "ن", "الهاء": "ه",
     "الواو": "و", "الياء": "ي"}
ALT = "|".join("ا?" + re.escape(n[1:]) for n in sorted(N, key=len, reverse=True))     # «ولراء» (الألف ساقطة في OCR)


def nm(g):
    return N.get(g) or N.get("ا" + g)
S = r"\s*\*?\s*"
FULL = re.compile(rf"({ALT}){S}و{S}({ALT}){S}و{S}({ALT})(?![\w])")
LOST = re.compile(rf"(?:^|[.:؛\]\)٠-٩\n])\s*\*\s*و({ALT}){S}و{S}({ALT})(?![\w])")
DOUBLED = re.compile(rf"({ALT})\s*\*?\s*و({ALT})\s+(?:فى|في)\s+المضاعف|وأم+ا\s+({ALT})\s*و({ALT})\s+فأصل")
PRE = re.compile(r"(\n|[٠-٩0-9\]\.:]|أما|أمّا|اعلم أن|اعلم أنَّ|\*)\s*\S{0,4}\s*$")


def known(k, table):
    return k in table or any(v in table for v in R.key_variants(k))


def scan():
    table = R._maqayis()
    out = {}
    con = sqlite3.connect(DB)
    for eid, disp, body in con.execute("select id, root_display, body_text from entries order by id"):
        bb, hk = HAR.sub("", body), K(disp)

        def add(k, pos, how):
            if k != hk and not known(k, table):
                out.setdefault(k, (disp, eid, pos, how, bb[pos:pos + 60].replace("\n", " ").replace("\t", " ")))
        for m in FULL.finditer(bb):
            if m.start() >= 5 and PRE.search(bb[max(0, m.start() - 14):m.start()]):
                add(K("".join(nm(g) for g in m.groups())), m.start(), "HEADING")
        for m in LOST.finditer(bb):
            add(K(hk[0] + "".join(nm(g) for g in m.groups())), m.start(), "HEADING_FIRST_LETTER_LOST")
        for m in DOUBLED.finditer(bb):
            g = [x for x in m.groups() if x]
            if nm(g[0]) != nm(g[1]):
                add(K(nm(g[0]) + nm(g[1]) + nm(g[1])), m.start(), "DOUBLED")
    return out


# ما ينصّ ابن فارس على أنّه مادّةٌ واحدة مع غيرها (لا تقطيع): يُبحث عن نصّه في السجلّ المضيف.
MANUAL = [("قرء", "قري", "وإذا همز هذا الباب كان هو والأول سواء", "SAME_ENTRY_HAMZ")]


def manual(out):
    con = sqlite3.connect(DB)
    for k, host, phrase, how in MANUAL:
        eid, body = con.execute("select id, body_text from entries where root_display=?", (host,)).fetchone()
        bb = HAR.sub("", body)
        pos = bb.find(phrase)
        if pos >= 0 and k not in out:
            out[k] = (host, eid, pos, how, bb[pos:pos + 60].replace("\n", " "))


HAMZ = re.compile(r"(?:فأما|وأما|ومن|وإذا|فإذا|وإن)\s+(?:المهموز|همز(?:ت)?)|وبالهمز|وأما\s+الهمز")


def targets():
    """الجذور المطلوبة: HFN (أحدث إصدار) وكلّ جذور القرآن (audit/all_roots/quran_all_roots.csv)."""
    ks = set()
    rel = sorted((d for d in os.listdir(os.path.join(R.REPOS["hfn"], "release")) if d.startswith("release_v")),
                 key=lambda d: int(d.split("_v")[1]))[-1]
    for r in csv.DictReader(open(os.path.join(R.REPOS["hfn"], "release", rel, "roots.csv"), encoding="utf-8")):
        ks.add(r["root_K"])
    q = os.path.join(HERE, "all_roots", "quran_all_roots.csv")
    if os.path.exists(q):
        ks |= {K(r["root_ar"].replace(" ", "")) for r in csv.DictReader(open(q, encoding="utf-8-sig"))}
    return ks


def same_entry(out):
    """ابن فارس يذكر المهموز اللام في مادّة المعتلّ أو المادّة المجاورة بنصّه: «وأمّا المهموز …»، «وإذا همز …» (درأ في درى،
    فتأ في فتى، نسأ في نسي). يُقبل إذا تلت العبارةَ كلمةٌ بحرفي الجذر الأوّلين ثم همزة في 160 حرفاً."""
    table = R._maqayis()
    con = sqlite3.connect(DB)
    ents = [(eid, disp, HAR.sub("", body)) for eid, disp, body in con.execute("select id, root_display, body_text from entries order by id")]
    for k in sorted(targets()):
        if len(k) != 3 or k[2] != "ء" or k in out or known(k, table):
            continue
        word = re.compile(k[0] + k[1] + "[أءئؤا]")
        for eid, disp, bb in ents:
            if K(disp)[:2] != k[:2]:
                continue
            hit = next((m for m in HAMZ.finditer(bb) if word.search(bb[m.start():m.start() + 160])), None)
            if hit:
                out[k] = (disp, eid, hit.start(), "SAME_ENTRY_HAMZ", bb[hit.start():hit.start() + 60].replace("\n", " "))
                break


def main():
    out = scan()
    manual(out)
    same_entry(out)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["root_K", "host_display", "host_entry_id", "offset", "how", "heading"])
        for k, row in sorted(out.items()):
            w.writerow([k, *row])
    print(len(out), "→", OUT)


if __name__ == "__main__":
    main()
