import pickle,re,os,csv,collections,math
SP=os.path.dirname(os.path.abspath(__file__))
IDX=pickle.load(open(SP+'/lexidx.pkl','rb'))
HAR=re.compile(r'[ً-ْٰـ]')
def bare(s): return re.sub('[أإآ]','ا',HAR.sub('',(s or '').replace('ٱ','ا'))).strip()
EQ={'ء':'ءاأإآؤئى','و':'واى','ي':'يىاو'}
def fits(K,w):
    # radicals in order as a subsequence; weak/hamza radicals may vary or drop; geminate last may drop
    i=0; w=w.replace('ة','ت')
    for j,ch in enumerate(K):
        alts=EQ.get(ch,ch)
        while i<len(w) and w[i] not in alts: i+=1
        if i<len(w): i+=1; continue
        if ch in 'وي' or (j>0 and K[j]==K[j-1]) or ch=='ء': continue
        return False
    return True
def forms(w):
    w=bare(w); out=[w]
    if w.startswith('ال') and len(w)>4: out.append(w[2:])
    return out
def route(word):
    cand=collections.Counter()
    for f in forms(word):
        for K,lx in IDX.get(f,{}).items():
            if fits(K,f): cand[K]=max(cand[K],len(lx))
    if not cand: return None,'NO_ATTEST'
    top=cand.most_common(2)
    if len(top)>1 and top[0][1]==top[1][1]: return None,'TIE'
    if top[0][1]<2: return None,'ONE_LEX'
    return top[0][0],'OK'
def wilson(k,n,z=1.96):
    if n==0: return 0
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); a=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return (c-a)/d
if __name__=='__main__':
    rows=list(csv.DictReader(open(SP+'/wn_vs_hfn.tsv',encoding='utf-8'),delimiter='\t'))
    c=collections.Counter(); seen=set()
    for r in rows:
        if r['status']!='AGREE' and r['status']!='AGREE_AFTER_FORMAT': continue
        if r['word'] in seen: continue
        seen.add(r['word']); K,st=route(r['word'])
        c[st]+=1
        if K: c['hit' if K==r['mapped_K'] else 'miss']+=1
    print('vs WN∧HFN agreeing words (silver):',dict(c),'precision',c['hit']/(c['hit']+c['miss']),'wilson',wilson(c['hit'],c['hit']+c['miss']))
