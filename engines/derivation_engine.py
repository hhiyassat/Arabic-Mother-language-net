"""
derivation_engine.py — المحرك الاشتقاقي
يولِّد مشتقات الجذر: مصدر، اسم فاعل، اسم مفعول، مكان، زمان، آلة، وأفعال مزيدة II–X
المبدأ الخامس: ما يمكن توليده لا يُخزَّن — المزيدات تُولَّد كلياً من الجذر + الوزن
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.types import RootType, Baab

# حركات مختصرة
F  = "َ"   # فتحة
D  = "ُ"   # ضمة
K  = "ِ"   # كسرة
S  = "ْ"   # سكون
SH = "ّ"   # شدة
A  = "ا"
W  = "و"
Y  = "ي"


# ══════════════════════════════════════════════════════════════════════
# هياكل المخرجات
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MazidEntry:
    """مدخلة وزن مزيد واحد (II–X)"""
    wazn:       str             # الوزن: "II", "III", ...
    verb:       str             # صيغة الفعل الماضي
    masdar:     str             # المصدر القياسي
    ism_faail:  str             # اسم الفاعل
    ism_mafuul: str             # اسم المفعول
    meaning:    str             # الدلالة من الجذر المخزَّن (awzaan_maqbuula)
    wazn_op:    str             # العملية الدلالية للوزن (+سببية، +ثنائية، ...)


@dataclass
class DerivationSet:
    """مجموعة المشتقات الكاملة للجذر"""
    root:        str
    root_type:   RootType
    baab:        Baab
    # ── باب I: مُسترجَع من البيانات المخزَّنة (ليست قياسية بالكامل) ──
    masadir_samiyya: list[str] = field(default_factory=list)
    masdar_qiyasi:   Optional[str] = None
    ism_faail:       Optional[str] = None   # مُولَّد
    ism_mafuul:      Optional[str] = None   # مُولَّد
    ism_makan:       Optional[str] = None   # مُولَّد
    ism_zaman:       Optional[str] = None   # مُولَّد
    ism_aala:        Optional[str] = None   # مُولَّد
    # ── المزيدات II–X: مُولَّدة كلياً ──
    mazidaat:    list[MazidEntry] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# دلالات الأوزان (المبدأ الثاني)
# ══════════════════════════════════════════════════════════════════════

WAZN_OPS = {
    "II":  "+سببية",       # فَعَّلَ  → علَّمَ
    "III": "+ثنائية",      # فَاعَلَ  → كاتَبَ
    "IV":  "+سببية",       # أَفْعَلَ → أَكرَمَ
    "V":   "+انعكاسية",    # تَفَعَّلَ
    "VI":  "+انعكاسية",    # تَفَاعَلَ
    "VII": "−أثر فاعلي",   # اِنْفَعَلَ
    "VIII":"−أثر فاعلي",   # اِفْتَعَلَ
    "IX":  "+حالة ثابتة",  # اِفْعَلَّ
    "X":   "+طلبية",       # اِسْتَفْعَلَ → اِستَكتَبَ
}


# ══════════════════════════════════════════════════════════════════════
# توليد باب I — اسم الفاعل
# ══════════════════════════════════════════════════════════════════════

def _gen_ism_faail_I(r1: str, r2: str, r3: str, root_type: RootType) -> str:
    """
    اسم الفاعل — باب I
    الصحيح:    فَاعِل  (كتب → كَاتِب)
    المضعَّف:  فَاعّ   (ردد → رَادّ)
    أجوف واوي: فَائِل  (قول → قَائِل)
    أجوف يائي: فَائِل  (بيع → بَائِع)
    ناقص يائي: فَاعٍ   (رمي → رَامٍ)
    ناقص واوي: فَاعٍ   (دعو → دَاعٍ)
    مثال واوي: وَاعِل  (وصل → وَاصِل)
    """
    if root_type == RootType.MUDAAF:
        # رَادّ (r2=r3 مدغمان)
        return r1 + F + A + r2 + SH

    if root_type in (RootType.AJWAF_WAW, RootType.AJWAF_YAA):
        # قَائِل / بَائِع (همزة بدل حرف العلة)
        return r1 + F + A + "ئ" + K + r3

    if root_type in (RootType.NAQIS_YAA, RootType.NAQIS_WAW):
        # رَامٍ / دَاعٍ — r3 محذوف + تنوين كسر (كسرتان)
        return r1 + F + A + r2 + "ٍ"

    # صحيح + مثال واوي
    return r1 + F + A + r2 + K + r3


def _gen_ism_mafuul_I(r1: str, r2: str, r3: str, root_type: RootType) -> str:
    """
    اسم المفعول — باب I
    الصحيح:    مَفْعُول (كتب → مَكتوب)
    المضعَّف:  مَفْعُول (ردد → مَرْدُود)
    أجوف واوي: مَفْعُول (قول → مَقُول) — الواو تبقى
    أجوف يائي: مَفْعِيل (بيع → مَبِيع)
    ناقص يائي: مَفْعِيّ  (رمي → مَرْمِيّ)
    ناقص واوي: مَفْعُوّ  (دعو → مَدْعُوّ)
    مثال واوي: مَفْعُول (وصل → مَوْصُول)
    """
    if root_type == RootType.AJWAF_YAA:
        # مَبِيع
        return "مَ" + r1 + K + Y + r3

    if root_type == RootType.NAQIS_YAA:
        # مَرْمِيّ
        return "مَ" + r1 + S + r2 + K + Y + SH

    if root_type == RootType.NAQIS_WAW:
        # مَدْعُوّ
        return "مَ" + r1 + S + r2 + D + W + SH

    if root_type == RootType.AJWAF_WAW:
        # إعلال: مَقْوُول → مَقُول (حذف واو r2 الساكنة، والضمة تبقى)
        return "مَ" + r1 + D + W + r3

    # صحيح / مضعَّف / مثال واوي
    return "مَ" + r1 + S + r2 + D + W + r3


def _gen_ism_makan_zaman_I(r1: str, r2: str, r3: str, baab: Baab) -> str:
    """
    اسم المكان والزمان — قياس: مَفْعَل أو مَفْعِل
    الباب فَعَلَ يَفْعِلُ  → مَفْعِل (مَجلِس)
    غير ذلك               → مَفْعَل (مَكتَب)
    الناقص: r3 ∈ {ي,و} → ينتهي بألف مقصورة (ى)
    """
    if r3 in (Y, W):
        if baab == Baab.FAA_YAF_I:
            return "مَ" + r1 + S + r2 + K + "ى"
        return "مَ" + r1 + S + r2 + F + "ى"
    if baab == Baab.FAA_YAF_I:
        return "مَ" + r1 + S + r2 + K + r3
    return "مَ" + r1 + S + r2 + F + r3


def _gen_ism_aala_I(r1: str, r2: str, r3: str) -> str:
    """
    اسم الآلة — قياس: مِفْعَل أو مِفْعَلة أو مِفْعَال
    نستخدم مِفْعَل (الأكثر انتشاراً)
    الناقص: r3 ∈ {ي,و} → ينتهي بألف مقصورة (ى)
    """
    if r3 in (Y, W):
        return "مِ" + r1 + S + r2 + F + "ى"
    return "مِ" + r1 + S + r2 + F + r3


# ══════════════════════════════════════════════════════════════════════
# إعلال الناقص في المزيدات
# ══════════════════════════════════════════════════════════════════════

def _fix_naqis_forms(forms: dict, r3: str, wazn: str) -> dict:
    """
    إعلال بالقلب للناقص يائي/واوي في الأوزان المزيدة:
    ١. الفعل:  نهاية r3+فتحة    → ألف مقصورة (ى)
    ٢. مصدر II: ...ْي/و     → ...يَة       (تَفْعِيل → تَفْعِلَة)
    ٣. مصدر III: ...يةٌ/وةٌ → ...اةٌ       (مُفَاعَلَة → مُفَاعَاة)
    ٤. اسم المفعول: نهاية فتحة+r3 → فتحة+ألف (مُفَعَّي → مُفَعَّى)
    """
    result = {}
    for key, val in forms.items():
        if key == "verb" and val.endswith(r3 + F):
            val = val[:-2] + "ى"
        elif key == "masdar":
            if wazn == "II" and val.endswith(Y + S + r3):
                # تَفْعِيْي / تَفْعِيْو  →  تَفْعِيَة
                # نزيل (ي + ْ + r3) ثلاثة محارف، ونضيف (يَة)
                val = val[:-3] + "يَة"
            elif val.endswith(r3 + "ةٌ"):
                # مُفَاعَيةٌ / مُفَاعَوةٌ  →  مُفَاعَاةٌ
                val = val[:-3] + A + "ةٌ"
        elif key == "i_mafuul" and val.endswith(F + r3):
            val = val[:-2] + F + "ى"
        result[key] = val
    return result


# ══════════════════════════════════════════════════════════════════════
# توليد الأوزان المزيدة II–X
# ══════════════════════════════════════════════════════════════════════

def _apply_wazn(wazn: str, r1: str, r2: str, r3: str, root_type: RootType) -> dict:
    """
    يُولِّد: فعل الوزن المزيد + مصدره القياسي + اسم فاعله + اسم مفعوله.
    يطبّق الإعلال الأساسي للأنواع الأربعة: مثال واوي / أجوف / ناقص.
    """
    is_naqis   = root_type in (RootType.NAQIS_YAA, RootType.NAQIS_WAW)
    is_mw      = root_type == RootType.MITHAL_WAW
    is_ajwaf_y = root_type == RootType.AJWAF_YAA
    is_ajwaf_w = root_type == RootType.AJWAF_WAW

    # ── الوزن II: فَعَّلَ ─────────────────────────────────────────────
    if wazn == "II":
        verb     = r1 + F + r2 + SH + F + r3 + F
        masdar   = "تَ" + r1 + S + r2 + K + Y + S + r3        # تَفْعِيل
        i_faail  = "مُ" + r1 + F + r2 + SH + K + r3           # مُفَعِّل
        i_mafuul = "مُ" + r1 + F + r2 + SH + F + r3           # مُفَعَّل

    # ── الوزن III: فَاعَلَ ────────────────────────────────────────────
    elif wazn == "III":
        verb     = r1 + F + A + r2 + F + r3 + F
        masdar   = "مُ" + r1 + F + A + r2 + F + r3 + "ةٌ"     # مُفَاعَلَة
        i_faail  = "مُ" + r1 + F + A + r2 + K + r3
        i_mafuul = "مُ" + r1 + F + A + r2 + F + r3

    # ── الوزن IV: أَفْعَلَ ────────────────────────────────────────────
    elif wazn == "IV":
        verb     = "أَ" + r1 + S + r2 + F + r3 + F
        if is_mw:
            # إِيفَال: الواو تُقلب ياءً بعد الكسرة
            masdar = "إِ" + Y + S + r2 + F + A + r3            # إِيصَال
        else:
            masdar = "إِ" + r1 + S + r2 + F + A + r3
        i_faail  = "مُ" + r1 + S + r2 + K + r3
        i_mafuul = "مُ" + r1 + S + r2 + F + r3

    # ── الوزن V: تَفَعَّلَ ────────────────────────────────────────────
    elif wazn == "V":
        verb     = "تَ" + r1 + F + r2 + SH + F + r3 + F
        masdar   = "تَ" + r1 + F + r2 + D + SH + r3
        i_faail  = "مُتَ" + r1 + F + r2 + SH + K + r3
        i_mafuul = "مُتَ" + r1 + F + r2 + SH + F + r3

    # ── الوزن VI: تَفَاعَلَ ───────────────────────────────────────────
    elif wazn == "VI":
        verb     = "تَ" + r1 + F + A + r2 + F + r3 + F
        masdar   = "تَ" + r1 + F + A + r2 + D + r3
        i_faail  = "مُتَ" + r1 + F + A + r2 + K + r3
        i_mafuul = "مُتَ" + r1 + F + A + r2 + F + r3

    # ── الوزن VII: اِنْفَعَلَ ─────────────────────────────────────────
    elif wazn == "VII":
        verb     = "اِنْ" + r1 + F + r2 + F + r3 + F
        masdar   = "اِنْ" + r1 + K + r2 + F + A + r3
        i_faail  = "مُنْ" + r1 + F + r2 + K + r3
        i_mafuul = "مُنْ" + r1 + F + r2 + F + r3

    # ── الوزن VIII: اِفْتَعَلَ ────────────────────────────────────────
    elif wazn == "VIII":
        if is_mw:
            # إبدال: فاء الفعل (واو) → تاء + إدغام مع تاء الافتعال
            # اِوْتَصَلَ → اِتَّصَلَ
            verb     = "اِتَّ" + r2 + F + r3 + F
            masdar   = "اِتِّ" + r2 + F + A + r3
            i_faail  = "مُتَّ" + r2 + K + r3
            i_mafuul = "مُتَّ" + r2 + F + r3
        elif is_ajwaf_y:
            # قلب الياء ألفاً بين فتحتين: اِبْتَيَعَ → اِبْتَاعَ
            verb     = "اِ" + r1 + S + "تَ" + A + r3 + F
            masdar   = "اِ" + r1 + S + "تِ" + Y + A + r3      # اِبْتِيَاع (ياء تبقى)
            i_faail  = "مُ" + r1 + S + "تَ" + A + r3
            i_mafuul = "مُ" + r1 + S + "تَ" + A + r3
        elif is_ajwaf_w:
            # قلب الواو ألفاً بين فتحتين (كاليائي)
            verb     = "اِ" + r1 + S + "تَ" + A + r3 + F
            masdar   = "اِ" + r1 + S + "تِ" + Y + A + r3      # ياء في المصدر
            i_faail  = "مُ" + r1 + S + "تَ" + A + r3
            i_mafuul = "مُ" + r1 + S + "تَ" + A + r3
        else:
            verb     = "اِ" + r1 + S + "تَ" + r2 + F + r3 + F
            masdar   = "اِ" + r1 + S + "تِ" + r2 + F + A + r3
            i_faail  = "مُ" + r1 + S + "تَ" + r2 + K + r3
            i_mafuul = "مُ" + r1 + S + "تَ" + r2 + F + r3

    # ── الوزن IX: اِفْعَلَّ ───────────────────────────────────────────
    elif wazn == "IX":
        verb     = "اِ" + r1 + S + r2 + F + r3 + SH + F
        masdar   = "اِ" + r1 + S + r2 + K + r3 + F + A + r3
        i_faail  = "مُ" + r1 + S + r2 + F + r3 + SH
        i_mafuul = i_faail

    # ── الوزن X: اِسْتَفْعَلَ ─────────────────────────────────────────
    elif wazn == "X":
        verb     = "اِسْتَ" + r1 + S + r2 + F + r3 + F
        masdar   = "اِسْتِ" + r1 + S + r2 + F + A + r3
        i_faail  = "مُسْتَ" + r1 + S + r2 + K + r3
        i_mafuul = "مُسْتَ" + r1 + S + r2 + F + r3

    else:
        return {}

    forms = {"verb": verb, "masdar": masdar, "i_faail": i_faail, "i_mafuul": i_mafuul}

    # ── إعلال الناقص ──────────────────────────────────────────────────
    if is_naqis:
        forms = _fix_naqis_forms(forms, r3, wazn)

    return forms


# ══════════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════════

def derive(
    letters:          str,
    root_type:        RootType,
    baab:             Baab,
    masadir_samiyya:  list[str],
    masdar_qiyasi:    Optional[str],
    ism_faail_stored: Optional[str],
    ism_mafuul_stored:Optional[str],
    ism_makan_stored: Optional[str],
    ism_zaman_stored: Optional[str],
    ism_aala_stored:  Optional[str],
    awzaan_maqbuula:  dict[str, str],
) -> DerivationSet:
    """
    المحرك الاشتقاقي — يُولِّد مجموعة المشتقات الكاملة.

    المدخلات:
        letters           — الحروف الأصلية الثلاثة
        root_type         — نوع الجذر
        baab              — الباب الصرفي
        masadir_samiyya   — المصادر السماعية (مخزَّنة)
        masdar_qiyasi     — المصدر القياسي (مخزَّن إن كان غير منتظم)
        ism_*_stored      — المشتقات المخزَّنة (تُقدَّم على المُولَّدة إن وُجدت)
        awzaan_maqbuula   — الأوزان المقبولة مع دلالاتها

    المخرجات:
        DerivationSet — مجموعة المشتقات الكاملة
    """
    chars = list(letters)
    if len(chars) < 3:
        raise ValueError(f"الجذر يجب أن يكون ثلاثياً: {letters}")
    r1, r2, r3 = chars[0], chars[1], chars[2]

    ds = DerivationSet(root=letters, root_type=root_type, baab=baab)

    # ── المصادر ───────────────────────────────────────────────────────
    ds.masadir_samiyya = masadir_samiyya
    ds.masdar_qiyasi   = masdar_qiyasi    # مخزَّن أو None

    # ── المشتقات الأساسية: المخزَّن يُقدَّم على المُولَّد ─────────────
    ds.ism_faail  = ism_faail_stored  or _gen_ism_faail_I(r1, r2, r3, root_type)
    ds.ism_mafuul = ism_mafuul_stored or _gen_ism_mafuul_I(r1, r2, r3, root_type)
    ds.ism_makan  = ism_makan_stored  or _gen_ism_makan_zaman_I(r1, r2, r3, baab)
    ds.ism_zaman  = ism_zaman_stored  or _gen_ism_makan_zaman_I(r1, r2, r3, baab)
    ds.ism_aala   = ism_aala_stored   or _gen_ism_aala_I(r1, r2, r3)

    # ── المزيدات II–X ─────────────────────────────────────────────────
    for wazn, meaning in awzaan_maqbuula.items():
        forms = _apply_wazn(wazn, r1, r2, r3, root_type)
        if not forms:
            continue
        ds.mazidaat.append(MazidEntry(
            wazn      = wazn,
            verb      = forms["verb"],
            masdar    = forms["masdar"],
            ism_faail = forms["i_faail"],
            ism_mafuul= forms["i_mafuul"],
            meaning   = meaning,
            wazn_op   = WAZN_OPS.get(wazn, ""),
        ))

    return ds


# ── واجهة مُختصرة تستقبل قاموس الجذر مباشرة (من JSON) ────────────────

def derive_from_dict(root_data: dict) -> DerivationSet:
    """
    واجهة مُيسَّرة — تستقبل قاموس بيانات الجذر من pilot_roots.json.
    المشتقات القياسية (اسم الفاعل، اسم المفعول، ...) تُولَّد دائماً ولا تُقرأ من JSON
    تطبيقاً للمبدأ: ما يمكن توليده لا يُخزَّن.
    المخزون الوحيد: masadir_samiyya (سماعية) + awzaan_maqbuula (سماعية الاختيار والدلالة).
    """
    m = root_data["morph"]
    return derive(
        letters           = root_data["letters"],
        root_type         = RootType(root_data["root_type"]),
        baab              = Baab(m["baab"]),
        masadir_samiyya   = m.get("masadir_samiyya", []),
        masdar_qiyasi     = m.get("masdar_qiyasi"),
        ism_faail_stored  = None,   # تُولَّد — لا تُخزَّن
        ism_mafuul_stored = None,   # تُولَّد — لا تُخزَّن
        ism_makan_stored  = None,   # تُولَّد — لا تُخزَّن
        ism_zaman_stored  = None,   # تُولَّد — لا تُخزَّن
        ism_aala_stored   = None,   # تُولَّد — لا تُخزَّن
        awzaan_maqbuula   = m.get("awzaan_maqbuula", {}),
    )
