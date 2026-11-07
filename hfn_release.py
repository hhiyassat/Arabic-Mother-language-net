"""أيّ إصدار من HusseinFrameNet تقرؤه طبقات AMLN (المالك 2026-11-08: «نقل الطبقات التي تقرأ HFN v36 إلى v45»).

مكانٌ واحد بدل تثبيت الإصدار في كلّ ملف: أحدث release_vN فيه MANIFEST.json، إلا أن يُثبَّت بمتغيّر البيئة AMLN_HFN_RELEASE
(مثلاً release_v36 لإعادة قياسٍ قديم كما هو). مكتبة قياسية فقط."""
import os
import re


def hfn_release_dir() -> str:
    base = os.path.join(os.path.expanduser(os.environ.get("ARABIC_NET_HOME", "~/arabic-net")), "HusseinFrameNet", "release")
    rel = os.environ.get("AMLN_HFN_RELEASE")
    if not rel:
        rels = [d for d in os.listdir(base) if re.fullmatch(r"release_v\d+", d) and os.path.exists(os.path.join(base, d, "MANIFEST.json"))]
        rel = max(rels, key=lambda d: int(d[9:]))
    return os.path.join(base, rel)
