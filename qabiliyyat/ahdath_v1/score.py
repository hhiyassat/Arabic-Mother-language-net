import csv,json
from collections import Counter
from math import sqrt
IN=list(csv.DictReader(open('EV1_IN.tsv'),delimiter='\t'))
P={r['cand']:r['path'] for r in IN}; V={r['eid']:(r['verb'],r['masdar']) for r in IN}
def rd(f): return {r['eid'].strip():r for r in csv.DictReader(open(f),delimiter='\t')}
R1,R2=rd('R1.tsv'),rd('R2.tsv')
def ps(x): return frozenset(p.strip() for p in x.replace('،',',').split(',') if p.strip())
def book(c): return P[c].split(' › ')[0] if c in P else c
c=Counter(); out=[]
for e in sorted(V):
    a,b=R1.get(e,{}),R2.get(e,{})
    pa,pb=ps(a.get('pick','?')),ps(b.get('pick','?'))
    if pa==pb: k='same'
    elif pa&pb: k='overlap'
    elif {book(x) for x in pa}=={book(x) for x in pb}: k='same_book'
    else: k='differ'
    da=(a.get('dalala','').strip(),a.get('luzum_martaba','').strip()); db=(b.get('dalala','').strip(),b.get('luzum_martaba','').strip())
    c[k]+=1
    out.append(dict(eid=e,verb=V[e][0],masdar=V[e][1],agree=k,R1=','.join(sorted(pa)),R2=','.join(sorted(pb)),
       books=' | '.join(sorted({book(x) for x in pa|pb})),role1=a.get('role',''),role2=b.get('role',''),dal1='/'.join(da),dal2='/'.join(db),
       note1=a.get('note','')[:140],note2=b.get('note','')[:140]))
w=csv.DictWriter(open('EV1_CMP.tsv','w'),list(out[0]),delimiter='\t');w.writeheader();w.writerows(out)
print(c)
cat=Counter()
for o in out:
    if o['agree']=='same':
        p=o['R1']; cat['NONE' if p=='NONE' else 'OTHER' if p=='OTHER_SENSE' else 'genus']+=1
print('agreed kinds',cat)
n=50;x=c['same'];z=1.96;p=x/n;print('wilson',round((p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),3))
for o in out: print(o['eid'],o['verb'],o['agree'],'|',o['R1'],'|',o['R2'],'|',o['books'][:60],'|',o['role1'],'/',o['role2'],'|',o['dal1'],'/',o['dal2'])
