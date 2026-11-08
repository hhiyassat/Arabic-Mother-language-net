"""المانع بالتعريف (R2 v5، 2026-11-08؛ المالك: «اعمل كل هذا بنفس شروطي»).

المانع في ahdath.py (MANI_GROUPS) يحكم بلفظ الفعل وحده. وما فاته في عيّنات R2 (عَشِقَ، ذَهَلَ، طَبَا…) يعرّفه الوسيط
بفعلٍ من المانع نفسه: «عَشِقَه: أحبَّه أشدَّ الحبّ»، «ذَهَلَه: نسيَه»، «طَبَاه: دعاه». والتعريف في المعجم تفسيرٌ بالمرادف،
فيأخذ المعرَّف حكم المعرِّف.

السند في القسمة نفسها:
  سيبويه، الكتاب (الشاملة 23018، ص456): «العمل الثابت الذي ليس فيه علاجٌ يرونه، نحو الآخذ واللازم والمخالط»
     في مقابل «ما كان علاجاً يرونه، نحو الضارب والكاسر».
  ابن مالك، التسهيل (تمهيد القواعد لناظر الجيش، الشاملة 16826، ص3703): «ومنها انفعل لمطاوعة فَعَل علاجاً».
  الجرجاني، التعريفات، والكفوي، الكليات (منقولان في ahdath.py عند MANI_GROUPS).

القاعدة (ثابتة قبل القياس، ولا تُعدَّل بعده): يُطلب الفعل في الوسيط (رأسٌ يطابقه، أو هو وضمير المفعول)، ويؤخذ
تعريف معناه الأوّل (ما بعد «:»)، وأوّل كلمة فيه بلا واو العطف ولا ضمير المفعول؛ فإن كانت فعلاً في MANI_GROUPS
(بلفظها لا بزيادة)، أخذ الفعل اسم مجموعتها بادئةً بـ GLOSS:. القائمة لا يُزاد فيها شيء هنا.
"""
import re
import ahdath as A
import taadiya as TD
from ext import wasit_frames as WF

_W = None


def _w():
    global _W
    if _W is None:
        _W = TD.wasit_index()
    return _W


def first_gloss_head(root: str, verb: str) -> str:
    vb = WF.bare(verb)
    for head, text in _w().get(WF.bare(root), []):
        hw = head.split()[0] if head.split() else ""
        hb = WF.bare(hw)
        if (hb == vb or hb in (vb + "ه", vb + "ها")) and WF.compatible(hw, verb):
            for fr in WF.SPLIT.split(text):
                if ":" not in fr:
                    continue
                d = fr.split(":", 1)[1].strip(" /.-_،")
                tok = d.split()[0] if d.split() else ""
                t = A.bare(tok).replace("ٱ", "ا")
                t = re.sub(r"^[وف](?=..)", "", t)
                t = re.sub(r"(?<=..)(هما|هم|هن|ها|ه)$", "", t)
                return t
    return ""


def gloss_mani(root: str, verb: str) -> str:
    h = first_gloss_head(root, verb)
    if not h:
        return ""
    for g, (vs, _) in A.MANI_GROUPS.items():
        if h in vs:
            return "GLOSS:" + g
    return ""
