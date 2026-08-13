"""
test_irab_judgment_kernel.py — LAYER 6 — IrabJudgmentKernel
13 اختبار: 6 حراس + 4 أمثلة + 3 ثوابت وحدة
"""
from __future__ import annotations

import sys
import os
import unittest

# الريبو root هو مستوى واحد فوق tests/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from ifadah_types import Layer6Handoff, SentenceType, IsnadType
from irab_types import (
    IrabRole, IrabCase, IrabSign,
    LAYER5_FROZEN_TOKEN, LAYER6_VERDICT_TOKEN,
)
from irab_judgment_kernel import irab_judge


def _make_handoff(
    root="كتب", synset_id="library.n.01",
    sentence_type=SentenceType.FI3LIYYA, isnad_type=IsnadType.HAQIQI,
    musnad="كَتَبَ", musnad_ilayh="الكاتبُ",
    qayd=("الرسالةَ",), raw_sentence="كَتَبَ الكاتبُ الرسالةَ",
    layer5_frozen=LAYER5_FROZEN_TOKEN,
) -> Layer6Handoff:
    return Layer6Handoff(root=root, synset_id=synset_id, sentence_type=sentence_type,
        isnad_type=isnad_type, musnad=musnad, musnad_ilayh=musnad_ilayh,
        qayd=qayd, raw_sentence=raw_sentence, layer5_frozen=layer5_frozen)


class TestGuards(unittest.TestCase):

    def test_T_L6_G00_wrong_layer5_frozen(self):
        h = _make_handoff(layer5_frozen="WRONG_TOKEN")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_00" in r for r in result.block_reasons))

    def test_T_L6_G01_empty_raw_sentence(self):
        h = _make_handoff(raw_sentence="")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_01" in r for r in result.block_reasons))

    def test_T_L6_G02_empty_musnad(self):
        h = _make_handoff(musnad="")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_02" in r for r in result.block_reasons))

    def test_T_L6_G03_empty_musnad_ilayh(self):
        h = _make_handoff(musnad_ilayh="")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_03" in r for r in result.block_reasons))

    def test_T_L6_G04_fi3liyya_no_faail(self):
        h = _make_handoff(sentence_type=SentenceType.FI3LIYYA, musnad_ilayh="")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_03" in r or "GUARD_L6_04" in r for r in result.block_reasons))

    def test_T_L6_G05_ismiyya_no_khabar(self):
        h = _make_handoff(sentence_type=SentenceType.ISMIYYA, musnad="",
            musnad_ilayh="المكتبُ", raw_sentence="المكتبُ")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "BLOCKED")
        self.assertTrue(any("GUARD_L6_02" in r or "GUARD_L6_05" in r for r in result.block_reasons))


class TestExamples(unittest.TestCase):

    def test_T_L6_E01_kataba_al_katib_al_risalah(self):
        h = _make_handoff()
        result = irab_judge(h)
        self.assertEqual(result.verdict, "IRAB_COMPLETE")
        roles = [e.irab_role for e in result.entries]
        self.assertIn(IrabRole.FI3L,    roles)
        self.assertIn(IrabRole.FAAIL,   roles)
        self.assertIn(IrabRole.MAF3OOL, roles)
        faail = next(e for e in result.entries if e.irab_role == IrabRole.FAAIL)
        self.assertEqual(faail.irab_case, IrabCase.MARFOO3)
        self.assertEqual(faail.irab_sign, IrabSign.DAMMA)
        maf3ool = next(e for e in result.entries if e.irab_role == IrabRole.MAF3OOL)
        self.assertEqual(maf3ool.irab_case, IrabCase.MANSOOB)
        self.assertEqual(maf3ool.irab_sign, IrabSign.FATHA)
        self.assertEqual(result.layer6_frozen, LAYER6_VERDICT_TOKEN)

    def test_T_L6_E02_alima_al_talib_al_haqeeqa(self):
        h = _make_handoff(root="علم", synset_id="knowledge.n.01",
            musnad="عَلِمَ", musnad_ilayh="الطالبُ", qayd=("الحقيقةَ",),
            raw_sentence="عَلِمَ الطالبُ الحقيقةَ")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "IRAB_COMPLETE")
        roles = [e.irab_role for e in result.entries]
        self.assertIn(IrabRole.FI3L,    roles)
        self.assertIn(IrabRole.FAAIL,   roles)
        self.assertIn(IrabRole.MAF3OOL, roles)

    def test_T_L6_E03_maktab_ismiyya(self):
        h = _make_handoff(sentence_type=SentenceType.ISMIYYA, isnad_type=IsnadType.HAQIQI,
            musnad="مكانُ كِتابةٍ", musnad_ilayh="مَكْتَب", qayd=(),
            raw_sentence="مَكْتَب مكانُ كِتابةٍ")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "IRAB_COMPLETE")
        roles = [e.irab_role for e in result.entries]
        self.assertIn(IrabRole.MUBTADA, roles)
        self.assertIn(IrabRole.KHABAR,  roles)
        mubtada = next(e for e in result.entries if e.irab_role == IrabRole.MUBTADA)
        self.assertEqual(mubtada.irab_case, IrabCase.MARFOO3)
        khabar = next(e for e in result.entries if e.irab_role == IrabRole.KHABAR)
        self.assertEqual(khabar.irab_case, IrabCase.MARFOO3)

    def test_T_L6_E04_kataba_with_jar_majroor(self):
        h = _make_handoff(qayd=("الرسالةَ", "في المكتب"),
            raw_sentence="كَتَبَ الكاتبُ الرسالةَ في المكتب")
        result = irab_judge(h)
        self.assertEqual(result.verdict, "IRAB_COMPLETE")
        roles = [e.irab_role for e in result.entries]
        self.assertIn(IrabRole.QAYD_JAR, roles)
        jar = next(e for e in result.entries if e.irab_role == IrabRole.QAYD_JAR)
        self.assertEqual(jar.irab_case, IrabCase.MAJROOR)
        self.assertEqual(jar.irab_sign, IrabSign.KASRA)


class TestModuleInvariants(unittest.TestCase):

    def test_layer6_frozen_token_is_set(self):
        self.assertTrue(LAYER6_VERDICT_TOKEN)
        self.assertIn("LAYER6", LAYER6_VERDICT_TOKEN)

    def test_layer5_frozen_token_matches_ifadah(self):
        h = _make_handoff()
        self.assertEqual(h.layer5_frozen, LAYER5_FROZEN_TOKEN)

    def test_irab_judgment_result_to_dict(self):
        import json
        h = _make_handoff()
        result = irab_judge(h)
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        serialized = json.dumps(d, ensure_ascii=False)
        self.assertIn("IRAB_COMPLETE", serialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
