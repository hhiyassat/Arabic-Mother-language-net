# -*- coding: utf-8 -*-
"""شواهدُ القاعدتَين وحراسُهما — وعقدُ التوازي.

الحراسُ هنا **بنيويّة**. واجتيازُها لا يُثبت صحّةً دلاليّة:

    `STRUCTURAL_PASS_IS_NOT_SEMANTIC_PROOF`
    `A_GUARD_THAT_CANNOT_FALL_IS_NOT_A_GUARD`

`APPLIED_TO_THE_CORPUS = False` · `PROJECT_FINISHED = NO`
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "word_tree" / "wordnet_split_rules.py"
ELIGIBLE = "DISJUNCTION_OF_CONCEPTS"


def _fresh():
    spec = importlib.util.spec_from_file_location("_wsr_%d" % len(sys.modules),
                                                  MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _analyzer():
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        from word_tree.word_identity_analyzer import analyze_word
        analyze_word("شخص")
        return analyze_word
    finally:
        os.chdir(cwd)


try:
    ANALYZE = _analyzer()
except Exception:                     # pragma: no cover
    ANALYZE = None

needs_morph = pytest.mark.skipif(ANALYZE is None, reason="MORPHOLOGY_UNAVAILABLE")


def M():
    m = _fresh()
    m.MORPH = ANALYZE
    return m


# التعريفاتُ أدناه **قائمةٌ في المصدر**، والمعرّفاتُ هنا وحدَها لا في الإنتاج.
# (gloss, expected_part_2 أو None, forbidden أو None, required_defer أو None)
W = {
 "successor.n.03": ("شخص يرث لقباً أو منصباً ما",
                    "شخص يرث منصباً ما", None, None),
 "kin.n.01": ("شخص لديه قرابة مع شخص آخر أو آخرين",
              "شخص لديه قرابة مع آخرين", None, None),
 "suavity.n.01": ("جودة كون المرء لطيفاً ودمثاً أو متودداً في الأسلوب",
                  "جودة كون المرء متودداً في الأسلوب",
                  "جودة كون المرء لطيفاً متودداً في الأسلوب", None),
 "catastrophic.s.01": ("يُسَبِّب دَمارًا شامِلًا أو خَرابًا بالِغًا",
                       None, "يُسَبِّب دَمارًا خَرابًا بالِغًا", None),
 "open.s.07": ("لا يملك غطاءً واقياً أو سياجاً محيطاً",
               None, "لا يملك غطاءً سياجاً محيطاً", None),
 "abject.s.03": ("يُظهِر استسلاماً تامّاً أو فقداناً للأمل",
                 None, "يُظهِر استسلاماً فقداناً للأمل", None),
 "scotch.v.02": ("صنع قطعاً صغيراً أو خدشاً في",
                 None, "صنع قطعاً خدشاً في", None),
 "scorch.n.02": ("مرض نباتي ينتج مظهراً بنياً أو محروقاً لأنسجة النبات",
                 "مرض نباتي ينتج مظهراً محروقاً لأنسجة النبات",
                 "مرض نباتي ينتج محروقاً لأنسجة النبات", None),
 "disk_drive.n.01": ("جهاز حاسوب يحمل ويدير قرصاً مغناطيسياً أو ضوئياً "
                     "ويقرأ ويكتب المعلومات عليه",
                     "جهاز حاسوب يحمل ويدير قرصاً ضوئياً ويقرأ ويكتب المعلومات عليه",
                     "جهاز حاسوب يحمل ويدير ضوئياً ويقرأ ويكتب المعلومات عليه",
                     None),
 "official.n.01": ("عامل يشغل منصباً أو مكلفاً بمكتب",
                   None, "عامل يشغل مكلفاً بمكتب", "PARALLELISM_NOT_PROVEN"),
 "magazine.n.01": ("مطبوع دوري يحتوي على صور وقصص ومقالات تهم من يشترونها "
                   "أو يشتركون فيها",
                   None, "مطبوع دوري يحتوي على صور وقصص ومقالات يشتركون فيها",
                   "HEAD_BOUNDARY_UNPROVEN"),
 "attraction.n.03": ("صفة إثارة الاهتمام؛ كون الشيء جذاباً أو شيئاً يجذب",
                     None, None, "PARALLELISM_NOT_PROVEN"),
}
G_POLYANDRIST = "امرأة لديها زوجان أو أكثر"
G_POLYGYNIST = "رجل لديه زوجتان أو أكثر"
G_INCREASE = "جعل الشيء أكبر أو أكثر"
G_GIVENNESS = "صفة كون الشيء ممنوحاً كافتراض؛ أو كونه معترفاً به أو مفترضاً"

#: النواتجُ المحظورةُ — **جردٌ مغلقٌ من حكمِ المالك**.
KNOWN_FORBIDDEN_OUTPUTS = tuple(v[2] for v in W.values() if v[2])

#: ما لم يُنتَج بعدُ من `expected_part_2` — لعدمِ ثبوتِ نوعِ التوازي.
NOT_YET_PRODUCIBLE = ("successor.n.03", "suavity.n.01",
                      "scorch.n.02", "disk_drive.n.01")


# ═════════════ ١ · لا ناتجَ محظورٌ البتّة — وهو الشرطُ الأصلب ═════════════

@needs_morph
@pytest.mark.parametrize("sid", sorted(W))
def test_no_forbidden_output_is_produced(sid):
    gloss, _, forbidden, _ = W[sid]
    if forbidden is None:
        pytest.skip("NO_FORBIDDEN_OUTPUT_DECLARED")
    assert M().decide(gloss, ELIGIBLE)["part_2"] != forbidden


@needs_morph
def test_the_forbidden_set_never_appears_across_all_witnesses():
    produced = {M().decide(g, ELIGIBLE)["part_2"] for g, _, _, _ in W.values()}
    assert produced & set(KNOWN_FORBIDDEN_OUTPUTS) == set()


# ═════════════ ٢ · الشواهدُ المنتَجة، وما لم يُنتَج بعد ═════════════

@needs_morph
@pytest.mark.parametrize("sid", [s for s in sorted(W)
                                 if W[s][1] and s not in NOT_YET_PRODUCIBLE])
def test_expected_output_is_produced(sid):
    gloss, expected, _, _ = W[sid]
    assert M().decide(gloss, ELIGIBLE)["part_2"] == expected


@needs_morph
@pytest.mark.parametrize("sid", sorted(NOT_YET_PRODUCIBLE))
@pytest.mark.xfail(strict=True,
                   reason="PARALLELISM_NOT_PROVEN — نوعُ التوازي غيرُ مثبتٍ "
                          "بالمصدرِ الصرفيِّ/النحويِّ المتاح؛ النتيجةُ المطلوبةُ "
                          "لم تُنتَج، ولا يُعتمد ناتجُ ما قبلَ الإصلاحِ بوصفِه صحيحًا")
def test_expected_output_not_yet_producible(sid):
    gloss, expected, _, _ = W[sid]
    assert M().decide(gloss, ELIGIBLE)["part_2"] == expected


@needs_morph
@pytest.mark.parametrize("sid", sorted(NOT_YET_PRODUCIBLE))
def test_what_is_not_producible_is_left_untouched(sid):
    """ما لم يثبت توازيه لا يتغيّر — لا يُخمَّن."""
    gloss = W[sid][0]
    m = M()
    d = m.decide(gloss, ELIGIBLE)
    assert d["CHANGE"] is False
    assert d["part_2"] == m._run(gloss, rules_enabled=False)["part_2"]


@needs_morph
@pytest.mark.parametrize("sid", [s for s in sorted(W) if W[s][3]])
def test_required_defer(sid):
    gloss, _, _, kind = W[sid]
    m = M()
    d = m.decide(gloss, ELIGIBLE)
    assert d["CHANGE"] is False
    assert d["part_2"] == m._run(gloss, rules_enabled=False)["part_2"]


# ═════════════ ٣ · عقدُ التوازي ═════════════

@needs_morph
def test_parallelism_is_never_proven_while_the_wazn_is_absent():
    """`FAIL_CLOSED` — لا نوعَ توازٍ بلا وزن، فلا حملَ ولا تخمين."""
    m = M()
    t, why = m.parallelism_type(["يُسَبِّب", "دَمارًا", "شامِلًا"],
                                ["خَرابًا", "بالِغًا"])
    assert t == "PARALLELISM_NOT_PROVEN"
    assert why.startswith("WAZN_UNAVAILABLE_FOR")


def test_the_parallelism_guard_can_fall():
    """لو أسعف المحلّلُ بالوزنِ لتجاوزت البوّابةُ مرحلةَ الوزن."""
    m = _fresh()
    m.MORPH = lambda tok: None
    m._MCACHE.clear()
    m.morph = lambda tok: {"base_pattern": "فَعَل", "root": "x", "number": "مفرد",
                           "gender": "مذكر", "definiteness": "نكرة",
                           "word_class": "اسم", "is_numeral": False,
                           "numeric_value": None}
    t, why = m.parallelism_type(["يُسَبِّب", "دَمارًا"], ["خَرابًا"])
    assert why == "TYPE_RESOLUTION_NOT_AUTHORISED"


def test_a_right_branch_that_opens_without_an_accusative_is_no_cue():
    m = _fresh()
    assert m.parallelism_type(["الأب"], ["الأم"])[0] == "NO_CUE"


def test_coordinated_accusatives_share_one_slot():
    """المعطوفُ بالواوِ يمتدُّ به سابقُه ولا يفتحُ خانةً جديدة."""
    m = _fresh()
    slots = m.accusative_slots(["كون", "المرء", "لطيفاً", "ودمثاً"], 2)
    assert [len(s) for s in slots] == [2]
    slots = m.accusative_slots(["ينتج", "مظهراً", "بنياً"], 1)
    assert [len(s) for s in slots] == [1, 1]


@needs_morph
def test_no_head_recovery_fires_on_a_governing_verb_cue():
    """`A_GOVERNING_VERB` معطَّلةٌ فعليًّا ما دام التوازي غيرَ مثبت."""
    m = M()
    for gloss, _, _, _ in W.values():
        for e in ():
            pass
        m.RULE_LOG.clear()
        m.decide(gloss, ELIGIBLE)
        fired = [e for e in m.RULE_LOG
                 if e.get("action", "").startswith("A_GOVERNING_VERB")]
        assert fired == []


# ═════════════ ٤ · تقييدُ `N_NUMBER_CONFLICT` ═════════════

@needs_morph
def test_two_verbs_are_never_a_number_conflict():
    """`E` — «يشترونها» و«يشتركون» فعلان، و lemma=شتر ليس برهانًا."""
    m = M()
    m.RULE_LOG.clear()
    m.decide(W["magazine.n.01"][0], ELIGIBLE)
    assert any("BOTH_SIDES_ARE_VERBS" in e.get("action", "") for e in m.RULE_LOG)


@needs_morph
def test_they_must_differ_in_number_only():
    m = M()
    out, rule, action = m.head_adjust(
        [["عكر", "بسبب", "الرواسب"], ["الترسّبات"]], ["عكر", "بسبب"])
    assert out == ["عكر", "بسبب"] and rule == ""
    assert "DIFFER_IN_MORE_THAN_NUMBER" in action or "NOT_AN_ATTRIBUTIVE_PAIR" in action


@needs_morph
def test_kin_is_still_carried_correctly():
    d = M().decide(W["kin.n.01"][0], ELIGIBLE)
    assert d["part_2"] == "شخص لديه قرابة مع آخرين"
    assert d["head"] == "شخص لديه قرابة مع"


@needs_morph
def test_the_carried_head_never_holds_an_accusative():
    m = M()
    for gloss, _, _, _ in W.values():
        head = (m.decide(gloss, ELIGIBLE)["head"] or "").split()
        ok, why = m.head_is_free_of_the_first_alternative(head)
        assert ok, why


def test_the_guard_G_S1_can_fall():
    m = _fresh()
    ok, why = m.head_is_free_of_the_first_alternative(["يُسَبِّب", "دَمارًا"])
    assert ok is False and "HEAD_CARRIES_AN_ACCUSATIVE" in why


@needs_morph
def test_every_word_of_part_2_comes_from_the_gloss():
    m = M()
    for gloss, _, _, _ in W.values():
        d = m.decide(gloss, ELIGIBLE)
        base = m.flatten(gloss).split()
        assert all(w in base for w in (d["part_2"] or "").split())


# ═════════════ ٥ · بوّابةُ الأهليّة في الوحدةِ نفسِها ═════════════

@needs_morph
def test_an_unresolved_disjunction_is_never_touched():
    m = M()
    before = m._run(G_GIVENNESS, rules_enabled=False)
    d = m.decide(G_GIVENNESS, "DISJUNCTION_UNRESOLVED")
    assert d["RULE_APPLIED"] is False and d["CHANGE"] is False
    assert d["DEFER"] == "DEFER:DISJUNCTION_UNRESOLVED"
    assert d["part_2"] == before["part_2"] and d["head"] == before["head"]


@needs_morph
def test_givenness_does_not_change_even_when_eligible():
    m = M()
    before = m._run(G_GIVENNESS, rules_enabled=False)
    after = m._run(G_GIVENNESS, rules_enabled=True)
    assert after["part_2"] == before["part_2"]


@needs_morph
def test_the_gate_protects_a_row_the_rule_would_change():
    m = M()
    gloss = W["kin.n.01"][0]
    protected = m.decide(gloss, "DISJUNCTION_UNRESOLVED")
    applied = m.decide(gloss, ELIGIBLE)
    assert protected["CHANGE"] is False and applied["CHANGE"] is True
    assert protected["part_2"] != applied["part_2"]


# ═════════════ ٦ · قاعدةُ الكمّيّة — منفصلةٌ ولم تُوسَّع ═════════════

@needs_morph
@pytest.mark.parametrize("gloss", [G_POLYANDRIST, G_POLYGYNIST])
def test_a_quantity_construction_is_not_split(gloss):
    d = M().decide(gloss, ELIGIBLE)
    assert d["split"] is False and d["reason"] == "X_OR_MORE_BLOCK"


@needs_morph
def test_increase_remains_splittable():
    m = M()
    assert m.decide(G_INCREASE, ELIGIBLE)["split"] is True
    blocked, why = m.x_or_more(["جعل الشيء أكبر", "أكثر"])
    assert blocked is False and why.startswith("DEFER:QUANTITY_HOST_NOT_PROVEN")


@needs_morph
def test_the_three_conditions_must_meet():
    m = M()
    blocked, why = m.x_or_more(["امرأة لديها زوجان", "أكثر"])
    assert blocked is True
    for name in ("RIGHT_BRANCH_IS_MORE", "IMMEDIATE_QUANTITY_HOST", "MORPH_DUAL"):
        assert name in why
    assert m.x_or_more(["الأب", "الأم"])[1] == "RIGHT_IS_AN_INDEPENDENT_ALTERNATIVE"


def test_fail_closed_without_morphology():
    m = _fresh()
    m.MORPH = None
    assert m.quantity_previous("زوجان") == (False, "NO_MORPHOLOGY_AVAILABLE")
    assert m.decide(G_POLYANDRIST, ELIGIBLE)["split"] is True
    assert m.decide(W["kin.n.01"][0], ELIGIBLE)["head"] == "شخص لديه قرابة مع شخص"


# ═════════════ ٧ · ما هو محظورٌ في مسارِ الإنتاج ═════════════

FORBIDDEN_IN_PRODUCTION = (
    "B_REPEATED_TOKEN", "REPEATED_TOKEN", "REPEATED_WORD",
    "kin.n.01", "successor.n.03", "polyandrist", "polygynist",
    "catastrophic", "open.s.07", "suavity", "abject", "scotch", "givenness",
    "scorch", "disk_drive", "official.n.01", "magazine", "attraction",
)


def test_no_forbidden_identifier_in_production():
    src = MODULE_PATH.read_text(encoding="utf-8")
    assert [i for i in FORBIDDEN_IN_PRODUCTION if i in src] == []


def test_no_witness_lemma_in_production():
    src = MODULE_PATH.read_text(encoding="utf-8")
    lemmas = ("قرابة", "يرث", "زوجان", "زوجتان", "سياجاً", "متودداً",
              "فقداناً", "خدشاً", "محروقاً", "ضوئياً", "مكلفاً", "يشتركون")
    assert [w for w in lemmas if w in src] == []


def _code_string_literals(path: Path) -> set:
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)) and body:
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                docs.add(id(first.value))
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs}


#: كلُّ نصٍّ عربيٍّ يقرؤه الكود — **جردٌ مغلق**، ولا يزيد إلّا بحكمِ المالك.
ARABIC_LITERALS_ALLOWED = {
    " أم ", " أو ",
    "؛;،,:()·—",
    "أكثر",
    "ً", "ًا",
    "ًٌٍَُِّْٰٕٓٔ",
    "مثنى",
    "و",
    "فعل",
}

NUMBER_SUFFIXES = ("ان", "ين", "تان", "تين", "ون", "ات")


def test_the_module_reads_no_number_suffix_and_its_arabic_is_a_closed_list():
    lits = _code_string_literals(MODULE_PATH)
    arabic = {s for s in lits if any("؀" <= ch <= "ۿ" for ch in s)}
    assert arabic == ARABIC_LITERALS_ALLOWED
    assert [s for s in arabic if s in NUMBER_SUFFIXES] == []


def test_production_imports_nothing_but_the_standard_library():
    import ast
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    names = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            names.append(n.module or "")
    assert sorted(set(names)) == ["__future__", "unicodedata"]


def test_production_touches_no_file_and_no_corpus():
    src = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("open(", "Path(", "read_text", "write_text", "json.",
                  "sqlite3", "requests", "urllib"):
        assert token not in src


# ═════════════ ٨ · السموم ═════════════

@needs_morph
@pytest.mark.parametrize("sid,cut", [("catastrophic.s.01", "last"),
                                     ("open.s.07", "last"),
                                     ("scorch.n.02", "first"),
                                     ("official.n.01", "first")])
def test_poison_an_unproven_boundary_produces_a_forbidden_output(sid, cut):
    """`P1` — حدٌّ بلا إثباتِ توازٍ يُنتج المحظورَ بعينِه، أوّلًا كان أم آخرًا."""
    m = M()

    def poisoned(toks, head):
        left, right = toks[0], toks[1]
        if right and m.is_accusative(right[0]):
            acc = [i for i, t in enumerate(left) if m.is_accusative(t)]
            if acc:
                k = acc[-1] if cut == "last" else acc[0]
                if k > 0:
                    return left[:k], "RULE_1_FIX_HEAD_RECOVERY", "POISONED"
        return head, "", "NO_CUE"

    m.head_adjust = poisoned
    assert m.decide(W[sid][0], ELIGIBLE)["part_2"] == W[sid][2]


@needs_morph
def test_poison_removing_the_length_lower_bound_changes_givenness():
    """`P2` — الطولُ حدٌّ أدنى؛ برفعِه يتغيّر ما يجب ألّا يتغيّر."""
    m = M()
    clean = m.decide(G_GIVENNESS, ELIGIBLE)

    def no_lower_bound(toks, head):
        left, right = toks[0], toks[1]
        if right and m.is_accusative(right[0]):
            acc = [i for i, t in enumerate(left) if m.is_accusative(t)]
            if acc and acc[0] > 0:
                return left[:acc[0]], "RULE_1_FIX_HEAD_RECOVERY", "POISONED"
        return head, "", "NO_CUE"

    m.head_adjust = no_lower_bound
    assert m.decide(G_GIVENNESS, ELIGIBLE)["part_2"] != clean["part_2"]


@needs_morph
def test_poison_allowing_two_verbs_breaks_magazine():
    """`P3` — لو قُبل الفعلان لتغيّر `magazine` إلى ناتجِه المحظور."""
    m = M()
    real = m.morph
    m.morph = lambda tok: ({**(real(tok) or {}), "word_class": "اسم"}
                           if real(tok) else None)
    assert m.decide(W["magazine.n.01"][0], ELIGIBLE)["part_2"] == W["magazine.n.01"][2]


@needs_morph
@pytest.mark.parametrize("gloss", [G_POLYANDRIST, G_POLYGYNIST])
def test_poison_disabling_the_block_splits_a_quantity(gloss):
    m = M()
    m.x_or_more = lambda parts: (False, "POISONED")
    assert m.decide(gloss, ELIGIBLE)["split"] is True


@needs_morph
def test_poison_accepting_any_previous_as_a_quantity_over_blocks_increase():
    m = M()
    m.quantity_previous = lambda tok: (True, "POISONED")
    assert m.decide(G_INCREASE, ELIGIBLE)["split"] is False


@needs_morph
def test_poison_a_repeated_word_cue_would_change_kin():
    m = M()
    original = m.head_adjust

    def repeated_cue(toks, head):
        if head and toks[0] and head[-1] in toks[0][:-1]:
            return head[:-1], "RULE_1_FIX_HEAD_RECOVERY", "B_REPEATED_TOKEN"
        return original(toks, head)

    m.head_adjust = repeated_cue
    assert m.decide(W["kin.n.01"][0], ELIGIBLE)["head"] == "شخص لديه قرابة مع"
    assert "B_REPEATED_TOKEN" not in MODULE_PATH.read_text(encoding="utf-8")
