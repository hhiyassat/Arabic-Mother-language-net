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
BANK = os.path.join(NET, "HusseinFrameNet", "02_roots", "HFN_ROOTS_v8.csv")
SYN = os.path.join(ROOT, "data", "wordnet", "wordnet_synsets.json")
LOG = os.path.join(ROOT, "data", "wordnet", "ROOTKEY_CHANGES_20261107.tsv")
DEC = os.path.join(ROOT, "audit", "wordnet_rootkey", "WN_ROOT_REVIEW_DECISIONS.tsv")
DEC2 = os.path.join(ROOT, "audit", "wordnet_rootkey", "census", "E_DECISIONS.tsv")
LOG2 = os.path.join(ROOT, "data", "wordnet", "ROOTKEY2_CHANGES_20261107.tsv")
VERIFIED = {"READ2", "READ2_LOAN_FILED", "LEX_ATTEST", "CENSUS2", "CENSUS2_LOAN_FILED", "CONFIRMED_HFN", "CONFIRMED_LEX",
            "ADJ2", "OWNER_DELEGATED", "RULE_R1", "RULE_R2", "RULE_MAP_v8"}
LOG3 = os.path.join(ROOT, "data", "wordnet", "ROOTKEY3_CHANGES_20261107.tsv")

pytestmark = pytest.mark.skipif(not os.path.exists(BANK), reason="HusseinFrameNet HFN_ROOTS_v8 غير موجود")


@pytest.fixture(scope="module")
def data():
    bk = {b["K"] for b in csv.DictReader(open(BANK, encoding="utf-8"))}
    syn = json.load(open(SYN, encoding="utf-8"))["synsets"]
    agreed_new = {d["K"] for p in (DEC, DEC2) for d in csv.DictReader(open(p, encoding="utf-8"), delimiter="\t")
                  if d["decision"] != "DISAGREE" and d["K"] and d["K"] not in bk}
    return bk, syn, agreed_new


def test_every_root_is_a_bank_key(data):
    """ROOTKEY v3: owner rulings done and bank v8 holds the new keys — every root is a bank key, nothing pending."""
    bk, syn, _ = data
    bad = [(s["id"], r) for s in syn for r in s.get("roots") or [] if r not in bk]
    assert not any("PENDING_OWNER_ROOT" in s.get("root_status_rootkey", []) for s in syn)
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
        if "root_key_basis" in s:   # v1 basis is aligned with the original roots
            assert len(s["root_key_basis"]) == len(s["roots_prev_rootkey"]), s["id"]
    log = list(csv.DictReader(open(LOG, encoding="utf-8"), delimiter="\t"))
    for r in log:
        s = changed[r["synset"]]
        assert r["roots_before"] == "|".join(s["roots_prev_rootkey"])
    for r in csv.DictReader(open(LOG2, encoding="utf-8"), delimiter="\t"):
        s = changed[r["synset"]]
        assert r["roots_before"] == "|".join(s["roots_prev_rootkey2"])
    for r in csv.DictReader(open(LOG3, encoding="utf-8"), delimiter="\t"):
        s = changed[r["synset"]]
        assert r["roots_before"] == "|".join(s["roots_prev_rootkey3"]) and r["roots_after"] == "|".join(s["roots"])
    # الجذر لا يُسقط إلا بحكم القارئين أنّ الكلمة معرّبة أو علم أو أداة
    for s in changed.values():
        if not s["roots"]:
            bs = s.get("root_key_basis", []) + s.get("root_key_basis2", []) + s.get("root_key_basis3", [])
            assert any("NO_ROOT_" in b for b in bs), s["id"]


def test_every_root_verified(data):
    """ROOTKEY v2: no root rests on its key alone — each has a reading, a measured route, or waits for the owner."""
    _, syn, _ = data
    bad = []
    for s in syn:
        if not s.get("roots"):
            continue
        bs = [b for b in (s.get("root_key_basis3") or s.get("root_key_basis2") or []) if "NO_ROOT_" not in b]
        assert bs, s["id"]
        bad += [(s["id"], b) for b in bs if b not in VERIFIED]
    assert not bad, bad[:20]
