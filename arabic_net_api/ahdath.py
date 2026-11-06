"""مزوّد AMLN: أثر الحدث (R1، R1W، T_JAL) وجهة الفاعل (J_SAJIYYA، J_DAA) — المقبول بالقياس وحده."""
from __future__ import annotations

from ._common import MEASURED, feature

PROVIDER = "ahdath"


def features(verb: str, synset: str | None = None) -> list[dict]:
    from word_tree import ahdath as WA
    out = []
    for x in WA.for_verb(verb, synset=synset, keep_rejected=True):  # الحكم بالتشكيل وأدلّته من vowel_evidence
        r = WA.ROUTES[x["route"]]
        out.append(feature("ahdath_effect", dict(fail=x["fail"], maful=x["maful"], mutawi=x["mutawi"],
                                                 athar=x["athar"], sifa=x["sifa"]),
                           provider=PROVIDER, status=MEASURED, source=x["src"], route=x["route"],
                           measure=f'p={r["p"]} wilson_low={r["wilson_low"]}', match=x["match"], matched=x["verb"], vowel_evidence=x["vowel_evidence"],
                           vowel_flags=x["vowel_flags"],
                           event_id=x["event_id"], verb=x["verb"], label_ar=x["label_ar"]))
    for x in WA.jiha(verb, synset=synset, keep_rejected=True):
        r = WA.JIHA_ROUTES[x["route"]]
        out.append(feature("fail_jiha", x["jiha"], provider=PROVIDER, status=MEASURED, source=x["src"],
                           route=x["route"], measure=f'p={r["p"]} wilson_low={r["wilson_low"]}',
                           match=x["match"], matched=x["verb"], vowel_evidence=x["vowel_evidence"],
                           vowel_flags=x["vowel_flags"], event_id=x["event_id"], verb=x["verb"],
                           musabbib_verb=x["musabbib_verb"], musabbib_route=x["musabbib_route"],
                           label_ar=x["label_ar"]))
    return out
