import json,re,csv,collections
exec(open('parse.py').read().split('E={}')[0])
E=json.load(open('lisan_entries.json'))
def flat(k): return k.replace('ء','ا').replace('ى','ي')
F={}
for k,v in E.items(): F.setdefault(flat(k),[]).extend(v)
def keys(r):
    r=flat(n(r)); out={r}
    if r.endswith('و'): out.add(r[:-1]+'ي'); out.add(r[:-1]+'ا')
    if r.endswith('ي'): out.add(r[:-1]+'و'); out.add(r[:-1]+'ا')
    return out
ev=[r for r in csv.DictReader(open('/Users/husseinhiyassat/arabic-net/HusseinFrameNet/06_handoff/ahdath_ajnas_v49/UNLINKED_EVENTS.tsv'),delimiter='\t') if r['status']=='NO_CANDIDATE']
def lookup(e):
    ks=[k for k in keys(e['root']) if k in F]; return ks
if __name__=='__main__':
    st=collections.Counter(); miss=[]
    for e in ev:
        ks=lookup(e)
        if not ks: st['absent']+=1; miss.append(e['root']); continue
        t=n(' '.join(b['text'] for k in ks for b in F[k])); v=n(e['verb']); m=n(e['masdar'])
        hit=(v and re.search(r'(^|\s|[وف])'+re.escape(v)+r'(\s|$|[ةتاوه])',t)) or (m and len(m)>2 and m in t)
        st['hit' if hit else 'root_only']+=1
    print(st); print(miss[:80])
