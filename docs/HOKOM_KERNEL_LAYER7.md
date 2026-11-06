# HOKOM_KERNEL_LAYER7 — توثيق

**الحالة:** BUILT — مجمَّد  
**الاختبارات:** 14/14 ✅  
**الحكم الختامي:** `HOKM_KERNEL_LAYER7_BUILT_READY_FOR_LAYER8_HANDOFF`

---

## النطاق

LAYER 7 = حكم لغوي على سلامة الجملة تركيبياً فحسب.

| مسموح | ممنوع |
|-------|-------|
| الحكم بسلامة الإسناد | حكم فقهي |
| الحكم بمطابقة الإعراب للدور | فتوى |
| كشف التعلُّق اليتيم | تفسير |
| إصدار HOKM_SALEEM / HOKM_MUKHTALL | إغلاق GRES-HUKM |
| — | إعادة فتح Wave11 / IfadahResult / IrabJudgmentResult |

> **تنبيه:** «الحكم» هنا لغويٌّ محض (سلامة تركيبية). لا علاقة له بأي حكم شرعي أو فقهي.

---

## الملفات

| الملف | الوصف |
|-------|-------|
| `hokom_types.py` | أنواع البيانات: HokomVerdict, SoundnessCheck, HokomResult, Layer7 tokens |
| `hokom_kernel.py` | الكيرنل الرئيسي: hokom_judge(), hokom_judge_from_irab() |
| `tests/test_hokom_kernel.py` | 14 اختبار — 14 ناجح |
| `docs/LAYER7_HOKOM_SCOPE.md` | وثيقة النطاق |
| `tmp/layer7_hokom_report.json` | تقرير الأمثلة المجمَّدة |

المدخل: `Layer7Handoff` (مُعرَّف في `irab_types.py`، يُنتَج عبر `IrabJudgmentResult.to_layer7_handoff()`).

---

## قواعد السلامة الثلاث

| القاعدة | الاسم | ما تفحصه |
|---------|------|----------|
| R1 | ISNAD | اكتمال الإسناد: فعلية ⟸ فعل + فاعل، اسمية ⟸ مبتدأ + خبر |
| R2 | AGREEMENT | مطابقة الحالة الإعرابية للدور (فاعل مرفوع، مفعول منصوب، مبتدأ/خبر مرفوعان، جار ومجرور مجرور…) |
| R3 | MUTTASIL | كل متعلَّق (muttasil) غير فارغ يُحيل إلى كلمة موجودة في الجملة — لا تعلُّق يتيم |

- لا اختلال في أيٍّ من القواعد ⟸ **HOKM_SALEEM**.
- اختلال واحد فأكثر ⟸ **HOKM_MUKHTALL** (مع قائمة `defects`).

---

## الحراس الأربعة

| الحارس | الشرط | النتيجة |
|--------|-------|---------|
| GUARD_L7_00 | layer6_frozen ≠ LAYER6_FROZEN_TOKEN | BLOCKED |
| GUARD_L7_01 | sentence فارغة | BLOCKED |
| GUARD_L7_02 | لا مدخلات إعرابية (entries فارغة) | BLOCKED |
| GUARD_L7_03 | نوع الجملة غير مدعوم | BLOCKED |

---

## الأمثلة المُجمَّدة

### S01 — كَتَبَ الكاتبُ الرسالةَ (فعلية)

```
ISNAD     ✅ جملة فعلية مكتملة الإسناد
AGREEMENT ✅ جميع الحالات مطابقة لأدوارها
MUTTASIL  ✅ جميع التعلُّقات تُحيل إلى عناصر موجودة
⟸ HOKM_SALEEM
```

### S03 — مَكْتَب مكانُ كِتابةٍ (اسمية)

```
ISNAD     ✅ جملة اسمية مكتملة الإسناد (مبتدأ + خبر)
AGREEMENT ✅ المبتدأ والخبر مرفوعان
MUTTASIL  ✅ الخبر يتعلَّق بالمبتدأ الموجود
⟸ HOKM_SALEEM
```

### M01 — الفاعل منصوب (اختلال مطابقة)

```
AGREEMENT ❌ «الكاتبَ» (فاعل) جاء منصوباً والمتوقَّع مرفوع
⟸ HOKM_MUKHTALL
```

---

## تسلسل الطبقات

```
✅ LAYER 0–4  Wave11Ancestry         مجمَّد
✅ LAYER 5    IfadahKernel            مجمَّد — 18/18
✅ LAYER 6    IrabJudgmentKernel      مجمَّد — 13/13
✅ LAYER 7    HokomKernel             مجمَّد — 14/14
```

---

**الحكم الختامي:**  
`HOKM_KERNEL_LAYER7_BUILT_READY_FOR_LAYER8_HANDOFF`
