"""
word_identity_analyzer.py — المحلل الرئيسي للهوية الجوهرية
ARABIC INTRINSIC WORD IDENTITY PROGRAM — نقطة الدخول الوحيدة

analyze_word(surface) → WordIdentityCertificate

المبادئ:
  • SILENT_FIRST_HIT_SELECTION = 0 — نُظهر جميع المرشحين
  • DOWNSTREAM_BACKFLOW = 0        — لا يُستخدم ناتج Hokom كدليل
  • CONTEXTUAL_GRAMMAR = NO        — لا إعراب هنا
  • DUAL_FACT_PRODUCER = 0         — هذا الملف هو المنتج الوحيد للهوية
  • الغموض محفوظ حتى يُحسمه دليل مُرخَّص
"""
from __future__ import annotations
import os
import re
import sqlite3
from functools import lru_cache
from typing import Optional

import pandas as pd

from word_tree.word_identity_types import (
    WordClass, WordClassConfidence,
    DerivedFormType, NumeralType,
    EvidenceRef, EvidenceSource,
    CertificationLevel,
    RootCandidate, RootAnalysis,
    MorphologicalIdentity, DerivationalIdentity,
    LexicalIdentity, NumeralIdentity,
    AmbiguityReport, Residuals, ResidualGap,
    WordIdentityCertificate,
)
from word_tree.word_class_engine import classify_word_class, normalize_surface, strip_diacritics
from word_tree.numeral_engine import classify_numeral
from word_tree.sifa_engine import (
    analyze_derived_form, build_morphological_identity, build_derivational_identity
)


# ══════════════════════════════════════════════════════════════════════
# المسارات الافتراضية
# ══════════════════════════════════════════════════════════════════════

_DEFAULT_DB_PATH  = "/root/maqayis_v2/maqayis.db"
_DEFAULT_CSV_PATH = (
    "/root/.claude/uploads/"
    "0d4fec3c-f650-561d-941a-a2d13065c603/"
    "4fd7ad7b-audited_roots.csv"
)

# مُبادِئ الأحرف الناقصة في مقاييس (MISSING_VOLUME)
_MAQAYIS_MISSING_INITIALS = frozenset(['ا', 'ب', 'ت', 'ث', 'ج'])


# ══════════════════════════════════════════════════════════════════════
# تحميل البيانات المرجعية (مرة واحدة)
# ══════════════════════════════════════════════════════════════════════

class _DataStore:
    """حامل البيانات المرجعية الثلاثة"""
    _instance: Optional["_DataStore"] = None

    def __init__(self, db_path: str, csv_path: str):
        # محرك البحث عن الجذر
        from word_tree.engines.noun_root_corrector import load_maqayis_index, lookup, candidates_from_word
        self.maqayis_index = load_maqayis_index(db_path)
        self._lookup       = lookup
        self._candidates   = candidates_from_word
        self._db_path      = db_path

        # جذور FAU_YAF_U من CSV
        self.fau_yaf_u_roots: set[str] = set()
        self.root_baab_map:   dict[str, str] = {}   # root → baab code
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                root = str(row['الجذر']).strip()
                baab_raw = str(row['باب الصرفي']).strip()
                baab_code = _map_baab(baab_raw)
                # إذا كان الجذر له أكثر من باب، نحتفظ بـ FAU_YAF_U إن وُجد
                if baab_code == "FAU_YAF_U" or root not in self.root_baab_map:
                    self.root_baab_map[root] = baab_code
                if baab_code == "FAU_YAF_U":
                    self.fau_yaf_u_roots.add(root)

    @classmethod
    def get(cls, db_path: str = _DEFAULT_DB_PATH, csv_path: str = _DEFAULT_CSV_PATH) -> "_DataStore":
        if cls._instance is None:
            cls._instance = cls(db_path, csv_path)
        return cls._instance

    def candidates_from_word(self, word: str) -> list[str]:
        return self._candidates(word)

    def lookup(self, candidate: str) -> Optional[str]:
        return self._lookup(candidate, self.maqayis_index)

    def get_baab(self, root: str) -> Optional[str]:
        return self.root_baab_map.get(root)


def _map_baab(raw: str) -> str:
    """حوِّل نص الباب من CSV إلى رمز قصير"""
    if 'ضم' in raw and raw.count('ضم') >= 2:
        return "FAU_YAF_U"
    if 'فتح' in raw and 'ضم' in raw:
        return "FAA_YAF_U"
    if 'فتح' in raw and 'كسر' in raw:
        return "FAA_YAF_I"
    if 'كسر' in raw and 'فتح' in raw:
        return "FAI_YAF_A"
    if 'فتحتان' in raw:
        return "FAA_YAF_A"
    return "UNKNOWN"


# ══════════════════════════════════════════════════════════════════════
# الهوية المعجمية من مقاييس
# ══════════════════════════════════════════════════════════════════════

def _build_lexical_identity(resolved_root: Optional[str], store: _DataStore) -> LexicalIdentity:
    """استعلم مقاييس عن الجذر وأرجع LexicalIdentity"""
    if not resolved_root:
        return LexicalIdentity(
            root=None,
            axes_texts=[],
            axes_count=0,
            body_snippet="",
            coverage_status="NOT_FOUND",
        )

    # تحقق: هل الحرف الأول من الأحرف الناقصة؟
    normed_root = re.sub(r'[أإآ]', 'ا', resolved_root)
    first_char = normed_root[0] if normed_root else ''
    if first_char in _MAQAYIS_MISSING_INITIALS:
        # قد يكون موجوداً رغم ذلك — نتحقق فعلياً
        pass  # نكمل البحث ونُصنِّف بعدها

    try:
        conn = sqlite3.connect(store._db_path)
        row = conn.execute(
            "SELECT id, body_text, axes_count FROM entries WHERE root_display = ?",
            (resolved_root,)
        ).fetchone()
        if row is None:
            # جرب root_letters
            two = resolved_root[:2] if len(resolved_root) >= 2 else resolved_root
            row = conn.execute(
                "SELECT id, body_text, axes_count FROM entries WHERE root_letters = ? AND root_display = ?",
                (two, resolved_root)
            ).fetchone()
        if row is None:
            conn.close()
            status = "MISSING_VOLUME" if first_char in _MAQAYIS_MISSING_INITIALS else "NOT_FOUND"
            return LexicalIdentity(
                root=resolved_root,
                axes_texts=[],
                axes_count=0,
                body_snippet="",
                coverage_status=status,
            )

        entry_id, body_text, axes_count = row
        # استعلم المحاور
        axes = conn.execute(
            "SELECT axis_text FROM semantic_axes WHERE entry_id = ?",
            (entry_id,)
        ).fetchall()
        conn.close()

        axes_texts = [a[0] for a in axes if a[0]]
        body_snippet = (body_text or "")[:300]
        ac = axes_count or len(axes_texts)

        evidence = [EvidenceRef(
            source=EvidenceSource.MAQAYIS_DB,
            detail=f"جذر '{resolved_root}' موجود في مقاييس ابن فارس",
            value=f"محاور:{ac}",
            weight=1.0,
        )]
        return LexicalIdentity(
            root=resolved_root,
            axes_texts=axes_texts,
            axes_count=ac,
            body_snippet=body_snippet,
            coverage_status="COVERED",
            evidence=evidence,
        )

    except Exception as exc:
        return LexicalIdentity(
            root=resolved_root,
            axes_texts=[],
            axes_count=0,
            body_snippet=str(exc),
            coverage_status="NOT_FOUND",
        )


# ══════════════════════════════════════════════════════════════════════
# تحليل الجذر (SILENT_FIRST_HIT_SELECTION = 0)
# ══════════════════════════════════════════════════════════════════════

def _build_root_analysis(surface: str, store: _DataStore) -> RootAnalysis:
    """
    ابنِ RootAnalysis — اعرض جميع المرشحين دون اختيار صامت.
    """
    stripped = strip_diacritics(surface)
    normed   = re.sub(r'[أإآ]', 'ا', stripped)

    raw_candidates = store.candidates_from_word(stripped)
    candidates: list[RootCandidate] = []

    for rank, cand in enumerate(raw_candidates, start=1):
        maqayis_result = store.lookup(cand)
        is_maq = maqayis_result is not None
        baab = store.get_baab(maqayis_result or cand) if is_maq else None

        ev: list[EvidenceRef] = []
        if is_maq:
            ev.append(EvidenceRef(
                source=EvidenceSource.MAQAYIS_DB,
                detail=f"'{cand}' موجود في مقاييس → '{maqayis_result}'",
                value=maqayis_result or cand,
                weight=max(0.3, 1.0 - rank * 0.1),
            ))
        if baab:
            ev.append(EvidenceRef(
                source=EvidenceSource.AUDITED_ROOTS_CSV,
                detail=f"باب '{cand}' = {baab}",
                value=baab,
                weight=0.8,
            ))

        # §3: assign certification_level per candidate
        if is_maq:
            cand_level = CertificationLevel.EVIDENCE_SUPPORTED  # single source → not CERTIFIED
        else:
            cand_level = CertificationLevel.CANDIDATE

        candidates.append(RootCandidate(
            root=maqayis_result or cand,
            is_maqayis=is_maq,
            rank=rank,
            algorithm_src="noun_root_corrector.candidates_from_word",
            baab=baab,
            certification_level=cand_level,
            evidence=ev,
        ))

    # المرشحون المقاييس فقط (مرتَّبون بالرتبة)
    maq_candidates = [c for c in candidates if c.is_maqayis]

    # الجذر المحسوم
    # §3 SILENT_SINGLE_CANDIDATE_PROMOTION = 0:
    #   مرشح واحد في مقاييس → EVIDENCE_SUPPORTED لا CERTIFIED
    #   يتطلب CERTIFIED: دليلان مستقلان (مقاييس + مطابقة وزن مثلاً)
    resolved = None
    ambiguous = False
    analysis_cert_level = CertificationLevel.UNRESOLVED

    if len(maq_candidates) == 1:
        resolved = maq_candidates[0].root
        analysis_cert_level = CertificationLevel.EVIDENCE_SUPPORTED  # NOT CERTIFIED — single source
    elif len(maq_candidates) == 0:
        # أول مرشح خوارزمي
        resolved = candidates[0].root if candidates else None
        analysis_cert_level = CertificationLevel.CANDIDATE
    else:
        # تعدد في مقاييس → غموض حقيقي (المبدأ: الغموض محفوظ)
        resolved = maq_candidates[0].root   # الأقوى رتبةً للإشارة
        ambiguous = True
        analysis_cert_level = CertificationLevel.CANDIDATE  # ambiguous = not promotable

    # تغطية
    if not candidates:
        coverage = "NO_ARABIC"
    elif not maq_candidates:
        first_char = normed[0] if normed else ''
        coverage = "MISSING_VOLUME" if first_char in _MAQAYIS_MISSING_INITIALS else "NOT_FOUND"
    else:
        coverage = "COVERED"

    return RootAnalysis(
        candidates=candidates,
        resolved_root=resolved,
        ambiguous=ambiguous,
        coverage=coverage,
        certification_level=analysis_cert_level,
    )


# ══════════════════════════════════════════════════════════════════════
# تقرير الغموض
# ══════════════════════════════════════════════════════════════════════

def _build_ambiguity(
    root_analysis: RootAnalysis,
    word_class: WordClass,
    word_class_conf: WordClassConfidence,
    numeral: NumeralIdentity,
) -> AmbiguityReport:
    sources = []
    candidate_roots = [c.root for c in root_analysis.candidates if c.is_maqayis]

    if root_analysis.ambiguous:
        sources.append("ROOT_AMBIGUITY")

    if word_class_conf == WordClassConfidence.AMBIGUOUS:
        sources.append("WORD_CLASS_AMBIGUITY")
    elif word_class_conf == WordClassConfidence.PROBABLE and word_class != WordClass.HARF:
        sources.append("WORD_CLASS_PROBABLE")

    has = bool(sources)
    resolution = has and ("WORD_CLASS_AMBIGUITY" in sources)  # قد يحتاج سياق إعرابي

    return AmbiguityReport(
        has_ambiguity=has,
        ambiguity_sources=sources,
        candidate_roots=candidate_roots,
        candidate_classes=[word_class] if not has else [WordClass.ISM, WordClass.FI3L],
        resolution_available=not has,
        resolution_note=(
            "يتطلب سياقاً إعرابياً" if "WORD_CLASS_AMBIGUITY" in sources
            else ("جذور متعددة في مقاييس" if "ROOT_AMBIGUITY" in sources else "محسوم")
        ),
    )


# ══════════════════════════════════════════════════════════════════════
# المحلل الرئيسي
# ══════════════════════════════════════════════════════════════════════

def analyze_word(
    surface: str,
    db_path: str = _DEFAULT_DB_PATH,
    csv_path: str = _DEFAULT_CSV_PATH,
) -> WordIdentityCertificate:
    """
    المحلل الرئيسي: surface → WordIdentityCertificate

    الخطوات:
      1. تطبيع السطح
      2. تصنيف WORD_CLASS
      3. فحص NUMERAL_IDENTITY
      4. تحليل الجذر (جميع المرشحين)
      5. الهوية المعجمية
      6. الصيغة الاشتقاقية + الصرفية
      7. الهوية الاشتقاقية
      8. تقرير الغموض
      9. المخلفات
    """
    store = _DataStore.get(db_path, csv_path)
    all_evidence: list[EvidenceRef] = []

    # 1. التطبيع
    normalized = normalize_surface(surface)

    # 2. WORD_CLASS
    word_class, wc_conf, wc_evidence = classify_word_class(surface)
    all_evidence.extend(wc_evidence)

    # 3. NUMERAL_IDENTITY
    numeral = classify_numeral(surface)
    if numeral.is_numeral:
        # الأعداد أسماء دائماً
        if word_class != WordClass.ISM:
            word_class = WordClass.ISM
            wc_conf    = WordClassConfidence.CERTAIN
        all_evidence.extend(numeral.evidence)

    # 4. تحليل الجذر
    root_analysis = _build_root_analysis(surface, store)
    for cand in root_analysis.candidates:
        all_evidence.extend(cand.evidence)

    resolved_root = root_analysis.resolved_root
    root_baab = store.get_baab(resolved_root) if resolved_root else None

    # 5. الهوية المعجمية
    lexical = _build_lexical_identity(resolved_root, store)
    all_evidence.extend(lexical.evidence)

    # 6. الصيغة الاشتقاقية
    derived_form, form_evidence = analyze_derived_form(
        surface=surface,
        resolved_root=resolved_root,
        root_baab=root_baab,
        fau_yaf_u_roots=store.fau_yaf_u_roots,
    )
    all_evidence.extend(form_evidence)

    # 7. الهوية الصرفية والاشتقاقية
    morph = build_morphological_identity(surface, derived_form, form_evidence)
    deriv = build_derivational_identity(
        surface=surface,
        resolved_root=resolved_root,
        root_baab=root_baab,
        derived_form=derived_form,
        form_evidence=form_evidence,
        fau_yaf_u_roots=store.fau_yaf_u_roots,
    )

    # 8. الغموض
    ambiguity = _build_ambiguity(root_analysis, word_class, wc_conf, numeral)

    # 9. المخلفات — §9: كل فجوة موثَّقة كـ ResidualGap وEvidenceRef(UNRESOLVED)
    gaps: list[ResidualGap] = []
    residual_notes: list[str] = []

    if resolved_root is None:
        g = ResidualGap(
            gap_id="MISSING_ROOT",
            description="لم يُعثر على جذر في مقاييس أو عبر الخوارزمية",
            first_missing_owner="LAYER_7_HOKOM أو إثراء مقاييس",
            failed_evidence="noun_root_corrector.candidates_from_word → 0 candidates",
            severity="BLOCK",
        )
        gaps.append(g)
        all_evidence.append(EvidenceRef(
            source=EvidenceSource.UNRESOLVED,
            detail=g.description,
            value=f"FIRST_MISSING_OWNER={g.first_missing_owner} | FAILED_EVIDENCE={g.failed_evidence}",
            weight=0.0,
        ))

    if word_class == WordClass.UNKNOWN:
        g = ResidualGap(
            gap_id="UNRESOLVED_CLASS",
            description="تصنيف الكلمة (اسم/فعل/حرف) لم يُحسم",
            first_missing_owner="LAYER_6_IRAB أو سياق جملة",
            failed_evidence="word_class_engine: لا شواهد حاسمة",
            severity="WARN",
        )
        gaps.append(g)
        all_evidence.append(EvidenceRef(
            source=EvidenceSource.UNRESOLVED,
            detail=g.description,
            value=f"FIRST_MISSING_OWNER={g.first_missing_owner} | FAILED_EVIDENCE={g.failed_evidence}",
            weight=0.0,
        ))

    if root_baab is None and resolved_root is not None:
        g = ResidualGap(
            gap_id="UNKNOWN_BAAB",
            description=f"الجذر '{resolved_root}' لم يُعثر على بابه في audited_roots.csv",
            first_missing_owner="audited_roots.csv (إثراء) أو LAYER_7_HOKOM",
            failed_evidence=f"audited_roots.csv: الجذر '{resolved_root}' غير موجود في العمود 'الجذر'",
            severity="WARN",
        )
        gaps.append(g)
        all_evidence.append(EvidenceRef(
            source=EvidenceSource.UNRESOLVED,
            detail=g.description,
            value=f"FIRST_MISSING_OWNER={g.first_missing_owner} | FAILED_EVIDENCE={g.failed_evidence}",
            weight=0.0,
        ))

    if root_analysis.coverage == "MISSING_VOLUME":
        note = f"الجذر '{resolved_root}' يبدأ بحرف من الأحرف الناقصة في مقاييس (ا/ب/ت/ث/ج)"
        residual_notes.append(note)
        g = ResidualGap(
            gap_id="MISSING_VOLUME",
            description=note,
            first_missing_owner="مقاييس ابن فارس (المجلدات الناقصة) أو مصدر معجمي بديل",
            failed_evidence=f"maqayis.db: الجذر '{resolved_root}' — حرف أول ناقص في الطبعة",
            severity="INFO",
        )
        gaps.append(g)
        all_evidence.append(EvidenceRef(
            source=EvidenceSource.UNRESOLVED,
            detail=g.description,
            value=f"FIRST_MISSING_OWNER={g.first_missing_owner} | FAILED_EVIDENCE={g.failed_evidence}",
            weight=0.0,
        ))

    if derived_form == DerivedFormType.UNKNOWN:
        g = ResidualGap(
            gap_id="NO_DERIVATION_PATH",
            description="لا مسار اشتقاقي واضح من الجذر إلى السطح",
            first_missing_owner="sifa_engine / derivation_engine (توسيع الأوزان)",
            failed_evidence="analyze_derived_form → DerivedFormType.UNKNOWN",
            severity="WARN",
        )
        gaps.append(g)
        all_evidence.append(EvidenceRef(
            source=EvidenceSource.UNRESOLVED,
            detail=g.description,
            value=f"FIRST_MISSING_OWNER={g.first_missing_owner} | FAILED_EVIDENCE={g.failed_evidence}",
            weight=0.0,
        ))

    if root_analysis.ambiguous:
        note = f"تعدد المرشحين في مقاييس: {[c.root for c in root_analysis.candidates if c.is_maqayis]}"
        residual_notes.append(note)

    residuals = Residuals(
        unresolved_root=resolved_root is None,
        unresolved_class=word_class == WordClass.UNKNOWN,
        unknown_baab=root_baab is None and resolved_root is not None,
        missing_volume=root_analysis.coverage == "MISSING_VOLUME",
        no_derivation_path=derived_form == DerivedFormType.UNKNOWN,
        gaps=gaps,
        notes=residual_notes,
    )

    return WordIdentityCertificate(
        original_surface=surface,
        normalized_surface=normalized,
        word_class=word_class,
        word_class_confidence=wc_conf,
        root_analysis=root_analysis,
        morphological_identity=morph,
        derivational_identity=deriv,
        lexical_identity=lexical,
        numeral_identity=numeral,
        ambiguity=ambiguity,
        evidence=all_evidence,
        residuals=residuals,
    )


# ══════════════════════════════════════════════════════════════════════
# طباعة التقرير
# ══════════════════════════════════════════════════════════════════════

def print_certificate(cert: WordIdentityCertificate, compact: bool = False) -> None:
    """اطبع الشهادة بتنسيق مقروء"""
    r = cert.root_analysis
    d = cert.derivational_identity
    m = cert.morphological_identity
    lx = cert.lexical_identity
    n = cert.numeral_identity

    print(f"\n{'═'*60}")
    print(f"  الكلمة: {cert.original_surface}   (مطبَّع: {cert.normalized_surface})")
    print(f"{'═'*60}")
    print(f"  التصنيف  : {cert.word_class.value}  [{cert.word_class_confidence.value}]")

    # جذر
    root_str = r.resolved_root or "—"
    if r.ambiguous:
        maq = [c.root for c in r.candidates if c.is_maqayis]
        root_str = "/".join(maq[:4]) + " (غامض)"
    print(f"  الجذر    : {root_str}   [{r.coverage}]")
    if not compact:
        print(f"  المرشحون : {[(c.root, '✓' if c.is_maqayis else '✗') for c in r.candidates[:5]]}")

    # باب
    print(f"  الباب    : {d.baab or '—'}")
    print(f"  الصيغة   : {m.derived_form.value}")
    print(f"  الجنس    : {m.gender or '—'}  |  العدد: {m.number or '—'}")

    # مسار اشتقاقي
    if not compact:
        print(f"  المسار   : {' → '.join(d.derivation_path)}")
        if d.generated_form:
            match_sym = "✓" if d.surface_matches else "~"
            print(f"  المولَّد  : {d.generated_form}  {match_sym}  [{d.confidence:.0%}]")

    # معجمية
    print(f"  المقاييس : {lx.coverage_status}  |  محاور={lx.axes_count}")
    if lx.body_snippet and not compact:
        print(f"  النص     : {lx.body_snippet[:120]}...")

    # عدد
    if n.is_numeral:
        print(f"  العدد    : {n.numeral_type.value}  قيمة={n.numeric_value}  جنس={n.gender_form}")

    # غموض
    if cert.ambiguity.has_ambiguity:
        print(f"  ⚠ الغموض : {', '.join(cert.ambiguity.ambiguity_sources)}")
        print(f"    ملاحظة : {cert.ambiguity.resolution_note}")

    # مخلفات
    r2 = cert.residuals
    pending = []
    if r2.unresolved_root:    pending.append("جذر_غير_محسوم")
    if r2.unknown_baab:       pending.append("باب_غير_معروف")
    if r2.missing_volume:     pending.append("مجلد_ناقص")
    if r2.no_derivation_path: pending.append("لا_مسار_اشتقاقي")
    if pending:
        print(f"  المخلفات : {', '.join(pending)}")
    print()
