"""تناغم جذور WordNet مع بنك HFN (ROOTKEY v1، 2026-11-07).

كلّ جذر في wordnet_synsets.json مفتاحٌ في HFN_ROOTS_v7، إلا:
  - ما اختلف فيه القارئان (root_status_rootkey = PENDING_OWNER_ROOT)، ينتظر حكم المالك؛
  - ما اتّفق القارئان أنّ جذره غير موجود في البنك بعد (NOT_IN_BANK في قراءتيهما) — ينتظر إضافته بحكم المالك.
ولا يضيع شيء: كلّ مجموعةٍ تغيّرت جذورها تحفظ roots_prev_rootkey وأساس كلّ جذر، وسجلّ التغيير يطابق الملفّ.
"""
import csv
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.environ.get("ARABIC_NET_HOME", os.path.dirname(ROOT))
BANK = os.path.join(NET, "HusseinFrameNet", "02_roots", "HFN_ROOTS_v7.csv")
SYN = os.path.join(ROOT, "data", "wordnet", "wordnet_synsets.json")
LOG = os.path.join(ROOT, "data", "wordnet", "ROOTKEY_CHANGES_20261107.tsv")
DEC = os.path.join(ROOT, "audit", "wordnet_rootkey", "WN_ROOT_REVIEW_DECISIONS.tsv")

pytestmark = pytest.mark.skipif(not os.path.exists(BANK), reason="HusseinFrameNet HFN_ROOTS_v7 غير موجود")


@pytest.fixture(scope="module")
def data():
    bk = {b["K"] for b in csv.DictReader(open(BANK, encoding="utf-8"))}
    syn = json.load(open(SYN, encoding="utf-8"))["synsets"]
    agreed_new = {d["K"] for d in csv.DictReader(open(DEC, encoding="utf-8"), delimiter="\t")
                  if d["decision"] != "DISAGREE" and d["K"] and d["K"] not in bk}
    return bk, syn, agreed_new


def test_every_root_is_a_bank_key(data):
    bk, syn, agreed_new = data
    bad = [(s["id"], r) for s in syn for r in s.get("roots") or []
           if r not in bk and r not in agreed_new and "PENDING_OWNER_ROOT" not in s.get("root_status_rootkey", [])]
    assert not bad, bad[:20]


def test_reader_fixes(data):
    _, syn, _ = data
    S = {s["id"]: s for s in syn}
    # حصان ← حصن (كان «حص»)؛ مكافح ← كفح (كان «مكا»)؛ شك ← شكك
    assert any(s.get("root_source_word") == "حصان" and s["roots"] == ["حصن"] for s in syn)
    assert S["agonist.n.02"]["roots"] == ["كفح"]
    assert all(r != "شك" for s in syn for r in s.get("roots") or [])


def test_nothing_lost(data):
    _, syn, _ = data
    changed = {s["id"]: s for s in syn if "roots_prev_rootkey" in s}
    for s in changed.values():
        assert len(s["root_key_basis"]) == len(s["roots_prev_rootkey"]), s["id"]
    log = list(csv.DictReader(open(LOG, encoding="utf-8"), delimiter="\t"))
    for r in log:
        s = changed[r["synset"]]
        assert r["roots_before"] == "|".join(s["roots_prev_rootkey"]) and r["roots_after"] == "|".join(s["roots"])
    # الجذر لا يُسقط إلا بحكم القارئين أنّ الكلمة معرّبة أو علم أو أداة
    for s in changed.values():
        if not s["roots"]:
            assert all(b.startswith("READ2_NO_ROOT_") for b in s["root_key_basis"]), s["id"]
