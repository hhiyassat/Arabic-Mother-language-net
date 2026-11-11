"""يرفق بكلّ حدث في الدفعة 1 معناه من لسان العرب: جمل مادّة الجذر التي فيها المصدر (فإن لم توجد فالفعل)."""
import csv,json,re,os
HAR=re.compile(r'[ً-ْٰـ]')
def bare(s): return HAR.sub('',s).translate(str.maketrans('ٱأإآ','اااا'))
def tok(w):
    w=bare(w)
    for p in ('وال','فال','بال','كال','لل','ال'):
        if w.startswith(p) and len(w)-len(p)>=3: return w[len(p):]
    if w[:1] in 'وف' and len(w)>=4: w=w[1:]
    return w
K=json.load(open('EV1_KEY.json'))
E={r['event_id']:r for r in csv.DictReader(open(os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v47/events.csv'),encoding='utf-8'))}
L=open(os.path.expanduser('~/mudaat_mashru/lisan.txt'),encoding='utf-8').read().split('\n')
H=re.compile(r'^### \$ ([^:]+):')
start={}
for i,l in enumerate(L):
    m=H.match(l)
    if m:
        start.setdefault(bare(m.group(1)).strip(),i); start.setdefault(HAR.sub('',m.group(1)).strip(),i)
heads=sorted(start.values())
import bisect
out=[];miss=[]
for eid in sorted(k for k in K if '#' not in k):
    e=E[K[eid]]; root=bare(e['root_K']).replace(' ','')
    for alt in [root, root.replace('ء','أ'), root[:-1]+'ا' if root[-1] in 'وي' else root, root[:-1]+'ى' if root[-1] in 'وي' else root]:
        if alt in start or alt.replace('أ','ا') in start: root=alt if alt in start else alt.replace('أ','ا'); break
    if root not in start: miss.append((eid,root)); out.append(dict(eid=eid,verb=e['verb'],masdar=e['masdar'],root=e['root_K'],basis='NO_ENTRY',lisan='')); continue
    a=start[root]; z=heads[bisect.bisect_right(heads,a)] if bisect.bisect_right(heads,a)<len(heads) else len(L)
    # sentences with line numbers
    sents=[];cur='';cl=a+1
    for j in range(a,z):
        t=L[j].lstrip('#~$ |')
        for part in re.split(r'(?<=[.؛])\s+',t):
            if not cur: cl=j+1
            cur=(cur+' '+part).strip()
            if part.endswith(('.','؛')): sents.append((cl,cur)); cur=''
    if cur: sents.append((cl,cur))
    def has(s,forms): return any(tok(w) in forms for w in re.findall(r'[ء-يً-ْٰٱ]+',s))
    m={bare(e['masdar'])}; v={bare(e['verb'])}
    both=[s for s in sents if has(s[1],m) and has(s[1],v) and m!=v]
    mo=[s for s in sents if has(s[1],m) and s not in both]
    vo=[s for s in sents if has(s[1],v) and s not in both and s not in mo]
    pick=(both+mo+vo)[:8]; pick.sort()
    basis=f'both{len(both)}/masdar{len(mo)}/verb{len(vo)}' if pick else 'NONE_FOUND'
    out.append(dict(eid=eid,verb=e['verb'],masdar=e['masdar'],root=e['root_K'],basis=basis,
        lisan=' ¦ '.join(f'[ل{l}] {s[:260]}' for l,s in pick)))
w=csv.DictWriter(open('EV1_GLOSS.tsv','w',encoding='utf-8',newline=''),list(out[0]),delimiter='\t');w.writeheader();w.writerows(out)
from collections import Counter; print(sum(1 for o in out if o['basis'].startswith('both0')), 'events without a verb+masdar sentence', miss)
