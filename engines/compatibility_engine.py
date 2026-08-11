"""
compatibility_engine.py — محرك التوافق
يحسب توافق الجذور بناءً على:
  - الفحص البنيوي: مطابقة أنواع الفتحات الدلالية (المبدأ الثالث)
  - الشبكة الدلالية: يشبه / يعاكس / يستلزم / عامّ / أخصّ
  - استثناءات التوافق: تجاوزات صريحة على نوع الفتحة
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.types import SemanticType
from engines.slots_engine import PredicateStructure, parse_predicate_from_dict


# ══════════════════════════════════════════════════════════════════════
# هياكل البيانات
# ══════════════════════════════════════════════════════════════════════

@dataclass
class NetworkRelations:
    """الشبكة الدلالية للجذر"""
    root:      str
    yushbih:   list[str] = field(default_factory=list)  # يشبه
    yuaakis:   list[str] = field(default_factory=list)  # يعاكس
    yastlzim:  list[str] = field(default_factory=list)  # يستلزم
    yasbiq:    list[str] = field(default_factory=list)  # يسبق
    aamma:     list[str] = field(default_factory=list)  # أعمّ
    akhass:    list[str] = field(default_factory=list)  # أخصّ

    def all_related(self) -> set[str]:
        """كل الجذور المرتبطة بأي علاقة"""
        return (
            set(self.yushbih) | set(self.yuaakis) |
            set(self.yastlzim) | set(self.yasbiq) |
            set(self.aamma) | set(self.akhass)
        )

    def relation_to(self, form: str) -> Optional[str]:
        """أرجع نوع العلاقة مع صيغة مُحدَّدة (أو None)"""
        if form in self.yushbih:  return "يشبه"
        if form in self.yuaakis:  return "يعاكس"
        if form in self.yastlzim: return "يستلزم"
        if form in self.yasbiq:   return "يسبق"
        if form in self.aamma:    return "أعمّ"
        if form in self.akhass:   return "أخصّ"
        return None


@dataclass
class SlotOverride:
    """استثناء تعديل نوع الفتحة لجذر بعينه"""
    slot:          str   # اسم الفتحة (فاعل، مفعول، ...)
    override_type: str   # النوع الدلالي البديل
    note:          str   # تفسير


@dataclass
class CompatibilityResult:
    """نتيجة فحص التوافق بين جذرين"""
    root_a:          str
    root_b:          str
    # فحص بنيوي
    can_chain_ab:    bool           # A يمكن أن يُرفَد بـ B (خرج A → دخل B)
    can_chain_ba:    bool           # B يمكن أن يُرفَد بـ A
    share_arg_type:  bool           # يتشاركان نوعاً دلالياً في الفتحات الإلزامية
    # علاقة شبكية
    net_relation_ab: Optional[str]  # علاقة شبكة A تجاه B
    net_relation_ba: Optional[str]  # علاقة شبكة B تجاه A
    # درجة توافق مركَّبة [0..1]
    score:           float

    @property
    def chain_direction(self) -> str:
        if self.can_chain_ab and self.can_chain_ba:
            return "ثنائي"
        if self.can_chain_ab:
            return f"{self.root_a} → {self.root_b}"
        if self.can_chain_ba:
            return f"{self.root_b} → {self.root_a}"
        return "لا تسلسل"

    @property
    def is_compatible(self) -> bool:
        """هل الجذران متوافقان (بنيوياً أو دلالياً)؟"""
        return self.score >= 0.3

    def summary(self) -> str:
        parts = []
        if self.can_chain_ab or self.can_chain_ba:
            parts.append(f"تسلسل: {self.chain_direction}")
        if self.share_arg_type:
            parts.append("يتشاركان نوعاً دلالياً")
        rel = self.net_relation_ab or self.net_relation_ba
        if rel:
            parts.append(f"شبكة: {rel}")
        if not parts:
            parts.append("لا توافق")
        return " | ".join(parts) + f"  [درجة: {self.score:.2f}]"

    def __repr__(self) -> str:
        return (
            f"CompatibilityResult({self.root_a!r} ↔ {self.root_b!r}: "
            f"score={self.score:.2f}, {self.chain_direction})"
        )


# ══════════════════════════════════════════════════════════════════════
# التحليل من JSON
# ══════════════════════════════════════════════════════════════════════

def parse_network_from_dict(root_data: dict) -> NetworkRelations:
    """استخرج الشبكة الدلالية من قاموس الجذر"""
    net = root_data.get("network", {})
    return NetworkRelations(
        root     = root_data["letters"],
        yushbih  = net.get("yushbih",  []),
        yuaakis  = net.get("yuaakis",  []),
        yastlzim = net.get("yastlzim", []),
        yasbiq   = net.get("yasbiq",   []),
        aamma    = net.get("aamma",    []),
        akhass   = net.get("akhass",   []),
    )


def parse_exceptions_from_dict(root_data: dict) -> list[SlotOverride]:
    """استخرج استثناءات التوافق من قاموس الجذر"""
    raw = root_data.get("compatibility_exceptions", [])
    result = []
    for item in raw:
        result.append(SlotOverride(
            slot          = item["slot"],
            override_type = item["override_type"],
            note          = item.get("note", ""),
        ))
    return result


# ══════════════════════════════════════════════════════════════════════
# حساب التوافق
# ══════════════════════════════════════════════════════════════════════

def _score(
    can_ab:     bool,
    can_ba:     bool,
    share_arg:  bool,
    has_net:    bool,
    is_opposes: bool,
) -> float:
    """
    درجة التوافق المركَّبة [0..1]:
      - التسلسل البنيوي ثنائي: 0.9
      - التسلسل البنيوي أحادي: 0.7
      - تشارك نوع دلالي فقط: 0.4
      - علاقة شبكية موجبة: +0.2
      - تعاكس شبكي: -0.2 (قد تكون لها قيمة بلاغية لكن بنيوياً متضادة)
    """
    base = 0.0
    if can_ab and can_ba:
        base = 0.9
    elif can_ab or can_ba:
        base = 0.7
    elif share_arg:
        base = 0.4

    if has_net and not is_opposes:
        base = min(1.0, base + 0.2)
    if is_opposes:
        base = max(0.0, base - 0.2)

    return round(base, 2)


def check_compatibility(
    ps_a:  PredicateStructure,
    ps_b:  PredicateStructure,
    net_a: NetworkRelations,
    net_b: NetworkRelations,
) -> CompatibilityResult:
    """
    افحص التوافق بين جذرين وأرجع نتيجة مفصَّلة.
    """
    can_ab   = ps_a.can_chain_to(ps_b)
    can_ba   = ps_b.can_chain_to(ps_a)
    share    = ps_a.shares_argument_type(ps_b)

    # البحث عن العلاقة الشبكية
    # نبحث عن حروف الجذر والصيغ المعروضة في كلا الاتجاهين
    rel_ab = net_a.relation_to(ps_b.root) or net_a.relation_to(
        _display_key(ps_b.root)
    )
    rel_ba = net_b.relation_to(ps_a.root) or net_b.relation_to(
        _display_key(ps_a.root)
    )

    is_opposes = (rel_ab == "يعاكس") or (rel_ba == "يعاكس")
    has_net    = bool(rel_ab or rel_ba) and not is_opposes

    score = _score(can_ab, can_ba, share, has_net, is_opposes)

    return CompatibilityResult(
        root_a         = ps_a.root,
        root_b         = ps_b.root,
        can_chain_ab   = can_ab,
        can_chain_ba   = can_ba,
        share_arg_type = share,
        net_relation_ab= rel_ab,
        net_relation_ba= rel_ba,
        score          = score,
    )


def _display_key(letters: str) -> str:
    """حروف الجذر كما قد تظهر في شبكة جذر آخر (مجرَّدة)"""
    return letters  # في بياناتنا التجريبية الشبكة تستخدم الصيغ المعروضة لا الحروف


# ══════════════════════════════════════════════════════════════════════
# واجهة الجملة الكاملة
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RootCompatibilityMap:
    """خريطة التوافق الكاملة لمجموعة من الجذور"""
    roots:   list[str]
    results: dict[tuple[str, str], CompatibilityResult] = field(default_factory=dict)

    def get(self, a: str, b: str) -> Optional[CompatibilityResult]:
        return self.results.get((a, b)) or self.results.get((b, a))

    def compatible_with(self, root: str, min_score: float = 0.3) -> list[CompatibilityResult]:
        """أرجع كل نتائج التوافق الموجبة للجذر المُعطى"""
        out = []
        for (a, b), res in self.results.items():
            if (a == root or b == root) and res.score >= min_score:
                out.append(res)
        return sorted(out, key=lambda r: -r.score)

    def chains(self) -> list[tuple[str, str]]:
        """أزواج التسلسل الأحادي والثنائي"""
        out = []
        for (a, b), res in self.results.items():
            if res.can_chain_ab:
                out.append((a, b))
            if res.can_chain_ba:
                out.append((b, a))
        return out

    def top_pairs(self, n: int = 5) -> list[CompatibilityResult]:
        """أعلى n زوج من حيث درجة التوافق"""
        all_res = list(self.results.values())
        return sorted(all_res, key=lambda r: -r.score)[:n]


def build_compatibility_map(roots_data: list[dict]) -> RootCompatibilityMap:
    """
    أنشئ خريطة التوافق الكاملة لقائمة من قواميس الجذور.
    """
    # تحليل البنى المسندية والشبكات
    structures: dict[str, PredicateStructure] = {}
    networks:   dict[str, NetworkRelations]   = {}

    for rd in roots_data:
        letters = rd["letters"]
        structures[letters] = parse_predicate_from_dict(rd)
        networks[letters]   = parse_network_from_dict(rd)

    roots_list = list(structures.keys())
    rcm = RootCompatibilityMap(roots=roots_list)

    for i, a in enumerate(roots_list):
        for b in roots_list[i + 1:]:
            res = check_compatibility(
                structures[a], structures[b],
                networks[a],   networks[b],
            )
            rcm.results[(a, b)] = res

    return rcm


def build_compatibility_map_from_file(path: str) -> RootCompatibilityMap:
    """واجهة مُيسَّرة — تستقبل مسار pilot_roots.json"""
    import json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return build_compatibility_map(data["roots"])


# ══════════════════════════════════════════════════════════════════════
# تحليل السياق والمشابهة
# ══════════════════════════════════════════════════════════════════════

def semantic_neighbors(
    root:      str,
    networks:  dict[str, NetworkRelations],
    rel_type:  str = "يشبه",
) -> list[str]:
    """
    أرجع الجذور التي يُشير إليها الجذر المُعطى بعلاقة مُحدَّدة.
    rel_type: "يشبه" | "يعاكس" | "يستلزم" | "يسبق" | "أعمّ" | "أخصّ"
    """
    net = networks.get(root)
    if not net:
        return []
    mapping = {
        "يشبه":   net.yushbih,
        "يعاكس":  net.yuaakis,
        "يستلزم": net.yastlzim,
        "يسبق":   net.yasbiq,
        "أعمّ":   net.aamma,
        "أخصّ":   net.akhass,
    }
    return mapping.get(rel_type, [])
