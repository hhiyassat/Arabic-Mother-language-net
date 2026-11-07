#!/usr/bin/env python3
"""WordNet roots on the HFN bank key (owner 2026-11-07: «يجب ان يصلح الاخطاء وتوحيد الاشكال والمدخلات مثل «شك» والبنك «شكك». وغيرها»).

wordnet_synsets.json `roots` came from word_tree/engines/noun_root_corrector (Ibn Faris display keys): geminates in two letters (شك),
weak roots with alif (قام), hamza on its seat (يأس), and extraction errors (حصان→حص، التهاب→هوب، إعادة→أود). Every synset root is
rewritten on the key of HusseinFrameNet/02_roots/HFN_ROOTS_v7.csv (K) by the first rule that applies, in this order:

  1. READ2      the (root, root_source_word) pair was read by two blind readers (audit/wordnet_rootkey/WN_ROOT_REVIEW_DECISIONS.tsv,
                3,257 pairs: every pair whose root is not a bank key, and every pair where HFN v45 gives the same word another root).
                Both agreed → their K; both said LOAN/PROPER (no root) → the root is dropped and root_status says so; they disagreed
                → the old root is kept and root_status = PENDING_OWNER_ROOT.  (WN_XCHK_A: the second reader followed option_2 without
                lexicon checks in 696 rows, so a third reader saw no options; the decision is reader 1 × reader 3.)
  2. LEX_ATTEST the word is attested in the text of bank-linked lexicon entries (nine lexicons) and one root wins in ≥2 lexicons
                (route_lex.py). Applied ONLY where it differs from the old root: measured on the 2,323 read pairs, where it differs
                from WordNet it is right 1,042/1,200 = 0.868, Wilson 0.848 ≥ 0.78. Where it agrees with WordNet the root is kept (step 3).
  3. FORMAT     the old root is the same root written another way: hamza seat (يأس→يءس), Ibn Faris maqayis entry linked in the bank
                (chain maqayis.db entry → M02 record → bank K), geminate in two letters (شك→شكك).
  4. otherwise  the old root is kept unchanged and root_status = UNVERIFIED_KEY (not a bank key, not read).
Each changed synset keeps `roots_prev_rootkey` (the old list) and gets `root_key_basis` (one basis per root).
The previous file is copied to data/wordnet/_pre_rootkey_20261107/ (gitignored, like the earlier _pre_ backups); a per-synset log is
written to data/wordnet/ROOTKEY_CHANGES_20261107.tsv. Everything CANDIDATE.
Usage: python3 audit/wordnet_rootkey/apply_rootkey.py   (refuses to run twice)"""
import csv, hashlib, json, os, re, shutil, sqlite3, sys, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
AMLN = os.path.dirname(os.path.dirname(HERE))
NET = os.environ.get('ARABIC_NET_HOME', os.path.dirname(AMLN))
HFN = os.path.join(NET, 'HusseinFrameNet')
WN = os.path.join(AMLN, 'data', 'wordnet')
SYN, BAK = os.path.join(WN, 'wordnet_synsets.json'), os.path.join(WN, '_pre_rootkey_20261107')
LOG = os.path.join(WN, 'ROOTKEY_CHANGES_20261107.tsv')
BANK = os.path.join(HFN, '02_roots', 'HFN_ROOTS_v7.csv')
sys.path.insert(0, HERE)
if os.path.exists(BAK): sys.exit(BAK + ' exists — already applied')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
HAR = re.compile(r'[ً-ِْٰـ]')
def seat(s): return re.sub('[أإآؤئ]', 'ء', HAR.sub('', s.replace('ٱ', 'ا'))).strip()

bank = list(csv.DictReader(open(BANK, encoding='utf-8'))); BK = {b['K'] for b in bank}
# chain: maqayis.db entry -> M02 record (bank ref_maqayis / ref_ayn / extra_refs) -> K
refs = {r['ref_id']: r for r in csv.DictReader(open(os.path.join(HFN, '02_roots', 'HFN_REFERENCES.csv'), encoding='utf-8'))}
rec2K = collections.defaultdict(set)
for b in bank:
    for c in ('ref_maqayis', 'ref_ayn'):
        if b[c].startswith('M02#'): rec2K[b[c][4:]].add(b['K'])
    for x in b['extra_refs'].split('·'):
        m = re.match(r'ref_(maqayis|ayn)=M02#(.+)', x)
        if m: rec2K[m.group(2)].add(b['K'])
m02 = os.path.expanduser(refs['M02']['path'])
if sha(m02) != refs['M02']['sha256']: sys.exit('M02 changed: ' + m02)
ent2K = collections.defaultdict(set)
for l in open(m02, encoding='utf-8'):
    r = json.loads(l)
    for ev in r['sources'].get('ibn_faris', {}).get('evidence', []):
        if r['record_id'] in rec2K: ent2K[ev['source_entry_id']] |= rec2K[r['record_id']]
db = sqlite3.connect(os.path.join(AMLN, 'word_tree', 'maqayis.db'))
disp2K = collections.defaultdict(set)
for eid, disp in db.execute('select id, root_display from entries where is_lexical_entry=1'):
    if ent2K.get(eid): disp2K[disp] |= ent2K[eid]

def fmt(r):
    s = seat(r)
    if s in BK: return s, ('EXACT' if s == r else 'FORMAT_HAMZA')
    via = disp2K.get(r)
    if via and len(via) == 1: return next(iter(via)), 'FORMAT_MAQAYIS_CHAIN'
    if len(s) == 2 and s + s[1] in BK: return s + s[1], 'FORMAT_GEMINATE'
    return None, None

dec = {}
for d in csv.DictReader(open(os.path.join(HERE, 'WN_ROOT_REVIEW_DECISIONS.tsv'), encoding='utf-8'), delimiter='\t'):
    dec[(d['wn_root'], d['word'])] = d

import lexindex  # noqa: builds lexidx.pkl next to this file when missing (see route_lex)
from route_lex import route

src_sha = sha(SYN)
S = json.load(open(SYN, encoding='utf-8'))
C = collections.Counter(); log = []
for s in S['synsets']:
    old = s.get('roots') or []
    if not old: continue
    w = s.get('root_source_word') or ''
    new, basis, status = [], [], []
    for r in old:
        d = dec.get((r, w))
        if d:
            if d['decision'] == 'DISAGREE':
                new.append(r); basis.append('READ2_DISAGREE'); status.append('PENDING_OWNER_ROOT')
            elif d['K']:
                new.append(d['K']); basis.append('READ2' + ('_LOAN_FILED' if d['verdict'] in ('LOAN', 'ROOT_LOAN') else ''))
            else:
                basis.append('READ2_NO_ROOT_' + d['verdict']); status.append('NO_ROOT_' + d['verdict'])
            continue
        K, how = fmt(r)
        rk, _ = route(w) if w else (None, None)
        if rk and rk != K:
            new.append(rk); basis.append('LEX_ATTEST'); continue
        if K:
            new.append(K); basis.append(how); continue
        new.append(r); basis.append('UNVERIFIED_KEY'); status.append('UNVERIFIED_KEY')
    new = list(dict.fromkeys(new))
    for b_ in basis: C[b_] += 1
    if new != old or any(x not in ('EXACT',) for x in basis):
        s['roots_prev_rootkey'] = old
        s['root_key_basis'] = basis
        if status: s['root_status_rootkey'] = sorted(set(status))
        s['roots'] = new
        if new != old:
            C['synsets_changed'] += 1
            log.append((s['id'], w, '|'.join(old), '|'.join(new), '|'.join(basis)))
S['_meta'].setdefault('revisions', []).append({
    'date': '2026-11-07', 'id': 'ROOTKEY_v1_HFN_BANK_K', 'what': 'synset roots rewritten on the HFN bank key (HFN_ROOTS_v7 K): READ2 > LEX_ATTEST (only where it differs; Wilson 0.848) > FORMAT; others kept and flagged',
    'counts': dict(C), 'bank': 'HusseinFrameNet/02_roots/HFN_ROOTS_v7.csv', 'bank_sha256': sha(BANK),
    'log': 'data/wordnet/ROOTKEY_CHANGES_20261107.tsv', 'backup': 'data/wordnet/_pre_rootkey_20261107/ (local, gitignored)',
    'source_sha256': src_sha, 'script': 'audit/wordnet_rootkey/apply_rootkey.py', 'status': 'CANDIDATE',
    'owner_instruction': '2026-11-07 «يجب ان يصلح الاخطاء وتوحيد الاشكال والمدخلات مثل «شك» والبنك «شكك». وغيرها»'})
os.makedirs(BAK); shutil.copy2(SYN, BAK)
if sha(os.path.join(BAK, 'wordnet_synsets.json')) != src_sha: sys.exit('backup mismatch')
with open(SYN, 'w', encoding='utf-8') as f: json.dump(S, f, ensure_ascii=False)
with open(LOG, 'w', encoding='utf-8', newline='') as f:
    w_ = csv.writer(f, delimiter='\t'); w_.writerow(['synset', 'root_source_word', 'roots_before', 'roots_after', 'basis']); w_.writerows(log)
print(dict(C))
