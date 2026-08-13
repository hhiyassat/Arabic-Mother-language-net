# LAYER 7 — HokomKernel: نطاق ومواصفة

**الحالة:** BUILT  
**الإصدار:** ARABIC-MOTHER-NET-LAYER7-HOKOM-KERNEL-01  
**يستقبل من:** `Layer7Handoff` (LAYER 6 — مجمَّد)  
**ينتج:** `HokomResult` — حكم سلامة الجملة تركيبياً

---

## النطاق الوحيد لـ LAYER 7

```
LAYER 7 = حكم لغوي على سلامة الجملة تركيبياً فحسب.
```

| مسموح به | ممنوع |
|----------|-------|
| الحكم باكتمال الإسناد | حكم فقهي |
| الحكم بمطابقة الحالة الإعرابية للدور | فتوى |
| كشف التعلُّق اليتيم (muttasil) | تفسير |
| إصدار HOKM_SALEEM / HOKM_MUKHTALL مع قائمة الاختلالات | إغلاق GRES-HUKM الفقهي |
| — | إعادة فتح Wave11 / IfadahResult / IrabJudgmentResult |
| — | تسمية نفسه "الحكم" المطلق — هو حكم لغوي فقط |

---

## مصادر LAYER 7

- **المدخل الوحيد:** `Layer7Handoff` من LAYER 6 (عبر `IrabJudgmentResult.to_layer7_handoff()`)
- **القواعد:** نحو عربي معروف — لا محرك خارجي مطلوب
- **لا يفتح:** أي طبقة سابقة — الجذر والإعراب مُعطَيان في الـ handoff

---

## قواعد السلامة الثلاث (R1–R3)

| القاعدة | الاسم | التفصيل |
|---------|------|---------|
| R1 | ISNAD | فعلية تتطلَّب فعلاً وفاعلاً؛ اسمية/وصفية تتطلَّب مبتدأً وخبراً |
| R2 | AGREEMENT | فاعل مرفوع، مفعول به منصوب، مبتدأ وخبر مرفوعان، جار ومجرور مجرور، ظرف/حال منصوب، فعل مبني أو مرفوع |
| R3 | MUTTASIL | كل `muttasil` غير فارغ يجب أن يطابق كلمة عنصرٍ موجود في الجملة |

الحكم: لا اختلال ⟸ `HOKM_SALEEM`، وإلا ⟸ `HOKM_MUKHTALL` مع `defects`.

---

## الحراس الأربعة (GUARD_L7_00 — GUARD_L7_03)

| الحارس | الشرط | النتيجة |
|--------|-------|---------|
| GUARD_L7_00 | layer6_frozen ≠ "IRAB_JUDGMENT_KERNEL_LAYER6_BUILT_READY_FOR_HOKOM_HANDOFF" | BLOCKED |
| GUARD_L7_01 | sentence فارغة | BLOCKED |
| GUARD_L7_02 | entries فارغة | BLOCKED |
| GUARD_L7_03 | sentence_type ∉ {فعلية، اسمية، وصفية} | BLOCKED |

---

## بنية المخرج

```python
@dataclass(frozen=True)
class SoundnessCheck:
    name:   str    # ISNAD / AGREEMENT / MUTTASIL
    passed: bool
    detail: str

@dataclass
class HokomResult:
    root:          str
    synset_id:     str
    sentence:      str
    sentence_type: str
    verdict:       str   # "HOKM_SALEEM" / "HOKM_MUKHTALL" / "BLOCKED"
    checks:        list[SoundnessCheck]
    defects:       list[str]
    block_reasons: list[str]
    layer7_frozen: str
```

---

## تسلسل الطبقات

```
✅ LAYER 0–4  Wave11Ancestry         مجمَّد
✅ LAYER 5    IfadahKernel            مجمَّد — 18/18 اختبار
✅ LAYER 6    IrabJudgmentKernel      مجمَّد — 13/13 اختبار
✅ LAYER 7    HokomKernel             مبني — هذا الملف — 14/14 اختبار
```

---

## ما بعد LAYER 7

LAYER 7 ينتج `HokomResult` — يُسلَّم إلى طبقات LAYER 8 العليا عبر ختم
`HOKM_KERNEL_LAYER7_BUILT_READY_FOR_LAYER8_HANDOFF`.  
لا يُغلق أي GRES-HUKM فقهي. اسمه الدقيق: **HokomKernel** — حكم لغوي فقط.
