"""دفعة الأحداث 1 — 50 حدثاً عشوائياً (بذرة 20261109) من HFN v47 على شجرة المخصّص v12.
لكلّ حدث: أعلى 5 أبواب في الكتب غير اللغويّة (قبل السطر 54264) بعدد ورود الفعل/المصدر مجرّدين، ومقتطفان من كلّ باب.
القارئ يختار الباب الذي يذكر الحدث مع ذاته (محلّ/فاعل/مكان/آلة/مصدر/زمان) أو NONE أو OTHER_SENSE، ويسم الدلالة."""
import json,csv,re,collections,random,os
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
R=os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v47/events.csv')
pool=[]
for e in csv.DictReader(open(R,encoding='utf-8')):
    forms={f for f in {bare(e['verb']),bare(e['masdar'])} if len(f)>=3}
    c=collections.Counter()
    for f in forms: c.update(cnt.get(f,{}))
    if sum(c.values())>=3: pool.append((e,forms,c))
print('pool',len(pool))
random.seed(20261109); B=random.sample(pool,50)
rows=[];key={}
for i,(e,forms,c) in enumerate(B):
    eid=f'E{i:02d}'; key[eid]=e['event_id']
    for r,(sid,k) in enumerate(c.most_common(5),1):
        a,z=span[sid]; sn=[]
        for j in range(a-1,z-1):
            if any(tok(w) in forms for w in re.findall(r'[ء-يً-ْٰٱ]+',T[j])):
                sn.append(f'[{j+1}] '+' '.join(T[x].lstrip('#~ $') for x in range(max(a-1,j-1),min(z-1,j+2)))[:330])
            if len(sn)>=2: break
        rows.append(dict(eid=eid,verb=e['verb'],masdar=e['masdar'],cand=f'{eid}#{r}',hits=k,path=path(sid),snippet=' ¦ '.join(sn)))
        key[f'{eid}#{r}']=sid
w=csv.DictWriter(open('EV1_IN.tsv','w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
json.dump(key,open('EV1_KEY.json','w'),ensure_ascii=False)
print('rows',len(rows))
