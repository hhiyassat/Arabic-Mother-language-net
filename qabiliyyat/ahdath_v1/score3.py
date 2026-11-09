import csv,sys
from math import sqrt
from collections import Counter
IN=list(csv.DictReader(open('EV1_IN.tsv'),delimiter='\t'))
def rd(f): return {r['cand'].strip():r for r in csv.DictReader(open(f),delimiter='\t')}
A,B=rd(sys.argv[1]),rd(sys.argv[2])
def W(x,n,z=1.96):
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
def nz(x): x=(x or '').strip(); return '-' if x in ('','-','—') else x
def key(r): 
    v=nz(r.get('verdict'))
    return (v,) if v!='YES' else (v,nz(r.get('role')),nz(r.get('dalala')),nz(r.get('luzum_martaba')))
c=Counter(); out=[]; ev={}
for r in IN:
    k=r['cand']; a,b=A.get(k,{}),B.get(k,{})
    ka,kb=key(a),key(b); v=ka[0]==kb[0]; f=ka==kb
    c['verdict']+=v; c['full']+=f; c['naw']+=f and nz(a.get('luzum_naw'))==nz(b.get('luzum_naw'))
    if f and ka[0]=='YES': c['agreed_yes']+=1
    ev.setdefault(r['eid'],[]).append(f)
    out.append(dict(cand=k,verb=r['verb'],path=r['path'],agree=f,A='/'.join(ka),B='/'.join(kb),dhatA=a.get('dhat',''),dhatB=b.get('dhat',''),noteA=a.get('note','')[:160],noteB=b.get('note','')[:160]))
n=len(IN)
w=csv.DictWriter(open('EV1_CMP_v3.tsv','w'),list(out[0]),delimiter='\t');w.writeheader();w.writerows(out)
for k in ['verdict','full','naw']: print(k,c[k],'/',n,'wilson',W(c[k],n))
print('agreed YES links',c['agreed_yes'])
ea=sum(all(v) for v in ev.values()); print('events fully agreed',ea,'/50',W(ea,50))
print(Counter(o['A'] for o in out if o['agree']).most_common())
for o in out:
    if not o['agree']: print(o['cand'],o['verb'],o['path'][:40],'|',o['A'],'|',o['B'])
