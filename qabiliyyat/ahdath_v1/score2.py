import csv,sys
from math import sqrt
from collections import Counter
IN=list(csv.DictReader(open('EV1_IN.tsv'),delimiter='\t'))
P={r['cand']:r['path'] for r in IN}; V={r['eid']:(r['verb'],r['masdar']) for r in IN}
def rd(f): return {r['eid'].strip():r for r in csv.DictReader(open(f),delimiter='\t')}
A,B=rd(sys.argv[1]),rd(sys.argv[2]); tag=sys.argv[3]
def ps(x): return tuple(p.strip() for p in x.replace('،',',').split(',') if p.strip())
def nz(x): x=(x or '').strip(); return '-' if x in ('','-','—') else x
def W(x,n=50,z=1.96):
    p=x/n; return round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3)
c=Counter(); out=[]
for e in sorted(V):
    a,b=A.get(e,{}),B.get(e,{})
    pa,pb=ps(a.get('pick','')),ps(b.get('pick',''))
    ra,rb=ps(a.get('role','')),ps(b.get('role',''))
    pick=set(pa)==set(pb)
    role=pick and dict(zip(pa,ra))==dict(zip(pb,rb))
    da=(nz(a.get('dalala')),nz(a.get('luzum_martaba'))); db=(nz(b.get('dalala')),nz(b.get('luzum_martaba')))
    na,nb=nz(a.get('luzum_naw')),nz(b.get('luzum_naw'))
    special=pa in [('NONE',),('OTHER_SENSE',)]
    dal=pick and (special or da==db)
    full=pick and (special or (role and da==db))
    c['pick']+=pick; c['role']+=role or (pick and special); c['dal']+=dal; c['full']+=full; c['naw']+=full and (special or na==nb)
    out.append(dict(eid=e,verb=V[e][0],pick=pick,full=full,A=','.join(pa),B=','.join(pb),roleA=','.join(ra),roleB=','.join(rb),
      dalA='/'.join(da)+'/'+na,dalB='/'.join(db)+'/'+nb,noteA=a.get('note','')[:160],noteB=b.get('note','')[:160]))
w=csv.DictWriter(open(f'EV1_CMP_{tag}.tsv','w'),list(out[0]),delimiter='\t');w.writeheader();w.writerows(out)
for k in ['pick','role','dal','full','naw']: print(k,c[k],'/50 wilson',W(c[k]))
for o in out:
    if not o['full']: print(o['eid'],o['verb'],'|',o['A'],o['roleA'],o['dalA'],'|',o['B'],o['roleB'],o['dalB'])
