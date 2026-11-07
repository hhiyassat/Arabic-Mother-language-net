#!/usr/bin/env python3
"""maqayis.db entries → HFN bank key (owner 2026-11-08: «نفذ كل … ربط مداخل maqayis.db بالبنك»).

Each lexical entry of word_tree/maqayis.db (Ibn Faris, مقاييس اللغة) is mapped to the root key of the newest HusseinFrameNet bank
(02_roots/HFN_ROOTS_v*.csv) by evidence, in this order:
  CHAIN       the bank links (ref_maqayis / ref_ayn / extra_refs) point to an M02 record (~/roots/arabic-root-meanings-v2.jsonl, sha256
              checked against HFN_REFERENCES.csv) whose ibn_faris evidence cites this entry id (source_entry_id). These bank links were
              read by two readers when they were made. One key → that key; several keys → all of them (Ibn Faris often treats و and ي
              of a weak root in one entry: «الشين والراء والحرف المعتل»).
  DISPLAY     no chain: the entry's root_display, with hamza seats → ء and diacritics removed, is itself a bank key.
  FORM_UNIQUE the display is the root written another way and exactly ONE bank key fits: a geminate written with two letters
              (دك → دكك), a weak root written with alif/alif maqsura or with و/ى before it (خنا → خنو|خني, أثوى → ءثو|ءثي), hamza seats.
              Several bank keys fit → AMBIGUOUS (listed with the candidates, not chosen).
  READ2       the 103 entries left AMBIGUOUS/UNMAPPED by the rules above were read by two blind readers
              (audit/maqayis_crosswalk/MAQ103_R1/R2.tsv): agreed key(s) → READ2; 37 headings both found missing from the bank were added
              to the bank (HusseinFrameNet v9, HFN-D071) → READ2_NEW_ROOT_v9; the 14 they split on were decided by Claude under the
              owner's «نفذ كل» (audit/maqayis_crosswalk/MY_RULINGS.tsv) → OWNER_DELEGATED.
  UNMAPPED    none of these; listed with the reason, never guessed.
The database is not modified. Output: data/maqayis_bank_crosswalk.tsv (entry_id, entry_num, root_display, bank_K, basis, n_keys).
Usage: python3 audit/build_maqayis_bank_crosswalk.py"""
import csv, hashlib, json, os, re, sqlite3, collections
AMLN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.environ.get('ARABIC_NET_HOME', os.path.dirname(AMLN))
HFN = os.path.join(NET, 'HusseinFrameNet')
banks = sorted((f for f in os.listdir(os.path.join(HFN, '02_roots')) if re.fullmatch(r'HFN_ROOTS_v\d+\.csv', f)), key=lambda f: int(f[11:-4]))
BANK = os.path.join(HFN, '02_roots', banks[-1])
bank = list(csv.DictReader(open(BANK, encoding='utf-8'))); BK = {b['K'] for b in bank}
refs = {r['ref_id']: r for r in csv.DictReader(open(os.path.join(HFN, '02_roots', 'HFN_REFERENCES.csv'), encoding='utf-8'))}
m02 = os.path.expanduser(refs['M02']['path'])
assert hashlib.sha256(open(m02, 'rb').read()).hexdigest() == refs['M02']['sha256'], 'M02 changed'
rec2K = collections.defaultdict(set)
for b in bank:
    for c in ('ref_maqayis', 'ref_ayn'):
        if b[c].startswith('M02#'): rec2K[b[c][4:]].add(b['K'])
    for x in b['extra_refs'].split('·'):
        m = re.match(r'ref_(maqayis|ayn)=M02#(.+)', x)
        if m: rec2K[m.group(2)].add(b['K'])
ent2K = collections.defaultdict(set)
for l in open(m02, encoding='utf-8'):
    r = json.loads(l)
    for ev in r['sources'].get('ibn_faris', {}).get('evidence', []):
        if r['record_id'] in rec2K: ent2K[ev['source_entry_id']] |= rec2K[r['record_id']]
HAR = re.compile(r'[ً-ْٰـ]')
def K(s): return re.sub('[أإآؤئ]', 'ء', HAR.sub('', s or '')).replace(' ', '')
def cands(k):
    out = set()
    stems = {k}
    if len(k) >= 3 and k[-1] == 'ى': stems |= {k[:-1], k[:-1] + 'ي'}          # أثوى, حروى: OCR/maqsura tail
    if len(k) >= 3 and k[-2:] in ('وى', 'وا', 'وأ'): stems.add(k[:-1])
    for s_ in stems:
        if len(s_) == 2: out.add(s_ + s_[1])                                     # دك → دكك
        if len(s_) == 3 and s_[-1] in 'اى': out |= {s_[:-1] + 'و', s_[:-1] + 'ي'}
        if len(s_) == 3 and s_[1] == 'ا': out |= {s_[0] + 'و' + s_[2], s_[0] + 'ي' + s_[2]}
        out.add(s_)
    return sorted(x for x in out if x in BK)
XW = os.path.join(AMLN, 'audit', 'maqayis_crosswalk')
def _tsv(n): return {r['entry_id']: r for r in csv.DictReader(open(os.path.join(XW, n), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE)}
READ = {}
if os.path.exists(os.path.join(XW, 'MAQ103_R1.tsv')):
    r1, r2, mine = _tsv('MAQ103_R1.tsv'), _tsv('MAQ103_R2.tsv'), _tsv('MY_RULINGS.tsv')
    for e in r1:
        a = (r1[e]['verdict'], '|'.join(sorted(filter(None, r1[e]['K'].split('|')))))
        b = (r2[e]['verdict'], '|'.join(sorted(filter(None, r2[e]['K'].split('|')))))
        if e in mine: READ[int(e)] = (sorted(filter(None, mine[e]['K'].split('|'))), 'OWNER_DELEGATED' if mine[e]['K'] else 'UNMAPPED_OWNER_DELEGATED')
        elif a == b and a[0] == 'K': READ[int(e)] = (a[1].split('|'), 'READ2')
        elif a == b and a[0] == 'NOT_IN_BANK': READ[int(e)] = (None, 'READ2_NEW_ROOT_v9')
NEWK = {}
for b in bank:
    m = re.search(r'READ2_MAQAYIS_ENTRY (\d+)', b['links_v2_changes'])
    if m: NEWK[int(m.group(1))] = b['K']
db = sqlite3.connect(os.path.join(AMLN, 'word_tree', 'maqayis.db'))
rows, C = [], collections.Counter()
for eid, num, disp in db.execute('select id, entry_num, root_display from entries where is_lexical_entry=1 order by id'):
    ks = sorted(ent2K.get(eid, ()))
    if eid in READ and not ks:
        ks, basis = READ[eid]
        if ks is None: ks = [NEWK[eid]] if eid in NEWK else []
        ks = [k for k in ks if k in BK]
        if not ks and basis.startswith('READ2'): basis = 'UNMAPPED_' + basis
    elif ks: basis = 'CHAIN'
    elif K(disp) in BK: ks, basis = [K(disp)], 'DISPLAY'
    else:
        c = cands(K(disp))
        if len(c) == 1: ks, basis = c, 'FORM_UNIQUE'
        elif c: ks, basis = c, 'AMBIGUOUS'
        else: basis = 'UNMAPPED_NO_CHAIN_DISPLAY_NOT_A_KEY'
    C[basis] += 1
    rows.append({'entry_id': eid, 'entry_num': num, 'root_display': disp, 'bank_K': '|'.join(ks), 'basis': basis, 'n_keys': len(ks)})
with open(os.path.join(AMLN, 'data', 'maqayis_bank_crosswalk.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)
print(os.path.basename(BANK), dict(C), 'multi-key', sum(1 for r in rows if r['n_keys'] > 1))
