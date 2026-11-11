"""يقيس كلّ جزء L له قارئان كاملان، ويطبع الحالة."""
import os,subprocess,glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
done=[];part=[];pend=[]
for f in sorted(glob.glob('Lc/L*_IN.tsv')):
    c=os.path.basename(f)[:4]; n=sum(1 for _ in open(f))-1
    r=[f'Lc/{c}_R{i}.tsv' for i in (1,2)]
    full=[os.path.exists(p) and sum(1 for _ in open(p))-1>=n for p in r]
    if all(full):
        done.append((c,subprocess.run(['python3','score5.py',f,r[0],r[1],f'Lc/{c}_CMP.tsv'],capture_output=True,text=True).stdout.strip()))
    elif any(os.path.exists(p) for p in r): part.append(c)
    else: pend.append(c)
for c,o in done: print(c,o)
print('done',len(done),'partial',part,'pending',pend)
