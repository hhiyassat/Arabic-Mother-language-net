"""الجولة 4 (T): الأحداث الـ691 التي لم تُوجد في لسان العرب (527 بلا صيغة في المادّة، 164 بلا مادّة) — تُبحث في تاج العروس (OpenITI، ~/mudaat_mashru/taj.txt). مشتقّ من make_l.py.
(الأصل:) الجولة 3 (L): الأحداث الـ2605 التي لا باب مرشّحاً لها في المخصّص — تُبحث في مادّة جذرها من لسان العرب (OpenITI، ~/mudaat_mashru/lisan.txt).
صيغ البحث: الفعل والمصدر وصيغ build_wide. حتّى 3 مواضع لكلّ حدث (الصيغة الأصليّة أوّلاً، متباعدة ≥600 حرف). مقتطف: 180 حرفاً قبل | 420 من موضع الورود."""
import csv,re,json,collections,sys
sys.path.insert(0,'../evall')
HAR=re.compile(r'[ً-ْٰـ]')
def bare(s): return HAR.sub('',s).translate(str.maketrans('ٱأإآؤئء','ااااااا'))
def tok(w):
    w=bare(w)
    for p in ('وال','فال','بال','كال','لل','ال'):
        if w.startswith(p) and len(w)-len(p)>=3: return w[len(p):]
    if w[:1] in 'وف' and len(w)>=4: w=w[1:]
    return w
src=open('../evall/build_wide.py').read(); exec(src[src.index('def forms'):src.index('span={}')])
def key(s): return bare(s).replace(' ','').replace('ء','ا').replace('ؤ','ا').replace('ئ','ا').replace('ى','ي')
# مداخل التاج: «### | جذر» (الحروف قد تُفصل بمسافات)؛ رؤوس الأبواب والفصول بين قوسين تُترك
ENT=collections.defaultdict(list); cur=None; RECOVERED=[]
for i,l in enumerate(open('/Users/husseinhiyassat/mudaat_mashru/taj.txt',encoding='utf-8'),1):
    if l.startswith('### |'):
        h=l[5:].strip()
        h=re.sub(r'\s*(PageV\d+P\d+|ms\d+)\s*',' ',h).strip()
        if h.startswith('(') or not h: cur=None; continue
        k=key(re.sub(r'[^ء-يأإآٱؤئى ]','',h))
        if 2<=len(k)<=5: cur=k; ENT[cur].append([])
        else: cur=None
        continue
    if cur is None or l.startswith('#META'): continue
    body=re.sub(r'^~~|^# ','',l.rstrip('\n'))
    body=re.sub(r'\s*(PageV\d+P\d+|ms\d+)\s*',' ',body).replace('{','').replace('}','').replace('!','').strip()
    if body: ENT[cur][-1].append((i,body))
def keys(r):
    r=key(r); out=[r]
    if r[-1:] in 'وي': out+= [r[:-1]+x for x in 'ويا' if r[:-1]+x!=r]
    # المضاعف الرباعيّ يُذكر في التاج في مادّة الثلاثيّ وبالعكس: وسوس ↔ وسس، قهه ↔ قهقه
    if len(r)==4 and r[0]==r[2] and r[1]==r[3]: out+=[r[:2]+r[1], r[:2]]
    if len(r)==3 and r[1]==r[2]: out+=[r[:2]*2]
    return [k for k in out if k in ENT]
E=list(csv.DictReader(open('../lisan/LISAN_NOHIT.tsv'),delimiter='\t'))
rows=[];stat=collections.Counter();nohit=[]
for e in E:
    ks=keys(e['root'])
    if not ks: stat['root_absent']+=1; nohit.append((e,'ROOT_NOT_IN_TAJ')); continue
    v=bare(e['verb']); m=bare(e['masdar']) if e['masdar'] not in ('','—') else ''
    base={x for x in (v,m) if len(x)>=3}; wide=forms(e)
    if len(v)==2: base|={v,v+'ت',v+'وا','ي'+v,'ت'+v}  # المضعّف: كَرّ ← كر (داخل مادّته فقط)
    hits=[]
    for k in ks:
        for blk in ENT[k]:
            text='';starts=[]
            for ln,b in blk: starts.append((len(text),ln)); text+=b+' '
            for mt in re.finditer(r'[ء-يً-ْٰٱ]+',text):
                t=tok(mt.group())
                if t in base or t in wide:
                    ln=max(s for s in starts if s[0]<=mt.start())[1]
                    hits.append((0 if t in base else 1,k,mt.start(),ln,text))
    if not hits: stat['no_form_hit']+=1; nohit.append((e,'NO_FORM_IN_ENTRY')); continue
    hits.sort(key=lambda h:(h[0],h[2])); pick=[]
    for h in hits:
        if all(h[1]!=p[1] or abs(h[2]-p[2])>=600 for p in pick): pick.append(h)
        if len(pick)==3: break
    stat['events']+=1
    for r,(lvl,k,pos,ln,text) in enumerate(pick,1):
        sn=f'[{ln}] … '+text[max(0,pos-180):pos].strip()+' | '+text[pos:pos+420].strip()
        rows.append(dict(cand=f"{e['event_id']}#T{r}",root=e['root'],verb=e['verb'],masdar=e['masdar'],taj_root=k,line=ln,form='base' if lvl==0 else 'wide',snippet=sn.replace('\t',' ')))
w=csv.DictWriter(open('TAJ_CAND.tsv','w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
with open('TAJ_NOHIT.tsv','w',encoding='utf-8') as f:
    f.write('event_id\troot\tverb\tmasdar\treason\n')
    for e,why in nohit: f.write(f"{e['event_id']}\t{e['root']}\t{e['verb']}\t{e['masdar']}\t{why}\n")
def chunk(rows,n=150):
    cur=[];k=0;last=None
    def flush():
        nonlocal cur,k
        w=csv.DictWriter(open(f'Tc/T{k:03d}_IN.tsv','w',encoding='utf-8',newline=''),['cand','root','verb','masdar','taj_root','snippet'],delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(cur);k+=1;cur=[]
    for r in rows:
        ev=r['cand'].split('#')[0]
        if ev!=last and len(cur)>=n: flush()
        last=ev;cur.append(r)
    if cur: flush()
    return k
print('recovered headings',len(RECOVERED),RECOVERED[:15]);print(stat,len(rows),'chunks',chunk(rows),collections.Counter(r['form'] for r in rows))
