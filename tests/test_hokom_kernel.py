"""
test_hokom_kernel.py — LAYER 7 — HokomKernel
14 اختبار: 4 حراس + 4 أمثلة سليمة + 3 أمثلة مختلَّة + 3 ثوابت وحدة

السلامة تُقاس عبر السلسلة الكاملة LAYER 5 → 6 → 7 حيثما أمكن.
"""
from __future__ import annotations

import sys
import os
import unittest

# الريبو root هو مستوى واحد فوق tests/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from ifadah_types import Layer6Handoff, SentenceType, IsnadType
from irab_types import (
    IrabEntry, IrabRole, IrabCase, IrabSign,
    Layer7Handoff, LAYER6_FROZEN_TOKEN,
)
from irab_judgment_kernel import irab_judge
from hokom_types import HokomVerdict, LAYER7_VERDICT_TOKEN
from hokom_kernel import hokom_judge, hokom_judge_from_irab


# ── مساعدات ───────────────────────────────────────────────────────────────────

def _make_l6_handoff(
    root="كتب", synset_id="library.n.01",
    sentence_type=SentenceType.FI3LIYYA, isnad_type=IsnadType.HAQIQI,
    musnad="كَتَبَ", musnad_ilayh="الكاتبُ",
    qayd=("الرسالةَ",), raw_sentence="كَتَبَ الكاتبُ الرسالةَ",
) -> Layer6Handoff:
    return Layer6Handoff(root=root, synset_id=synset_id, sentence_type=sentence_type,
        isnad_type=isnad_type, musnad=musnad, musnad_ilayh=musnad_ilayh,
        qayd=qayd, raw_sentence=raw_sentence)


def _judge_chain(**kwargs):
    """LAYER 6 ثم LAYER 7 عبر to_layer7_handoff()."""
    irab = irab_judge(_make_l6_handoff(**kwargs))
    return hokom_judge(irab.to_layer7_handoff())


def _make_l7_handoff(
    root="كتب", synset_id="library.n.01",
    sentence="كَتَبَ الكاتبُ الرسالةَ", sentence_type=SentenceType.FI3LIYYA,
    entries=(), irab_verdict="IRAB_COMPLETE",
    layer6_frozen=LAYER6_FROZEN_TOKEN,
) -> Layer7Handoff:
    return Layer7Handoff(root=root, synset_id=synset_id, sentence=sentence,
        sentence_type=sentence_type, entries=tuple(entries),
        irab_verdict=irab_verdict, layer6_frozen=layer6_frozen)


def _entry(word, pos, role, case, sign, reason="سبب", muttasil=""):
    return IrabEntry(word=word, position=pos, irab_role=role, irab_case=case,
        irab_sign=sign, irab_reason=reason, muttasil=muttasil)


# ── الحراس ────────────────────────────────────────────────────────────────────

class TestGuards(unittest.TestCase):

    def test_T_L7_G00_wrong_layer6_frozen(self):
        entries = (_entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),)
        h = _make_l7_handoff(entries=entries, layer6_frozen="WRONG_TOKEN")
        result = hokom_judge(h)
        self.assertEqual(result.verdict, HokomVerdict.BLOCKED)
        self.assertTrue(any("GUARD_L7_00" in r for r in result.block_reasons))

    def test_T_L7_G01_empty_sentence(self):
        entries = (_entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),)
        h = _make_l7_handoff(sentence="", entries=entries)
        result = hokom_judge(h)
        self.assertEqual(result.verdict, HokomVerdict.BLOCKED)
        self.assertTrue(any("GUARD_L7_01" in r for r in result.block_reasons))

    def test_T_L7_G02_empty_entries(self):
        h = _make_l7_handoff(entries=())
        result = hokom_judge(h)
        self.assertEqual(result.verdict, HokomVerdict.BLOCKED)
        self.assertTrue(any("GUARD_L7_02" in r for r in result.block_reasons))

    def test_T_L7_G03_unknown_sentence_type(self):
        entries = (_entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),)
        h = _make_l7_handoff(entries=entries, sentence_type="مجهولة")
        result = hokom_judge(h)
        self.assertEqual(result.verdict, HokomVerdict.BLOCKED)
        self.assertTrue(any("GUARD_L7_03" in r for r in result.block_reasons))


# ── أمثلة سليمة (عبر السلسلة LAYER 6 → 7) ────────────────────────────────────

class TestSaleem(unittest.TestCase):

    def test_T_L7_S01_kataba_al_katib_al_risalah(self):
        result = _judge_chain()
        self.assertEqual(result.verdict, HokomVerdict.SALEEM)
        self.assertTrue(result.is_saleem)
        self.assertEqual(result.defects, [])
        self.assertEqual(result.layer7_frozen, LAYER7_VERDICT_TOKEN)
        self.assertTrue(all(c.passed for c in result.checks))

    def test_T_L7_S02_alima_al_talib_al_haqeeqa(self):
        result = _judge_chain(root="علم", synset_id="knowledge.n.01",
            musnad="عَلِمَ", musnad_ilayh="الطالبُ", qayd=("الحقيقةَ",),
            raw_sentence="عَلِمَ الطالبُ الحقيقةَ")
        self.assertEqual(result.verdict, HokomVerdict.SALEEM)
        self.assertEqual(result.defects, [])

    def test_T_L7_S03_maktab_ismiyya(self):
        result = _judge_chain(sentence_type=SentenceType.ISMIYYA,
            musnad="مكانُ كِتابةٍ", musnad_ilayh="مَكْتَب", qayd=(),
            raw_sentence="مَكْتَب مكانُ كِتابةٍ")
        self.assertEqual(result.verdict, HokomVerdict.SALEEM)
        self.assertEqual(result.defects, [])

    def test_T_L7_S04_kataba_with_jar_majroor(self):
        result = _judge_chain(qayd=("الرسالةَ", "في المكتب"),
            raw_sentence="كَتَبَ الكاتبُ الرسالةَ في المكتب")
        self.assertEqual(result.verdict, HokomVerdict.SALEEM)
        self.assertEqual(result.defects, [])


# ── أمثلة مختلَّة (اختلال واحد لكل قاعدة) ─────────────────────────────────────

class TestMukhtall(unittest.TestCase):

    def test_T_L7_M01_agreement_faail_not_marfoo3(self):
        # R2: الفاعل جاء منصوباً — اختلال مطابقة
        entries = (
            _entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),
            _entry("الكاتبَ", 1, IrabRole.FAAIL, IrabCase.MANSOOB, IrabSign.FATHA, muttasil="كَتَبَ"),
        )
        result = hokom_judge(_make_l7_handoff(entries=entries))
        self.assertEqual(result.verdict, HokomVerdict.MUKHTALL)
        self.assertTrue(result.is_mukhtall)
        self.assertTrue(any("AGREEMENT" == c.name and not c.passed for c in result.checks))
        self.assertTrue(result.defects)

    def test_T_L7_M02_isnad_fi3liyya_no_faail(self):
        # R1: جملة فعلية بلا فاعل — إسناد ناقص
        entries = (
            _entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),
            _entry("الرسالةَ", 1, IrabRole.MAF3OOL, IrabCase.MANSOOB, IrabSign.FATHA, muttasil="كَتَبَ"),
        )
        result = hokom_judge(_make_l7_handoff(entries=entries))
        self.assertEqual(result.verdict, HokomVerdict.MUKHTALL)
        self.assertTrue(any("ISNAD" == c.name and not c.passed for c in result.checks))

    def test_T_L7_M03_orphan_muttasil(self):
        # R3: تعلُّق يتيم — الفاعل يتعلق بفعل غير موجود
        entries = (
            _entry("كَتَبَ", 0, IrabRole.FI3L, IrabCase.MABNI, IrabSign.MABNI_FATH),
            _entry("الكاتبُ", 1, IrabRole.FAAIL, IrabCase.MARFOO3, IrabSign.DAMMA, muttasil="غائب"),
        )
        result = hokom_judge(_make_l7_handoff(entries=entries))
        self.assertEqual(result.verdict, HokomVerdict.MUKHTALL)
        self.assertTrue(any("MUTTASIL" == c.name and not c.passed for c in result.checks))


# ── ثوابت الوحدة ──────────────────────────────────────────────────────────────

class TestModuleInvariants(unittest.TestCase):

    def test_layer7_frozen_token_is_set(self):
        self.assertTrue(LAYER7_VERDICT_TOKEN)
        self.assertIn("LAYER7", LAYER7_VERDICT_TOKEN)

    def test_hokom_judge_from_irab_chain(self):
        irab = irab_judge(_make_l6_handoff())
        result = hokom_judge_from_irab(irab)
        self.assertIsNotNone(result)
        self.assertEqual(result.verdict, HokomVerdict.SALEEM)

    def test_hokom_result_to_dict(self):
        import json
        result = _judge_chain()
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        serialized = json.dumps(d, ensure_ascii=False)
        self.assertIn("HOKM_SALEEM", serialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
