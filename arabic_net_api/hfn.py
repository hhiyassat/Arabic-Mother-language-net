"""مزوّد HFN: الحدث، والمصادر، والتعدّي، ومعنى الصيغة، والمشتقّات من الإصدار المتحقَّق.

الإصدار: ARABIC_NET_HFN_RELEASE أو SARF_HFN إن وُجد، وإلا أحدث إصدارٍ يتحقّق بـ MANIFEST (عمل hfn_api نفسه).
"""
from __future__ import annotations

import csv
import os
from functools import lru_cache

from ._common import RELEASE, REPOS, feature, match_kind, nfc, on_path

PROVIDER = "hfn"
LU_FEATURE = {"مصدر": "masdar", "اسم فاعل": "ism_fail", "اسم مفعول": "ism_maful"}


def release_dir():
    return os.environ.get("ARABIC_NET_HFN_RELEASE") or os.environ.get("SARF_HFN") or None


@lru_cache(maxsize=1)
def api():
    with on_path(os.path.join(REPOS["hfn"], "api")):
        from hfn_api import HFN
    h = HFN(release_dir())
    import hfn_api
    h._newest = os.path.basename(hfn_api._release_candidates()[0]) if hfn_api._release_candidates() else ""
    return h


@lru_cache(maxsize=1)
def _form_meanings():
    p = os.path.join(api().dir, "form_meanings.csv")
    out = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            out.setdefault(r["event_id"], r)
    return out


def info() -> dict:
    h = api()
    newest = getattr(h, "_newest", "")
    return dict(release=h.release, dir=h.dir, manifest_sha256=h.manifest_sha256, refused_newer=h.refused_newer,
                pinned_by=("ARABIC_NET_HFN_RELEASE" if os.environ.get("ARABIC_NET_HFN_RELEASE") else
                           "SARF_HFN" if os.environ.get("SARF_HFN") else "NEWEST_VERIFIED"),
                newest_available=newest, behind_newest=bool(newest) and not h.dir.endswith(newest))


def events(verb: str, root: str = "", form: str = "") -> list[tuple[dict, str]]:
    """أحداث الفعل مع نوع المطابقة. يُطابق لمّة الفعل (#V) لا كلّ وحدةٍ معجمية."""
    h = api()
    env = h.lookup_word(verb)
    out = []
    for b in env["payload"]["events"]:
        e = h.events[b["event_id"]]
        if root and e["root_K"] != root and nfc(e["root_K"]) != nfc(root):
            continue
        if form and e["form"].split(" ")[0] != nfc(form):
            continue
        out.append((e, match_kind(e["verb"], verb)))
    return out


def features(verb: str, root: str = "", form: str = "") -> list[dict]:
    h, fm, out = api(), _form_meanings(), []
    src = h.release
    for e, m in events(verb, root, form):
        eid = e["event_id"]
        kw = dict(provider=PROVIDER, status=RELEASE, source=src, match=m, event_id=eid, verb=e["verb"], matched=e["verb"],
                  found_trans=e.get("transitivity", ""))
        out.append(feature("hfn_event", dict(event_id=eid, root=e["root_K"], form=e["form"], layer=e["layer"],
                                             tier=e.get("tier", ""), n_lex=e.get("n_lex", ""),
                                             licensing=e.get("licensing_status", ""), residual=e.get("residual", "")), **kw))
        out.append(feature("transitivity", e.get("transitivity", ""), evidence=e.get("transitivity_wasit_v37", ""), **kw))
        for lu in h.lus[eid]:
            name = LU_FEATURE.get(lu["pos_ar"])
            if name:
                out.append(feature(name, lu["lemma"], route=lu["lu_id"].split("#")[-1],
                                   evidence=f'{lu["basis"]} · {lu["status"]}', **kw))
        if e.get("masdar_wasit_v37"):
            out.append(feature("masdar_wasit_check", e["masdar_wasit_v37"], **kw))
        r = fm.get(eid)
        if r:
            out.append(feature("form_meaning", r["meaning"], route=r["method"], evidence=r["evidence"],
                               concept_id=r["concept_id"], **dict(kw, status=r["status"] or RELEASE)))
    return out


def root_events(root: str) -> list[dict]:
    env = api().lookup_root(root)
    return [feature("hfn_event", b, provider=PROVIDER, status=RELEASE, source=api().release, match="ROOT")
            for b in env["payload"]["events"]]
