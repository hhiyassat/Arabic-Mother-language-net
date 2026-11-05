#!/usr/bin/env python3
"""build_tahayyuz.py — طبقة التحيّز المكاني لأسماء الشجرة (CANDIDATE، لا حكم إلا بالمالك)

الأصناف (مأخوذة من نصّ سيبويه، لا من WordNet):
  MUTAHAYYIZ      ذاتٌ لها جثّة          «والأماكن لها جثة» (الكتاب 1/36)
    subtype=MAKAN   مكانٌ مختصّ           «تكون منها خِلقٌ لا يكون لكل مكان … كالجبل والوادي والبحر» (1/36) ؛ «أشياء لا تزول» (الكتاب، باب التثنية)
  HAYYIZ_MUBHAM   حيّزٌ مبهم نسبيّ        «ظروفٌ فيها الأشياء وتكون فيها … خلفك وقدامك وأمامك وتحتك وقبالتك» (1/403) ؛ ومقادير المسافة «ذهبت فرسخين وسرت الميلين» (1/35)
  MANA            معنى لا جثّة له         المصدر «هو الحدث» (1/35) ، وما ليس بذات
  ZAMAN           زمان                    «وإنما الدهر مضيّ الليل والنهار فهو إلى الفعل أقرب» (1/36)
  DEFER           لم يُحسم بمسلك مقيس ≥ 78%

المسالك (كلها تُقاس على GOLD_TAHAYYUZ_v1.tsv قبل أن تُطبَّق):
  L_SIB   قائمة سيبويه المغلقة لظروف المكان + نقاط الجهات + وحدات الطول (PWN linear_unit)
  L_LEX   باب WordNet الإنجليزي (lexname) — قرينة لا حكم؛ يُقبل الباب إن بلغت دقّته على الذهب ≥ 78%
  L_HEAD  رأس التعريف العربي (أول كلمة في gloss_ar) — قائمة مغلقة
  الترجيح: L_SIB أولاً ؛ ثم L_LEX المقبول ما لم يعارضه L_HEAD ؛ فإن تعارضا → DEFER ؛ والباب المحجوب يُحسم بـ L_HEAD وحده إن وُجد، وإلا DEFER.

python3 -B build_tahayyuz.py measure      يقيس المسالك على الذهب ويطبع الجداول
python3 -B build_tahayyuz.py build        يكتب data/wordnet/wordnet_tahayyuz.json + META
"""
import sys, os, json, csv, re, hashlib, collections, datetime
from nltk.corpus import wordnet as wn

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SYN = os.path.join(REPO, 'data', 'wordnet', 'wordnet_synsets.json')
GOLD = os.path.join(HERE, 'GOLD_TAHAYYUZ_v1.tsv')
OUT = os.path.join(REPO, 'data', 'wordnet', 'wordnet_tahayyuz.json')
HFN_LU = os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v36/lexical_units.csv')
THRESH = 0.78

DI = re.compile('[ً-ْٰـ]')
def bare(s): return DI.sub('', (s or '')).strip()

# ── L_SIB: قائمة سيبويه المغلقة (الكتاب 1/403–405 و 1/418–419) ─────────────────────────
# «خلفك وقدامك وأمامك وتحتك وقبالتك … ناحية … نحوك … ذات اليمين وشرقي كذا … يمينا ويسارا وشمالا»
# «خلف وأمام وقدام ووراء وفوق وتحت وعند … ومع وعلى … وعن … وقبالة ومكانك ودون … وإزاء وحذاء»
SIB_ZURUF = {'خلف','قدام','أمام','امام','تحت','فوق','وراء','قبالة','ناحية','نحو','يمين','يسار','شمال',
             'عند','دون','إزاء','ازاء','حذاء','جنب','جانب','مكان'}
SIB_CITE = 'سيبويه، الكتاب 1/403–405 (باب ما ينتصب من الأماكن والوقت) و1/418–419'
# الجهات: «شرقيَّ كذا» (1/404) — تُعرف بأب PWN compass_point / direction
COMPASS_ROOTS = {wn.synset('compass_point.n.01'), wn.synset('direction.n.02')}
LINEAR_UNIT = wn.synset('linear_unit.n.01')       # «ذهبت فرسخين وسرت الميلين» (1/35)
AREA_UNIT = wn.synset('area_unit.n.01')           # قياسٌ على المسافة — غير منصوص → DEFER
# موانع (DEFER بلا ترجيح — مسألة للمالك):
TAXON = wn.synset('taxonomic_group.n.01')          # الجنس/الفصيلة في التصنيف: كلّيٌّ لا جثّة له بعينه
SPIRIT = wn.synset('spiritual_being.n.01')         # الآلهة والكائنات الغيبية والأسطورية: لا يُحكم فيها بالتحيّز آلياً

def ancestors(s):
    seen = set(); st = [s]
    while st:
        x = st.pop()
        for h in x.hypernyms() + x.instance_hypernyms():
            if h not in seen: seen.add(h); st.append(h)
    return seen

# ── L_LEX: باب WordNet → صنف مرشَّح ───────────────────────────────────────────────
LEX_MAP = {
  'noun.animal':'MUTAHAYYIZ','noun.artifact':'MUTAHAYYIZ','noun.body':'MUTAHAYYIZ','noun.food':'MUTAHAYYIZ',
  'noun.object':'MUTAHAYYIZ','noun.plant':'MUTAHAYYIZ','noun.substance':'MUTAHAYYIZ','noun.person':'MUTAHAYYIZ',
  'noun.location':'MUTAHAYYIZ',
  'noun.act':'MANA','noun.attribute':'MANA','noun.cognition':'MANA','noun.communication':'MANA','noun.event':'MANA',
  'noun.feeling':'MANA','noun.motive':'MANA','noun.process':'MANA','noun.quantity':'MANA','noun.relation':'MANA',
  'noun.shape':'MANA','noun.state':'MANA','noun.phenomenon':'MANA','noun.possession':'MANA',
  'noun.time':'ZAMAN',
  'noun.group':None,'noun.Tops':None,
}
PLACE_LEX = {'noun.location'}
# نصّ سيبويه يعدّ هذه أماكن مختصّة: «كالجبل والوادي والبحر» (1/36) ، «ذهبت الشام … دخلت البيت» (1/35) ، «الأماكن والجبال أشياء لا تزول»
PLACE_ANC = {wn.synset('geological_formation.n.01'), wn.synset('body_of_water.n.01'), wn.synset('building.n.01'),
             wn.synset('room.n.01'), wn.synset('land.n.04')}

# ── L_HEAD: رأس التعريف العربي (قائمة مغلقة) ──────────────────────────────────────
H_PLACE = {'مدينة','بلدة','منطقة','مكان','عاصمة','نهر','بحيرة','جزيرة','جبل','دولة','جمهورية','مساحة','أرض','قرية',
           'ميناء','إقليم','ولاية','مقاطعة','بلد','وادي','واد','صحراء','خليج','مضيق','سهل','هضبة','شبه','غابة','ساحل','حي','مملكة'}
H_DHAT = {'شخص','نبات','شجرة','شجيرة','جهاز','أداة','عضو','عشب','عشبة','مادة','مواطن','قطعة','رجل','كاتب','طائر','امرأة',
          'سمكة','قماش','فطر','آلة','حمض','فرد','لحم','سرخس','دواء','معدن','غطاء','ورقة','هيكل','كتلة','سبيكة','سائل',
          'غشاء','جسم','وريد','شريان','عضلة','بخار','رياح','مكسرات','عملة','طعام','مشروب','حيوان','حشرة','ثمرة','بذرة',
          'حجر','صخر','صخرة','مبنى','بيت','غاز','ملح','زهرة','فاكهة','خبز','كائن','طفل','لاعب','طبيب','ملك','عالم?',
          'قارب','سفينة','سلاح','بندقية','ثوب','حذاء','وعاء','إناء','صندوق','عظم','عظمة','خلية','بكتيريا','فيروس','دودة',
          'زواحف','ثعبان','حبل','خيط','لوح','أنبوب','قناة','مركبة','سيارة','طائرة','ملابس','لباس','كعكة','حلوى','جبن',
          'نسيج','ألياف','بروتين','إنزيم','هرمون','مركب','عنصر','سلاح','جندي','ضابط','عامل','موظف','فنان','شاعر','فيلسوف',
          'رسام','مؤلف','قائد','سياسي','رئيس','أمير','نبي','قديس'}
H_DHAT.discard('عالم?')
H_MANA = {'فعل','حالة','عملية','صفة','خاصية','شكل','شعور','دافع','علاقة','العلاقة','عدد','العدد','زاوية','الزاوية','مقياس',
          'حق','عاطفة','انتقال','علم','هوس','طريقة','كمية','رغبة','ألم','تفاعل','سمة','مرض','التهاب','لغة','لعبة','عدم',
          'حركة','نشاط','مصطلح','منصب','نظام','فن','قدرة','مهارة','معرفة','فكرة','مبدأ','نظرية','مذهب','اعتقاد','حدث',
          'تغيير','تغير','زيادة','نقص','انخفاض','ارتفاع','إنتاج','استخدام','نسبة','درجة','مستوى','قانون','قاعدة','عقيدة',
          'خوف','حب','غضب','حزن','فرح','موقف','وضع','قوة','طاقة','إشارة','رسالة','كلام','كلمة','عبارة','جملة','اسم',
          'قصة','حكاية','أغنية','موسيقى','تعبير','وصف','تقدير','حكم','خطأ','جريمة','حرب','معركة','سباق','مباراة','رياضة',
          'ضريبة','دين','مبلغ','سعر','ثمن','أجر','راتب','ربح','خسارة','عقد','اتفاق','اتفاقية','حساب','ممارسة','فترة?'}
H_MANA.discard('فترة?')
H_ZAMAN = {'الشهر','شهر','الفترة','فترة','يوم','اليوم','سنة','السنة','عصر','العصر','قرن','القرن','ليلة','موسم','الوقت','وقت',
           'عيد','عشية','الساعة','دقيقة','ثانية','أسبوع','عقد?'}
H_ZAMAN.discard('عقد?')

def gloss_head(g):
    g = bare(g); g = re.sub(r'^\([^)]*\)\s*', '', g)
    w = g.split()
    return w[0].strip('،؛:.') if w else ''

def head_class(g):
    h = gloss_head(g)
    if h in H_PLACE: return ('MUTAHAYYIZ', 'MAKAN', h)
    if h in H_DHAT:  return ('MUTAHAYYIZ', None, h)
    if h in H_ZAMAN: return ('ZAMAN', None, h)
    if h in H_MANA:  return ('MANA', None, h)
    return (None, None, h)

# مراجعة يدوية لكل ما أصابته القائمة المغلقة (2026-11-05): المقبول حيّزاً مبهماً نسبياً، والمردود إلى مسلكه
SIB_HAND_ACCEPT = {'hand.n.05','north.n.04','presence.n.02','rearward.n.01','north.n.05','left.n.01','location.n.01','north.n.03',
                   'north.n.06','place.n.04','position.n.01','right.n.02','side.n.01','somewhere.n.01','vicinity.n.01','northland.n.01'}
# أجزاء الذات (مؤخّرة، مقدّمة، وجه) وأماكن مختصّة ومؤسسات — تُردّ إلى L_LEX
SIB_HAND_REJECT = {'back.n.03','front.n.09','place.n.02','rear.n.02','scene.n.01','seat.n.01','side.n.04','site.n.01','space.n.03',
                   'topographic_point.n.01','township.n.01','north.n.01','union.n.02','district.n.01','home.n.01','side.n.07'}
# علاقات وهيئات تحت direction.n.02 ليست جهة: تقابل، تعامد، تماثل، وضعية → معنى
JIHA_HAND_MANA = {'antipodal.n.01','attitude.n.04','enantiomorphism.n.01','horizontal.n.01','vertical.n.01','orthogonality.n.01',
                  'trim.n.03','orientation.n.03'}

def sib_class(x, s):
    if x['id'] in JIHA_HAND_MANA:
        return ('MANA', None, 'L_SIB_HAND:هيئة/علاقة لا جهة')
    words = {bare(w) for w in x['words_ar']}
    words |= {w[2:] for w in words if w.startswith('ال')}
    lx = s.lexname()
    hit = sorted(words & SIB_ZURUF)
    if x['id'] in SIB_HAND_ACCEPT:
        return ('HAYYIZ_MUBHAM', 'ZARF', 'L_SIB_HAND:' + '،'.join(hit))
    if hit and x['id'] not in SIB_HAND_REJECT and lx in ('noun.location', 'noun.relation', 'noun.Tops', 'noun.object'):
        return ('DEFER', 'ZARF_UNREVIEWED', 'L_SIB:' + '،'.join(hit) + ' (لم يُراجَع يدوياً)')
    anc = ancestors(s) | {s}
    if anc & COMPASS_ROOTS:
        return ('HAYYIZ_MUBHAM', 'JIHA', 'L_SIB:compass_point')
    if LINEAR_UNIT in anc:
        return ('HAYYIZ_MUBHAM', 'MIQDAR_MASAFA', 'L_SIB:linear_unit')
    if AREA_UNIT in anc:
        return ('DEFER', 'MIQDAR_MISAHA', 'L_SIB:area_unit (قياس على المسافة غير منصوص)')
    if TAXON in anc:
        return ('DEFER', 'TAXON', 'MANI:taxonomic_group — الجنس كلّي')
    if SPIRIT in anc:
        return ('DEFER', 'GHAYB', 'MANI:spiritual_being — غيبي/أسطوري')
    return None

def load_masadir():
    out = set()
    if os.path.exists(HFN_LU):
        for r in csv.DictReader(open(HFN_LU, encoding='utf-8')):
            if r['pos_ar'] == 'مصدر': out.add(r['lemma'].strip())
    return out

GOLD_MAP = {'D':'MUTAHAYYIZ','P':'MUTAHAYYIZ','M':'HAYYIZ_MUBHAM','N':'MANA','Z':'ZAMAN','U':'U'}

def signals(x):
    s = wn.synset(x['id'])
    lx = s.lexname()
    return s, lx, sib_class(x, s), LEX_MAP.get(lx), head_class(x.get('gloss_ar', ''))

def measure(syn):
    gold = list(csv.DictReader(open(GOLD, encoding='utf-8'), delimiter='\t'))
    # 1) per-lexname precision of L_LEX
    by = collections.defaultdict(lambda: [0, 0, 0])   # ok, n(non-U), U
    for g in gold:
        cls = GOLD_MAP[g['judgement']]
        lxc = LEX_MAP.get(g['lexname'])
        b = by[g['lexname']]
        if cls == 'U': b[2] += 1
        b[1] += 1
        if lxc and cls == lxc: b[0] += 1
    lex_prec = {}
    for lx, (ok, n, u) in sorted(by.items()):
        p = ok / n if n else 0
        lex_prec[lx] = (ok, n, p)
    # 2) L_HEAD precision (where it fires)
    hd = collections.Counter(); hd_ok = collections.Counter()
    sib = []
    for g in gold:
        x = syn[g['id']]; s, lx, sb, lc, hc = signals(x)
        cls = GOLD_MAP[g['judgement']]
        if sb: sib.append((g['i'], g['id'], sb[0], cls))
        if hc[0]:
            hd[hc[0]] += 1
            if hc[0] == cls: hd_ok[hc[0]] += 1
    return lex_prec, hd, hd_ok, sib, gold

def decide(x, lex_ok):
    s, lx, sb, lc, hc = signals(x)
    ev = {'lexname': lx, 'gloss_head': hc[2]}
    if sb:
        return sb[0], sb[1], 'L_SIB', sb[2], ev
    if lc and lex_ok.get(lx):
        if hc[0] and hc[0] != lc:
            return 'DEFER', None, 'CONFLICT', f'L_LEX={lc} ≠ L_HEAD={hc[0]}({hc[2]})', ev
        sub = None
        if lc == 'MUTAHAYYIZ' and (lx in PLACE_LEX or hc[1] == 'MAKAN' or (ancestors(s) & PLACE_ANC)):
            sub = 'MAKAN'
        return lc, sub, 'L_LEX' + ('+L_HEAD' if hc[0] == lc else ''), lx, ev
    if hc[0]:
        return hc[0], hc[1], 'L_HEAD', hc[2], ev
    return 'DEFER', None, 'NO_ACCEPTED_SIGNAL', lx, ev

def wilson_low(ok, n, z=1.96):
    if n == 0: return 0.0
    p = ok / n; d = 1 + z*z/n
    return (p + z*z/(2*n) - z*((p*(1-p)+z*z/(4*n))/n) ** 0.5) / d

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'measure'
    syn = {x['id']: x for x in json.load(open(SYN, encoding='utf-8'))['synsets'] if x['pos'] == 'n'}
    lex_prec, hd, hd_ok, sib, gold = measure(syn)
    lex_ok = {lx: (p >= THRESH) for lx, (ok, n, p) in lex_prec.items() if LEX_MAP.get(lx)}
    print('== L_LEX precision on gold (U counts as wrong)')
    for lx, (ok, n, p) in lex_prec.items():
        print(f'  {lx:22s} {LEX_MAP.get(lx) or "-":12s} {ok:>2}/{n:<2} {p:.3f}  wilson95_low={wilson_low(ok,n):.3f}  {"ACCEPT" if lex_ok.get(lx) else "BLOCK"}')
    print('== L_HEAD precision on gold (where it fires)')
    for c in hd: print(f'  {c:14s} {hd_ok[c]}/{hd[c]} {hd_ok[c]/hd[c]:.3f}')
    print('== L_SIB hits in gold'); [print('  ', t) for t in sib]
    # decision precision on gold (end-to-end)
    ok = n = dfr = 0; errs = []
    for g in gold:
        cls = GOLD_MAP[g['judgement']]
        c, sub, how, why, ev = decide(syn[g['id']], lex_ok)
        if c == 'DEFER': dfr += 1; continue
        n += 1
        if c == cls: ok += 1
        else: errs.append((g['i'], g['id'], c, how, cls))
    print(f'== END-TO-END on gold: decided {n}, correct {ok} ({ok/n:.3f}, wilson_low {wilson_low(ok,n):.3f}), DEFER {dfr}')
    for e in errs: print('   ERR', e)
    # held-out validation (unseen while building the lists)
    VAL = os.path.join(HERE, 'VALIDATION_TAHAYYUZ_v1.tsv')
    val = list(csv.DictReader(open(VAL, encoding='utf-8'), delimiter='\t'))
    vok = vn = vdf = 0; verrs = []; vroute = collections.defaultdict(lambda: [0, 0])
    for g in val:
        cls = GOLD_MAP[g['judgement']]
        c, sub, how, why, ev = decide(syn[g['id']], lex_ok)
        if c == 'DEFER': vdf += 1; continue
        vn += 1; vroute[how][1] += 1
        if c == cls: vok += 1; vroute[how][0] += 1
        else: verrs.append((g['i'], g['id'], c, how, cls))
    print(f'== HELD-OUT VALIDATION: decided {vn}/{len(val)}, correct {vok} ({vok/vn:.3f}, wilson_low {wilson_low(vok,vn):.3f}), DEFER {vdf}')
    for k, (a, b) in vroute.items(): print(f'   route {k:16s} {a}/{b}')
    for e in verrs: print('   VERR', e)
    validation = {'n': len(val), 'decided': vn, 'correct': vok, 'precision': round(vok/vn, 3), 'wilson95_low': round(wilson_low(vok, vn), 3),
                  'deferred': vdf, 'by_route': {k: {'ok': a, 'n': b} for k, (a, b) in vroute.items()}, 'sha256': sha(VAL)}
    if mode != 'build': return
    out = {}; cnt = collections.Counter(); how_c = collections.Counter(); sub_c = collections.Counter(); masdar_dhat = []
    for sid, x in syn.items():
        c, sub, how, why, ev = decide(x, lex_ok)
        rec = {'class': c, 'subtype': sub, 'route': how, 'why': why, 'lexname': ev['lexname'], 'gloss_head': ev['gloss_head'],
               'status': 'CANDIDATE', 'is_fact': False}
        out[sid] = rec; cnt[c] += 1; how_c[how] += 1; sub_c[(c, sub)] += 1
    meta = {
        'file': 'wordnet_tahayyuz.json', 'built': datetime.date.today().isoformat(), 'builder': 'tahayyuz/build_tahayyuz.py',
        'derived_from': 'wordnet_synsets.json', 'derived_from_sha256': sha(SYN),
        'gold': 'tahayyuz/GOLD_TAHAYYUZ_v1.tsv', 'gold_sha256': sha(GOLD), 'gold_judged_by': 'agent (Claude), blind to lexname — OWNER REVIEW PENDING',
        'threshold': THRESH, 'classes_source': 'سيبويه، الكتاب 1/35–36 ، 1/403–405 ، 1/418–419',
        'counts': dict(cnt), 'routes': dict(how_c), 'subtypes': {f'{a}/{b}': v for (a, b), v in sub_c.items()},
        'masdar_naming_dhat': 'DROPPED — vowelled-masdar match measured ~5/25 on sample; most hits come from D-01 L2 vowelling errors (see REPORT)',
        'lex_precision': {lx: {'ok': ok_, 'n': n_, 'p': round(p_, 3), 'accepted': bool(lex_ok.get(lx))} for lx, (ok_, n_, p_) in lex_prec.items()},
        'validation_heldout': validation,
        'gold_end_to_end': {'decided': n, 'correct': ok, 'note': 'in-sample — head lists were read against this gold; use validation_heldout'},
        'status': 'CANDIDATE — لا اعتماد إلا بحكم المالك', 'source_file_untouched': True,
    }
    json.dump({'_meta': meta, 'synsets': out}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    meta['sha256'] = sha(OUT)
    json.dump(meta, open(OUT.replace('.json', '.META.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1)[:3000])

if __name__ == '__main__':
    main()
