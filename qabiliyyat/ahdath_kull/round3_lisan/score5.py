"""score5.py IN.tsv RA.tsv RB.tsv OUT.tsv — يقارن قارئين صفّاً صفّاً ويطبع المقاييس."""
import csv,sys
from math import sqrt
from collections import Counter
IN=list(csv.DictReader(open(sys.argv[1]),delimiter='\t'))
def rd(f): return {r['cand'].strip():r for r in csv.DictReader(open(f),delimiter='\t') if r.get('cand')}
A,B=rd(sys.argv[2]),rd(sys.argv[3])
def W(x,n,z=1.96):
    if n==0: return 0
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
import re
HAR=re.compile(r'[\u064b-\u0652\u0670\u0640]')
def nz(x): x=HAR.sub('',(x or '')).strip(); return '-' if x in ('','-','—') else x
def key(r):
    v=nz(r.get('verdict'))
    return (v,) if v!='YES' else (v,nz(r.get('role')),nz(r.get('dalala')),nz(r.get('luzum_martaba')))
c=Counter(); out=[]
for r in IN:
    k=r['cand']; a,b=A.get(k),B.get(k)
    if a is None or b is None: c['missing']+=1; ka=kb=('MISSING',)
    else: ka,kb=key(a),key(b)
    f=ka==kb and ka[0]!='MISSING'
    c['n']+=1; c['full']+=f
    y='YES' in (ka[0],kb[0]); c['y']+=y; c['y_ok']+=y and f
    out.append(dict(cand=k,root=r['root'],verb=r['verb'],masdar=r['masdar'],path=r['lisan_root'],agree=int(f),A='/'.join(ka),B='/'.join(kb),
        dhatA=(a or {}).get('dhat',''),dhatB=(b or {}).get('dhat',''),naw=nz((a or {}).get('luzum_naw')),noteA=(a or {}).get('note','')[:120],noteB=(b or {}).get('note','')[:120]))
csv.DictWriter(open(sys.argv[4],'w'),list(out[0]),delimiter='\t').writeheader()
w=csv.DictWriter(open(sys.argv[4],'a'),list(out[0]),delimiter='\t'); w.writerows(out)
print(f"rows {c['full']}/{c['n']} W={W(c['full'],c['n'])} | YES-rows {c['y_ok']}/{c['y']} W={W(c['y_ok'],c['y'])} | missing {c['missing']}")
