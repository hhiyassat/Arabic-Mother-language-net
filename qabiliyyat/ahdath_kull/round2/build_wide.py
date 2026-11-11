"""الجولة الثانية: الأحداث التي لا رابط متّفقاً عليه لها (بلا ورود 3762 + لها مرشّحات بلا رابط) — تُبحث بصيغ أوسع
(المضارع، اسم الفاعل/المفعول، الماضي بتاء التأنيث، المؤنّث) في الأبواب نفسها (المخصّص v12 غير اللغويّ)، ويُستبعد كلّ باب قُرئ للحدث من قبل.
حتّى 3 أبواب لكلّ حدث بعدد الورود، ومقتطف حول أوّل ورود."""
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
def forms(e):
    v,m=bare(e['verb']),bare(e['masdar']) if e['masdar'] not in ('','—') else ''
    base={x for x in (v,m) if len(x)>=3}
    f=set()
    if len(v)>=3:
        stem=v[1:] if v[0]=='ا' else v
        f|={'ي'+stem,'ت'+stem,'م'+stem,'م'+stem+'ة',v+'ت',v+'وا'}
        if len(v)==3 and v[0]!='ا':
            f|={v[0]+'ا'+v[1:],v[0]+'ا'+v[1:]+'ة',v[0]+'ا'+v[1:]+'ون','م'+v[:2]+'و'+v[2:],'م'+v[:2]+'و'+v[2:]+'ة'}
    if m and len(m)>=3: f|={m+'ة',m+'ه'}
    return {x for x in f if len(x)>=4}-base
span={}; cnt=collections.defaultdict(collections.Counter)
for k,n in enumerate(S):
    if n['naw'] in ('كتاب','رأس') or n['line']>=LING: continue
    e=S[k+1]['line'] if k+1<len(S) else len(T)
    span[n['id']]=(n['line'],e)
    for w in re.findall(r'[ء-يً-ْٰٱ]+',' '.join(T[n['line']-1:e-1])): cnt[tok(w)][n['id']]+=1
E=list(csv.DictReader(open(os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v48/events.csv'),encoding='utf-8')))
seen=collections.defaultdict(set)
for r in csv.DictReader(open('ALL_CAND.tsv'),delimiter='\t'): seen[r['event_id']].add(r['sid'])
linked={r['event_id'] for r in csv.DictReader(open('LINKS.tsv'),delimiter='\t')}
rows=[];stat=collections.Counter()
for e in E:
    if e['event_id'] in linked or e.get('event_review_v36','').startswith('WITHDRAWN'): continue
    fs=forms(e); c=collections.Counter()
    for f in fs: c.update(cnt.get(f,{}))
    for s in seen[e['event_id']]: c.pop(int(s),None)  # تصحيح لاحق: sid في ALL_CAND نصّ (لم يُطبَّق على WIDE_CAND المقروء؛ انظر collect2)
    stat['events']+=1
    if not c: stat['nohit']+=1; continue
    for r,(sid,k) in enumerate(c.most_common(3),1):
        a,z=span[sid]; sn=''
        for j in range(a-1,z-1):
            if any(tok(w) in fs for w in re.findall(r'[ء-يً-ْٰٱ]+',T[j])):
                sn=f'[{j+1}] '+' '.join(T[x].lstrip('#~ $') for x in range(max(a-1,j-2),min(z-1,j+3)))[:600]; break
        rows.append(dict(event_id=e['event_id'],root=e['root_K'],verb=e['verb'],masdar=e['masdar'],rank=f'W{r}',sid=sid,hits=k,path=path(sid),snippet=sn))
w=csv.DictWriter(open('WIDE_CAND.tsv','w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
print(stat,len(rows),len({r['event_id'] for r in rows}),len({r['root'] for r in rows}))
