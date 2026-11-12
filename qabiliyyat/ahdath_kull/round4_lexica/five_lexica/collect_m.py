"""يجمع الجولة 4 (M، المعاجم الخمسة بالبحث في النصّ كلّه) — مشتقّ من collect3 (الجولة 3، لسان العرب). الأصل:
يجمع الجولة 3 (L، لسان العرب): الصفّ رابط إذا اتّفق القارئان الأعميان على YES بالصفّ كاملاً (الحكم/الدور/الدلالة/المرتبة)،
بشرط أن يجتاز الجزء حدّ Wilson 0.78 على صفوفه كلّها؛ الجزء الذي يفشل يُعاد بزوج جديد مرّة، فإن فشل ثانية استُبعد (EXCLUDE.txt).
المتّفق على غير YES ← NEG3؛ المختلف فيه ← KHILAF3 للمالك.
L020 (11 صفّاً) لا يبلغ الحدّ وحده ولو اتّفق كلّه (11/11 = 0.741)، فيُحكم عليه مع L019 مجموعين (POOL)."""
import csv,glob,os,collections
from math import sqrt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def W(x,n,z=1.96):
    if not n: return 0
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
CAN={'محل':'محلّ','تضمن':'تضمّن','ذهني':'ذهنيّ','عادي':'عاديّ','عقلي':'عقليّ','شرعي':'شرعيّ'}
EXCLUDE=set(open('EXCLUDE.txt').read().split()) if os.path.exists('EXCLUDE.txt') else set()
POOL={}
A={r['cand']:r for r in csv.DictReader(open('M_CAND.tsv'),delimiter='\t')}
links=[];neg=[];kh=[];sc=[];c=collections.Counter()
for f in sorted(glob.glob('Mc/M*_CMP.tsv')):
    ch=os.path.basename(f)[:4]; rows=list(csv.DictReader(open(f),delimiter='\t'))
    n=len(rows); ag=sum(r['agree']=='1' for r in rows); y=[r for r in rows if 'YES' in (r['A'][:3],r['B'][:3])]
    sc.append(dict(chunk=ch,rows=n,agree=ag,wilson=W(ag,n),yes_rows=len(y),yes_agree=sum(r['agree']=='1' for r in y),yes_wilson=W(sum(r['agree']=='1' for r in y),len(y)),excluded=ch in EXCLUDE,pooled_with='',pooled_wilson=''))
    if ch in POOL:
        pr=rows+list(csv.DictReader(open(f'Lc/{POOL[ch]}_CMP.tsv'),delimiter='\t')); sc[-1]['pooled_with']=POOL[ch]; sc[-1]['pooled_wilson']=W(sum(r['agree']=='1' for r in pr),len(pr))
    for r in rows:
        a=A[r['cand']]; ev=r['cand'].split('#')[0]; ok=r['agree']=='1' and ch not in EXCLUDE
        c['rows']+=1; c['ok']+=ok
        if ok and r['A'].startswith('YES'):
            _,role,dal,mar=[CAN.get(x,x) for x in r['A'].split('/')]
            links.append(dict(event_id=ev,root=a['root'],verb=a['verb'],masdar=a['masdar'],book_file=a['book_file'],book_line=a['line'],form=a['form'],
                role=role,dalala=dal,luzum_martaba=mar,luzum_naw=CAN.get(r['naw'],r['naw']) if dal!='تضمّن' else '-',
                dhat=r['dhatA'] if r['dhatA']==r['dhatB'] else f"{r['dhatA']}|{r['dhatB']}",snippet=a['snippet'],cand=r['cand'],chunk=ch,noteA=r['noteA'],noteB=r['noteB']))
        elif ok: neg.append(dict(cand=r['cand'],event_id=ev,verdict=r['A']))
        else: kh.append(dict(chunk_fail=ch if ch in EXCLUDE else '',cand=r['cand'],event_id=ev,root=a['root'],verb=a['verb'],book_line=a['line'],A=r['A'],B=r['B'],dhatA=r['dhatA'],dhatB=r['dhatB'],noteA=r['noteA'],noteB=r['noteB'],snippet=a['snippet']))
def wr(name,rows):
    if rows:
        w=csv.DictWriter(open(name,'w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
wr('LINKS_M.tsv',links);wr('KHILAF_M.tsv',kh);wr('NEG_M.tsv',neg);wr('CHUNK_SCORES_M.tsv',sc)
ys=sum(s['yes_rows'] for s in sc if not s['excluded']); ya=sum(s['yes_agree'] for s in sc if not s['excluded'])
print(dict(c),'links',len(links),'events',len({l['event_id'] for l in links}),'roots',len({l['root'] for l in links}),'neg',len(neg),'khilaf',len(kh))
print('YES rows',ya,'/',ys,'W',W(ya,ys))
