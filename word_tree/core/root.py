"""
root.py — النواة: ٧ العناصر الدنيا لكل جذر
المصدر: الوثيقة المرجعية الدستورية، القسم الثالث
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .types import RootType, Baab, SemanticType, PrimaryPredicate


# ══════════════════════════════════════════════════════════════════════
# الطبقة ٢ — المحمول البنيوي
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Slot:
    """فتحة دور (Slot) واحدة"""
    name:    str             # اسم الدور (فاعل، مفعول، حرف...)
    type:    SemanticType    # نوع الموضوع الدلالي
    example: str             # مثال عربي
    optional: bool = False   # هل هو اختياري؟
    preposition: Optional[str] = None  # حرف الجر إن وُجد


@dataclass
class StructuralPredicate:
    """المحمول البنيوي — الطبقة ٢"""
    primary_predicate: PrimaryPredicate   # المحمول الأولي
    slots: list[Slot]                     # الـ Slots المفتوحة
    raw_text: str                         # النص الكامل للمحمول


# ══════════════════════════════════════════════════════════════════════
# الطبقة ٣ — ملف السلوك الصرفي
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MorphBehavior:
    """ملف السلوك الصرفي — الطبقة ٣"""
    baab:              Baab              # الباب الصرفي
    masadir_samiyya:   list[str]         # المصادر السماعية لباب I
    masdar_qiyasi:     Optional[str]     # المصدر القياسي (إن وُجد)
    # أنماط الاشتقاق
    ism_faail:         Optional[str] = None   # اسم الفاعل
    ism_mafuul:        Optional[str] = None   # اسم المفعول
    ism_makan:         Optional[str] = None   # اسم المكان
    ism_zaman:         Optional[str] = None   # اسم الزمان
    ism_aala:          Optional[str] = None   # اسم الآلة
    # الصيغ المزيدة المقبولة (II–X)
    awzaan_maqbuula: dict[str, str] = field(default_factory=dict)
    # {وزن: دلالة التحويل} مثل: {"II": "تعليم الكتابة", "X": "طلب الكتابة"}
    # جموع التكسير
    jumuu_taksir: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# الطبقة ٤ — الشبكة العلائقية
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RelationalNetwork:
    """الشبكة العلائقية — الطبقة ٤"""
    yushbih:    list[str] = field(default_factory=list)  # يُشبه
    yasbiq:     list[str] = field(default_factory=list)  # يسبق
    yuaakis:    list[str] = field(default_factory=list)  # يُعاكس
    yastlzim:   list[str] = field(default_factory=list)  # يستلزم
    aamma:      list[str] = field(default_factory=list)  # أعمّ
    akhass:     list[str] = field(default_factory=list)  # أخصّ


# ══════════════════════════════════════════════════════════════════════
# النواة الكاملة — ٧ العناصر
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ArabicRoot:
    """
    النواة الكاملة للجذر: ٧ عناصر دنيا مكتملة
    كل عنصر يُشغِّل محركاً واحداً أو أكثر
    """

    # ── العنصر ١: الحروف الأصلية + النوع الصرفي ─────────────────────
    letters:     str       # الحروف الأصلية (كتب، حكم، ردد...)
    display:     str       # الجذر كما يُكتب (كَتَبَ، حَكَمَ...)
    root_type:   RootType  # النوع الصرفي

    # ── العنصر ٢: المعنى الأصلي (رباعي الطبقات) ──────────────────────
    # الطبقة ١ — ابن فارس
    ibn_faris:   str       # جملة ابن فارس الأصلية
    # الطبقة ٢ — المحمول البنيوي
    predicate:   StructuralPredicate
    # الطبقة ٣ — السلوك الصرفي (= العنصر ٣ + ٤ + ٥)
    morph:       MorphBehavior
    # الطبقة ٤ — الشبكة العلائقية
    network:     RelationalNetwork

    # ── العنصر ٦: جموع التكسير ──────────────────────────────────────
    # (مُضمَّن في morph.jumuu_taksir)

    # ── العنصر ٧: استثناءات القابلية ────────────────────────────────
    compatibility_exceptions: list[dict] = field(default_factory=list)
    # [{slot: "فاعل", override_type: "أداة", note: "سبب الاستثناء"}]

    def summary(self) -> str:
        return (
            f"الجذر: {self.display} ({self.letters}) — {self.root_type.value}\n"
            f"ابن فارس: {self.ibn_faris[:80]}...\n"
            f"الباب: {self.morph.baab.value}\n"
            f"أوزان مقبولة: {list(self.morph.awzaan_maqbuula.keys())}\n"
            f"مصادر سماعية: {self.morph.masadir_samiyya}"
        )
