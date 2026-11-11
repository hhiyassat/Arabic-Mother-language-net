"""يقيس كلّ جزء له قارئان، ويطبع حالة الأجزاء كلّها."""
import os,subprocess,glob,re
done=[];pend=[];part=[]
for f in sorted(glob.glob('round2/chunks/[KW]*_IN.tsv')):
    c=f.split('/')[-1][:4]
    r1,r2=f'round2/chunks/{c}_R1.tsv',f'round2/chunks/{c}_R2.tsv'
    n=sum(1 for _ in open(f))-1
    def full(p): return os.path.exists(p) and sum(1 for _ in open(p))-1>=n
    h1,h2=full(r1),full(r2)
    if not (h1 and h2) and os.path.exists(f'round2/chunks/{c}_CMP.tsv'): os.remove(f'round2/chunks/{c}_CMP.tsv')
    h1=h1 or os.path.exists(r1); h2=h2 or os.path.exists(r2)
    if not (full(r1) and full(r2)):
        if h1 or h2: part.append(c)
        else: pend.append(c)
        continue
    if h1 and h2:
        o=subprocess.run(['python3','score5.py',f,r1,r2,f'round2/chunks/{c}_CMP.tsv'],capture_output=True,text=True).stdout.strip()
        done.append((c,o))
    elif h1 or h2: part.append(c)
    else: pend.append(c)
for c,o in done: print(c,o)
print('done',len(done),'partial',part,'pending',len(pend), 'next', pend[:6])
