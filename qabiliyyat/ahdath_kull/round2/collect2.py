"""يجمع الجولة 2.
K (صفوف الخلاف): يُقبل الصفّ إذا اتّفق القارئان الجديدان على الصفّ كاملاً (الحكم/الدور/الدلالة/المرتبة) **وطابق** اتّفاقُهما قراءةَ أحد القارئين الأوّلين = 3 من 4 قراءات عمياء. YES → رابط؛ غيره → محسوم نفياً. وإلّا يبقى خلافاً للمالك.
W (المرشّحات الأوسع): كالجولة 1: الصفّ رابط إذا اتّفق القارئان على YES بالصفّ كاملاً، بشرط أن يجتاز الجزء حدّ Wilson 0.78؛ الجزء الذي يفشل مرّتين يُستبعد."""
import csv,glob,os,re,collections
from math import sqrt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
HAR=re.compile(r'[ً-ْٰـ]')
def nz(x): x=HAR.sub('',(x or '')).strip(); return '-' if x in ('','-','—') else x
def W(x,n,z=1.96):
    if not n: return 0
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
CAN={'محل':'محلّ','تضمن':'تضمّن','ذهني':'ذهنيّ','عادي':'عاديّ','عقلي':'عقليّ','شرعي':'شرعيّ'}
EXCLUDE=set(open('EXCLUDE.txt').read().split()) if os.path.exists('EXCLUDE.txt') else set()
KH={r['cand']:r for r in csv.DictReader(open('../KHILAF.tsv'),delimiter='\t')}
A={}
for f in ('../ALL_CAND.tsv','../WIDE_CAND.tsv'):
    for r in csv.DictReader(open(f),delimiter='\t'): A[f"{r['event_id']}#{r['rank']}"]=r
R1PAIRS={(r['event_id'],r['sid']) for r in csv.DictReader(open('../ALL_CAND.tsv'),delimiter='\t')}
# build_wide.py أخطأ في استبعاد أبواب الجولة الأولى (sid نصّ مقابل رقم)، فدخلت 1750 صفّاً قُرئ زوجها في الجولة الأولى.
# حكم هذه الأزواج للجولة الأولى ولقاعدة 3 من 4 وحدها؛ قراءتها في W لا يُكتب منها شيء (تُعدّ W_DUP_R1).
links=[];neg=[];kh=[];c=collections.Counter();sc=[]
for f in sorted(glob.glob('chunks/[KW]*_CMP.tsv')):
    ch=os.path.basename(f)[:4]; p=ch[0]; rows=list(csv.DictReader(open(f),delimiter='\t'))
    n=len(rows); ag=sum(r['agree']=='1' for r in rows); y=[r for r in rows if 'YES' in (r['A'][:3],r['B'][:3])]
    sc.append(dict(chunk=ch,rows=n,agree=ag,wilson=W(ag,n),yes_rows=len(y),yes_agree=sum(r['agree']=='1' for r in y),excluded=ch in EXCLUDE))
    for r in rows:
        a=A[r['cand']]
        if p=='W' and (a['event_id'],a['sid']) in R1PAIRS: c['W_DUP_R1']+=1; continue
        c[p+'_rows']+=1
        ok=r['agree']=='1' and ch not in EXCLUDE
        if p=='K':
            o=KH[r['cand']]; orig={'/'.join(nz(x) for x in o['A'].split('/')),'/'.join(nz(x) for x in o['B'].split('/'))}
            ok=ok and r['A'] in orig
        c[p+'_ok']+=ok
        if ok and r['A'].startswith('YES'):
            _,role,dal,mar=[CAN.get(x,x) for x in r['A'].split('/')]
            links.append(dict(event_id=a['event_id'],root=a['root'],verb=a['verb'],masdar=a['masdar'],mukhassas_sid=a['sid'],path=a['path'],
                role=role,dalala=dal,luzum_martaba=mar,luzum_naw=CAN.get(r['naw'],r['naw']),dhat=r['dhatA'] if r['dhatA']==r['dhatB'] else f"{r['dhatA']}|{r['dhatB']}",
                snippet=a['snippet'],hits=a['hits'],cand=r['cand'],chunk=ch,noteA=r['noteA'],noteB=r['noteB'],
                round='R2_KHILAF_3of4' if p=='K' else 'R2_WIDE_FORMS',first_pair=(KH[r['cand']]['A']+' || '+KH[r['cand']]['B']) if p=='K' else ''))
        elif ok: neg.append(dict(cand=r['cand'],event_id=a['event_id'],verdict=r['A'],round=p))
        else: kh.append(dict(set=p,chunk_fail=ch if ch in EXCLUDE else '',cand=r['cand'],event_id=a['event_id'],root=a['root'],verb=a['verb'],path=a['path'],
                A2=r['A'],B2=r['B'],noteA2=r['noteA'],noteB2=r['noteB'],A1=KH[r['cand']]['A'] if p=='K' else '',B1=KH[r['cand']]['B'] if p=='K' else ''))
def wr(name,rows):
    if rows:
        w=csv.DictWriter(open(name,'w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
wr('LINKS2.tsv',links);wr('KHILAF2.tsv',kh);wr('NEG2.tsv',neg);wr('CHUNK_SCORES2.tsv',sc)
print(dict(c),'links',len(links),'neg',len(neg),'khilaf',len(kh))
print('links K',sum(l['round'].startswith('R2_K') for l in links),'W',sum(l['round']=='R2_WIDE_FORMS' for l in links))
