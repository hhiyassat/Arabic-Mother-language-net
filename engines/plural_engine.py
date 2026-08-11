"""
plural_engine.py — محرك التكسير
يُحلِّل جموع التكسير المخزَّنة ويُحدِّد أوزانها بالإحلال التلقائي (ف-ع-ل)
المبدأ الخامس: جموع التكسير سماعية — تُخزَّن ولا تُولَّد إلا في الأنماط القياسية
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.types import RootType

# حركات يُتجاهَل وجودها عند تجريد الكلمة
_DIACRITICS = set("ٌٍَُِّْٰ")


# ══════════════════════════════════════════════════════════════════════
# تحديد الوزن بطريقة الإحلال (ف-ع-ل)
# ══════════════════════════════════════════════════════════════════════

def _wazn_of(plural: str, r1: str, r2: str, r3: str) -> str:
    """
    استبدل جذور الكلمة (r1, r2, r3) بالحروف (ف, ع, ل) مع الحفاظ على الحركات
    ليظهر الوزن الصرفي للجمع.

    نستخدم عناصر وسيطة (①②③) لتجنُّب الإحلال المتداخل عند تكرار حرف.
    في الجذر المضعَّف (r2 = r3)، نستبدل التكرار الأوَّل بـ② والبقية بـ③.
    """
    result = plural
    result = result.replace(r1, "①")
    if r2 == r3:
        # مضعَّف: أوَّل ظهور لـr2 → ②، ما تبقَّى → ③
        result = result.replace(r2, "②", 1)
        result = result.replace(r2, "③")
    else:
        result = result.replace(r2, "②")
        result = result.replace(r3, "③")
    result = result.replace("①", "ف")
    result = result.replace("②", "ع")
    result = result.replace("③", "ل")
    return result


# خريطة معرفة لأكثر أوزان جموع التكسير شيوعاً
_KNOWN_WAZN_LABELS: dict[str, str] = {
    "فُعُل":    "فُعُل (كُتُب)",
    "فِعَال":   "فِعَال (رِجَال)",
    "أَفْعَال": "أَفْعَال (أَقْوَال)",
    "أَفْعُل":  "أَفْعُل (أَنْهُر)",
    "أَفْعِلَة":"أَفْعِلَة (أَسْلِحَة)",
    "فُعَلاء":  "فُعَلاء (عُلَمَاء)",
    "فُعَّال":  "فُعَّال (كُتَّاب)",
    "فَعَلة":   "فَعَلة (كَتَبة)",
    "فَعَائِل": "فَعَائِل (رَسَائِل)",
    "مَفَاعِل": "مَفَاعِل (مَسَاجِد)",
    "مَفَاعِيل":"مَفَاعِيل (مَفَاتِيح)",
    "فِعْلَان": "فِعْلَان (غِلْمَان)",
    "فُعُول":   "فُعُول (قُلُوب)",
    "فَوَاعِل": "فَوَاعِل (جَوَاهِر)",
    "فَعَالِل": "فَعَالِل (جَعَافِر)",
    "فِعَلَة":  "فِعَلَة (قِرَدَة)",
    "كِرَام":   "فِعَال (كِرَام)",    # مع تصحيح الأجوف
}


def _label_wazn(wazn: str) -> str:
    """أضف وصفاً توضيحياً للوزن إن عُرف"""
    return _KNOWN_WAZN_LABELS.get(wazn, wazn)


# ══════════════════════════════════════════════════════════════════════
# هياكل المخرجات
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PluralEntry:
    """مدخلة جمع تكسير واحدة"""
    form:         str           # صيغة الجمع (مُشكَّلة)
    wazn:         str           # الوزن الصرفي بعد الإحلال (فُعُل، فِعَال، ...)
    is_generated: bool = False  # مُولَّد بالقياس أم مخزَّن (سماعي)

    def __str__(self) -> str:
        tag = "[قياس]" if self.is_generated else "[سماع]"
        return f"{self.form} ({self.wazn}) {tag}"


@dataclass
class PluralSet:
    """مجموعة جموع التكسير للجذر"""
    root:      str
    root_type: RootType
    plurals:   list[PluralEntry] = field(default_factory=list)

    def forms(self) -> list[str]:
        """قائمة صيغ الجموع فقط"""
        return [p.form for p in self.plurals]

    def stored(self) -> list[PluralEntry]:
        """الجموع السماعية المخزَّنة فقط"""
        return [p for p in self.plurals if not p.is_generated]

    def generated(self) -> list[PluralEntry]:
        """الجموع القياسية المُولَّدة فقط"""
        return [p for p in self.plurals if p.is_generated]

    def wazn_set(self) -> set[str]:
        """مجموعة الأوزان المستخدمة"""
        return {p.wazn for p in self.plurals}

    def __str__(self) -> str:
        parts = [f"{p.form}({p.wazn})" for p in self.plurals]
        return f"PluralSet({self.root}: {', '.join(parts) if parts else '∅'})"


# ══════════════════════════════════════════════════════════════════════
# توليد قياسي للجمع (أنماط منتظمة فقط)
# ══════════════════════════════════════════════════════════════════════

F  = "َ"   # فتحة
D  = "ُ"   # ضمة
K  = "ِ"   # كسرة
S  = "ْ"   # سكون
SH = "ّ"   # شدة
A  = "ا"   # ألف مد
W  = "و"
Y  = "ي"


def _generate_regular_plurals(
    r1: str, r2: str, r3: str, root_type: RootType
) -> list[PluralEntry]:
    """
    يُولِّد الجموع القياسية المنتظمة حيث يمكن ذلك.
    يقتصر على الأنماط الموثَّقة توثيقاً كافياً لكي يكون التوليد آمناً.

    ملاحظة: معظم جموع التكسير سماعية؛ هذه الدالة لا تُستخدم إلا احتياطياً
    حين لا تُوجَد جموع مخزَّنة.
    """
    generated = []

    if root_type == RootType.SAHIH:
        # فُعُل — شائع للأسماء الثلاثية مفتوحة الأول ساكنة الثاني
        fuul_form  = r1 + D + r2 + D + r3
        fuul_wazn  = _wazn_of(fuul_form, r1, r2, r3)
        generated.append(PluralEntry(fuul_form, fuul_wazn, is_generated=True))

        # أَفْعَال — جمع عام شائع
        afaal_form = "أَ" + r1 + S + r2 + F + A + r3
        afaal_wazn = _wazn_of(afaal_form, r1, r2, r3)
        generated.append(PluralEntry(afaal_form, afaal_wazn, is_generated=True))

    elif root_type == RootType.MUDAAF:
        # فُعُول — شائع للمضعَّف
        fuuul_form = r1 + D + r2 + D + W + r2  # r2=r3 مُدغمان في المضعَّف
        fuuul_wazn = _wazn_of(fuuul_form, r1, r2, r3)
        generated.append(PluralEntry(fuuul_form, fuuul_wazn, is_generated=True))

    # غير ذلك: لا توليد آمن
    return generated


# ══════════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════════

def build_plural_set(
    letters:       str,
    root_type:     RootType,
    jumuu_taksir:  list[str],
    generate_if_empty: bool = True,
) -> PluralSet:
    """
    أنشئ PluralSet للجذر.

    المدخلات:
        letters         — الحروف الأصلية الثلاثة
        root_type       — نوع الجذر
        jumuu_taksir    — قائمة الجموع المخزَّنة
        generate_if_empty — إذا كانت القائمة فارغة، أنشئ جموعاً قياسية
    """
    chars = list(letters)
    if len(chars) < 3:
        raise ValueError(f"الجذر يجب أن يكون ثلاثياً: {letters!r}")
    r1, r2, r3 = chars[0], chars[1], chars[2]

    ps = PluralSet(root=letters, root_type=root_type)

    # ── الجموع المخزَّنة ──────────────────────────────────────────────
    for form in jumuu_taksir:
        wazn = _wazn_of(form, r1, r2, r3)
        ps.plurals.append(PluralEntry(form=form, wazn=wazn, is_generated=False))

    # ── الجموع القياسية (عند الحاجة) ──────────────────────────────────
    if not ps.plurals and generate_if_empty:
        ps.plurals.extend(_generate_regular_plurals(r1, r2, r3, root_type))

    return ps


def build_plural_set_from_dict(root_data: dict) -> PluralSet:
    """واجهة مُيسَّرة — تستقبل قاموس الجذر من pilot_roots.json"""
    return build_plural_set(
        letters          = root_data["letters"],
        root_type        = RootType(root_data["root_type"]),
        jumuu_taksir     = root_data["morph"].get("jumuu_taksir", []),
        generate_if_empty= True,
    )


# ══════════════════════════════════════════════════════════════════════
# أدوات إحصائية
# ══════════════════════════════════════════════════════════════════════

def wazn_frequency(plural_sets: list[PluralSet]) -> dict[str, int]:
    """احسب تكرار كل وزن عبر مجموعة من الجذور"""
    freq: dict[str, int] = {}
    for ps in plural_sets:
        for entry in ps.plurals:
            freq[entry.wazn] = freq.get(entry.wazn, 0) + 1
    return dict(sorted(freq.items(), key=lambda x: -x[1]))
