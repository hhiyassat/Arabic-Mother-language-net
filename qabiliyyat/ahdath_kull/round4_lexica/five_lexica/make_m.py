"""الجولة 4 (M): الأحداث التي لم توجد صيغتها في لسان العرب ولا في تاج العروس — تُبحث صيغها (الفعل والمصدر ثمّ صيغ build_wide) في نصّ خمسة معاجم كاملاً
(الصحاح، المحكم، تهذيب اللغة، العين، الجمهرة؛ OpenITI، ~/mudaat_mashru/round4_dl/، نُزّلت بإذن المالك 2026-11-12). البحث في النصّ كلّه لا في مادّة الجذر (رؤوس المواد في هذه النسخ غير منتظمة)،
فالمقتطف قد يكون لكلمة أخرى توافق الحروف: يحكم القارئ بـOTHER_SENSE. حتّى 3 مواضع لكلّ حدث، من كتب مختلفة أوّلاً، الأصليّة قبل الأوسع. مقتطف 180 قبل | 420 بعد."""
import re,csv,collections,sys
sys.path.insert(0,'../evall')
exec(open('../taj/make_t.py').read().split('# مداخل التاج')[0])
E=list(csv.DictReader(open('../taj/TAJ_NOHIT.tsv'),delimiter='\t'))
D='/Users/husseinhiyassat/mudaat_mashru/round4_dl/'
BOOKS=[('sihah.txt','الصحاح للجوهري'),('muhkam.txt','المحكم لابن سيده'),('tahdhib.txt','تهذيب اللغة للأزهري'),('ayn.txt','العين للخليل'),('jamhara.txt','جمهرة اللغة لابن دريد')]
TXT={};POS={};HIT={}
for fn,_ in BOOKS:
    text='';starts=[];idx=collections.defaultdict(list)
    for i,l in enumerate(open(D+fn,encoding='utf-8'),1):
        if l.startswith('#META') or not l.strip(): continue
        b=re.sub(r'\s*(PageV\d+P\d+|ms\d+)\s*',' ',re.sub(r'^~~|^# |^### \| |^### \$ ','',l.rstrip('\n'))).replace('{','').replace('}','').strip()
        if not b: continue
        starts.append(len(text))
        for m in re.finditer(r'[ء-يً-ْٰٱ]+',b): idx[tok(m.group())].append((len(text)+m.start(),i))
        text+=b+' '
    TXT[fn]=text;HIT[fn]=idx
rows=[];nohit=[];stat=collections.Counter()
for e in E:
    v=bare(e['verb']); m=bare(e['masdar']) if e['masdar'] not in ('','—') else ''
    base={x for x in (v,m) if len(x)>=3}; wide=set(forms(e))
    if len(v)==2: base|={v+'ت',v+'وا','ي'+v}
    hits=[]
    for bi,(fn,_) in enumerate(BOOKS):
        for lvl,S in ((0,base),(1,wide)):
            for t in S:
                for pos,ln in HIT[fn].get(t,[]): hits.append((lvl,bi,pos,ln,fn))
    if not hits: nohit.append(e); stat['none']+=1; continue
    hits.sort(key=lambda h:(h[0],h[1],h[2])); pick=[]
    for h in hits:  # كتب مختلفة أوّلاً
        if all(h[4]!=p[4] for p in pick): pick.append(h)
        if len(pick)==3: break
    for h in hits:
        if len(pick)>=3: break
        if all(h[4]!=p[4] or abs(h[2]-p[2])>=600 for p in pick): pick.append(h)
    stat['events']+=1
    for r,(lvl,bi,pos,ln,fn) in enumerate(sorted(pick,key=lambda h:(h[0],h[1])),1):
        t=TXT[fn]; sn=f'[{ln}] … '+t[max(0,pos-180):pos].strip()+' | '+t[pos:pos+420].strip()
        rows.append(dict(cand=f"{e['event_id']}#M{r}",root=e['root'],verb=e['verb'],masdar=e['masdar'],book=dict(BOOKS)[fn],book_file=fn,line=ln,form='base' if lvl==0 else 'wide',snippet=sn.replace('\t',' ')))
w=csv.DictWriter(open('M_CAND.tsv','w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
with open('M_NOHIT.tsv','w',encoding='utf-8') as f:
    f.write('event_id\troot\tverb\tmasdar\treason\n')
    for e in nohit: f.write(f"{e['event_id']}\t{e['root']}\t{e['verb']}\t{e['masdar']}\tNO_FORM_IN_SIX_LEXICA\n")
import os; os.makedirs('Mc',exist_ok=True)
cw=csv.DictWriter(open('Mc/M000_IN.tsv','w',encoding='utf-8',newline=''),['cand','root','verb','masdar','book','snippet'],delimiter='\t',extrasaction='ignore');cw.writeheader();cw.writerows(rows)
print(stat,len(rows),collections.Counter(r['form'] for r in rows),collections.Counter(r['book_file'] for r in rows))
