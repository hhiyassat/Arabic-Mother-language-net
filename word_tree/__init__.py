"""
word_tree — Arabic Mother Language Net
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الطبقات:
  LAYER 0–4  Wave11Ancestry         مجمَّد
  LAYER 5    IfadahKernel            مجمَّد — 18/18
  LAYER 6    IrabJudgmentKernel      مجمَّد — 13/13
"""

# ── LAYER 0–4 ─────────────────────────────────────────────────────────────────
from word_tree.wave11_ancestry import Wave11Ancestry, wave11_build  # noqa: F401

# ── LAYER 5 ───────────────────────────────────────────────────────────────────
from word_tree.ifadah_types import (   # noqa: F401
    Layer6Handoff,
    IfadahResult,
    FilledSlot,
    SentenceType,
    IsnadType,
)
from word_tree.ifadah_kernel import (  # noqa: F401
    ifadah_build,
    ifadah_from_words,
    activate_slots,
)

# ── LAYER 6 ───────────────────────────────────────────────────────────────────
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

__all__ = [
    # LAYER 0–4
    "Wave11Ancestry", "wave11_build",
    # LAYER 5
    "Layer6Handoff", "IfadahResult", "FilledSlot",
    "SentenceType", "IsnadType",
    "ifadah_build", "ifadah_from_words", "activate_slots",
    # LAYER 6
    "IrabRole", "IrabCase", "IrabSign",
    "IrabEntry", "IrabJudgmentResult",
    "LAYER5_FROZEN_TOKEN", "LAYER6_VERDICT_TOKEN",
    "irab_judge", "irab_judge_from_ifadah",
]
