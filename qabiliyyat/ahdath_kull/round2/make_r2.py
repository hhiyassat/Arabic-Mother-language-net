"""الجولة 2: K = صفوف الخلاف الـ4262 بمقتطف أوسع (حتّى 180 حرفاً قبل سطر الورود، ثمّ سطر الورود وما بعده حتّى 420 حرفاً، داخل الباب)؛ W = المرشّحات الأوسع (WIDE_CAND.tsv). أجزاء ~250 صفّاً دون شطر حدث."""
import csv,json,os,re
os.chdir(os.path.dirname(os.path.abspath(__file__))+'/..')
T=open(os.path.expanduser('~/mudaat_mashru/mukhassas.txt'),encoding='utf-8').read().split('\n')
N=json.load(open('../muk_v2/ajnas_v12.json'))['ajnas']
S=sorted(N,key=lambda n:(n['line'],0 if n['naw']=='كتاب' else 1))
span={}
for k,n in enumerate(S):
    e=S[k+1]['line'] if k+1<len(S) else len(T); span[n['id']]=(n['line'],e)
A={f"{r['event_id']}#{r['rank']}":r for r in csv.DictReader(open('ALL_CAND.tsv'),delimiter='\t')}
def wide(r):
    m=re.match(r'\[(\d+)\]',r['snippet'])
    if not m: return r['snippet']
    j=int(m.group(1))-1; a,z=span[int(r['sid'])] if int(r['sid']) in span else span[r['sid']]
    pre=' '.join(T[x].lstrip('#~ $') for x in range(max(a-1,j-2),j))[-180:]
    post=' '.join(T[x].lstrip('#~ $') for x in range(j,min(z-1,j+3)))
    return f'[{j+1}] … '+pre+' | '+post[:420]
K=[]
for r in csv.DictReader(open('KHILAF.tsv'),delimiter='\t'):
    a=A[r['cand']]; K.append(dict(cand=r['cand'],root=a['root'],verb=a['verb'],masdar=a['masdar'],hits=a['hits'],path=a['path'],snippet=wide(a)))
W=[dict(cand=f"{r['event_id']}#{r['rank']}",root=r['root'],verb=r['verb'],masdar=r['masdar'],hits=r['hits'],path=r['path'],snippet=wide(r)) for r in csv.DictReader(open('WIDE_CAND.tsv'),delimiter='\t')]
def chunk(rows,p,n=250):
    cur=[];k=0;last=None
    def flush():
        nonlocal cur,k
        w=csv.DictWriter(open(f'round2/chunks/{p}{k:03d}_IN.tsv','w',encoding='utf-8',newline=''),list(cur[0]),delimiter='\t');w.writeheader();w.writerows(cur);k+=1;cur=[]
    for r in rows:
        ev=r['cand'].split('#')[0]
        if ev!=last and len(cur)>=n: flush()
        last=ev; cur.append(r)
    if cur: flush()
    return k
print('K',chunk(K,'K'),'W',chunk(W,'W'),len(K),len(W))
