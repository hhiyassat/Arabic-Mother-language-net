"""مزوّد wazn-net: المطاوعة (الحقل ٢) والتعدية (الحقل ٣) — المسالك المقبولة وحدها، كما يعرضها المحرّكان."""
from __future__ import annotations

import os
from functools import lru_cache

from ._common import MEASURED, REPOS, feature, match_kind, on_path, wasl

PROVIDER = "wazn"


@lru_cache(maxsize=1)
def _engines():
    with on_path(REPOS["wazn"]):
        from engines import mutawaa_engine as M, taadiya_engine as T
    return M, T


def _call(fn, v):
    try:
        return fn(v) or []
    except Exception as e:  # NoSamaa / RouteNotAccepted: لم يُسمع أو غير مقبول — لا يُخمَّن
        if type(e).__name__ in ("NoSamaa", "RouteNotAccepted"):
            return []
        raise


def features(verb: str) -> list[dict]:
    M, T = _engines()
    out = []
    verb = wasl(verb)   # HFN v44 يكتب همزة الوصل ٱ؛ جداول wazn-net بالألف (HFN-D068)
    src = os.path.basename(M.TABLE)
    for x in _call(M.mutawaa_of, verb):
        out.append(feature("mutawaa", x.mutawaa, provider=PROVIDER, status=MEASURED, source=src,
                           route=x.route, match=match_kind(x.base, verb), matched=x.base, found_trans="متعدي", evidence=x.evidence[:300],
                           athar=x.athar, mutawaa_form=x.mutawaa_form, n_lex=x.n_lex))
    for x in _call(M.base_of, verb):
        if not x.base:   # BASE_UNRESOLVED: الوسيط «مطاوع X» ولم يُحلَّ X إلى فعل — لا قيمة تُعرض (فحص الجذور، الدفعة 3: 21 صفّاً)
            continue
        out.append(feature("mutawaa_base", x.base, provider=PROVIDER, status=MEASURED, source=src,
                           route=x.route, match=match_kind(x.mutawaa, verb), matched=x.mutawaa, found_trans="لازم", evidence=x.evidence[:300],
                           base_form=x.base_form, athar=x.athar))
    for x in _call(T.taadiya_of, verb):
        out.append(feature("taadiya", x.mutaaddi, provider=PROVIDER, status=MEASURED, source="ahdath taadiya",
                           route=x.route, measure=x.measure, match=match_kind(x.lazim, verb), matched=x.lazim, found_trans="لازم",
                           form=x.form, sifa=x.sifa, maful=x.maful))
    return out
