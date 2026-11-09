"""ملخّص نهائيّ: الروابط حسب الكتاب والدور والدلالة، وتغطية الجذور والأحداث."""
import csv
from collections import Counter
L=list(csv.DictReader(open('LINKS.tsv'),delimiter='\t'))
K=list(csv.DictReader(open('KHILAF.tsv'),delimiter='\t'))
A=list(csv.DictReader(open('ALL_CAND.tsv'),delimiter='\t'))
N=list(csv.DictReader(open('NOHIT.tsv'),delimiter='\t'))
roots_all=6003
rc={r['root'] for r in A}; rl={r['root'] for r in L}
ec={r['event_id'] for r in A}; el={r['event_id'] for r in L}
out=[]
out.append(f"links {len(L)} | khilaf rows {len(K)}")
out.append(f"events: candidates {len(ec)}, linked {len(el)}, no-hit {len(N)}")
out.append(f"roots: {roots_all} total, with candidates {len(rc)}, linked {len(rl)}")
out.append("by book: "+'; '.join(f'{b} {n}' for b,n in Counter(r['path'].split(' › ')[0] for r in L).most_common(15)))
out.append("by role/dalala: "+'; '.join(f'{a}/{b} {n}' for (a,b),n in Counter((r['role'],r['dalala']) for r in L).most_common(10)))
out.append("martaba: "+str(dict(Counter(r['luzum_martaba'] for r in L))))
open('SUMMARY.txt','w').write('\n'.join(out)+'\n'); print('\n'.join(out))
