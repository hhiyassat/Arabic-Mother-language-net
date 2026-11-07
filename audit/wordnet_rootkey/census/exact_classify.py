import json,csv,collections,re,os,sys
sys.path.insert(0,'.')
from route_lex import route
HAR=re.compile(r'[ً-ْٰـ]')
def b(s): return re.sub('[أإآ]','ا',HAR.sub('',(s or '').replace('ٱ','ا'))).strip()
A=os.path.expanduser('~/arabic-net'); R=A+'/HusseinFrameNet/release/release_v45/'
E={e['event_id']:e for e in csv.DictReader(open(R+'events.csv',encoding='utf-8')) if not e['event_review_v36'].startswith('WITHDRAWN')}
w2r=collections.defaultdict(set)
for l in csv.DictReader(open(R+'lexical_units.csv',encoding='utf-8')):
    if l['event_id'] in E: w2r[b(l['lemma'])].add(E[l['event_id']]['root_K'])
for e in E.values():
    for w in (e['verb'],e['masdar']):
        if w: w2r[b(w)].add(e['root_K'])
S=json.load(open(A+'/Arabic-Mother-language-net/data/wordnet/wordnet_synsets.json'))['synsets']
P=collections.defaultdict(list)
for s in S:
    bs=s.get('root_key_basis'); rs=s.get('roots') or []
    if bs is None: bs=['EXACT']*len(rs)   # unchanged synsets
    # pair roots with basis only where lengths align
    for r,bb in zip(rs,bs):
        if bb in('EXACT','FORMAT_HAMZA','FORMAT_MAQAYIS_CHAIN','FORMAT_GEMINATE'):
            P[(r,s.get('root_source_word') or '')].append(s['id'])
c=collections.Counter(); occ=collections.Counter(); rows=[]
for (r,w),ids in P.items():
    hf=w2r.get(b(w),set())
    rk,st=route(w) if w else (None,'NOWORD')
    if r in hf: ev='HFN_AGREES'
    elif rk==r: ev='LEX_AGREES'
    elif hf: ev='HFN_OTHER'
    elif rk: ev='LEX_OTHER'
    else: ev='NO_EVIDENCE_'+st
    c[ev]+=1; occ[ev]+=len(ids); rows.append((r,w,len(ids),ev,ids[0],'|'.join(sorted(hf)),rk or ''))
print('pairs',dict(c)); print('occurrences',dict(occ), sum(occ.values()))
with open('exact_pairs.tsv','w',encoding='utf-8') as f:
    f.write('root\tword\tn\tevidence\tsynset\thfn\tlex\n'); [f.write('\t'.join(map(str,x))+'\n') for x in rows]
