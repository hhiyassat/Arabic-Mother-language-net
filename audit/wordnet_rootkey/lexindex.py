"""Index: every word in the text of a bank-linked lexicon record (9 lexicons, sha256 checked) -> bank K -> lexicons. Writes lexidx.pkl here."""
import csv,json,os,re,collections,pickle
A=os.environ.get('ARABIC_NET_HOME',os.path.expanduser('~/arabic-net')); H=A+'/HusseinFrameNet'; SP=os.path.dirname(os.path.abspath(__file__))
HAR=re.compile(r'[ً-ْٰـ]')
def bare(s): return re.sub('[أإآ]','ا',HAR.sub('',s.replace('ٱ','ا')))
bank=list(csv.DictReader(open(H+'/02_roots/HFN_ROOTS_v7.csv',encoding='utf-8')))
refs={r['ref_id']:r for r in csv.DictReader(open(H+'/02_roots/HFN_REFERENCES.csv',encoding='utf-8'))}
COL={'ref_ayn':'M02','ref_maqayis':'M02','ref_sihah':'M03','ref_muhkam':'M04','ref_lisan':'M05','ref_qamus':'M06','ref_taj':'M07','ref_asas':'M08','ref_misbah':'M09','ref_wasit':'M11'}
rec=collections.defaultdict(set)
for b in bank:
    for c,m in COL.items():
        v=b[c]
        if v.startswith(m+'#'): rec[(m,v.split('#',1)[1])].add(b['K'])
    for x in b['extra_refs'].split('·'):
        mm=re.match(r'(ref_\w+)=(M\d\d)#(.+)',x)
        if mm: rec[(mm.group(2),mm.group(3))].add(b['K'])
TOK=re.compile(r'[ء-يٱ]+')
idx=collections.defaultdict(lambda: collections.defaultdict(set))  # word -> K -> set(lexicons)
def texts(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k in('text','headword') and isinstance(v,str): yield v
            else: yield from texts(v)
    elif isinstance(o,list):
        for v in o: yield from texts(v)
for m in ['M02','M03','M04','M05','M06','M07','M08','M09','M11']:
    pth=os.path.expanduser(refs[m]['path'])
    import hashlib
    if hashlib.sha256(open(pth,'rb').read()).hexdigest()!=refs[m]['sha256']: raise SystemExit(m+' lexicon file changed: '+pth)
    for l in open(pth,encoding='utf-8'):
        r=json.loads(l); Ks=rec.get((m,r['record_id']))
        if not Ks or len(Ks)>1: continue
        K=next(iter(Ks))
        for t in texts(r.get('sources',{})):
            for w in TOK.findall(bare(t)):
                if len(w)>=2: idx[w][K].add(m)
pickle.dump({w:{k:sorted(v) for k,v in d.items()} for w,d in idx.items()},open(SP+'/lexidx.pkl','wb'))
print('words indexed',len(idx))
