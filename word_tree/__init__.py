"""
word_tree — Arabic Mother Language Net
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الطبقات:
  LAYER 0–4  Wave11Ancestry         مجمَّد
  LAYER 5    IfadahKernel            مجمَّد — 18/18
  LAYER 6    IrabJudgmentKernel      مجمَّد — 13/13

ملاحظة معمارية — LAZY IMPORT BOUNDARY:
  LAYER 0–4 (Wave11Ancestry) و LAYER 5 kernel (IfadahKernel) يحتاجان:
    • maqayis_v2  — حزمة بيانات خارجية (غير مُدرجة في هذا الـrepo)
    • word_tree/engines/ — بنية تحتية مُجمَّدة

  وحدات Word Identity (word_identity_types, fi3l_engine, word_class_engine,
  numeral_engine, sifa_engine, word_identity_analyzer, engines/noun_root_corrector)
  لا تحتاج هذه الطبقات. لذا يُستورَد LAYER 0–4 و ifadah_kernel بشكل كسول
  (lazy) عبر دالة _load_frozen_layers() بدلاً من أن يُنفَّذ عند استيراد الحزمة.

  المستوردون الخارجيون الذين يحتاجون Wave11Ancestry يستخدمون:
    from word_tree.wave11_ancestry import Wave11Ancestry, wave11_build
    from word_tree.ifadah_kernel import ifadah_build, ifadah_from_words, activate_slots
  مباشرةً بدلاً من `from word_tree import ...`.
"""

# ── LAYER 5 — TYPES ONLY (stdlib-clean, no external deps) ─────────────────────
from word_tree.ifadah_types import (   # noqa: F401
    Layer6Handoff,
    IfadahResult,
    FilledSlot,
    SentenceType,
    IsnadType,
)

# ── LAYER 6 — TYPES + KERNEL (no wave11 dependency) ───────────────────────────
from word_tree.irab_types import (     # noqa: F401
    IrabRole,
    IrabCase,
    IrabSign,
    IrabEntry,
    IrabJudgmentResult,
    LAYER5_FROZEN_TOKEN,
    LAYER6_VERDICT_TOKEN,
)
from word_tree.irab_judgment_kernel import (  # noqa: F401
    irab_judge,
    irab_judge_from_ifadah,
)

# ── LAYER 0–4 + LAYER 5 KERNEL — lazy, declared separately ────────────────────
# Wave11Ancestry و ifadah_kernel يُستورَدان فقط عند الطلب الصريح.
# LAZY_FROZEN_LAYER_BOUNDARY = True
# استخدم: from word_tree.wave11_ancestry import Wave11Ancestry, wave11_build
#          from word_tree.ifadah_kernel import ifadah_build, ifadah_from_words, activate_slots


def _load_frozen_layers():
    """
    استورد LAYER 0–4 و LAYER 5 kernel كسولاً.
    يتطلب: maqayis_v2 + word_tree/engines/ في PYTHONPATH.
    لا تُستدعَى إلا من كود يحتاج Wave11Ancestry أو ifadah_build فعلاً.
    """
    from word_tree.wave11_ancestry import Wave11Ancestry, wave11_build       # noqa: F401
    from word_tree.ifadah_kernel import (                                    # noqa: F401
        ifadah_build, ifadah_from_words, activate_slots,
    )
    return {
        "Wave11Ancestry": Wave11Ancestry,
        "wave11_build":   wave11_build,
        "ifadah_build":   ifadah_build,
        "ifadah_from_words": ifadah_from_words,
        "activate_slots": activate_slots,
    }


__all__ = [
    # LAYER 0–4 (lazy — استورد مباشرة من word_tree.wave11_ancestry)
    # "Wave11Ancestry", "wave11_build",
    # LAYER 5 — types
    "Layer6Handoff", "IfadahResult", "FilledSlot",
    "SentenceType", "IsnadType",
    # LAYER 5 — kernel (lazy — استورد مباشرة من word_tree.ifadah_kernel)
    # "ifadah_build", "ifadah_from_words", "activate_slots",
    # LAYER 6
    "IrabRole", "IrabCase", "IrabSign",
    "IrabEntry", "IrabJudgmentResult",
    "LAYER5_FROZEN_TOKEN", "LAYER6_VERDICT_TOKEN",
    "irab_judge", "irab_judge_from_ifadah",
    # lazy loader
    "_load_frozen_layers",
]
