"""يقسم ALL_CAND.tsv إلى أجزاء بحجم N صفّ تقريباً دون شطر حدث؛ يتخطّى أحداث الدفعة 1 والتجربة 2."""
import csv,sys,json,os
N=int(sys.argv[1]) if len(sys.argv)>1 else 250
R=list(csv.DictReader(open('ALL_CAND.tsv'),delimiter='\t'))
os.makedirs('chunks',exist_ok=True)
cur=[];k=0;last=None
def flush():
    global cur,k
    if not cur: return
    w=csv.DictWriter(open(f'chunks/C{k:03d}_IN.tsv','w',encoding='utf-8',newline=''),list(cur[0]),delimiter='\t');w.writeheader();w.writerows(cur)
    k+=1;cur=[]
for r in R:
    if r['event_id']!=last and len(cur)>=N: flush()
    last=r['event_id']
    cur.append(dict(cand=f"{r['event_id']}#{r['rank']}",root=r['root'],verb=r['verb'],masdar=r['masdar'],hits=r['hits'],path=r['path'],snippet=r['snippet']))
flush(); print('chunks',k)
