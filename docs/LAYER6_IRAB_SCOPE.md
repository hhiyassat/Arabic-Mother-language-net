# LAYER 6 — IrabJudgmentKernel: نطاق ومواصفة

**الحالة:** BUILT  
**الإصدار:** ARABIC-MOTHER-NET-LAYER6-IRAB-JUDGMENT-KERNEL-01  
**يستقبل من:** `Layer6Handoff` (LAYER 5 — مجمَّد)  
**ينتج:** `IrabJudgmentResult` — أحكام إعرابية لكل عنصر في الجملة

---

## النطاق الوحيد لـ LAYER 6

```
LAYER 6 = حكم إعرابي / تركيبي نحوي فحسب.
```

| مسموح به | ممنوع |
|----------|-------|
| رفع الفاعل | حكم فقهي |
| نصب المفعول به | فتوى |
| رفع المبتدأ | تفسير |
| رفع الخبر | إغلاق GRES-HUKM الفقهي |
| إعراب القيد (الجار والمجرور، الظرف، المفعول المطلق) | إعادة فتح Wave11 أو IfadahResult |
| تحديد علامة الإعراب والسبب النحوي | تسمية نفسه "الحكم" المطلق |

---

## مصادر LAYER 6

- **المدخل الوحيد:** `Layer6Handoff` من LAYER 5
- **القواعد:** نحو عربي معروف — لا محرك خارجي مطلوب
- **لا يفتح:** maqayis مباشرةً — الجذر مُعطى في الـ handoff

---

## القواعد الإعرابية الست (A–F)

| القاعدة | العنصر | الحكم | العلامة |
|---------|--------|-------|---------|
| A | الفعل (مسند فعلية) | فعل ماضٍ مبني على الفتح / مضارع مرفوع بالضمة | مبني / مرفوع |
| B | الفاعل (مسند إليه في فعلية) | فاعل مرفوع | الضمة |
| C | المفعول به (قيد أول في فعلية) | مفعول به منصوب | الفتحة |
| D | المبتدأ (مسند إليه في اسمية) | مبتدأ مرفوع | الضمة |
| E | الخبر (مسند في اسمية) | خبر مرفوع | الضمة |
| F | القيد العام (جار ومجرور / ظرف / مفعول مطلق) | شبه جملة / مفعول فيه / توكيد | حسب النوع |

---

## الحراس السبعة (GUARD_L6_00 — GUARD_L6_06)

| الحارس | الشرط | النتيجة |
|--------|-------|---------|
| GUARD_L6_00 | layer5_frozen ≠ "IFADAH_KERNEL_LAYER5_FROZEN_READY_FOR_LAYER6_HANDOFF" | BLOCKED |
| GUARD_L6_01 | raw_sentence فارغة | BLOCKED |
| GUARD_L6_02 | musnad فارغ | BLOCKED |
| GUARD_L6_03 | musnad_ilayh فارغ | BLOCKED |
| GUARD_L6_04 | sentence_type == "فعلية" وفاعل مفقود | BLOCKED |
| GUARD_L6_05 | sentence_type == "اسمية" وبدون مبتدأ أو خبر | BLOCKED |
| GUARD_L6_06 | لا يوجد حكم إعرابي واحد ممكن الاستنتاج | BLOCKED |

---

## بنية المخرج

```python
@dataclass(frozen=True)
class IrabEntry:
    word:        str   # الكلمة
    position:    int   # الموقع في الجملة (0-indexed)
    irab_role:   str   # فاعل / مفعول به / مبتدأ / خبر / فعل / قيد
    irab_case:   str   # مرفوع / منصوب / مجرور / مبني
    irab_sign:   str   # الضمة / الفتحة / الكسرة / السكون / الفتح
    irab_reason: str   # السبب النحوي
    muttasil:    str   # المتعلَّق به (أو "")

@dataclass
class IrabJudgmentResult:
    root:       str
    synset_id:  str
    sentence:   str
    entries:    list[IrabEntry]
    verdict:    str   # "IRAB_COMPLETE" / "BLOCKED"
    block_reasons: list[str]
    layer5_ref: Layer6Handoff
```

---

## تسلسل الطبقات

```
✅ LAYER 0–4  Wave11Ancestry         مجمَّد
✅ LAYER 5    IfadahKernel            مجمَّد — 18/18 اختبار
✅ LAYER 6    IrabJudgmentKernel      مبني — هذا الملف
```

---

## ما بعد LAYER 6

LAYER 6 ينتج `IrabJudgmentResult` — يُسلَّم إلى طبقات Hokom العليا.  
لا يُغلق أي GRES-HUKM فقهي. اسمه الدقيق: **IrabJudgmentKernel** فقط.
