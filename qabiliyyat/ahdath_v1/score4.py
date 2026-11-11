import csv,sys,re
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
def sl(x): x=nz(x); return {'NO_GLOSS'} if 'NO_GLOSS' in x else set(re.findall(r'\d+',x))
c=Counter(); out=[]; ev={}; sense={}
for r in IN:
    k=r['cand']; a,b=A.get(k,{}),B.get(k,{})
    ka,kb=key(a),key(b); f=ka==kb
    c['verdict']+=ka[0]==kb[0]; c['full']+=f
    anyyes='YES' in (ka[0],kb[0]); c['anyyes']+=anyyes; c['anyyes_ok']+=anyyes and f
    nonoth=not(ka[0]==kb[0]=='OTHER_SENSE'); c['nonoth']+=nonoth; c['nonoth_ok']+=nonoth and f
    if f and ka[0]=='YES': c['agreed_yes']+=1
    ev.setdefault(r['eid'],[]).append(f)
    sense.setdefault(r['eid'],(sl(a.get('sense')),sl(b.get('sense')),nz(a.get('sense_text'))[:60],nz(b.get('sense_text'))[:60]))
    out.append(dict(cand=k,verb=r['verb'],path=r['path'],agree=f,senseA=nz(a.get('sense')),senseB=nz(b.get('sense')),A='/'.join(ka),B='/'.join(kb),dhatA=a.get('dhat',''),dhatB=b.get('dhat',''),noteA=a.get('note','')[:160],noteB=b.get('note','')[:160]))
n=len(IN)
w=csv.DictWriter(open('EV1_CMP_v4.tsv','w'),list(out[0]),delimiter='\t');w.writeheader();w.writerows(out)
print('rows full',c['full'],'/',n,W(c['full'],n))
print('rows excl. both-OTHER',c['nonoth_ok'],'/',c['nonoth'],W(c['nonoth_ok'],c['nonoth']))
print('rows any YES',c['anyyes_ok'],'/',c['anyyes'],W(c['anyyes_ok'],c['anyyes']))
print('agreed YES links',c['agreed_yes'])
ea=sum(all(v) for v in ev.values()); print('events fully agreed',ea,'/50',W(ea,50))
same=sum(1 for a,b,_,_ in sense.values() if a==b); ov=sum(1 for a,b,_,_ in sense.values() if a&b)
print('sense same',same,'/50',W(same,50),'| overlap',ov,'/50',W(ov,50))
for e,(a,b,ta,tb) in sorted(sense.items()):
    if not a&b: print(' sense differ',e,sorted(a),ta,'|',sorted(b),tb)
print(Counter(o['A'] for o in out if o['agree']).most_common())
for o in out:
    if not o['agree']: print(o['cand'],o['verb'],o['path'][:36],'|',o['A'],'|',o['B'])
