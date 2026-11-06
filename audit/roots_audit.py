"""
roots_audit.py — فحص كلّ ما في arabic-net على الجذور الأكثر تكراراً، بثوابت مسمّاة لا بالصدفة (قراءة فقط).

القائمة (--list): أعلى 500 جذر قرآني بالتكرار، ~/roots/root-frequency-handoff/outputs/quran_top500_roots.csv
(مقيسة من Quranic Arabic Corpus 0.4، corpus.quran.com، 2026-09-21؛ sha256 dd1660af…8720). والتحقّق المتقاطع:
audit/roots_top200_parallelquran.tsv (https://parallelquran.com/morphology-explorer/?index=roots، جُلبت 2026-11-06):
اتّفقتا في 99 من أعلى 100، و198 من أعلى 200. الدفعة: --from 1 --to 100.

كلّ فحص ثابتٌ مسمّى يعطي PASS أو FAIL أو NA (لا ينطبق، بسببه) أو INFO، مع التفصيل:

  الجذر
    R_HFN        الجذر في HFN roots.csv (بمفتاح K)
    R_MEANING    معنى الجذر في بنك HFN (عشرة معاجم): كم معجماً، وأيّها غائب
    R_LEXLINK    لكلّ معجم: سجلٌّ للجذر في ملفّ المعجم (~/roots) والبنك لا يربطه → REVIEW مع نسبة نصوصه التي تذكر الجذر
                 (ربطٌ ناقص أم سجلّ مقطَّع خطأً — يُقرأ)؛ لا سجلّ أصلاً → INFO (نقص OCR)
    R_MAQAYIS    الجذر في مقاييس ابن فارس (Maqaiys-roots)
    R_WORDNET    الجذر في wordnet_roots.json، وعدد synsets
    R_TAHAYYUZ   توزيع تحيّز معاني الجذر الاسمية (word_tree.tahayyuz)
  الحدث (لكلّ حدث في HFN للجذر)
    E_ORTHO      رسم الفعل: لا حرف عليه حركتان، ولا حرفٌ (غير مدّ أو وصل) بلا حركة
    E_CONJ       المجرّد: الماضي للغائب من تصريف wazn-net (بنوع الجذر وحركة العين) = فعل HFN
    E_TEMPLATE   الفعل = الوزن بعد وضع حروف الجذر فيه (الحروف والحركات معاً). يُفسَّر الفرق بالإعلال/الإدغام/الإبدال
                 إن كان في الجذر حرف علّة أو تضعيف أو كان افتعل بحرف إبدال؛ وما لا تفسير له FAIL.
    E_MASDAR     للحدث مصدر
    E_PART_GEN   اسم الفاعل/المفعول في HFN = مولَّد wazn-net (للمجرّد الصحيح)؛ الفرق FAIL (أحدهما خطأ)
    E_PT_LAZIM   اسم مفعول على حدثٍ لازمٍ في HFN (فَعُلَ أو transitivity=لازم) → FAIL
    E_MAZID_GEN  فعل المزيد في HFN = _apply_wazn في wazn-net (للصحيح)
    E_API        arabic_net_api.verb(الفعل): لا مزوّد فاشل، والحدث نفسه مسترجع EXACT
  الطبقات المقيسة
    A_AHDATH     كلّ صفّ R1/R1W/T_JAL/J_* للجذر: event_id في HFN v37، والفعل نفسه مشكولاً، ووزنه وزن المسلك
    A_WAZN       المطاوعة والتعدية من wazn-net: الناتج فيه حروف الجذر الصحيحة بترتيبها
    W_ROOTWORDS  كلمات WordNet المنسوبة إلى الجذر (arabic_synset_map): كم منها لا تحوي حروفه الصحيحة بترتيبها
  الحالات: PASS · FAIL خطأ · REVIEW يحتاج قراءة · KNOWN فرقٌ يوثّقه المصدر نفسه (HFN residual) · CONV عُرف · INFO مفسَّر · NA لا ينطبق
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
AMLN = os.path.dirname(HERE)
sys.path.insert(0, AMLN)

from arabic_net_api import verb as api_verb  # noqa: E402
from arabic_net_api import hfn as P_HFN, roots as P_ROOTS, wazn as P_WAZN  # noqa: E402
from arabic_net_api._common import K, REPOS, nfc, on_path  # noqa: E402

HAR = re.compile("[ً-ْٰ]")
WEAK = set("اويىء")
HAMZA = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء"})
IBDAL_VIII = set("صضطظدذزثوت")
FORM_ROMAN = {"فَعَّلَ": "II", "فَاعَلَ": "III", "أَفْعَلَ": "IV", "تَفَعَّلَ": "V", "تَفَاعَلَ": "VI",
              "انْفَعَلَ": "VII", "افْتَعَلَ": "VIII", "افْعَلَّ": "IX", "اسْتَفْعَلَ": "X"}
ROUTE_FORM = {"J_SAJIYYA": "فَعُلَ", "J_DAA": "فَعِلَ", "T_JAL": "أَفْعَلَ"}


def form_is(form, want):
    """وزن HFN: «أَفْعَلَ» أو صيغته المعتلّة بالنصّ «أَفْعَى (أفعل ناقص)» (فحص الجذور، الدفعة 2: أَغْنَى)."""
    head, _, note = form.partition(" ")
    return head == want or HAR.sub("", nfc(want)) in note


def letters(s):
    return HAR.sub("", nfc(s)).replace("ـ", "")


def skel(s):
    return letters(s).translate(HAMZA)


def subseq(rad, word):
    it = iter(skel(word))
    return all(c in it for c in rad)


def instantiate(form, rad):
    """ضع حروف الجذر في الوزن: ف→1، ع→2، ل→3 ثم 4 (فَعْلَلَ)."""
    if " " in form or "(" in form or "/" in form:
        return None
    ls = iter(rad[2:])
    out = []
    for ch in nfc(form):
        if ch == "ف":
            out.append(rad[0])
        elif ch == "ع":
            out.append(rad[1])
        elif ch == "ل":
            out.append(next(ls, rad[-1]))
        else:
            out.append(ch)
    return "".join(out)


def mentions(text, R):
    """في النصّ كلمةٌ فيها حروف الجذر بترتيبها (الهمزة بمقاعدها ألفٌ؛ المضعّف بحرفيه)."""
    t = HAR.sub("", nfc(text)).translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ء": "ا", "ؤ": "ا", "ئ": "ا"}))
    rad = R.replace("ء", "ا")
    if len(rad) == 3 and rad[1] == rad[2]:
        rad = rad[:2]
    pat = re.compile(".*".join(map(re.escape, rad)))
    return any(pat.search(w) for w in t.split())


def variants(R):
    """مفاتيح الجذر في عُرف المقاييس وWordNet — من الواجهة نفسها (arabic_net_api.roots.key_variants)،
    مع مفتاح الناقص الثنائي الملتبس (يدي→يد)."""
    from arabic_net_api.roots import key_variants
    return key_variants(R, biliteral_naqis=True)


WASL = re.compile("^اِ")
VOWELS = set("ًٌٍَُِْ")          # تنوين، فتحة، ضمّة، كسرة، سكون (الشدّة تُجامعها)
MARKS = VOWELS | {"ّ", "ٰ"}


def ortho(v):
    """أخطاء رسمٍ بيّنة في فعلٍ مشكول: حرفٌ عليه حركتان، أو حرفٌ (غير حرف مدّ ولا ألف وصل) بلا حركة ولا سكون."""
    v = nfc(v)
    units, cur = [], None
    for ch in v:
        if ch in MARKS:
            if cur is not None:
                cur[1].append(ch)
        else:
            cur = [ch, []]
            units.append(cur)
    probs = []
    for i, (c, ms) in enumerate(units):
        vs = [m for m in ms if m in VOWELS]
        if len(vs) > 1:
            probs.append(f"«{c}» عليه حركتان ({''.join(vs)})")
        if not vs and i < len(units) - 1 and c not in "اى" and not (i == 0 and c == "ا"):
            prev = units[i - 1][1] if i else []
            madd = (c == "و" and "ُ" in prev) or (c == "ي" and "ِ" in prev) or c == "ٱ"
            if not madd and c not in "آ":
                probs.append(f"«{c}» بلا حركة")
    return probs


def explain(rad, form):
    why = []
    if set(rad) & set("ويا"):
        why.append("معتلّ")
    if len(rad) >= 3 and rad[1] == rad[2]:
        why.append("مضعّف")
    if "ء" in rad:
        why.append("مهموز (كرسيّ الهمزة)")
    if form.startswith("افْتَعَلَ") and rad[0] in IBDAL_VIII:
        why.append("إبدال افتعل")
    return why


class Audit:
    def __init__(self):
        self.h = P_HFN.api()
        rel = os.path.join(self.h.release_dir) if hasattr(self.h, "release_dir") else None
        info = P_HFN.info()
        self.release = info["release"]
        d = info["dir"]
        self.events = list(csv.DictReader(open(os.path.join(d, "events.csv"), encoding="utf-8")))
        self.ev_by_id = {e["event_id"]: e for e in self.events}
        self.ev_by_root = defaultdict(list)
        for e in self.events:
            self.ev_by_root[e["root_K"]].append(e)
        self.roots = {r["root_K"] for r in csv.DictReader(open(os.path.join(d, "roots.csv"), encoding="utf-8"))}
        self.lus = defaultdict(list)
        for x in csv.DictReader(open(os.path.join(d, "lexical_units.csv"), encoding="utf-8")):
            self.lus[x["event_id"]].append(x)
        hfn_tools = os.path.join(REPOS["hfn"], "tools")
        with on_path(hfn_tools):
            import root_meaning as RM
        self.bank = {r["K"]: r for r in csv.DictReader(open(RM.BANK, encoding="utf-8"))}
        base = os.path.expanduser("~/roots")
        files = defaultdict(set)
        for col, (fn, src) in RM.LEX.items():
            files[fn].add(src)
        found = defaultdict(set)                       # (file, src) → مفاتيح K
        self.lexshare = {}                             # (col, K) → (claims تذكر الجذر، claims ذات نصّ)
        for fn, srcs in files.items():
            pth = os.path.join(base, fn)
            if not os.path.exists(pth):
                continue
            for line in open(pth, encoding="utf-8"):
                r = json.loads(line)
                k = K(r["root"]["source_display"])
                for sname, sv in (r.get("sources") or {}).items():
                    if sname in srcs and (sv.get("claims") or []):
                        found[(fn, sname)].add(k)
                        for col, (f2, s2) in RM.LEX.items():
                            if f2 == fn and s2 == sname:
                                txt = [c.get("text") for c in sv["claims"] if c.get("text")]
                                self.lexshare[(col, k)] = (sum(mentions(t, k) for t in txt), len(txt))
        self.lexkeys = {col: (found[(fn, src)], RM.NAME.get(col, col)) for col, (fn, src) in RM.LEX.items()}
        wr = json.load(open(os.path.join(AMLN, "data", "wordnet", "wordnet_roots.json"), encoding="utf-8"))["roots"]
        self.wn_roots = {K(r["display"]): r for r in wr}
        self.syn_map = json.load(open(os.path.join(AMLN, "arabic_synset_map.json"), encoding="utf-8"))
        self.syn_by_root = defaultdict(list)
        for sid, v in self.syn_map.items():
            for r in v.get("roots") or []:
                self.syn_by_root[K(r)].append((sid, v.get("words") or []))
        with on_path(REPOS["wazn"]):
            from core.classify import classify, past_baab
            from engines import derivation_engine as D
            from engines import morphological_engine as M
        self.classify, self.D, self.M, self.past_baab = classify, D, M, past_baab
        from word_tree import ahdath as WA
        self.WA = WA
        self.text_only = {nfc(r["mutawaa_text"]) for r in csv.DictReader(
            open(os.path.join(AMLN, "audit", "mutawaa_text_only.tsv"), encoding="utf-8"), delimiter="\t")}
        self.ahdath_rows = defaultdict(list)
        # حكم المالك «أبقِها معلَّمة» يشمل كلّ مطاوعٍ معلَّم (PARTIAL_VOWELLING وROOT_LETTERS_MISSING)، لا ملفّ القائمة وحده
        self.text_only |= {nfc(x["mutawi"]) for x in WA._table() if x.get("mutawi_flags")}
        for x in WA._table():
            k = K(x["root"]) if x["root"] else None
            if k:
                self.ahdath_rows[k].append(x)
            else:                              # T_JAL بلا جذر: من HFN
                e = self.ev_by_id.get(x["event_id"])
                if e:
                    self.ahdath_rows[e["root_K"]].append(x)
        for xs in WA._jiha().values():
            for x in xs:
                self.ahdath_rows[K(x["root"])].append(dict(x, verb=x["verb"]))

    # ── الجذر ─────────────────────────────────────────────────────────
    def root_checks(self, R):
        out = []
        out.append(("R_HFN", "PASS" if R in self.roots else "FAIL", "" if R in self.roots else "ليس في roots.csv"))
        try:
            ms = P_ROOTS.meaning(R)
            lex = [m["source"] for m in ms]
            out.append(("R_MEANING", "PASS" if lex else "FAIL", f"{len(lex)} معجم: " + "، ".join(lex)))
        except Exception as e:
            out.append(("R_MEANING", "FAIL", f"{type(e).__name__}: {e}"[:200]))
        b = self.bank.get(R)
        for col, (keys, name) in self.lexkeys.items():
            linked = bool(b and b.get(col))
            infile = R in keys
            if linked:
                continue
            if not infile:
                out.append(("R_LEXLINK", "INFO", f"{name}: لا سجلّ للجذر في ملفّ المعجم (نقص OCR)"))
                continue
            k, n = self.lexshare.get((col, R), (0, 0))
            # لا عتبة: في السجلّات المربوطة نفسها كثيرٌ نصفُ نصوصه لا يذكر الجذر (القاموس 0.40، المحكم 0.48 وسيطاً)،
            # وفي غير المربوطة سجلّات مقطَّعة خطأً (لسان «علم» 1/38 نصّه عن نظم). فالحكم بالقراءة لا بالنسبة.
            out.append(("R_LEXLINK", "REVIEW", f"{name}: سجلّ الجذر في ملفّ المعجم والبنك لا يربطه — "
                                               f"{k}/{n} من نصوصه تذكر الجذر؛ يُقرأ: ربطٌ ناقص أم سجلّ مقطَّع خطأً"))
        for chk, table in (("R_MAQAYIS", P_ROOTS._maqayis()), ("R_WORDNET", self.wn_roots)):
            x = table.get(R)
            if x is not None:
                out.append((chk, "PASS", f'synsets={x["synsets_count"]}' if chk == "R_WORDNET" else ""))
                continue
            v = next((v for v in variants(R) if v in table), None)
            if v:
                amb = len(v) == 2 and R[1] != R[2]
                out.append((chk, "CONV", f"لا يوجد بمفتاح «{R}» بل «{v}» (عُرف المضعّف/الناقص): "
                                         + ("مفتاح ثنائي ملتبس بالمضعّف، والواجهة لا تسترجع به"
                                            if amb else "الواجهة تسترجع به منذ الدفعة 1")))
            elif chk == "R_MAQAYIS" and R in P_ROOTS._embedded():
                e = P_ROOTS._embedded()[R]
                out.append((chk, "INFO", f'مدفون في سجلّ «{e["host_display"]}» ({e["how"]}، الموضع {e["offset"]}): '
                                         "خطأ تقطيع في الاستخراج، والواجهة تسترجعه من النصّ الكامل منذ الدفعة 5"))
            else:
                out.append((chk, "FAIL", f"لا بـ«{R}» ولا بـ{variants(R) or 'بديل'}"))
        try:
            t = P_ROOTS.tahayyuz(R)
            out.append(("R_TAHAYYUZ", "PASS" if t else "INFO", "" if t else "لا معاني اسمية مصنّفة"))
        except Exception as e:
            out.append(("R_TAHAYYUZ", "FAIL", f"{type(e).__name__}: {e}"[:200]))
        return out

    # ── الحدث ─────────────────────────────────────────────────────────
    def event_checks(self, R):
        out = []
        evs = self.ev_by_root.get(R, [])
        if not evs:
            return [("E_*", "NA", "لا أحداث للجذر في HFN")]
        rad = list(R)
        mujarrad = [e for e in evs if e["form"] in ("فَعَلَ", "فَعِلَ", "فَعُلَ")]
        rtype = None
        if len(rad) == 3 and mujarrad:
            try:
                rtype = self.classify(R, mujarrad[0]["verb"]).root_type
            except Exception:
                rtype = None
        for e in evs:
            v, f, eid = e["verb"], e["form"], e["event_id"]
            tag = f"{v} ({f}) {eid}"
            i0 = len(out)
            pr = ortho(v)
            out.append(("E_ORTHO", "FAIL" if pr else "PASS", f"{tag}" + (": " + "؛ ".join(pr) if pr else "")))
            f0 = f.split(" ")[0]
            if f0 in ("فَعَلَ", "فَعِلَ", "فَعُلَ") and len(rad) == 3:
                try:
                    rc = self.classify(R, v)
                    par = self.M.conjugate(R, rc.root_type, self.past_baab(f0))
                    g = next(x.form for x in par.cells if x.mood == "ماضٍ" and x.voice == "معلوم"
                             and x.person == "غائب" and x.number == "مفرد" and x.gender == "مذكر")
                    if nfc(g) == nfc(v):
                        out.append(("E_CONJ", "PASS", f"{tag}: wazn-net «{g}» ({rc.root_type.value})"))
                    elif nfc(g).translate(HAMZA) == nfc(v).translate(HAMZA):
                        out.append(("E_CONJ", "CONV", f"{tag}: wazn-net «{g}» — كرسيّ الهمزة"))
                    else:
                        out.append(("E_CONJ", "FAIL", f"{tag}: wazn-net يصرّف «{g}» ({rc.root_type.value}، {f0})"))
                except Exception as ex:
                    out.append(("E_CONJ", "NA", f"{tag}: {type(ex).__name__}: {ex}"[:160]))
            inst = instantiate(f, rad) if len(rad) in (3, 4) else None
            if inst is None:
                out.append(("E_TEMPLATE", "NA", f"{tag}: وزنٌ موسوم بالإعلال أو غير قابل للتعويض"))
            elif nfc(inst).translate(HAMZA) == nfc(v).translate(HAMZA):
                out.append(("E_TEMPLATE", "PASS", tag))
            else:
                why = explain(rad, f)
                out.append(("E_TEMPLATE", "INFO" if why else "FAIL",
                            f"{tag}: الوزن يعطي «{inst}»" + (f" — يُفسَّر: {'، '.join(why)}" if why else " — بلا تفسير")))
            ms = [x for x in self.lus[eid] if x["pos_ar"] == "مصدر"]
            out.append(("E_MASDAR", "PASS" if ms or e.get("masdar") else "FAIL",
                        f"{tag}: " + "، ".join(x["lemma"] for x in ms)))
            # KNOWN: الفرق موثَّق في HFN نفسه (residual) — ليس خطأً جديداً، ويبقى نقصاً معلناً.
            res = e.get("residual") or ""
            for j in range(i0, len(out)):
                chk, st, d = out[j]
                if st != "FAIL":
                    continue
                if "JAMID" in res and chk in ("E_CONJ", "E_TEMPLATE", "E_MASDAR"):
                    out[j] = (chk, "KNOWN", d + " — HFN: فعلٌ جامد موثَّق (" + res.split(" · ")[0][:80] + ")")
                elif chk == "E_MASDAR" and "NO_MASDAR_FOUND" in res:
                    out[j] = (chk, "KNOWN", d + " — HFN يعلن: VERB_ATTESTED_NO_MASDAR_FOUND")
            # المشتقّات مقابل المولِّد
            ag = [x["lemma"] for x in self.lus[eid] if x["pos_ar"] == "اسم فاعل"]
            pt = [x["lemma"] for x in self.lus[eid] if x["pos_ar"] == "اسم مفعول"]
            lazim = f == "فَعُلَ" or e.get("transitivity") == "لازم"
            if pt and lazim:
                out.append(("E_PT_LAZIM", "FAIL", f"{tag}: اسم مفعول «{pt[0]}» على حدثٍ لازم (transitivity={e.get('transitivity')})"))
            if f in ("فَعَلَ", "فَعِلَ", "فَعُلَ") and len(rad) == 3 and rtype is not None and str(rtype.name) == "SAHIH" \
                    and not (set(rad) & set("ءوي")):
                g_ag = self.D._gen_ism_faail_I(*rad, rtype)
                g_pt = self.D._gen_ism_mafuul_I(*rad, rtype)
                for kind, have, gen in (("اسم الفاعل", ag, g_ag), ("اسم المفعول", pt, g_pt)):
                    if have:
                        ok = nfc(gen) in {nfc(x) for x in have}
                        out.append(("E_PART_GEN", "PASS" if ok else "FAIL",
                                    f"{tag}: {kind} HFN «{'، '.join(have)}» / wazn-net «{gen}»"))
            roman = FORM_ROMAN.get(f)
            if roman and len(rad) == 3 and not (set(rad) & set("ءوي")) and rad[1] != rad[2]:
                try:
                    g = self.D._apply_wazn(roman, *rad, self.D.RootType.SAHIH)["verb"]
                    ok = nfc(g) == nfc(v)
                    if not ok and WASL.sub("ا", nfc(g)) == nfc(v):
                        out.append(("E_MAZID_GEN", "CONV", f"{tag}: wazn-net «{g}» — همزة الوصل مكسورة هناك بلا حركة هنا"))
                    else:
                        why = explain(rad, f)
                        out.append(("E_MAZID_GEN", "PASS" if ok else ("INFO" if why else "FAIL"),
                                    f"{tag}: wazn-net «{g}»" + (f" — {'، '.join(why)}" if (why and not ok) else "")))
                except Exception as ex:
                    out.append(("E_MAZID_GEN", "FAIL", f"{tag}: {type(ex).__name__}: {ex}"[:200]))
            # الواجهة
            try:
                r = api_verb(v, root=R)
                got = {x["event_id"] for x in r["features"].get("hfn_event", [])}
                bad = [m["provider"] + ": " + m["reason"][:80] for m in r["missing"]]
                ok = eid in got and not bad
                out.append(("E_API", "PASS" if ok else "FAIL",
                            f"{tag}: " + ("" if eid in got else "الحدث غير مسترجع EXACT; ") + "; ".join(bad)))
            except Exception as ex:
                out.append(("E_API", "FAIL", f"{tag}: {type(ex).__name__}: {ex}"[:200]))
        return out

    # ── الطبقات المقيسة ───────────────────────────────────────────────
    def layer_checks(self, R):
        out = []
        RR = R[:2] if len(R) == 3 and R[1] == R[2] else R      # المضعّف: الشدّة تُسقط تكرار الحرف في الرسم
        sound = [c for c in RR if c not in "ءوي"]
        for x in self.ahdath_rows.get(R, []):
            e = self.ev_by_id.get(x["event_id"])
            tag = f'{x["route"]} {x["verb"]} {x["event_id"]}'
            if not e:
                out.append(("A_AHDATH", "FAIL", f"{tag}: event_id ليس في HFN {self.release}"))
                continue
            probs = []
            if nfc(e["verb"]) != nfc(x["verb"]):
                probs.append(f'الفعل في HFN «{e["verb"]}»')
            want = ROUTE_FORM.get(x["route"])
            if want and not form_is(e["form"], want):
                probs.append(f'وزن الحدث {e["form"]} لا {want}')
            known = (f'المطاوع «{x["mutawi"]}» ({x.get("mutawi_src", "")}): ' + "، ".join(x["mutawi_flags"])
                     + " — معلَّم بحكم المالك 2026-11-06 «أبقِها معلَّمة»") if x.get("mutawi_flags") else ""
            st = "FAIL" if probs else ("KNOWN" if known else "PASS")
            out.append(("A_AHDATH", st, tag + (": " + "؛ ".join(probs + ([known] if known else [])) if probs or known else "")))
        for e in self.ev_by_root.get(R, []):
            for x in P_WAZN.features(e["verb"]):
                if x["match"] != "EXACT":
                    continue
                why = []
                if not subseq(sound, x["value"]):
                    why.append("حروف الجذر غائبة")
                if not HAR.search(nfc(x["value"])):
                    why.append("الناتج بلا حركات")
                why += ortho(x["value"])
                st = "FAIL" if why else "PASS"
                if why and nfc(x["value"]) in self.text_only:
                    st, why = "KNOWN", why + ["مطاوع من نصّ الوسيط معلَّم بحكم المالك 2026-11-06 (audit/mutawaa_text_only.tsv)"]
                out.append(("A_WAZN", st,
                            f'{x["feature"]} {e["verb"]} → {x["value"]} ({x["route"]})' + (" — " + "؛ ".join(why) if why else "")))
        syns = [(sid, [w for w in ws if len(letters(w)) >= 2]) for sid, ws in self.syn_by_root.get(R, [])]
        syns = [(sid, ws) for sid, ws in syns if ws]
        if syns:
            bad = [(sid, ws) for sid, ws in syns if not any(subseq(sound, w) for w in ws)]
            rate = len(bad) / len(syns)
            out.append(("W_ROOTWORDS", "FAIL" if rate > 0.10 else "PASS",
                        f"{len(bad)}/{len(syns)} synset منسوب إلى الجذر ولا كلمة فيه تحوي {''.join(sound)}: "
                        + "، ".join(f"{sid}={' '.join(ws)[:30]}" for sid, ws in bad[:6])))
        else:
            out.append(("W_ROOTWORDS", "INFO", "لا synset منسوب إلى الجذر في arabic_synset_map"))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", type=int, default=1)
    ap.add_argument("--to", dest="b", type=int, default=100)
    ap.add_argument("--out", default=None)
    ap.add_argument("--list", default="~/roots/root-frequency-handoff/outputs/quran_top500_roots.csv")
    a = ap.parse_args()
    lst = list(csv.DictReader(open(os.path.expanduser(a.list), encoding="utf-8-sig"),
                              delimiter="\t" if a.list.endswith(".tsv") else ","))
    for r in lst:
        r["root"] = (r.get("root") or r.get("root_ar") or "").replace(" ", "")
    lst = [r for r in lst if a.a <= int(r["rank"]) <= a.b]
    A = Audit()
    out = a.out or os.path.join(HERE, f"batch_{a.a:03d}_{a.b:03d}")
    os.makedirs(out, exist_ok=True)
    rows = []
    for r in lst:
        R = K(r["root"])
        for fn in (A.root_checks, A.event_checks, A.layer_checks):
            for chk, st, det in fn(R):
                rows.append(dict(rank=r["rank"], root=r["root"], K=R, check=chk, status=st, detail=det))
    with open(os.path.join(out, "findings.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    c = Counter((x["check"], x["status"]) for x in rows)
    summ = dict(release=A.release, roots=len(lst), rows=len(rows),
                by_check={k: {s: c[(k, s)] for s in ("PASS", "FAIL", "REVIEW", "KNOWN", "CONV", "INFO", "NA") if c[(k, s)]}
                          for k in sorted({x["check"] for x in rows})})
    json.dump(summ, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
