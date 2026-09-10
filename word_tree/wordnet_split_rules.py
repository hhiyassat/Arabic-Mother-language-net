#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""طبقةُ قواعدِ شقِّ تعريفاتِ ووردنت العربيّة — بلا مدخلٍ ولا مخرجٍ ولا متن.

هذا الملفُّ هو **الموضعُ الكنسيُّ** للقاعدتَين المُصلَحتَين. نُقل نصُّه حرفًا
من ملفِ التشغيلِ المُصدَّقِ في الجولةِ `TWO-RULE-REPAIR-02`، ولم يُعَد صوغُه.

    RULE_1_FIX_HEAD_RECOVERY            — استرجاعُ الرأسِ المشترك
    RULE_2_BLOCK_X_OR_MORE_FROM_SPLITTING — منعُ شقِّ «س أو أكثر»

وكلتاهما `FAIL_CLOSED`: لا برهانَ صرفيًّا ⟶ تأجيلٌ، لا تخمين.

`MORPH` يُحقن من الخارج بالمحلّلِ الصرفيِّ الموجود (`analyze_word`)، ولا
يُنشأ هنا محلّلٌ ثانٍ. و`None` ⟶ لا برهانَ ⟶ تأجيل.

ممنوعٌ في هذا الملفّ: معرّفُ synset · نصُّ تعريفٍ بعينِه · جردُ ألفاظٍ
مغلقٌ للأهداف · قرينةُ تكرارِ الكلمة · لاحقةٌ وحدَها دليلًا صرفيًّا ·
استيرادٌ من FrameNet أو Wazn أو Maqaiys أو vendor · أيُّ API أو نموذجٍ لغويّ.

`APPLIED_TO_THE_CORPUS = False` · `PROJECT_FINISHED = NO`
"""
from __future__ import annotations

import unicodedata

MARKERS = (" أو ", " أم ")


SEPARATORS = "؛;،,:()·—"


MARKS = set("ًٌٍَُِّْٰٕٓٔ")


def bare(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFC", s)
                   if c not in MARKS)


def flatten(gloss: str) -> str:
    """التعريفُ بفواصلِه مُبدَلةً فراغًا — **تطبيعُ حدٍّ لا إعادةُ صوغ**.

    وبه تُقابَل الأطرافُ بالأصل، فلا يُحسب «(خاصة» غيرَ «خاصة».
    """
    cur = gloss
    for c in SEPARATORS:
        cur = cur.replace(c, " ")
    return " ".join(cur.split())


def paren_spans(gloss: str) -> list[tuple[int, int]]:
    """مواضعُ الاعتراض بين قوسَين — تُقرأ من الترقيمِ الحاضرِ في النصّ."""
    out, stack = [], []
    for i, c in enumerate(gloss):
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            out.append((stack.pop(), i))
    return out


def segments(gloss: str) -> list[dict]:
    """مقاطعُ فيها أداةُ فصل — ولكلٍّ **أفي اعتراضٍ هو أم في صلبِ الحدّ**."""
    spans = paren_spans(gloss)
    out, start = [], 0
    cur = gloss
    for c in SEPARATORS:
        cur = cur.replace(c, "\x00")
    for piece in cur.split("\x00"):
        at = start
        start += len(piece) + 1
        if not any(m in piece for m in MARKERS):
            continue
        inside = any(a < at + len(piece) and at < b for a, b in spans)
        out.append({"text": piece.strip(), "at": at, "parenthetical": inside})
    return out


def split_segment(seg: str) -> list[str]:
    """أطرافُ الفصل — ثلاثةٌ فأكثرُ إن تعدّدت الأداة."""
    cur = seg
    for m in MARKERS:
        cur = cur.replace(m, "\x00")
    return [p.strip() for p in cur.split("\x00") if p.strip()]


#: أسبابُ الامتناعِ عن الشقّ — **جردٌ مغلق**، ولا يُشقّ ما لم يُعرف نمطُه.
REFUSALS = ("PARENTHETICAL_ASIDE", "NO_TWO_PARTS", "MIDDLE_IS_LONGEST",
            "EMPTY_PART", "X_OR_MORE_BLOCK")


#: الطرفُ الأيمنُ الذي لا يقوم حدًّا مستقلًّا. **جردٌ مغلق**.
QUANTITY_TAIL = ("أكثر",)


#: تنوينُ الفتحِ آخرَ اللفظ، بالترتيبَين. **جردٌ مغلق** — للقرينةِ `A` وحدَها.
#: وهو علامةُ النصبِ أيًّا كان حاملُه: ألفًا (ـاً) أو همزةً (ـاءً) أو تاءً (ـةً).
#: والجردُ السابقُ اشترط الألفَ وحدَها، فأسقط «غطاءً» و«جودةً» — وهو خطأٌ مقيس.
ACCUSATIVE_ENDINGS = ("\u064b", "\u064b\u0627")


#: سجلُّ القرارِ — يُقرأ بالتشغيل.
RULE_LOG: list[dict] = []


#: المحلّلُ الصرفيُّ الموجود — يُحقن، ولا يُنشأ هنا. `None` ⟶ لا برهان ⟶ تأجيل.
MORPH = None


_MCACHE: dict = {}


def morph(tok: str):
    """قراءةٌ واحدةٌ لكلِّ لفظٍ من المحلّلِ الموجود. `None` ⟶ لا برهان."""
    if MORPH is None:
        return None
    if tok in _MCACHE:
        return _MCACHE[tok]
    try:
        c = MORPH(tok)
        v = {"root": getattr(getattr(c, "root_analysis", None), "resolved_root", None),
             "number": getattr(c.morphological_identity, "number", None),
             "gender": getattr(c.morphological_identity, "gender", None),
             "word_class": getattr(getattr(c, "word_class", None), "value", None),
             "base_pattern": getattr(c.morphological_identity, "base_pattern", None),
             "definiteness": getattr(c.morphological_identity, "definiteness", None),
             "is_numeral": bool(getattr(c.numeral_identity, "is_numeral", False)),
             "numeric_value": getattr(c.numeral_identity, "numeric_value", None)}
        v["root"] = str(v["root"]) if v["root"] else None
    except Exception:
        v = None
    _MCACHE[tok] = v
    return v


def is_accusative(tok: str) -> bool:
    """منصوبٌ بعلامةٍ ظاهرةٍ على الألف — تُقرأ من سطحِ النصِّ نفسِه."""
    return tok.endswith(ACCUSATIVE_ENDINGS)


def quantity_previous(tok: str) -> tuple[bool, str]:
    """`QUANTITY_PREVIOUS` — **باللاحقةِ لا يُبرهَن**. ثلاثةُ طرقٍ لا رابعَ لها:
    رقمٌ صريح · عددٌ لفظيٌّ يُثبته المحلّل · مثنًّى يُثبته المحلّل.
    وما لم يثبت ⟶ `DEFER`."""
    if any(ch.isdigit() for ch in tok):
        return True, "EXPLICIT_DIGIT"
    m = morph(tok)
    if m is None:
        return False, "NO_MORPHOLOGY_AVAILABLE"
    if m["is_numeral"]:
        return True, "MORPH_NUMERAL(value=%s)" % m["numeric_value"]
    if m["number"] == "مثنى":
        return True, "MORPH_DUAL"
    return False, "NOT_A_PROVEN_QUANTITY(number=%s)" % m["number"]


def x_or_more(parts: list[str]) -> tuple[bool, str]:
    """`RULE_2_BLOCK_X_OR_MORE_FROM_SPLITTING` — `FAIL_CLOSED`.

    **السبب:** «س أو أكثر» تركيبٌ كمّيٌّ واحد، لا حدّان.
    **الشرط:** ثلاثةٌ **مجتمعةٌ**، لا يُغني واحدٌ منها عن صاحبَيه:
      `RIGHT_BRANCH_IS_MORE` · `IMMEDIATE_QUANTITY_HOST` ·
      `MORPH_OR_EXPLICIT_NUMBER_PROOF`.
    **المانع:** يمينٌ يقوم حدًّا مستقلًّا، أو حدٌّ كمّيٌّ لم يثبت ⟶
      `DEFER:QUANTITY_HOST_NOT_PROVEN`، ولا منع.
    """
    if len(parts) != 2:
        return False, "NOT_TWO_PARTS"
    right = parts[-1].split()
    if len(right) != 1 or bare(right[0]) not in {bare(x) for x in QUANTITY_TAIL}:
        return False, "RIGHT_IS_AN_INDEPENDENT_ALTERNATIVE"
    left = parts[0].split()
    if not left:
        return False, "DEFER:QUANTITY_HOST_NOT_PROVEN(EMPTY_LEFT)"
    ok, why = quantity_previous(left[-1])
    if not ok:
        return False, "DEFER:QUANTITY_HOST_NOT_PROVEN(%s)" % why
    return True, ("QUANTITY_PREVIOUS:RIGHT_BRANCH_IS_MORE+"
                  "IMMEDIATE_QUANTITY_HOST+" + why)


def head_is_free_of_the_first_alternative(head: list[str]) -> tuple[bool, str]:
    """`G_S1` — حارسٌ **بنيويٌّ**: الرأسُ المحمولُ لا يحمل منصوبًا.

    وهو حارسُ بنيةٍ لا دلالة: اجتيازُه لا يُثبت صحّةَ الناتج.
    """
    bad = [t for t in head if is_accusative(t)]
    if bad:
        return False, "HEAD_CARRIES_AN_ACCUSATIVE(%s)" % " ".join(bad)
    return True, "CLEAN"


def accusative_slots(toks: list[str], start: int) -> list[list[str]]:
    """خاناتُ المنصوبِ المتّصلةُ ابتداءً من `start`.

    والمعطوفُ بالواوِ يمتدُّ به سابقُه ولا يفتحُ خانةً جديدة.
    """
    slots: list[list[str]] = []
    for t in toks[start:]:
        if not is_accusative(t):
            break
        if slots and t.startswith("\u0648"):
            slots[-1].append(t)
        else:
            slots.append([t])
    return slots


def parallelism_type(left: list[str], right: list[str]) -> tuple[str, str]:
    """`PARALLELISM_CONTRACT` — نوعُ التوازي بين الفرعَين، أو التأجيل.

    النصبُ وحدَه ليس حدًّا للرأس. فقبلَ أيِّ حملٍ يجب أن يُعرف **أيُّ
    توازٍ** بين الفرعَين، وذلك لا يُعرف إلّا بفئةِ كلِّ خانةٍ منصوبة:

      `NOUN_VS_NOUN`        · اسمٌ مقابل اسم ⟶ يُحمل العاملُ وحدَه.
      `ADJ_VS_ADJ_SAME_NOUN`· صفةٌ مقابل صفةٍ لاسمٍ واحد ⟶ يُحمل الاسم.
      `OBJECT_VS_OBJECT`    · مفعولٌ اسميٌّ مقابل مثلِه ⟶ يُحمل الفعلُ ومقدّمتُه.
      `PARALLELISM_NOT_PROVEN` · فئتان مختلفتان أو تحليلٌ غيرُ موثوق.

    لا يثبتُ نوعُ الخانةِ من علامةِ النصبِ أو عددِ الخاناتِ وحدَهما — إذ
    قد يتطابق تعريفان في العلامةِ وفي عددِ الخانات، ويختلفُ حكمُهما لأنّ
    الخانةَ في أحدِهما اسمٌ وفي الآخرِ صفة. ويحتاجُ الإثباتُ إلى مصدرٍ
    صرفيٍّ أو نحويٍّ موثوقٍ **بإذنِ المالك**. والمسارُ الحاليُّ لا يملكُ
    إلّا `base_pattern`، وغيابُه يوجبُ `DEFER` — ولا يحصرُ العقدَ
    المستقبليَّ في الوزن.
    """
    if not right or not is_accusative(right[0]):
        return "NO_CUE", "RIGHT_DOES_NOT_OPEN_WITH_AN_ACCUSATIVE"
    acc = [i for i, t in enumerate(left) if is_accusative(t)]
    if not acc:
        return "NO_CUE", "NO_ACCUSATIVE_IN_THE_LEFT_BRANCH"
    if acc[0] == 0:
        return "PARALLELISM_NOT_PROVEN", "NO_GOVERNOR_BEFORE_THE_FIRST_ACCUSATIVE"
    lslots = accusative_slots(left, acc[0])
    rslots = accusative_slots(right, 0)
    if not lslots or not rslots:
        return "PARALLELISM_NOT_PROVEN", "EMPTY_SLOT_RUN"
    unknown = [t for slot in lslots + rslots for t in slot
               if (morph(t) or {}).get("base_pattern") is None]
    if unknown:
        return "PARALLELISM_NOT_PROVEN", ("WAZN_UNAVAILABLE_FOR(%s)"
                                          % " ".join(unknown[:3]))
    return "PARALLELISM_NOT_PROVEN", "TYPE_RESOLUTION_NOT_AUTHORISED"


def head_adjust(toks: list[list[str]], head: list[str]) -> tuple[list[str], str, str]:
    """`RULE_1_FIX_HEAD_RECOVERY` — قرينتان، وكلتاهما `FAIL_CLOSED`.

    `A_GOVERNING_VERB`: **لا يُطبَّق إلّا بعدَ إثباتِ نوعِ التوازي**
      (`parallelism_type`). والنصبُ وحدَه لا يكفي، وأوّلُ منصوبٍ ليس حدًّا
      عامًّا: فقد يكون أوّلُ المنصوبِ اسمًا مشتركًا يُحمل، وقد يكون أوّلَ
      حمولةِ الفرعِ الأوّلِ فلا يُحمل — والعلامةُ وحدَها لا تفرّق.
    `N_NUMBER_CONFLICT`: ببرهانِ المحلّلِ الصرفيِّ الموجود لا غير، وبشروطِ
      `E`: ليسا فعلَين · lemma واحدة · لا يختلفان إلّا في العدد ·
      وتبعيّةُ النعتِ للمنعوتِ في الجنسِ والتعريف.

    **الموانع** — وكلُّها ⟶ `DEFER`، ولا يتغيّر الناتجُ السابق:
      · نوعُ التوازي غيرُ مثبت.
      · حدٌّ تركيبيٌّ أقصرُ ممّا أثبته الطول.
      · رأسٌ يحمل منصوبًا (`G_S1`).
      · اجتماعُ القرينتَين.
    """
    if len(toks) != 2:
        return head, "", "NO_CUE_ARITY_NOT_TWO"
    left, right = toks[0], toks[1]
    cand_a = cand_n = None
    note_a = note_n = ""
    ptype, pwhy = parallelism_type(left, right)
    if ptype == "PARALLELISM_NOT_PROVEN":
        note_a = "DEFER:PARALLELISM_NOT_PROVEN(%s)" % pwhy
    elif ptype != "NO_CUE":
        acc = [i for i, t in enumerate(left) if is_accusative(t)]
        cut = acc[0] + (1 if ptype == "ADJ_VS_ADJ_SAME_NOUN" else 0)
        cand = left[:cut]
        if len(cand) < len(head):
            note_a = ("DEFER:HEAD_BOUNDARY_UNPROVEN"
                      "(SYNTAX_SHORTER_THAN_LENGTH:%d<%d)" % (len(cand), len(head)))
        else:
            ok_g, why_g = head_is_free_of_the_first_alternative(cand)
            if ok_g:
                cand_a = cand
            else:
                note_a = "DEFER:HEAD_BOUNDARY_UNPROVEN(%s)" % why_g
    if head and left and right:
        L, R, H = left[-1], right[0], head[-1]
        mL, mR, mH = morph(L), morph(R), morph(H)
        if None in (mL, mR, mH):
            note_n = "NO_MORPHOLOGY_AVAILABLE"
        elif mL["word_class"] == "\u0641\u0639\u0644" and mR["word_class"] == "\u0641\u0639\u0644":
            note_n = "DEFER:BOTH_SIDES_ARE_VERBS"
        elif not (mL["root"] and mR["root"] and mL["root"] == mR["root"]):
            note_n = "NOT_ONE_LEMMA(%s|%s)" % (mL["root"], mR["root"])
        elif mL["number"] == mR["number"]:
            note_n = "SAME_NUMBER(%s)" % mL["number"]
        elif not (mL["gender"] == mR["gender"]
                  and mL["definiteness"] == mR["definiteness"]):
            note_n = ("DEFER:THEY_DIFFER_IN_MORE_THAN_NUMBER(L=%s/%s R=%s/%s)"
                      % (mL["gender"], mL["definiteness"],
                         mR["gender"], mR["definiteness"]))
        elif not (mH["number"] == mL["number"] and mH["number"] != mR["number"]):
            note_n = "CARRIED_NOUN_IS_NOT_THE_CONFLICT(H=%s L=%s R=%s)" % (
                mH["number"], mL["number"], mR["number"])
        elif not (mH["gender"] == mL["gender"]
                  and mH["definiteness"] == mL["definiteness"]):
            note_n = ("DEFER:HEAD_BOUNDARY_UNPROVEN(NOT_AN_ATTRIBUTIVE_PAIR:"
                      "H=%s/%s L=%s/%s)" % (mH["gender"], mH["definiteness"],
                                            mL["gender"], mL["definiteness"]))
        elif len(head) > 1:
            cand = head[:-1]
            ok_g, why_g = head_is_free_of_the_first_alternative(cand)
            if ok_g:
                cand_n = cand
                note_n = "PROVEN(lemma=%s %s\u2260%s)" % (mL["root"], mL["number"], mR["number"])
            else:
                note_n = "DEFER:HEAD_BOUNDARY_UNPROVEN(%s)" % why_g
        else:
            note_n = "HEAD_WOULD_BE_EMPTY"
    if cand_a is not None and cand_n is not None:
        return head, "", "DEFER_AMBIGUOUS_SHARED_MATERIAL"
    if cand_a is not None and cand_a != head:
        return cand_a, "RULE_1_FIX_HEAD_RECOVERY", "A_GOVERNING_VERB:" + ptype
    if cand_n is not None and cand_n != head:
        return cand_n, "RULE_1_FIX_HEAD_RECOVERY", "N_NUMBER_CONFLICT:" + note_n
    tail = "/".join(x for x in (note_a, note_n) if x)
    return head, "", ("NO_CUE" if not tail else "NO_CUE/" + tail)


def pattern_of(parts: list[str], rules_enabled: bool = True) -> tuple[str, str]:
    """النمطُ — **مقيسٌ من الطول ومن الرأسِ الأوّل، لا مخمَّن**.

    ورأسٌ مشتركٌ في اليسار يُعرف بشرطَين معًا: أن يكون اليسارُ أطولَ،
    **وأن تختلف أوّلُ كلمةٍ فيهما**. فـ«ابن ابنة أخيك أو ابن أخيك»
    يمينُه أقصرُ وهو تامٌّ — أوّلُه «ابن» كأوّلِ اليسار — فلا حذفَ فيه.
    """
    if len(parts) < 2:
        return "UNRESOLVED_ELLIPSIS", "NO_TWO_PARTS"
    blocked, why = x_or_more(parts) if rules_enabled else (False, "RULES_DISABLED")
    if blocked:
        RULE_LOG.append({"rule_id": "RULE_2_BLOCK_X_OR_MORE_FROM_SPLITTING",
                         "action": why, "changed": True})
        return "UNRESOLVED_ELLIPSIS", "X_OR_MORE_BLOCK"
    if why.startswith("DEFER:"):
        RULE_LOG.append({"rule_id": "RULE_2_BLOCK_X_OR_MORE_FROM_SPLITTING",
                         "action": why, "changed": False})
    toks = [p.split() for p in parts]
    if any(not t for t in toks):
        return "UNRESOLVED_ELLIPSIS", "EMPTY_PART"
    first = {t[0] for t in toks}
    if len(first) == 1:
        return "NO_ELLIPSIS", ""
    n = [len(t) for t in toks]
    if n[0] > max(n[1:]):
        return "HEAD_SHARED_LEFT", ""
    if n[-1] > max(n[:-1]):
        return "HEAD_SHARED_RIGHT", ""
    if len(set(n)) == 1:
        return "NO_ELLIPSIS", ""
    return "UNRESOLVED_ELLIPSIS", "MIDDLE_IS_LONGEST"


def complete(parts: list[str], pat: str, rules_enabled: bool = True) -> list[dict]:
    """يُكمَّل الطرفُ **برأسٍ منقولٍ حرفًا** — ولا صياغةَ جديدة."""
    toks = [p.split() for p in parts]
    out = []
    if pat == "HEAD_SHARED_LEFT":
        by_length = toks[0][:len(toks[0]) - max(len(t) for t in toks[1:])]
        head, rule, action = (head_adjust(toks, by_length) if rules_enabled
                              else (by_length, "", "RULES_DISABLED"))
        RULE_LOG.append({"rule_id": rule or "—", "action": action,
                         "head_by_length": " ".join(by_length),
                         "head_after": " ".join(head),
                         "changed": head != by_length})
        for i, p in enumerate(parts):
            out.append({"raw": p, "head_carried": "" if i == 0 else
                        " ".join(head),
                        "text": p if i == 0 else
                        (" ".join(head) + " " + p).strip()})
    elif pat == "HEAD_SHARED_RIGHT":
        tail = toks[-1][max(len(t) for t in toks[:-1]):]
        for i, p in enumerate(parts):
            last = i == len(parts) - 1
            out.append({"raw": p, "head_carried": "" if last else
                        " ".join(tail),
                        "text": p if last else
                        (p + " " + " ".join(tail)).strip()})
    else:
        for p in parts:
            out.append({"raw": p, "head_carried": "", "text": p})
    return out


# ═════════ بوّابةُ الأهليّة — في الوحدةِ نفسِها لا في مستوردٍ خارجيّ ═════════
#: التصنيفُ الوحيدُ الذي تُطبَّق عليه القاعدتان. **جردٌ مغلقٌ من عنصرٍ واحد.**
ELIGIBLE_CLASSIFICATION = "DISJUNCTION_OF_CONCEPTS"


def eligible(classification: str) -> tuple[bool, str]:
    """`FAIL_CLOSED` — ما لم يثبت التصنيفُ فلا قاعدةَ ولا تغيير."""
    if classification == ELIGIBLE_CLASSIFICATION:
        return True, "ELIGIBLE"
    return False, "DEFER:" + (classification or "NO_CLASSIFICATION")


def _run(gloss: str, rules_enabled: bool) -> dict:
    segs = segments(gloss)
    if not segs:
        return {"split": False, "reason": "NO_SEGMENT", "part_1": None,
                "part_2": None, "head": None}
    if segs[0]["parenthetical"]:
        return {"split": False, "reason": "PARENTHETICAL_ASIDE", "part_1": None,
                "part_2": None, "head": None}
    raw = split_segment(segs[0]["text"])
    pat, why = pattern_of(raw, rules_enabled)
    if pat == "UNRESOLVED_ELLIPSIS":
        return {"split": False, "reason": why, "part_1": None,
                "part_2": None, "head": None}
    parts = complete(raw, pat, rules_enabled)
    return {"split": True, "reason": pat, "part_1": parts[0]["text"],
            "part_2": parts[1]["text"], "head": parts[1]["head_carried"]}


def decide(gloss: str, classification: str) -> dict:
    """القرارُ الكامل — والأهليّةُ تُفحص هنا، لا خارجَ الوحدة.

    غيرُ المؤهَّلِ يُرجَع بناتجِه **قبلَ الإصلاح** حرفًا، فـ`CHANGE = False`
    ليست دعوى بل مقابلةٌ محسوبة.
    """
    ok, why = eligible(classification)
    before = _run(gloss, rules_enabled=False)
    if not ok:
        return {"RULE_APPLIED": False, "CHANGE": False, "DEFER": why,
                "eligibility": why, **before}
    after = _run(gloss, rules_enabled=True)
    changed = (after.get("part_2") != before.get("part_2")
               or after.get("head") != before.get("head")
               or after.get("split") != before.get("split"))
    return {"RULE_APPLIED": True, "CHANGE": changed, "DEFER": "",
            "eligibility": "ELIGIBLE", **after}
