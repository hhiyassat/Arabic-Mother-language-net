"""
kind_tagger.py — يَسِم خاصيّة «فَعُلَ» بقسمها من أقسام الكيف عند الجرجاني (التعريفات، الكيف):
  MAHSUSA  كيفيّة محسوسة (في جسم)      ·  NAFSANIYYA كيفيّة نفسانيّة (ملكة)
  BOTH     يُستعمل في الجسم والنفس معاً   ·  NONE لا قرينة
القرينة: شرح المعجم للرأس المشكول نفسه (فَعُلَ)، وما فيه من فاعلٍ جسمٍ أو علامةٍ نفسانيّة. CANDIDATE.
"""
import re
import measure_routes as M

BODY = re.compile(r"(?:^|[\s(])(?:ال)?(?:شء|شيء|شىء|شئ|ماء|طعام|شراب|صوت|مكان|لون|بناء|ثوب|أرض|ارض|جسم|جسمه|مرتع|لبن|جلد|حجر|عود|خشب|حديد|نبات|شجر|ريح|هواء|ليل|نهار)[ُِ]?(?=[\s.،:-]|$)")
SOUL = re.compile(r"(عقل|رأي|رأْي|ذهن|ذكاء|ظرف|ظَرُف|حذق|حَذَق|جبن|شجع|شجاع|حلم|حلُم|وقر|وَقُر|لسان|خُلُق|خلق|كيس|كيّس|منزلت|فطن|حياء|كرم|بخل|صبر|زهد|تعبّد|تعبد|فقيه|حكيم|ناسك|عالم|جريء|جرئ)")
SAR = re.compile(r"صار\s+[^\s.،]+")


def exact_glosses(idx, verb):
    hs = idx.get(M.strip(verb), [])
    return [h[2] for h in hs if M.nfc(h[1]).rstrip("َ") == M.nfc(verb).rstrip("َ")]


def tag(glosses):
    if not glosses:
        return "NONE", ""
    t = " ".join(glosses)
    b = bool(BODY.search(t))
    s = bool(SOUL.search(t)) or bool(SAR.search(t) and not b)
    if b and s:
        return "BOTH", t[:120]
    if b:
        return "MAHSUSA", t[:120]
    if s:
        return "NAFSANIYYA", t[:120]
    return "NONE", t[:120]
