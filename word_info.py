#!/usr/bin/env python3
"""
word_info.py — كلُّ ما في شجرة الكلمات عن كلمة واحدة (قراءة فقط).

    python3 word_info.py جبل
    python3 word_info.py جَبَل --all          # لا اختصار في العلاقات والأمثلة
    python3 word_info.py جبل --lexicons       # ومعه مواد الجذر في المعاجم الثمانية (~/roots)
    python3 word_info.py جبل --json           # المخرَج JSON
    python3 word_info.py mountain.n.01        # بمعرّف المعنى مباشرة

المصادر (لا يعدّل منها شيئاً):
  data/wordnet/wordnet_synsets.json      الكلمات، التشكيل، الجذر، الشرح
  data/wordnet/wordnet_search_index.json  فهرس البحث
  data/wordnet/wordnet_relations.json     العلاقات (أعلى/أدنى/جزء/ضدّ ...) والأمثلة
  data/wordnet/wordnet_wazn.json          الوزن
  data/wordnet/wordnet_tahayyuz.json      التحيّز (CANDIDATE)
  data/wordnet/wordnet_roots.json         أصول ابن فارس (المقاييس) للجذر
  word_tree/maqayis.db                    شواهد الشعر من المقاييس
  ~/roots/*_out/*-root-meanings-v2.jsonl  مواد الجذر في المعاجم (مع --lexicons فقط)

كلّ الأحكام في هذه الطبقات CANDIDATE إلا ما حكم به المالك.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
WN = os.path.join(HERE, "data", "wordnet")
MAQ_DB = os.path.join(HERE, "word_tree", "maqayis.db")
ROOTS_DIR_DEFAULT = os.path.expanduser("~/roots")

REL_AR = {
    "hypernyms": "أعمّ منه", "instance_hypernyms": "هو فردٌ من",
    "hyponyms": "أخصّ منه", "instance_hyponyms": "أفراده",
    "part_holonyms": "هو جزءٌ من", "part_meronyms": "أجزاؤه",
    "member_holonyms": "هو عضوٌ في", "member_meronyms": "أعضاؤه",
    "substance_holonyms": "هو مادّةٌ لـ", "substance_meronyms": "مادّته",
    "antonyms": "ضدّه", "similar_to": "قريبٌ منه", "also_see": "انظر أيضاً",
    "derivations": "مشتقّات مرتبطة", "attributes": "صفات/ما يوصف به",
    "entailments": "يستلزم", "causes": "يسبّب",
}
REL_ORDER = list(REL_AR)
POS_AR = {"n": "اسم", "v": "فعل", "a": "صفة", "s": "صفة", "r": "ظرف"}
TAH_LABEL = {
    "MUTAHAYYIZ": "ذات متحيّزة (لها جثّة)", "HAYYIZ_MUBHAM": "حيّز مبهم نسبيّ",
    "MANA": "معنى (لا جثّة له)", "ZAMAN": "زمان", "DEFER": "لم يُحسم — للمالك",
}
TAH_SUB = {
    "MAKAN": "مكان مختصّ", "ZARF": "ظرف مكان", "JIHA": "جهة",
    "MIQDAR_MASAFA": "مقدار مسافة", "MIQDAR_MISAHA": "مقدار مساحة (غير منصوص)",
    "TAXON": "جنس تصنيفيّ (كلّي)", "GHAYB": "غيبيّ/أسطوريّ",
}


# ── تطبيع ─────────────────────────────────────────────────────────────────────
def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def strip_h(s: str) -> str:
    """حذف الحركات والشدّة والسكون والألف الخنجرية والتطويل."""
    return "".join(c for c in nfc(s) if not (0x064B <= ord(c) <= 0x0652 or ord(c) in (0x0670, 0x0640)))


def fold(s: str) -> str:
    """تطبيعٌ أوسع للبحث الاحتياطي فقط: الهمزات والألف المقصورة والتاء المربوطة وأل."""
    s = strip_h(s)
    s = s.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}))
    return s


def fold_root(s: str) -> str:
    """مقارنة الجذور: كلّ صور الهمزة ← ء ؛ ى ← ي."""
    s = strip_h(s)
    return s.translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء", "ى": "ي"}))


# ── تحميل ─────────────────────────────────────────────────────────────────────
def _rd(name):
    p = os.path.join(WN, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


class Tree:
    def __init__(self):
        syn = _rd("wordnet_synsets.json")
        self.meta = syn.get("_meta", {})
        self.syn = {x["id"]: x for x in syn.get("synsets", [])}
        self.index = _rd("wordnet_search_index.json")
        self.rel = _rd("wordnet_relations.json")
        self.wazn = _rd("wordnet_wazn.json").get("wazn_map", {})
        self.tah = _rd("wordnet_tahayyuz.json").get("synsets", {})
        self.roots = {fold_root(r["display"]): r for r in _rd("wordnet_roots.json").get("roots", [])}
        # فهارس البحث: نصٌّ مجرّد من الحركات ، ونصٌّ مطبّع تطبيعاً أوسع
        self.by_strip, self.by_fold = {}, {}
        for sid, x in self.syn.items():
            for w in x.get("words_ar", []) + [v for v in x.get("words_ar_vowelled", []) if v]:
                self.by_strip.setdefault(strip_h(w), set()).add(sid)
                self.by_fold.setdefault(fold(w), set()).add(sid)
        for k, ids in self.index.items():
            self.by_strip.setdefault(strip_h(k), set()).update(ids)
            self.by_fold.setdefault(fold(k), set()).update(ids)

    # ---
    def label(self, sid):
        x = self.syn.get(sid)
        if not x:
            return sid
        vw = [v for v in x.get("words_ar_vowelled", []) if v]
        w = (vw or x.get("words_ar") or [""])[0]
        return f"{w} ({sid})" if w else sid

    def find(self, q):
        q = nfc(q.strip())
        if q in self.syn:
            return [q], "id"
        s = strip_h(q)
        if s in self.by_strip:
            ids, how = self.by_strip[s], "exact"
        else:
            f = fold(q)
            ids, how = self.by_fold.get(f), "folded"
            if not ids and f.startswith("ال"):          # «الجبل» ← «جبل»
                ids, how = self.by_fold.get(f[2:]), "folded-no-al"
            ids = ids or set()
        # إن كان المدخل مشكولاً: قدّم المعاني التي تشكيلُها يطابقه
        vowelled = q != s

        def key(sid):
            x = self.syn.get(sid, {})
            exact_v = vowelled and q in [nfc(v) for v in x.get("words_ar_vowelled", [])]
            first = strip_h((x.get("words_ar") or [""])[0]) == s
            return (not exact_v, not first, {"n": 0, "v": 1}.get(x.get("pos"), 2), sid)
        return sorted((i for i in ids if i in self.syn), key=key), how


# ── أقسام المخرَج ────────────────────────────────────────────────────────────
def synset_record(t: Tree, sid: str, full: bool) -> dict:
    x = t.syn[sid]
    lim = None if full else 6
    rec = {
        "id": sid,
        "pos": x.get("pos"), "pos_ar": POS_AR.get(x.get("pos"), x.get("pos")),
        "words_ar": x.get("words_ar", []),
        "words_ar_vowelled": x.get("words_ar_vowelled", []),
        "vowel_source": x.get("words_ar_vowel_source", []),
        "roots": x.get("roots", []), "root_status": x.get("root_status"),
        "gloss_ar": x.get("gloss_ar"), "gloss_status": x.get("gloss_status"),
        "review_status": x.get("review_status"),
        "def_ar": x.get("def_ar"), "domain_ar": x.get("domain_ar"),
        "wazn": t.wazn.get(sid),
        "tahayyuz": None,
        "relations": {}, "examples_en": [],
    }
    th = t.tah.get(sid)
    if th:
        lab = TAH_LABEL.get(th["class"], th["class"])
        if th.get("subtype"):
            lab += " — " + TAH_SUB.get(th["subtype"], th["subtype"])
        rec["tahayyuz"] = dict(th, label_ar=lab)
    r = t.rel.get(sid, {})
    for k in REL_ORDER:
        if r.get(k):
            rec["relations"][k] = {"count": len(r[k]), "targets": [t.label(i) for i in r[k][:lim]]}
    rec["examples_en"] = (r.get("examples") or [])[: (None if full else 2)]
    return {k: v for k, v in rec.items() if v not in (None, [], {}, "")}


def root_record(t: Tree, root: str, full: bool) -> dict:
    out = {"root": root}
    rr = t.roots.get(fold_root(root))
    if rr:
        axes = rr.get("axes")
        out["maqayis_axes"] = axes if isinstance(axes, list) else axes
        txt = rr.get("ibn_faris") or ""
        out["maqayis_text"] = txt if full else (txt[:400] + ("…" if len(txt) > 400 else ""))
        out["synsets_count"] = rr.get("synsets_count") or len(rr.get("synsets") or [])
    # شواهد الشعر من قاعدة المقاييس
    if os.path.exists(MAQ_DB):
        try:
            c = sqlite3.connect(f"file:{MAQ_DB}?mode=ro", uri=True)
            rows = c.execute("SELECT id, root_display FROM entries").fetchall()
            ids = [i for i, d in rows if fold_root(d) == fold_root(root)]
            if ids:
                q = ",".join("?" * len(ids))
                poems = [p for (p,) in c.execute(
                    f"SELECT line_text FROM poetry_evidence WHERE entry_id IN ({q}) ORDER BY entry_id, line_num", ids)]
                out["maqayis_poetry"] = poems if full else poems[:4]
                out["maqayis_poetry_count"] = len(poems)
            c.close()
        except sqlite3.Error as e:
            out["maqayis_db_error"] = str(e)
    # توزيع التحيّز على معاني الجذر الاسمية
    from collections import Counter
    noun_ids = [sid for sid, x in t.syn.items() if x.get("pos") == "n"
                and any(fold_root(r) == fold_root(root) for r in x.get("roots", []))]
    cnt = Counter(t.tah[i]["class"] for i in noun_ids if i in t.tah)
    if noun_ids:
        out["tahayyuz_by_class"] = {TAH_LABEL.get(k, k): v for k, v in cnt.most_common()}
        out["noun_senses"] = len(noun_ids)
    return out


def lexicon_records(roots: list, roots_dir: str, full: bool) -> dict:
    """مواد الجذر في المعاجم الثمانية — بحثٌ نصّيّ سريع ثم تحليل السطر المطابق فقط."""
    want = {fold_root(r) for r in roots}
    out = {}
    for path in sorted(glob.glob(os.path.join(roots_dir, "*_out", "*-root-meanings-v2.jsonl"))):
        name = os.path.basename(path).split("-root-meanings")[0]
        needles = []
        for r in roots:
            for v in {r, r.replace("ء", "أ"), r.replace("أ", "ء")}:
                needles.append(f'"source_display": "{v}"')
        hits = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not any(n in line for n in needles):
                    continue
                d = json.loads(line)
                if fold_root(d["root"]["source_display"]) not in want:
                    continue
                for src, body in d.get("sources", {}).items():
                    claims = body.get("claims", [])
                    hits.append({
                        "root": d["root"]["source_display"], "source": src,
                        "status": body.get("status"), "claims_count": len(claims),
                        "claims": [f'{c.get("headword", "")}: {c.get("text", "")}'.strip()
                                   for c in (claims if full else claims[:8])],
                        "evidence": [f'{e.get("source_title", "")} — {e.get("evidence_id", "")}'
                                     for e in body.get("evidence", [])[:3]],
                    })
        if hits:
            out[name] = hits
    return out


# ── طباعة ─────────────────────────────────────────────────────────────────────
def show(res: dict):
    p = print
    p(f"\n═══ «{res['query']}» — {len(res['senses'])} معنى (مطابقة: {res['match']}) ═══")
    if not res["senses"]:
        p("لا شيء في الشجرة لهذه الكلمة.")
    for n, s in enumerate(res["senses"], 1):
        vw = [v for v in s.get("words_ar_vowelled", []) if v]
        p(f"\n── {n}. {s['id']}  [{s.get('pos_ar')}]")
        p(f"   الكلمات: {'، '.join(s.get('words_ar', []))}")
        if vw:
            src = [v for v in s.get("vowel_source", []) if v]
            p(f"   التشكيل: {'، '.join(vw)}" + (f"   (مصدره: {'، '.join(sorted(set(src)))})" if src else ""))
        if s.get("roots"):
            p(f"   الجذر: {'، '.join(s['roots'])}   ({s.get('root_status', '')})")
        if s.get("gloss_ar"):
            p(f"   الشرح: {s['gloss_ar']}   [{s.get('gloss_status', '')}]")
        if s.get("def_ar"):
            p(f"   تعريف: {s['def_ar']}" + (f"   — المجال: {s['domain_ar']}" if s.get("domain_ar") else ""))
        if s.get("review_status"):
            p(f"   مراجعة المالك: {s['review_status']}")
        if s.get("wazn"):
            w = s["wazn"]
            p(f"   الوزن: {w.get('wazn')} — {w.get('label')} (عمليّة: {w.get('op')}، المسلك: {w.get('source')})")
        if s.get("tahayyuz"):
            th = s["tahayyuz"]
            p(f"   التحيّز: {th['label_ar']}   [مسلك {th.get('route')}، دليل: {th.get('why')}، {th.get('status')}]")
        for k, v in s.get("relations", {}).items():
            more = f" … (+{v['count'] - len(v['targets'])})" if v["count"] > len(v["targets"]) else ""
            p(f"   {REL_AR[k]}: {'، '.join(v['targets'])}{more}")
        for e in s.get("examples_en", []):
            p(f"   مثال (EN): {e}")

    for r in res.get("roots", []):
        p(f"\n═══ الجذر «{r['root']}» ═══")
        if r.get("maqayis_axes"):
            p(f"   أصول ابن فارس: {r['maqayis_axes']}")
        if r.get("maqayis_text"):
            p("   نصّ المقاييس: " + r["maqayis_text"].replace("\n", " ⁄ "))
        for line in r.get("maqayis_poetry", []):
            p(f"   شاهد: {line}")
        if r.get("maqayis_poetry_count", 0) > len(r.get("maqayis_poetry", [])):
            p(f"   … ({r['maqayis_poetry_count']} شاهداً في المجموع)")
        if r.get("noun_senses"):
            dist = "، ".join(f"{k}: {v}" for k, v in r["tahayyuz_by_class"].items())
            p(f"   معاني الجذر الاسمية في الشجرة: {r['noun_senses']} — التحيّز: {dist}")

    for lex, hits in res.get("lexicons", {}).items():
        for h in hits:
            p(f"\n═══ {lex} — مادة «{h['root']}» ({h['claims_count']} ادّعاء، {h['status']}) ═══")
            for c in h["claims"]:
                p(f"   • {c}")
            if h["claims_count"] > len(h["claims"]):
                p(f"   … (+{h['claims_count'] - len(h['claims'])})")
    if "lexicons" in res and not res["lexicons"]:
        p("\n(لم يوجد الجذر في ملفّات المعاجم.)")
    p(f"\n— كلّ ما سبق CANDIDATE ما لم يحكم به المالك. زمن البحث: {res['seconds']} ث\n")


def main():
    ap = argparse.ArgumentParser(description="كلّ ما في شجرة الكلمات عن كلمة")
    ap.add_argument("word", help="كلمة عربية (مشكولة أو غير مشكولة) أو معرّف معنى مثل mountain.n.01")
    ap.add_argument("--all", action="store_true", help="بلا اختصار")
    ap.add_argument("--lexicons", action="store_true", help="أضف مواد الجذر من المعاجم الثمانية (أبطأ)")
    ap.add_argument("--roots-dir", default=ROOTS_DIR_DEFAULT, help="مجلّد المعاجم (افتراضيّاً ~/roots)")
    ap.add_argument("--pos", choices=list(POS_AR), help="قصر النتائج على قسم كلام")
    ap.add_argument("--json", action="store_true", help="المخرَج JSON")
    a = ap.parse_args()

    t0 = time.time()
    t = Tree()
    ids, how = t.find(a.word)
    if a.pos:
        ids = [i for i in ids if t.syn[i].get("pos") == a.pos]
    senses = [synset_record(t, i, a.all) for i in ids]

    roots = []
    for s in senses:
        for r in s.get("roots", []):
            if r not in roots:
                roots.append(r)
    # إن كانت الكلمة نفسها جذراً معروفاً في المقاييس فأضفه
    q = strip_h(a.word)
    if fold_root(q) in t.roots and not any(fold_root(r) == fold_root(q) for r in roots):
        roots.insert(0, t.roots[fold_root(q)]["display"])

    res = {"query": a.word, "match": how, "senses": senses,
           "roots": [root_record(t, r, a.all) for r in roots]}
    if a.lexicons:
        res["lexicons"] = lexicon_records(roots, a.roots_dir, a.all)
    res["seconds"] = round(time.time() - t0, 1)

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        show(res)


if __name__ == "__main__":
    sys.exit(main())
