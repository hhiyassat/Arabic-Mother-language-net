"""كلّ أحداث HFN v47 × أبواب المخصّص v12 (غير اللغويّة، قبل 54264): لكلّ حدث حتّى 5 أبواب بعدد ورود الفعل/المصدر مجرّدين، ومقتطف واحد قصير لكلّ باب."""
import json,csv,re,collections,os
T=open(os.path.expanduser('~/mudaat_mashru/mukhassas.txt'),encoding='utf-8').read().split('\n')
N=json.load(open('../muk_v2/ajnas_v12.json'))['ajnas']; I={n['id']:n for n in N}
S=sorted(N,key=lambda n:(n['line'],0 if n['naw']=='كتاب' else 1))
LING=54264
HAR=re.compile(r'[ً-ْٰـ]')
def bare(s): return HAR.sub('',s).translate(str.maketrans('ٱأإآ','اااا'))
def tok(w):
    w=bare(w)
    for p in ('وال','فال','بال','كال','لل','ال'):
        if w.startswith(p) and len(w)-len(p)>=3: return w[len(p):]
    if w[:1] in 'وف' and len(w)>=4: w=w[1:]
    return w
def path(i):
    p=[]
    while i is not None: p.append(I[i]['title']); i=I[i]['parent']
    return ' › '.join(reversed(p))
span={}; cnt=collections.defaultdict(collections.Counter)
for k,n in enumerate(S):
    if n['naw'] in ('كتاب','رأس') or n['line']>=LING: continue
    e=S[k+1]['line'] if k+1<len(S) else len(T)
    span[n['id']]=(n['line'],e)
    for w in re.findall(r'[ء-يً-ْٰٱ]+',' '.join(T[n['line']-1:e-1])): cnt[tok(w)][n['id']]+=1
E=list(csv.DictReader(open(os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v47/events.csv'),encoding='utf-8')))
rows=[];nohit=[]
for e in E:
    forms={f for f in {bare(e['verb']),bare(e['masdar'])} if len(f)>=3}
    c=collections.Counter()
    for f in forms: c.update(cnt.get(f,{}))
    if not c: nohit.append(dict(event_id=e['event_id'],root=e['root_K'],verb=e['verb'],masdar=e['masdar'])); continue
    for r,(sid,k) in enumerate(c.most_common(5),1):
        a,z=span[sid]; sn=''
        for j in range(a-1,z-1):
            if any(tok(w) in forms for w in re.findall(r'[ء-يً-ْٰٱ]+',T[j])):
                sn=f'[{j+1}] '+' '.join(T[x].lstrip('#~ $') for x in range(max(a-1,j-1),min(z-1,j+2)))[:300]; break
        rows.append(dict(event_id=e['event_id'],root=e['root_K'],verb=e['verb'],masdar=e['masdar'],rank=r,sid=sid,hits=k,path=path(sid),snippet=sn))
w=csv.DictWriter(open('ALL_CAND.tsv','w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
w=csv.DictWriter(open('NOHIT.tsv','w',encoding='utf-8',newline=''),list(nohit[0]),delimiter='\t');w.writeheader();w.writerows(nohit)
ev={r['event_id'] for r in rows}
print('rows',len(rows),'events with cands',len(ev),'nohit events',len(nohit))
roots_all={e['root_K'] for e in E}; roots_c={r['root'] for r in rows}
print('roots',len(roots_all),'roots with cands',len(roots_c))
print('rows by hits', collections.Counter(min(int(r['hits']),5) for r in rows))
