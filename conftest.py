# -*- coding: utf-8 -*-
"""عزلُ قاعدةِ الاختبارات — **نسخةٌ مؤقّتةٌ خارجَ المستودع**.

`MAQAYIS_DB_PATH` يُضبط قبل استيرادِ وحدةِ التحليل، فتُحلّ المساراتُ عند
الاستيرادِ إلى النسخةِ المؤقّتة. والقاعدةُ الكنسيّةُ لا تُفتح من اختبار:
لا `-wal` ولا `-shm` بجوارها.

`TEST_DATABASE_ISOLATION` — ولا تُغيَّر بياناتٌ ولا مخطَّط.
"""
import os
import shutil
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent
_CANONICAL_DB = _REPO / "word_tree" / "maqayis.db"

if _CANONICAL_DB.is_file() and not os.environ.get("MAQAYIS_DB_PATH"):
    _tmp = Path(tempfile.mkdtemp(prefix="amln-testdb-"))
    _copy = _tmp / "maqayis.db"
    shutil.copy2(_CANONICAL_DB, _copy)
    os.environ["MAQAYIS_DB_PATH"] = str(_copy)
    os.environ.setdefault("AMLN_TEST_DB_DIR", str(_tmp))
