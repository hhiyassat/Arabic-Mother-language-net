"""الجولة 3، الأجزاء الثمانية المستبعدة (L002 L003 L005 L006 L008 L012 L016 L018): قاعدة إجماع الستّة (حكم المالك 2026-11-11 «Six-reader unanimity»).
لكلّ صفّ ثلاث قراءات مستقلّة بزوج أعمى جديد في كلّ مرّة (quarantine/ = الأولى، quarantine2/ = الثانية، Lc/ = الثالثة)، بالضابط BRIEF7.
الصفّ رابط إذا اتّفق كلّ زوج على صفّه، وكانت الصفوف الثلاثة واحدة (الحكم/الدور/الدلالة/المرتبة)، والحكم YES. لا عبرة بحدّ الجزء هنا.
نوع اللزوم: إن اختلف بين الأزواج كُتب مجموعاً بـ|. لفظ الذات: الأكثر بين القرّاء الستّة، وكلّ الألفاظ في dhat_readers.
ما سواه ← KHILAF4 (للمالك)؛ المجمع عليه بغير YES ← NEG4."""
import csv, os, subprocess, collections
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CH = 'L002 L003 L005 L006 L008 L012 L016 L018'.split()
CAN = {'محل': 'محلّ', 'تضمن': 'تضمّن', 'ذهني': 'ذهنيّ', 'عادي': 'عاديّ', 'عقلي': 'عقليّ', 'شرعي': 'شرعيّ'}
A = {r['cand']: r for r in csv.DictReader(open('LISAN_CAND.tsv'), delimiter='\t')}
os.makedirs('work/score4', exist_ok=True)
links, neg, kh, sc = [], [], [], []
for ch in CH:
    R = collections.defaultdict(list)
    for k, d in ((1, 'quarantine'), (2, 'quarantine2'), (3, 'Lc')):
        out = f'work/score4/{ch}_q{k}.tsv'
        subprocess.run(['python3', 'score5.py', f'Lc/{ch}_IN.tsv', f'{d}/{ch}_R1.tsv', f'{d}/{ch}_R2.tsv', out], check=True, capture_output=True)
        for r in csv.DictReader(open(out), delimiter='\t'): R[r['cand']].append(r)
    n = len(R); u = 0
    for cand, rs in R.items():
        a = A[cand]; ev = cand.split('#')[0]
        assert len(rs) == 3, cand
        unan = all(r['agree'] == '1' for r in rs) and len({r['A'] for r in rs}) == 1
        if unan and rs[0]['A'].startswith('YES'):
            u += 1
            _, role, dal, mar = [CAN.get(x, x) for x in rs[0]['A'].split('/')]
            naws = list(dict.fromkeys(CAN.get(r['naw'], r['naw']) for r in rs))
            words = [w for r in rs for w in (r['dhatA'], r['dhatB']) if w]
            top = collections.Counter(words).most_common(1)[0][0] if words else ''
            alts = [top] + [w for w in dict.fromkeys(words) if w != top]
            links.append(dict(event_id=ev, root=a['root'], verb=a['verb'], masdar=a['masdar'], lisan_root=a['lisan_root'], lisan_line=a['line'], form=a['form'],
                              role=role, dalala=dal, luzum_martaba=mar, luzum_naw='-' if dal == 'تضمّن' else '|'.join(naws),
                              dhat='|'.join(alts), dhat_votes=collections.Counter(words)[top], snippet=a['snippet'], cand=cand, chunk=ch,
                              noteA=rs[2]['noteA'], noteB=rs[2]['noteB']))
        elif unan:
            neg.append(dict(cand=cand, event_id=ev, chunk=ch, verdict=rs[0]['A']))
        else:
            kh.append(dict(chunk=ch, cand=cand, event_id=ev, root=a['root'], verb=a['verb'], lisan_line=a['line'],
                           pair1=f"{rs[0]['A']} || {rs[0]['B']}", pair2=f"{rs[1]['A']} || {rs[1]['B']}", pair3=f"{rs[2]['A']} || {rs[2]['B']}",
                           dhat=' / '.join(dict.fromkeys(w for r in rs for w in (r['dhatA'], r['dhatB']) if w)), snippet=a['snippet']))
    sc.append(dict(chunk=ch, rows=n, unanimous_yes=u))
def wr(name, rows):
    w = csv.DictWriter(open(name, 'w', encoding='utf-8', newline=''), list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)
wr('LINKS4.tsv', links); wr('KHILAF4.tsv', kh); wr('UNAN_SCORES4.tsv', sc)
if neg: wr('NEG4.tsv', neg)
print('rows', sum(s['rows'] for s in sc), 'links', len(links), 'events', len({l['event_id'] for l in links}), 'roots', len({l['root'] for l in links}),
      'neg', len(neg), 'khilaf', len(kh), 'dhat_differ', sum('|' in l['dhat'] for l in links), 'naw_differ', sum('|' in l['luzum_naw'] for l in links))
