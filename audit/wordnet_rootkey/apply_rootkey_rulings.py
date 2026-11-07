#!/usr/bin/env python3
"""ROOTKEY v3 — owner rulings applied (2026-11-07: «١ اجتهد بها ؛ ٢ اضفها ؛ ٣. اجتهد بها ؛ استعمل موقع الشاملة»).

1. The 563 pairs the readers disagreed on (v1: 89, v2 census: 474; root_status PENDING_OWNER_ROOT) were judged by two independent
   adjudicators on rulings/RULES.md (R1–R8, sources quoted from al-Shamela). Agreed 435; both said "no root" 74 (A's label kept);
   the 54 they split on were decided by Claude under the owner's delegation (rulings/MY_RULINGS.tsv). Final: rulings/ADJ_FINAL.tsv.
2. The rules are applied to every root, not only the disputed ones:
   R1  a reduplicated word (صلصال، تمتمة، مشمش، دردار …) whose root was given as the doubled triliteral (صلل، تمم …) gets the
       quadriliteral key (صلصل، تمتم …) — Ibn al-Hajib, al-Shafiya: «ونحو زلزل … رباعي … وقال الكوفيون زلزل من زل».
   R2  ستت → سدس for the numerals — al-Muhkam: «ستة وست أصلها سدسة … وستون من العشرات مشتق منه».
   MAP the bank-v8 review mapped قرنفل→قرفل (Ibn Jinni: third sakin nun of a five-letter word is extra), عنصل→عصل, سمندل→سمدل, بدق→بذق.
3. Bank: HusseinFrameNet 02_roots/HFN_ROOTS_v8.csv (HFN PR #10) adds the 76 new keys.
Per synset: roots_prev_rootkey3 (before this step) and root_key_basis3. Log data/wordnet/ROOTKEY3_CHANGES_20261107.tsv,
backup data/wordnet/_pre_rootkey3_20261107/ (gitignored). Everything CANDIDATE.
Usage: python3 audit/wordnet_rootkey/apply_rootkey_rulings.py   (refuses to run twice)"""
import csv, hashlib, json, os, re, shutil, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); RU = os.path.join(HERE, 'rulings')
AMLN = os.path.dirname(os.path.dirname(HERE)); WN = os.path.join(AMLN, 'data', 'wordnet')
SYN, BAK, LOG = (os.path.join(WN, 'wordnet_synsets.json'), os.path.join(WN, '_pre_rootkey3_20261107'),
                 os.path.join(WN, 'ROOTKEY3_CHANGES_20261107.tsv'))
if os.path.exists(BAK): sys.exit(BAK + ' exists — already applied')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def tsv(p): return list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
HAR = re.compile(r'[ً-ْٰـ]')
def bare(s): return re.sub('[أإآ]', 'ا', HAR.sub('', s or '')).replace('ٱ', 'ا')
# disputed pair → (wn_root, word)
PAIR = {}
for d in tsv(os.path.join(HERE, 'WN_ROOT_REVIEW_DECISIONS.tsv')): PAIR[d['pair_id']] = (d['wn_root'], d['word'])
for d in tsv(os.path.join(HERE, 'census', 'E_DECISIONS.tsv')): PAIR[d['pair_id']] = (d['wn_root'], d['word'])
ADJ = {PAIR[a['pair_id']]: a for a in tsv(os.path.join(RU, 'ADJ_FINAL.tsv'))}
MAP = {m['K_in']: m['K_bank'] for m in tsv(os.path.join(RU, 'MAPS_v8.tsv'))}
for n in tsv(os.path.join(RU, 'NEW_ROOTS_v8.tsv')):
    if n['K_reviewed_as'] and n['K_reviewed_as'] != n['K']: MAP[n['K_reviewed_as']] = n['K']
def r1(K, w):
    stem = bare(w); stem = stem[2:] if stem.startswith('ال') and len(stem) > 4 else stem
    if not (len(K) == 3 and K[1] == K[2] and K[0] != K[1]): return None
    if re.search(K[0] + K[1] + K[0] + '[اوي]?' + K[1], stem): return K[0] + K[1] + K[0] + K[1]
    m = re.match(r'(.)(.)\1[اوي]?\2', stem)      # السلسلة: extractor gave لسس; the reduplicated stem is سلسل
    if m and m.group(1) != m.group(2) and set(K) <= {m.group(1), m.group(2)}: return m.group(1) + m.group(2) + m.group(1) + m.group(2)
src_sha = sha(SYN); S = json.load(open(SYN, encoding='utf-8')); C = collections.Counter(); log = []
for s in S['synsets']:
    roots = s.get('roots') or []
    if not roots: continue
    w = s.get('root_source_word') or ''
    basis = [b for b in (s.get('root_key_basis2') or []) if 'NO_ROOT_' not in b] or ['EXACT'] * len(roots)
    status = set(s.get('root_status_rootkey', []))
    new, nb = [], []
    for r, b in zip(roots, basis):
        a = ADJ.get((r, w)) if b in ('READ2_DISAGREE', 'CENSUS2_DISAGREE') else None
        if a:
            status.discard('PENDING_OWNER_ROOT')
            tag = 'ADJ2' if a['basis'].startswith('ADJ2') else 'OWNER_DELEGATED'
            if a['K']:
                new.append(a['K']); nb.append(tag); C['adj_root'] += 1
                if 'NAME' in a['reason']: status.add('NAME_WITH_ROOT')
            else:
                nb.append(f"{tag}_NO_ROOT_{a['verdict']}"); status.add('NO_ROOT_' + a['verdict']); C['adj_no_root_' + a['verdict']] += 1
            continue
        k2 = r1(r, w)
        if k2: new.append(k2); nb.append('RULE_R1'); C['R1'] += 1; continue
        if r == 'ستت' and 'ست' in bare(w): new.append('سدس'); nb.append('RULE_R2'); C['R2'] += 1; continue
        if r in MAP: new.append(MAP[r]); nb.append('RULE_MAP_v8'); C['map'] += 1; continue
        new.append(r); nb.append(b)
    new = list(dict.fromkeys(new))
    if new != roots or nb != basis:
        if new != roots:
            log.append((s['id'], w, '|'.join(roots), '|'.join(new), '|'.join(nb))); C['synsets_changed'] += 1
        s['roots_prev_rootkey3'] = list(roots); s['root_key_basis3'] = nb; s['roots'] = new
    s['root_status_rootkey'] = sorted(status)
    if not s['root_status_rootkey']: del s['root_status_rootkey']
S['_meta']['revisions'].append({
    'date': '2026-11-07', 'id': 'ROOTKEY_v3_OWNER_RULINGS', 'what': 'disputed pairs adjudicated (two adjudicators on R1–R8 with al-Shamela sources; 54 split decided by Claude under owner delegation); R1/R2/MAP applied to all roots; bank HFN_ROOTS_v8',
    'counts': dict(C), 'rules': 'audit/wordnet_rootkey/rulings/RULES.md', 'log': 'data/wordnet/ROOTKEY3_CHANGES_20261107.tsv',
    'backup': 'data/wordnet/_pre_rootkey3_20261107/ (local, gitignored)', 'source_sha256': src_sha,
    'script': 'audit/wordnet_rootkey/apply_rootkey_rulings.py', 'status': 'CANDIDATE',
    'owner_instruction': '2026-11-07 «١ اجتهد بها ؛ ٢ اضفها ؛ ٣. اجتهد بها ؛ استعمل موقع الشاملة»'})
os.makedirs(BAK); shutil.copy2(SYN, BAK)
if sha(os.path.join(BAK, 'wordnet_synsets.json')) != src_sha: sys.exit('backup mismatch')
with open(SYN, 'w', encoding='utf-8') as f: json.dump(S, f, ensure_ascii=False)
with open(LOG, 'w', encoding='utf-8', newline='') as f:
    wr = csv.writer(f, delimiter='\t'); wr.writerow(['synset', 'root_source_word', 'roots_before', 'roots_after', 'basis3']); wr.writerows(log)
print(dict(C))
