# Arabic Mother Net — شجرة الأسماء

مشروع **تصحيح جذور الأسماء العربية** المبني على مقاييس اللغة لابن فارس.  
يُغطّي 70,909 كلمة بنسبة توثيق **97.2%** (68,922 كلمة مُعالجة بجذور من المقاييس).

## المتطلبات

- Python 3.9+
- مقاييس اللغة SQLite database: `maqayis_v2/maqayis.db` — جاهز من مشروع [Maqayis-roots](https://github.com/hhiyassat/Maqaiys-roots)

---

## الاستخدام السريع — تشغيل كامل

```bash
python -m engines.noun_root_corrector \
  --synmap  /path/to/arabic_synset_map.json \
  --db      /path/to/maqayis.db \
  --out     /path/to/arabic_synset_map_corrected.json \
  --report  /path/to/correction_report.json
```

المخرج: ملف JSON مصحَّح + تقرير إحصائي.

---

## API

### 1. تحميل فهرس المقاييس

```python
from engines.noun_root_corrector import load_maqayis_index

idx = load_maqayis_index("maqayis_v2/maqayis.db")
# idx.raw         → مجموعة الجذور الخام
# idx.normalized  → مجموعة الجذور المُطبَّعة
# idx.norm_to_raw → تطبيع → شكل أصلي
```

### 2. البحث عن جذر كلمة واحدة في المقاييس

```python
from engines.noun_root_corrector import lookup

result = lookup("كتب", idx)   # → "كتب"  (موجود)
result = lookup("كتاب", idx)  # → None   (غير موجود مباشرة، هذا ليس جذراً)
```

### 3. توليد مرشَّحات الجذر من كلمة

```python
from engines.noun_root_corrector import candidates_from_word

cands = candidates_from_word("المكتبة")
# → ["كتب", "كتب", ...]  قائمة مرشَّحات مرتَّبة من الأعلى احتمالاً
```

### 4. استخراج الجذر لمجموعة كلمات (synset)

```python
from engines.noun_root_corrector import extract_root_for_maqayis

root, status, source_word = extract_root_for_maqayis(
    words=["المكتبة", "library"],
    idx=idx,
)
# root        → "كتب"
# status      → "maqayis_verified" | "not_found" | "no_arabic"
# source_word → "المكتبة"
```

**حالات الحالة (status):**

| القيمة | المعنى |
|---|---|
| `maqayis_verified` | جُذر موثَّق في مقاييس ابن فارس |
| `not_found` | لم يُوجَد جذر مناسب في المقاييس |
| `no_arabic` | لا توجد كلمات عربية في المدخلة |

### 5. تصحيح خريطة أسماء كاملة

```python
from engines.noun_root_corrector import correct_noun_tree

corrected_map, results = correct_noun_tree(
    synmap_path="arabic_synset_map.json",
    db_path="maqayis_v2/maqayis.db",
)

for r in results:
    print(r.synset_id, r.new_root, r.status, r.source_word)
```

`CorrectionResult` يحتوي:

| الحقل | النوع | الوصف |
|---|---|---|
| `synset_id` | `str` | معرِّف المجموعة |
| `old_roots` | `list[str]` | الجذور القديمة |
| `new_root` | `str \| None` | الجذر المُصحَّح |
| `status` | `str` | maqayis_verified / not_found / no_arabic |
| `source_word` | `str` | الكلمة التي استُخرج منها الجذر |

### 6. تطبيع النص وإزالة الحركات

```python
from engines.noun_root_corrector import strip_harakat, normalize_for_match

strip_harakat("كَتَبَ")       # → "كتب"
normalize_for_match("رئيس")  # → "رايس"  (مُطبَّع للمقارنة)
```

---

## التصحيحات الصرفية (Fixes A–H)

يُطبِّق المحرك 8 تصحيحات تلقائية للحالات الصرفية الخاصة قبل البحث في المقاييس:

| التصحيح | الوزن | مثال |
|---|---|---|
| Fix A | تاء التأنيث | تكريم → كرم |
| Fix B | جمع مؤنث سالم (ـات) | مكتبات → كتب |
| Fix C | جمع مذكر سالم (ـون/ـين) | معلمون → علم |
| Fix D | النسب (ـي) | مصري → مصر |
| Fix E | التصغير | كُتيِّب → كتب |
| Fix F | المصدر الميمي | مكتب → كتب |
| Fix G | الوزن الثامن (افتعال) | اكتساب → كسب |
| Fix H | إفعال من الناقص | الإغماء → غمي |

---

## هيكل المشروع

```
engines/
  noun_root_corrector.py   ← المحرك الرئيسي
  morphological_engine.py
  derivation_engine.py
  plural_engine.py
  compatibility_engine.py
  slots_engine.py
core/
  root.py
  types.py
data/
  noun_root_correction_report.json   ← تقرير إحصائي
  pilot_roots.json
tests/                               ← اختبارات الوحدة
noun_root_report.html                ← تقرير تفاعلي
```

---

## الإحصائيات

```
total_words:              70,909
maqayis_verified:         68,922  (97.2%)
not_found_in_maqayis:      1,322  (1.9%)
no_arabic_words:             665  (0.9%)
roots_actually_changed:   37,754
```

---

## المصدر

يعتمد هذا المشروع على **مقاييس اللغة** لابن فارس (ت 395هـ) كمرجع وحيد للجذور المقبولة.  
لا يُقبل أي جذر إلا إذا وُجد في المقاييس.  
للاستخدام الأكاديمي البحثي فقط.
