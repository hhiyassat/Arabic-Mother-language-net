"""يجمع الأجزاء المقيسة: الروابط المتّفق عليها (YES) → LINKS.tsv، والخلاف → KHILAF.tsv، والإحصاء العامّ."""
import csv,glob,json
from math import sqrt
from collections import Counter
def W(x,n,z=1.96):
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
SID={}
for r in csv.DictReader(open('ALL_CAND.tsv'),delimiter='\t'): SID[f"{r['event_id']}#{r['rank']}"]=(r['event_id'],r['sid'],r['snippet'][:200])
links=[];khilaf=[];c=Counter();ev_seen=set();roots_seen=set();ev_link=set();roots_link=set()
for f in sorted(glob.glob('chunks/C*_CMP.tsv')):
    c['chunks']+=1
    for r in csv.DictReader(open(f),delimiter='\t'):
        e,sid,sn=SID[r['cand']]; c['rows']+=1; ev_seen.add(e); roots_seen.add(r['root'])
        ok=r['agree']=='1'; c['agree']+=ok
        y='YES' in (r['A'].split('/')[0],r['B'].split('/')[0]); c['y']+=y; c['y_ok']+=y and ok
        if ok and r['A'].startswith('YES'):
            _,role,dal,mar=r['A'].split('/')
            links.append(dict(event_id=e,root=r['root'],verb=r['verb'],masdar=r['masdar'],mukhassas_sid=sid,path=r['path'],role=role,dalala=dal,luzum_martaba=mar,luzum_naw=r['naw'],
                dhat=r['dhatA'] if r['dhatA']==r['dhatB'] else f"{r['dhatA']}|{r['dhatB']}",shahid=sn,qawl='على ذكر ابن سيده في المخصّص (باب '+r['path'].split(' › ')[-1]+')',i3timad='CANDIDATE'))
            ev_link.add(e); roots_link.add(r['root'])
        elif not ok:
            khilaf.append(dict(cand=r['cand'],event_id=e,root=r['root'],verb=r['verb'],path=r['path'],A=r['A'],B=r['B'],noteA=r['noteA'],noteB=r['noteB']))
for name,rows in (('LINKS.tsv',links),('KHILAF.tsv',khilaf)):
    if rows:
        w=csv.DictWriter(open(name,'w',encoding='utf-8',newline=''),list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
print(f"chunks {c['chunks']} rows {c['rows']} agree {c['agree']} W={W(c['agree'],c['rows'])} | YES-rows {c['y_ok']}/{c['y']} W={W(c['y_ok'],c['y'])}")
print(f"links {len(links)} events linked {len(ev_link)}/{len(ev_seen)} roots linked {len(roots_link)}/{len(roots_seen)} khilaf {len(khilaf)}")
print(Counter((l['role'],l['dalala']) for l in links).most_common(8))
