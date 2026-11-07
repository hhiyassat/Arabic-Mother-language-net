#!/usr/bin/env python3
"""Measure what moving AMLN's layers from HusseinFrameNet release_v36 to the newest release changes (owner 2026-11-08: «نقل الطبقات
التي تقرأ HFN v36 إلى v45»). Nothing in the repo is written: each layer is run in a temp copy, once per release (AMLN_HFN_RELEASE),
and the outputs are compared row by row (key = route + event_id, or the file's first column).

Layers: qabiliyyat/measure_routes.py extract (candidates_*.tsv) → ahdath/ahdath.py build (rules_R1.tsv, pool_R2.tsv) and r2w
(pool_R2_v3.tsv), and tahayyuz/build_tahayyuz.py (class per synset). Random samples written by those commands are ignored here: the
gold samples are kept as measured (their event ids are checked against the new release instead).
A change is classed WASL_ONLY when replacing ٱ by ا makes the two rows equal (HFN v44 wrote همزة الوصل as in the Mushaf).
Usage: python3 audit/hfn_v45_migration/measure.py [old=release_v36] [new=newest]  → audit/hfn_v45_migration/REPORT.tsv + stdout"""
import csv, json, os, shutil, subprocess, sys, tempfile, collections
HERE = os.path.dirname(os.path.abspath(__file__)); AMLN = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, AMLN)
from hfn_release import hfn_release_dir
OLD = sys.argv[1] if len(sys.argv) > 1 else 'release_v36'
NEW = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(hfn_release_dir())
RUNNER = r'''
import os, sys, json, importlib.util
tmp, amln = sys.argv[1], sys.argv[2]
sys.path.insert(0, amln)
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
q = load('mr', os.path.join(tmp, 'qabiliyyat', 'measure_routes.py')); q.HERE = os.path.join(tmp, 'qabiliyyat'); q.extract()
a = load('ah', os.path.join(tmp, 'ahdath', 'ahdath.py')); a.HERE = os.path.join(tmp, 'ahdath')
a.R1_FILE = os.path.join(tmp, 'qabiliyyat', 'candidates_R1_MUTAWAA.tsv'); a.build(); a.build_r2_wasit()
t = load('th', os.path.join(tmp, 'tahayyuz', 'build_tahayyuz.py')); t.OUT = os.path.join(tmp, 'tahayyuz_out.json'); t.SYN = os.path.join(amln, 'data', 'wordnet', 'wordnet_synsets.json'); t.main.__globals__['SYN'] = t.SYN; t.main.__globals__['OUT'] = t.OUT; t.main.__globals__['sys'].argv = ['x', 'build']; t.main()
'''
def run(rel):
    tmp = tempfile.mkdtemp(prefix='v45mig_')
    for d in ('qabiliyyat', 'ahdath', 'tahayyuz'):
        shutil.copytree(os.path.join(AMLN, d), os.path.join(tmp, d))
    open(os.path.join(tmp, 'runner.py'), 'w').write(RUNNER)
    env = dict(os.environ, AMLN_HFN_RELEASE=rel)
    p = subprocess.run([sys.executable, os.path.join(tmp, 'runner.py'), tmp, AMLN], env=env, capture_output=True, text=True, cwd=tmp)
    if p.returncode: sys.exit(rel + ' failed:\n' + p.stderr[-3000:])
    return tmp
def rows(p, key):
    R = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    return {key(r): r for r in R}
def cmp(a, b):
    c = collections.Counter(); ex = []
    for k in set(a) | set(b):
        if k not in a: c['added'] += 1; ex.append(('added', k)); continue
        if k not in b: c['removed'] += 1; ex.append(('removed', k)); continue
        if a[k] == b[k]: c['same'] += 1; continue
        if {x: (v or '').replace('ٱ', 'ا') for x, v in a[k].items()} == {x: (v or '').replace('ٱ', 'ا') for x, v in b[k].items()}:
            c['wasl_only'] += 1; continue
        cols = sorted(x for x in a[k] if a[k].get(x) != b[k].get(x)); c['changed:' + ','.join(cols)] += 1; ex.append(('changed', k, cols))
    return c, ex
o, n = run(OLD), run(NEW)
out = []
files = [('qabiliyyat', f) for f in sorted(os.listdir(os.path.join(o, 'qabiliyyat'))) if f.startswith('candidates_')] + \
        [('ahdath', f) for f in ('rules_R1.tsv', 'pool_R2.tsv', 'pool_R2_v3.tsv')]
for d, f in files:
    first = next(csv.reader(open(os.path.join(o, d, f), encoding='utf-8'), delimiter='\t'))
    key = (lambda r: (r.get('route', ''), r['event_id'])) if 'event_id' in first else (lambda r, c=first[0]: r[c])
    c, ex = cmp(rows(os.path.join(o, d, f), key), rows(os.path.join(n, d, f), key))
    out.append({'file': f'{d}/{f}', **{k: v for k, v in c.items()}, 'examples': json.dumps(ex[:8], ensure_ascii=False)})
    print(f'{d}/{f}', dict(c))
to, tn = (json.load(open(os.path.join(x, 'tahayyuz_out.json')))['synsets'] for x in (o, n))
tc = collections.Counter('same' if to[k]['class'] == tn.get(k, {}).get('class') else 'class_changed' for k in to)
print('tahayyuz', dict(tc)); out.append({'file': 'tahayyuz/wordnet_tahayyuz.json', **tc, 'examples': json.dumps([k for k in to if to[k]['class'] != tn.get(k, {}).get('class')][:10])})
# gold/sample event ids still live in the new release?
ev = {e['event_id']: e for e in csv.DictReader(open(os.path.join(os.path.dirname(hfn_release_dir()), NEW, 'events.csv'), encoding='utf-8'))}
for d in ('ahdath', 'qabiliyyat'):
    for f in sorted(os.listdir(os.path.join(AMLN, d))):
        if (f.startswith('gold') or f.startswith('sample') or f.startswith('mutawaa_R1W_gold')) and f.endswith('.tsv'):
            R = list(csv.DictReader(open(os.path.join(AMLN, d, f), encoding='utf-8'), delimiter='\t'))
            if not R or 'event_id' not in R[0]: continue
            miss = [r['event_id'] for r in R if r['event_id'] not in ev or ev[r['event_id']]['event_review_v36'].startswith('WITHDRAWN')]
            out.append({'file': f'{d}/{f}', 'gold_rows': len(R), 'gold_events_missing_or_withdrawn': len(miss), 'examples': json.dumps(miss[:8])})
            print(f'{d}/{f}', 'rows', len(R), 'missing/withdrawn in', NEW, len(miss))
keys = sorted({k for r in out for k in r if k not in ('file', 'examples')})
with open(os.path.join(HERE, 'REPORT.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['file'] + keys + ['examples'], delimiter='\t'); w.writeheader(); w.writerows(out)
print('old', OLD, 'new', NEW, '→', os.path.join(HERE, 'REPORT.tsv'))
