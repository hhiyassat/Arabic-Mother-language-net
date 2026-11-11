#!/usr/bin/env python3
"""build_arkan_v11.py — v10 + وسم الدلالة لكلّ صفّ. CANDIDATE.
حكم المالك 2026-11-09: تُقبل دلالة الالتزام على المذهبين ويُسمّى المذهب على كلّ حافّة:
luzum_martaba «ذهنيّ» (شرط المناطقة: في جميع الأذهان والأزمان — مقبول عند الجميع) أو «مطلق» (أهل العربية والأصول: ذهنياً كان أو خارجياً)؛
luzum_naw: عقليّ/عاديّ/شرعيّ. الحدود والعضويّة بالمطابقة والتضمّن وحدهما (الغزالي: «المعتبر في التعريفات دلالة المطابقة والتضمن»).
ضابطان: لا التزام بلا نصّ وشرط؛ ولا يُحسب لازم اللازم آليّاً.
أعمدة جديدة: dalala، luzum_naw، luzum_martaba، mani (غائب/لم يُفحص/غير منطبق)، hukm (مثبتة في نطاق القول/مؤجّلة)، i3timad، wasm_khilaf.
الوسم قرأه قارئان أعميان (ARKAN_v11_R1/R2): اتّفقا على 83/91؛ 8 خطأ متّفق عليه صُحّحت (J5b، J10، J20b، J27، J27b، J27f، J28، A6b)؛ 8 خلاف بقي وسمها مع wasm_khilaf.
لا يكتب فوق ملفّ قائم، ولا يمسّ v1–v10."""
import csv, os, sys
H = os.path.dirname(os.path.abspath(__file__))
T = ["FRAME", "NODES", "ATTACH", "AHWAL", "SILA", "INHERIT", "CHANGES"]
for t in T:
    if os.path.exists(f"{H}/ARKAN_v11_{t}.tsv"): sys.exit(t + " exists")
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))
L = {r["rid"]: r for r in rd(f"{H}/ARKAN_v11_LABELS.tsv")}
R1 = {r["rid"]: r for r in rd(f"{H}/ARKAN_v11_R1.tsv")}; R2 = {r["rid"]: r for r in rd(f"{H}/ARKAN_v11_R2.tsv")}
FIX = {"J5b": "—", "J10": "—", "J20b": "التزام/عقليّ/ذهنيّ", "J27": "تضمّن", "J27b": "تضمّن", "J27f": "تضمّن", "J28": "تضمّن", "A6b": "تضمّن"}
def wr(t, rows):
    with open(f"{H}/ARKAN_v11_{t}.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print(t, len(rows))
ch = []
for t in ["NODES", "ATTACH", "AHWAL", "SILA"]:
    rows = rd(f"{H}/ARKAN_v10_{t}.tsv")
    for r in rows:
        l = L[r["rid"]]; d, ln, lm, mn = l["dalala"], l["luzum_naw"], l["luzum_martaba"], l["mani"]
        if r["rid"] in FIX:
            p = FIX[r["rid"]].split("/"); d = p[0]; ln, lm = (p[1], p[2]) if len(p) == 3 else ("—", "—")
            mn = "لم يُفحص" if (d == "التزام" and lm == "مطلق") else "غير منطبق"
            ch.append(dict(rid=r["rid"], v10_label=f'{l["dalala"]}/{l["luzum_naw"]}/{l["luzum_martaba"]}', v11_label=f"{d}/{ln}/{lm}",
                           why=(R1[r["rid"]]["note"] or R2[r["rid"]]["note"])[:200]))
        a, b = R1[r["rid"]]["verdict"].strip().upper(), R2[r["rid"]]["verdict"].strip().upper()
        kh = "" if a == b else f'R1 {a} {R1[r["rid"]]["correct"]} / R2 {b} {R2[r["rid"]]["correct"]}'
        nass = (r.get("quote") or "").strip()
        r.update(dalala=d, luzum_naw=ln, luzum_martaba=lm, mani=mn,
                 hukm="مثبتة في نطاق القول" if nass else "مؤجّلة (بلا نصّ)", i3timad="CANDIDATE", wasm_khilaf=kh)
    wr(t, rows)
fr = rd(f"{H}/ARKAN_v10_FRAME.tsv")
fr += [dict(rid="F6", claim="المطابقة دلالة اللفظ على تمام ما وُضع له؛ التضمّن على جزئه؛ الالتزام على لازمٍ خارج عنه. والمعتبر في التعريفات المطابقة والتضمّن، لا الالتزام لأنّ لوازم الأشياء لا تنحصر",
             quote="كدلالة لفظ الحائط على الحائط … كدلالة لفظ البيت على الحائط ودلالة لفظ الإنسان على الحيوان … كدلالة لفظ السقف على الحائط … والمعتبر في التعريفات دلالة المطابقة والتضمن … إذ لوازم الأشياء ولوازم لوازمها لا تنضبط ولا تنحصر",
             source="الغزالي، معيار العلم (OpenITI 0505Ghazali.MicyarCilm.Shamela0026575) — سطر 249–258، قبل PageV01P072"),
       dict(rid="F7", claim="اشترط المناطقة في الالتزام اللزوم الذهني، واكتفى أهل العربية والأصول بمطلق اللزوم؛ والمشروع يقبل المذهبين ويسمّي المذهب على الحافّة (حكم المالك)",
             quote="المنطقيون اشترطوا في دلالة الالتزام اللزوم الذهني … وأهل العربية والأصول وكثير من متأخري المنطقيين والإمام الرازي لم يشترطوا ذلك. فالمعتبر عندهم مطلق اللزوم ذهنيا كان أو خارجيا",
             source="التهانوي، كشّاف اصطلاحات الفنون (OpenITI 1158IbnCaliFaruqiTahanawi.KashshafIstalahat.Shamela0002573) — سطر 29736–29740")]
wr("FRAME", fr)
wr("INHERIT", rd(f"{H}/ARKAN_v10_INHERIT.tsv"))
wr("CHANGES", ch)
