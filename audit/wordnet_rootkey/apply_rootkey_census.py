#!/usr/bin/env python3
"""ROOTKEY v2 — every WordNet root verified (owner 2026-11-07: «اصلاح»: the 71,047 roots that were bank keys but never checked).

After ROOTKEY v1 (apply_rootkey.py) every synset root whose basis is EXACT or FORMAT_* was only known to be a bank key. Each such
(root, root_source_word) pair — 31,409 pairs, 86,100 synset roots — was classified by independent evidence (census/exact_classify.py →
census/exact_pairs.tsv):
  HFN_AGREES   HFN release_v45 gives the same word the same root                     6,363 pairs
  LEX_AGREES   the word is attested in bank-linked lexicon text under the same root   5,297 pairs
  NO_EVIDENCE  neither                                                                19,148 pairs
Census: all 19,148 NO_EVIDENCE pairs, plus a random 400 of each *_AGREES class, were read by two blind readers who did NOT see the
root (census/E_??.tsv, E_??_X.tsv, E_??_Y.tsv; decisions census/E_DECISIONS.tsv, key census/E_KEY.tsv). Readers agreed on 19,474 of
19,948 (97.6%). On the random samples the readers confirmed the existing root in 374/397 (HFN_AGREES, Wilson 0.915) and 371/396
(LEX_AGREES, Wilson 0.908): both ≥ 0.78, so the unread pairs of these two classes are accepted as CONFIRMED routes.
Rules, per synset root (basis EXACT / FORMAT_*):
  read pair, readers agreed on a root  → that root (basis CENSUS2, or CENSUS2_LOAN_FILED when one said LOAN with the same root)
  read pair, readers agreed: no root   → root dropped; root_status_rootkey NO_ROOT_LOAN / NO_ROOT_PROPER / NO_ROOT_UNSURE
  read pair, readers disagreed         → root kept; PENDING_OWNER_ROOT
  unread HFN_AGREES / LEX_AGREES pair  → root kept; basis CONFIRMED_HFN / CONFIRMED_LEX
roots_prev_rootkey keeps the ORIGINAL (pre-v1) roots; roots_prev_rootkey2 the v1 roots. Log: data/wordnet/ROOTKEY2_CHANGES_20261107.tsv.
Backup: data/wordnet/_pre_rootkey2_20261107/ (gitignored). Everything CANDIDATE.
Usage: python3 audit/wordnet_rootkey/apply_rootkey_census.py   (refuses to run twice)"""
import csv, hashlib, json, os, shutil, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); C_ = os.path.join(HERE, 'census')
AMLN = os.path.dirname(os.path.dirname(HERE)); WN = os.path.join(AMLN, 'data', 'wordnet')
SYN, BAK, LOG = os.path.join(WN, 'wordnet_synsets.json'), os.path.join(WN, '_pre_rootkey2_20261107'), os.path.join(WN, 'ROOTKEY2_CHANGES_20261107.tsv')
if os.path.exists(BAK): sys.exit(BAK + ' exists — already applied')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def tsv(p): return list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
EV = {(r['root'], r['word']): r['evidence'] for r in tsv(os.path.join(C_, 'exact_pairs.tsv'))}
DEC = {(d['wn_root'], d['word']): d for d in csv.DictReader(open(os.path.join(C_, 'E_DECISIONS.tsv'), encoding='utf-8'), delimiter='\t')}
UNVERIFIED = ('EXACT', 'FORMAT_HAMZA', 'FORMAT_MAQAYIS_CHAIN', 'FORMAT_GEMINATE')
src_sha = sha(SYN); S = json.load(open(SYN, encoding='utf-8'))
C = collections.Counter(); log = []
for s in S['synsets']:
    roots = s.get('roots') or []
    if not roots: continue
    basis = s.get('root_key_basis') or ['EXACT'] * len(roots)
    w = s.get('root_source_word') or ''
    # v1 basis list is aligned with the ORIGINAL roots; rebuild the per-current-root basis
    if 'roots_prev_rootkey' in s:
        cur = []
        for b in basis:
            if b.startswith('READ2_NO_ROOT'): continue
            cur.append(b)
        if len(cur) != len(roots):   # duplicates collapsed in v1: fall back to recomputing per root
            cur = [basis[0]] * len(roots) if len(set(basis)) == 1 else cur[:len(roots)] + ['EXACT'] * (len(roots) - len(cur))
        basis_cur = cur
    else:
        basis_cur = basis
    new, nb, status, changed = [], [], set(s.get('root_status_rootkey', [])), False
    for r, b in zip(roots, basis_cur):
        if b not in UNVERIFIED:
            new.append(r); nb.append(b); continue
        d = DEC.get((r, w))
        if d:
            if d['decision'] == 'DISAGREE':
                new.append(r); nb.append('CENSUS2_DISAGREE'); status.add('PENDING_OWNER_ROOT'); C['disagree'] += 1
            elif d['K']:
                new.append(d['K']); nb.append('CENSUS2' + ('_LOAN_FILED' if d['verdict'] in ('LOAN', 'ROOT_LOAN') else ''))
                C['census_same' if d['K'] == r else 'census_changed'] += 1; changed |= d['K'] != r
            else:
                nb.append('CENSUS2_NO_ROOT_' + d['verdict']); status.add('NO_ROOT_' + d['verdict']); C['census_no_root_' + d['verdict']] += 1; changed = True
            continue
        ev = EV.get((r, w), '')
        if ev in ('HFN_AGREES', 'LEX_AGREES'):
            new.append(r); nb.append('CONFIRMED_' + ev.split('_')[0]); C['confirmed_' + ev] += 1
        else:
            new.append(r); nb.append('UNVERIFIED_KEY'); status.add('UNVERIFIED_KEY'); C['still_unverified'] += 1
    new = list(dict.fromkeys(new))
    if 'roots_prev_rootkey' not in s: s['roots_prev_rootkey'] = list(roots)
    if changed: s['roots_prev_rootkey2'] = list(roots); log.append((s['id'], w, '|'.join(roots), '|'.join(new), '|'.join(nb))); C['synsets_changed'] += 1
    s['roots'] = new; s['root_key_basis2'] = nb
    if status: s['root_status_rootkey'] = sorted(status)
S['_meta']['revisions'].append({
    'date': '2026-11-07', 'id': 'ROOTKEY_v2_CENSUS', 'what': 'every EXACT/FORMAT root verified: census of 19,148 unevidenced pairs by two blind readers (root hidden); HFN_AGREES and LEX_AGREES accepted as routes (Wilson 0.915 / 0.908 on random read samples of 400)',
    'counts': dict(C), 'log': 'data/wordnet/ROOTKEY2_CHANGES_20261107.tsv', 'backup': 'data/wordnet/_pre_rootkey2_20261107/ (local, gitignored)',
    'source_sha256': src_sha, 'script': 'audit/wordnet_rootkey/apply_rootkey_census.py', 'status': 'CANDIDATE', 'owner_instruction': '2026-11-07 «اصلاح» (the 71,047 unverified roots)'})
os.makedirs(BAK); shutil.copy2(SYN, BAK)
if sha(os.path.join(BAK, 'wordnet_synsets.json')) != src_sha: sys.exit('backup mismatch')
with open(SYN, 'w', encoding='utf-8') as f: json.dump(S, f, ensure_ascii=False)
with open(LOG, 'w', encoding='utf-8', newline='') as f:
    wr = csv.writer(f, delimiter='\t'); wr.writerow(['synset', 'root_source_word', 'roots_before', 'roots_after', 'basis2']); wr.writerows(log)
print(dict(C))
