"""
noun_root_corrector.py — مصحِّح جذور شجرة الأسماء
يأخذ كل مدخلة اسم في arabic_synset_map.json
ويعيد الجذر الصحيح من مقاييس ابن فارس

المبدأ: الجذر يجب أن يكون من مقاييس — لا جذر بلا شاهد
"""
from __future__ import annotations
import re
import json
import sqlite3
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════
# ثوابت الحروف
# ══════════════════════════════════════════════════════════════════

_HARAKAT   = set("ًٌٍَُِّْٰ")
_WEAK      = set("اوي")            # حروف العلة / المد
_HAMZA_ON_CARRIER = {"ؤ": "أ", "ئ": "أ"}   # همزة متحملة → أصلها أ

# حروف لا تُعدّ جذوراً مستقلة (أدوات وضمائر وحروف جر)
_PARTICLES = {
    "من", "عن", "في", "إلى", "على", "مع", "أو",
    "هو", "هي", "هم", "هن", "أنا", "أنت",
    "لا", "ما", "لم", "لن", "قد",
    "أن", "إن", "كان", "ليس",
    "في", "كي", "إذ", "إذا", "حتى",
}

# البادئات الزائدة مرتَّبة من الأطول للأقصر
_PREFIXES_ORDERED = [
    "بال", "وال", "فال", "كال", "لل",
    "ال",
    "مست", "است", "إست",   # Form X: مُستَفعِل / اِستَفعَل / إستَفعَل
    "انت", "انف",
    "افت", "اقت",
    "مت",          # متفعِّل: متغيِّب، متقدِّم، متعلِّم
    "تف",
]

# اللواحق الزائدة من الأطول للأقصر
_SUFFIXES_ORDERED = [
    "تان", "تين", "ات", "ون", "ين", "ان",
    "ية", "ية",
    "ة", "ى", "ا",
    "ي",    # لاحقة النسبة (مسيحي، تحرري، فرنسي)
]

# همزات الوصل الدالة على البداية (للوزن VIII من الفعل)
_HAMZAT_WASL = {'ا', 'أ', 'إ'}


# ══════════════════════════════════════════════════════════════════
# تطبيع النص
# ══════════════════════════════════════════════════════════════════

def strip_harakat(text: str) -> str:
    return "".join(c for c in text if c not in _HARAKAT)


def normalize_for_match(text: str) -> str:
    """
    تطبيع للمقارنة:
    - حذف الحركات
    - توحيد أشكال الألف (أإآٱ → ا)
    - ى → ي
    - ة → ه
    - ؤ/ئ/ء → أ  (لكشف الهمزة أصلاً)
    - تقليص التشديد: كتّب → كتب
    """
    t = strip_harakat(text)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    t = t.replace("ى", "ي")
    t = t.replace("ة", "ه")
    t = t.replace("ؤ", "أ")
    t = t.replace("ئ", "أ")
    t = t.replace("ء", "ا")   # همزة مفردة (برء → برا = برأ)
    # تقليص الحروف المضعَّفة المتتالية: كتّب → تُصبح كتب بعد حذف الشدة
    # (الشدة حُذفت أعلاه ضمن الحركات)
    return t


def normalize_root(root: str) -> str:
    return normalize_for_match(root)


# ══════════════════════════════════════════════════════════════════
# بناء فهرس المقاييس
# ══════════════════════════════════════════════════════════════════

@dataclass
class MaqayisIndex:
    raw:         set[str]        = field(default_factory=set)
    normalized:  set[str]        = field(default_factory=set)
    norm_to_raw: dict[str, str]  = field(default_factory=dict)


def load_maqayis_index(db_path: str) -> MaqayisIndex:
    idx = MaqayisIndex()
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT root_display FROM entries WHERE root_display IS NOT NULL"
    ).fetchall()
    conn.close()

    for (display,) in rows:
        raw = strip_harakat(display.strip())
        if not raw or len(raw) < 2:
            continue
        idx.raw.add(raw)
        norm = normalize_root(raw)
        idx.normalized.add(norm)
        if norm not in idx.norm_to_raw:
            idx.norm_to_raw[norm] = raw

    return idx


def lookup(candidate: str, idx: MaqayisIndex) -> Optional[str]:
    """أرجع الجذر الأصلي في المقاييس أو None"""
    c = strip_harakat(candidate)
    if c in idx.raw:
        return c
    norm = normalize_root(c)
    if norm in idx.normalized:
        return idx.norm_to_raw[norm]
    return None


# ══════════════════════════════════════════════════════════════════
# توليد مرشَّحات الجذر من كلمة واحدة
# ══════════════════════════════════════════════════════════════════

def _strip_prefix(word: str) -> list[str]:
    """جرِّد البادئات الممكنة وأرجع قائمة البقايا"""
    results = [word]
    for pre in _PREFIXES_ORDERED:
        if word.startswith(pre) and len(word) > len(pre) + 1:
            results.append(word[len(pre):])
    return results


def _strip_suffix(word: str) -> list[str]:
    """جرِّد اللواحق الممكنة"""
    results = [word]
    for suf in _SUFFIXES_ORDERED:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            results.append(word[: -len(suf)])
    return results


def _extract_3letter_from_4(base: str) -> list[str]:
    """
    من كلمة 4 حروف استخرج الجذر الثلاثي بحذف حرف زائد.
    الأولوية (من الأعلى للأدنى):
      0. حذف م أو ت من الموضع الأول (حروف زيادة مشيعة في أوزان المشتقات)
         → مأمن: حذف م (موضع 0) → أمن ✓
      1. حذف حرف علة (اوي) في موضع داخلي
         → هارب: حذف ا (موضع 1) → هرب ✓
         → رأيس: حذف ي (موضع 2) → رأس ✓
      2. حذف حرف صحيح داخلي
      3. حذف الأول أو الأخير (غير م/ت)
    """
    _PREFIX_LETTERS = {'م', 'ت'}   # حروف زيادة شائعة في أول الكلمة

    prio_prefix    = []   # م/ت في الموضع الأول
    internal_weak  = []   # حرف علة داخلي
    internal_other = []   # حرف صحيح داخلي
    boundary       = []   # أول أو آخر (غير م/ت)

    for i in range(len(base)):
        reduced = base[:i] + base[i+1:]
        if len(reduced) != 3:
            continue
        if i == 0 and base[0] in _PREFIX_LETTERS:
            prio_prefix.append(reduced)
        elif i == 0 or i == len(base) - 1:
            boundary.append(reduced)
        elif base[i] in _WEAK:
            internal_weak.append(reduced)
        else:
            internal_other.append(reduced)

    return prio_prefix + internal_weak + internal_other + boundary


def _fix_hamza_in_base(base: str) -> str:
    """
    إصلاح الهمزة المتحمَّلة قبل الاستخراج.
    ؤ → أ ، ئ → أ ، ء → أ
    مثال: رئيس → رأيس ثم نحذف ي الزائد → رأس
    مثال: برء → برأ
    """
    return base.replace("ؤ", "أ").replace("ئ", "أ").replace("ء", "أ")


def _extract_form_iii_root(base: str) -> list[str]:
    """
    الوزن الثالث المزيد بألف: مُفاعِل (5 حروف).
    الشرط: b[0]='م', b[2]='ا' (الألف حرف زيادة).
    الجذر = b[1] + b[3] + b[4].
    أمثلة:
      موافق → و+ف+ق = وفق ✓
      مواطن → و+ط+ن = وطن ✓
      معادي → ع+د+ي = عدي → (ناقص) → عدو ✓
      معاصر → ع+ص+ر = عصر ✓
    """
    if len(base) != 5 or base[0] != "م" or base[2] != "ا":
        return []
    f, ain, lam = base[1], base[3], base[4]
    cands = [f + ain + lam]
    # ناقص: اللام حرف علة (و/ي) → جرِّب البديل الآخر
    if lam in ("و", "ي"):
        other = "و" if lam == "ي" else "ي"
        cands.append(f + ain + other)
    # أجوف: الفاء حرف علة → جرِّب البديل
    if f in ("و", "ي"):
        other = "و" if f == "ي" else "ي"
        cands.append(other + ain + lam)
    return cands


def _extract_form_viii_root(base: str) -> list[str]:
    """
    الوزن الثامن المزيد بتاء: مُفتَعِل / اِفتَعَل (5 حروف).
    نمط أ: b[0]='م', b[2]='ت', b[1]≠'ت' → المشتق الاسمي (مُفتَعِل)
    نمط ب: b[0] همزة وصل, b[2]='ت', b[1]≠همزة → المصدر / الفعل (اِفتَعَل)
    الجذر العادي = b[1] + b[3] + b[4].
    الجذر الأجوف = b[1] + 'و' + b[4]  أو  b[1] + 'ي' + b[4]  عندما b[3]=ا.
    أمثلة (نمط أ):
      ممتنع → م+ن+ع = منع ✓
      مقتدر → ق+د+ر = قدر ✓
    أمثلة (نمط ب صحيح):
      اقتصد → ق+ص+د = قصد ✓
      اختصر → خ+ص+ر = خصر ✓
    أمثلة (نمط ب أجوف):
      اختار → خ+و+ر = خور / خ+ي+ر = خير ✓
      اقتاد → ق+و+د = قود / ق+ي+د = قيد ✓
    """
    if len(base) != 5:
        return []

    ok_viii = False
    if base[0] == "م" and base[2] == "ت" and base[1] != "ت":
        # استبعاد وزن مُستَفعِل (Form X): م+س+ت → بادئة مست الكاملة
        if base[1] == "س":
            return []
        ok_viii = True   # مُفتَعِل
    elif base[0] in _HAMZAT_WASL and base[2] == "ت" and base[1] not in _HAMZAT_WASL:
        ok_viii = True   # اِفتَعَل

    if not ok_viii:
        return []

    f, lam = base[1], base[4]
    cands: list[str] = []

    if base[3] == "ا":
        # أجوف في الوزن الثامن: الحرف الثالث = ا → جرِّب ي ثم و مكانه
        # ي أولاً لأن اختار (خير) أشيع من اختار (خور) في الاستخدام
        cands.append(f + "ي" + lam)
        cands.append(f + "و" + lam)
    elif base[3] not in _WEAK:
        ain = base[3]
        cands.append(f + ain + lam)
        # ناقص: اللام حرف علة
        if lam in ("و", "ي"):
            other = "و" if lam == "ي" else "ي"
            cands.append(f + ain + other)
        # أجوف: الفاء حرف علة
        if f in ("و", "ي"):
            other = "و" if f == "ي" else "ي"
            cands.append(other + ain + lam)

    return cands


def candidates_from_word(word: str) -> list[str]:
    """
    أنتج مرشَّحات الجذر لكلمة واحدة بترتيب الثقة (الأعلى أولاً).
    """
    if not word:
        return []

    # تجريد الحركات مع الاحتفاظ بالهمزة المرسومة
    w = strip_harakat(word)
    if not w or len(w) < 2:
        return []

    # إصلاح الهمزة المتحمَّلة أولاً
    w = _fix_hamza_in_base(w)

    cands: list[str] = []

    # ── خطوة أولى: كشف الوزن III / VIII على الكلمة المجرَّدة من ال فقط ──
    # يمنع الاختيار الخاطئ حين تُجرِّد البادئة الكلمةَ إلى كلمتين فقط
    # مثال: اقتصد (5ح) → اقت مجرَّدة → صد (مقبول في المقاييس لكنه خطأ)
    # نضع مرشَّح الوزن VIII أولاً ليُختار قبل صد.
    w_noart = w[2:] if w.startswith("ال") else w
    if len(w_noart) == 5:
        for early_cand in _extract_form_iii_root(w_noart) + _extract_form_viii_root(w_noart):
            if early_cand not in cands:
                cands.append(early_cand)

    # كشف مصدر الوزن الثامن (اِفتِعال) - 6 حروف: ا+ف+ت+ع+ا+ل
    # مثال: اقتصاد → ق+ص+د = قصد  ،  اجتهاد → ج+ه+د = جهد
    # أزواج الإدغام في الوزن الثامن: فاء ∈ {ز,ذ} → ت تصبح د ، فاء ∈ {ض,ط,ص} → ت تصبح ط
    _ASSIM_PAIRS_VIII = {('ز','د'), ('ذ','د'), ('ض','ط'), ('ط','ط'), ('ص','ط')}
    if len(w_noart) == 6:
        b6 = w_noart
        # نمط عادي: ا+ف+ت+ع+ا+ل
        if (b6[0] in _HAMZAT_WASL and b6[2] == "ت" and b6[4] == "ا"
                and b6[1] not in _HAMZAT_WASL):
            f6, ain6, lam6 = b6[1], b6[3], b6[5]
            viii_masdar = f6 + ain6 + lam6
            if viii_masdar not in cands:
                cands.append(viii_masdar)
            # إذا كانت العين حرف مد، جرِّب البديل
            if ain6 in _WEAK:
                other6 = "و" if ain6 == "ي" else "ي"
                alt6 = f6 + other6 + lam6
                if alt6 not in cands:
                    cands.append(alt6)
        # Fix B — نمط الإدغام: ا+فاء+مُدغَم+عين+ا+لام
        # مثال: ازدهار→زهر ، اصطدام→صدم ، ازدحام→زحم ، اصطياد→صيد
        # الشرط: b6[1]≠همزة ، (b6[1],b6[2]) زوج إدغام صحيح
        if (b6[0] in _HAMZAT_WASL and b6[4] == "ا"
                and b6[1] not in _HAMZAT_WASL
                and (b6[1], b6[2]) in _ASSIM_PAIRS_VIII):
            root_assim = b6[1] + b6[3] + b6[5]
            if root_assim not in cands:
                cands.append(root_assim)
            # أجوف: العين ألف → جرِّب و/ي
            if b6[3] in _WEAK:
                other_a = "و" if b6[3] == "ي" else "ي"
                alt_a = b6[1] + other_a + b6[5]
                if alt_a not in cands:
                    cands.append(alt_a)
        # Fix C — مصدر الوزن السابع (اِنفِعال): ا+ن+فاء+عين+ا+لام → الجذر = b[2]+b[3]+b[5]
        # مثال: انطباع→طبع ، انطباق→طبق
        if (b6[0] in _HAMZAT_WASL and b6[1] == "ن" and b6[4] == "ا"):
            root_vii = b6[2] + b6[3] + b6[5]
            if root_vii not in cands:
                cands.append(root_vii)

    # ── جرِّد البادئات (مرحلتان) ───────────────────────────────
    # المرحلة الأولى: جرِّد بادئة من الكلمة الأصلية
    phase1: list[str] = []
    for pre in _PREFIXES_ORDERED:
        if w.startswith(pre) and len(w) > len(pre) + 1:
            phase1.append(w[len(pre):])
    phase1.append(w)

    # المرحلة الثانية: جرِّد بادئة ثانية من نتائج المرحلة الأولى
    # (تعالج نمط ال+مت+فعل مثل المتغيب → ال → متغيب → مت → غيب)
    bases_after_prefix: list[str] = list(phase1)
    for b in phase1:
        if b == w:
            continue
        for pre in _PREFIXES_ORDERED:
            if b.startswith(pre) and len(b) > len(pre) + 1:
                extra = b[len(pre):]
                if extra not in bases_after_prefix:
                    bases_after_prefix.append(extra)

    # رتِّب القواعد من الأقصر إلى الأطول حتى تُعطَى الأولوية للقواعد الأكثر أصالة
    bases_after_prefix.sort(key=len)

    for base in bases_after_prefix:
        # ── جرِّد اللواحق (الأقصر = الأقرب للجذر يُعالَج أولاً) ──
        seen_bases: set[str] = set()
        all_suf = _strip_suffix(base) + [base]
        bases_after_suffix = []
        for _b in sorted(all_suf, key=len):   # أقصر أولاً
            if _b not in seen_bases:
                seen_bases.add(_b)
                bases_after_suffix.append(_b)

        for b in bases_after_suffix:
            if not b:
                continue
            n = len(b)

            if 2 <= n <= 3:
                # كلمة 2-3 حروف → أضفها مباشرة
                cands.append(b)
                # الأجوف: إذا كانت 3 حروف والأوسط ألف، جرِّب و/ي بدلاً منه
                # شار → شور / شير ، قال → قول / قيل ، نام → نوم
                if n == 3 and b[1] == "ا":
                    cands.append(b[0] + "و" + b[2])
                    cands.append(b[0] + "ي" + b[2])
                # Fix D — ناقص بالواو: XYو → الجذر في المقاييس XYي
                # مثال: نمو → نمي (المقاييس يخزِّن الجذر بالياء)
                if n == 3 and b[2] == "و":
                    cands.append(b[0] + b[1] + "ي")
                # Fix F — أسماء القرابة وما شابهها: XYت → XYو / XYي
                # مثال: أخت → أخو ، بنت → بني (بنى في المقاييس)
                if n == 3 and b[2] == "ت":
                    cands.append(b[0] + b[1] + "و")
                    cands.append(b[0] + b[1] + "ي")
                # Fix G — الأجوف بالواو أو الياء في العين: XوZ / XيZ → XاZ والبديل
                # يحل: موت (من مستميت) ، حول (من مستحيل) ، طول (من مستطيل)
                # قوم (من المستقيم) ، موه (من مياه/ميّه) ، صوغ (من صيغة→صيغ)
                if n == 3 and b[1] in {"و", "ي"}:
                    cands.append(b[0] + "ا" + b[2])
                    alt_g = "ي" if b[1] == "و" else "و"
                    cands.append(b[0] + alt_g + b[2])

            elif n == 4:
                # كلمة 4 حروف → جرِّب حذف كل حرف لإعطاء 3-حروف
                for r3 in _extract_3letter_from_4(b):
                    cands.append(r3)
                    # الأجوف من الرباعي: إذا كانت النتيجة 3 حروف والأوسط ألف
                    # قاأل → قال → قول/قيل، نائم → ناأم → نام → نوم
                    if len(r3) == 3 and r3[1] == "ا":
                        cands.append(r3[0] + "و" + r3[2])
                        cands.append(r3[0] + "ي" + r3[2])
                # Fix A — مصدر فِعَاء من ناقص: X+Y+ا+أ (أصله X+Y+ا+ء)
                # مثال: غطاء→غطو ، رداء→ردى ، دعاء→دعو ، أداء→أدو ، سماء→سمو
                # الهمزة آخر الكلمة جاءت من ء في مصدر الناقص عبر _fix_hamza
                if b[2] == "ا" and b[3] == "أ":
                    cands.append(b[0] + b[1] + "و")
                    cands.append(b[0] + b[1] + "ي")
                # Fix E — وزن VIII من المضاعف: م+X+ت+Y → الجذر الثنائي XY
                # مثال: مبتز→بز ، ممتص→مص
                if b[0] == "م" and b[2] == "ت":
                    gem = b[1] + b[3]
                    cands.append(gem)
                # وأضف الكلمة كاملة للجذور الرباعية
                cands.append(b)

            elif n == 5:
                # كلمة 5 حروف → على الأرجح مزيدة
                #
                # الأولوية 1: وزن مُفاعِل (الوزن III) → b[0]='م', b[2]='ا'
                form_iii = _extract_form_iii_root(b)
                if form_iii:
                    cands.extend(form_iii)
                # الأولوية 2: وزن مُفتَعِل (الوزن VIII) → b[0]='م', b[2]='ت'
                form_viii = _extract_form_viii_root(b)
                if form_viii:
                    cands.extend(form_viii)
                # Fix H — مصدر الوزن الرابع (إفعال) من الناقص: ا+ف+ع+ا+ء → الجذر فعو/فعي
                # مثال: اغماء→غمي ، ادعاء→دعو
                # ملاحظة: _fix_hamza_in_base تحوّل ء إلى أ قبل الدخول، لذا نفحص أ أيضاً
                if b[0] in _HAMZAT_WASL and b[3] == "ا" and b[4] in {"ء", "أ"}:
                    root_h_w = b[1] + b[2] + "و"
                    root_h_y = b[1] + b[2] + "ي"
                    if root_h_w not in cands:
                        cands.append(root_h_w)
                    if root_h_y not in cands:
                        cands.append(root_h_y)
                # الأولوية 3: حذف حروف المد الداخلية
                for i in range(1, n - 1):
                    if b[i] in _WEAK:
                        reduced = b[:i] + b[i+1:]
                        if len(reduced) == 4:
                            for r3 in _extract_3letter_from_4(reduced):
                                cands.append(r3)
                                # الأجوف من الرباعي
                                if len(r3) == 3 and r3[1] == "ا":
                                    cands.append(r3[0] + "و" + r3[2])
                                    cands.append(r3[0] + "ي" + r3[2])
                        elif len(reduced) == 3:
                            cands.append(reduced)
                            if reduced[1] == "ا":
                                cands.append(reduced[0] + "و" + reduced[2])
                                cands.append(reduced[0] + "ي" + reduced[2])
                # أول 3 حروف كاحتياطي
                cands.append(b[:3])

            elif n >= 6:
                # كلمة 6+ حروف → وزن مزيد كثير الحروف
                start = 2 if b.startswith("ال") else 0

                # الأولوية: مصدر الوزن الثامن (اِفتِعال) - 6 حروف بعد إزالة البادئة
                # مثال: اجتماع→جمع ، اقتصاد→قصد ، اقتراح→قرح
                if n == 6 and b[0] in _HAMZAT_WASL and b[2] == "ت" and b[4] == "ا" and b[1] not in _HAMZAT_WASL:
                    f6, ain6, lam6 = b[1], b[3], b[5]
                    cands.append(f6 + ain6 + lam6)
                    if ain6 in _WEAK:
                        cands.append(f6 + ("و" if ain6 == "ي" else "ي") + lam6)
                # Fix B (n>=6 branch) — إدغام الوزن الثامن: ا+فاء+مُدغَم+عين+ا+لام
                if n == 6 and b[0] in _HAMZAT_WASL and b[4] == "ا" and b[1] not in _HAMZAT_WASL and (b[1], b[2]) in _ASSIM_PAIRS_VIII:
                    root_a = b[1] + b[3] + b[5]
                    if root_a not in cands:
                        cands.append(root_a)
                    if b[3] in _WEAK:
                        other_b = "و" if b[3] == "ي" else "ي"
                        alt_b = b[1] + other_b + b[5]
                        if alt_b not in cands:
                            cands.append(alt_b)
                # Fix C (n>=6 branch) — مصدر الوزن السابع: ا+ن+فاء+عين+ا+لام
                if n == 6 and b[0] in _HAMZAT_WASL and b[1] == "ن" and b[4] == "ا":
                    root_c = b[2] + b[3] + b[5]
                    if root_c not in cands:
                        cands.append(root_c)

                # تجاوز ال إن كانت البداية بها لتفادي جذور زائفة مثل (الق→ألق)
                for slice_start in (start, start + 1):
                    sliced = b[slice_start:slice_start + 3]
                    if len(sliced) == 3:
                        cands.append(sliced)
                        # الأجوف: الأوسط ألف → جرِّب و/ي
                        if sliced[1] == "ا":
                            cands.append(sliced[0] + "و" + sliced[2])
                            cands.append(sliced[0] + "ي" + sliced[2])
                # جرِّب الشرائح الأعمق للكلمات الطويلة جداً
                if n >= 8:
                    extra = b[start + 2:start + 5]
                    if len(extra) == 3:
                        cands.append(extra)

    # ── إزالة التكرار والقصير جداً ──────────────────────────────
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        c = c.strip()
        if c and len(c) >= 2 and c not in seen and c not in _PARTICLES:
            seen.add(c)
            out.append(c)

    # ── توسعة المضاعف: XYY → XY (الجذر الثنائي في المقاييس) ──────
    # جذور كثيرة في المقاييس ثنائية: غش، حر، أس، فز، كر…
    # الكلمات المضاعفة تُولِّد مرشَّحاً XYY لا يُوجَد في المقاييس،
    # فنُضيف XY كبديل ذي أولوية منخفضة.
    geminate_extras: list[str] = []
    for c in out:
        if len(c) == 3 and c[1] == c[2] and c[:2] not in seen:
            geminate_extras.append(c[:2])
            seen.add(c[:2])
    out.extend(geminate_extras)

    return out


# ══════════════════════════════════════════════════════════════════
# اختيار الجذر من قائمة كلمات الـ synset
# ══════════════════════════════════════════════════════════════════

_ARABIC_RE = re.compile(r"[؀-ۿ]")


def _is_arabic(word: str) -> bool:
    return bool(_ARABIC_RE.search(word))


def _is_proper_name(word: str) -> bool:
    """هل هذه كلمة أعجمية / اسم علم لا جذر عربي؟"""
    w = strip_harakat(word)
    # كلمات قصيرة جداً أو لا تحتوي على حروف عربية كافية
    arabic_chars = [c for c in w if "؀" <= c <= "ۿ"]
    if len(arabic_chars) < 2:
        return True
    # إذا كانت الكلمة تنتهي بحرف أعجمي
    if w and ("A" <= w[-1] <= "z"):
        return True
    return False


def extract_root_for_maqayis(
    words: list[str],
    idx: MaqayisIndex,
) -> tuple[Optional[str], str, str]:
    """
    استخرج الجذر الأمثل من قائمة كلمات الـ synset ووثِّقه من المقاييس.

    المخرج: (الجذر_المصحَّح، الحالة، الكلمة_المصدر)
    الحالة: maqayis_verified | not_found | no_arabic
    """
    arabic_words = [
        w.strip() for w in words
        if w and _is_arabic(w) and not _is_proper_name(w)
    ]

    if not arabic_words:
        return None, "no_arabic", ""

    # رتِّب: الكلمات الأقصر أولاً (أقل احتمالاً لكونها عبارات مركَّبة)
    arabic_words_sorted = sorted(arabic_words, key=lambda x: len(x.split()))

    best_candidate: Optional[str] = None
    best_word = ""

    for word in arabic_words_sorted:
        tokens = word.split()

        # جرِّب كل رمز في العبارة (بغضّ النظر عن طولها)
        # يُعالج الترجمات متعددة الكلمات مثل "وحدة المعالجة المركزي"
        first_cands_in_phrase: Optional[tuple[str, str]] = None  # (cands[0], token)

        for token in tokens:
            # تجاوز الأدوات والأسماء الأعجمية
            token_norm = normalize_for_match(token)
            if token_norm in _PARTICLES or _is_proper_name(token):
                continue

            cands = candidates_from_word(token)

            # احفظ أول رمز معبِّر كمرشَّح احتياطي
            if first_cands_in_phrase is None and cands:
                first_cands_in_phrase = (cands[0], token)

            # ابحث عن تطابق في المقاييس
            for cand in cands:
                result = lookup(cand, idx)
                if result:
                    return result, "maqayis_verified", token

        # لم يُسفر أيّ رمز في هذه العبارة عن تطابق
        if best_candidate is None and first_cands_in_phrase:
            best_candidate, best_word = first_cands_in_phrase

    # لم نجد تطابقاً
    return best_candidate, "not_found", best_word


# ══════════════════════════════════════════════════════════════════
# المعالجة الرئيسية
# ══════════════════════════════════════════════════════════════════

@dataclass
class CorrectionResult:
    synset_id:   str
    old_roots:   list[str]
    new_root:    Optional[str]
    status:      str
    source_word: str


def correct_noun_tree(
    synmap_path: str,
    db_path: str,
) -> tuple[dict, list[CorrectionResult]]:
    idx = load_maqayis_index(db_path)

    with open(synmap_path, encoding="utf-8") as f:
        synmap: dict = json.load(f)

    results: list[CorrectionResult] = []
    corrected_map: dict = {}

    for synset_id, entry in synmap.items():
        words     = entry.get("words", [])
        old_roots = entry.get("roots", [])

        if ".n." not in synset_id:
            corrected_map[synset_id] = entry
            continue

        new_root, status, src_word = extract_root_for_maqayis(words, idx)

        new_entry = dict(entry)
        if status == "maqayis_verified" and new_root:
            new_entry["roots"]       = [new_root]
            new_entry["root_conf"]   = "maqayis"
            new_entry["root_source"] = "maqayis_verified"
        else:
            new_entry["root_source"] = status

        corrected_map[synset_id] = new_entry

        results.append(CorrectionResult(
            synset_id   = synset_id,
            old_roots   = list(old_roots),
            new_root    = new_root,
            status      = status,
            source_word = src_word,
        ))

    return corrected_map, results


def run(
    synmap_path: str = "/root/hokom/pipeline/taaqol_integration/arabic_synset_map.json",
    db_path:     str = "/root/maqayis_v2/maqayis.db",
    out_path:    str = "/root/hokom/pipeline/taaqol_integration/arabic_synset_map_corrected.json",
    report_path: str = "/root/word_tree/data/noun_root_correction_report.json",
) -> dict:

    print("تحميل المقاييس...")
    idx = load_maqayis_index(db_path)
    print(f"  {len(idx.raw):,} جذر")

    print("تصحيح شجرة الأسماء...")
    corrected_map, results = correct_noun_tree(synmap_path, db_path)

    verified  = [r for r in results if r.status == "maqayis_verified"]
    not_found = [r for r in results if r.status == "not_found"]
    no_arabic = [r for r in results if r.status == "no_arabic"]
    changed   = [
        r for r in verified
        if sorted(r.old_roots) != sorted([r.new_root] if r.new_root else [])
    ]

    stats = {
        "total_noun_synsets":   len(results),
        "maqayis_verified":     len(verified),
        "not_found_in_maqayis": len(not_found),
        "no_arabic_words":      len(no_arabic),
        "roots_actually_changed": len(changed),
        "coverage_pct":         round(100 * len(verified) / max(1, len(results)), 1),
    }

    print(f"\n{'─'*50}")
    print(f"إجمالي الأسماء:            {stats['total_noun_synsets']:,}")
    print(f"مُتحقَّق من المقاييس:       {stats['maqayis_verified']:,}  ({stats['coverage_pct']}%)")
    print(f"لم يُوجَد في المقاييس:     {stats['not_found_in_maqayis']:,}")
    print(f"بلا كلمات عربية:           {stats['no_arabic_words']:,}")
    print(f"جذور تغيَّرت فعلياً:       {stats['roots_actually_changed']:,}")

    print(f"\nحفظ النتائج...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corrected_map, f, ensure_ascii=False, separators=(",", ":"))

    import os
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    # عيِّنة من التغييرات
    corrected_examples = [
        {
            "synset":    r.synset_id,
            "old":       r.old_roots,
            "new":       r.new_root,
            "src_word":  r.source_word,
        }
        for r in changed[:200]
    ]
    # عيِّنة من not_found
    not_found_examples = [
        {
            "synset":   r.synset_id,
            "src_word": r.source_word,
            "old":      r.old_roots,
        }
        for r in not_found[:200]
    ]

    report = {
        "stats": stats,
        "corrected_sample":  corrected_examples,
        "not_found_sample":  not_found_examples,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✓ {out_path}")
    print(f"  ✓ {report_path}")
    return stats


if __name__ == "__main__":
    run()
