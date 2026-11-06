# arabic_net_api: واجهة واحدة لـ arabic-net

`arabic_net_api` واجهة للقراءة فقط، وكلّ ما ترجعه مرتبته CANDIDATE. صُمّمت لتخدم arabic-sarf-2026 وكلّ مستهلك آخر.

**بنيتها:** مدخل جامع واحد، فوقه مزوّدات مستقلّة يمكن أن يُستدعى كلّ منها وحده. لا تُنسخ البيانات، بل تُقرأ من مستودعاتها في `~/arabic-net`. ويمكن تغيير هذا المكان بـ `ARABIC_NET_HOME`.

## الاستعمال

```python
import sys; sys.path.insert(0, "~/arabic-net/Arabic-Mother-language-net")   # مسار AMLN
from arabic_net_api import verb, root, sources

r = verb("كَسَرَ", root="كسر", include={"hfn", "wazn", "ahdath", "roots"})
r["features"]["masdar"][0]["value"]        # 'كَسْر'          (HFN، RELEASE_CANDIDATE)
r["features"]["mutawaa"][0]["value"]       # 'انْكَسَرَ'       (wazn-net، MEASURED_ACCEPTED)
r["features"]["ahdath_effect"][0]["value"] # {'fail':'كَاسِر','maful':'مَكْسُور','athar':'انْكِسَار',…}
verb("ضَجِرَ")["features"]["fail_jiha"]     # MAHALL، والمسبِّب أَضْجَرَ (T_JAL)
root("كسر")                                 # معنى الجذر في المعاجم العشرة، وأحداث HFN، والتحيّز
sources()                                   # التزام كلّ مستودع، وإصدار HFN وبصمته، وهل هو أحدث إصدار
```

```bash
python3 -m arabic_net_api كَسَرَ --root كسر
python3 -m arabic_net_api --root-only كسر
python3 -m arabic_net_api --sources
```

## السمات

| السمة | المزوّد | الحالة | المحتوى |
|---|---|---|---|
| `hfn_event` | hfn | RELEASE_CANDIDATE | معرّف الحدث، والجذر، والوزن، والطبقة، والمرتبة، وعدد المعاجم |
| `transitivity` | hfn | RELEASE_CANDIDATE | تعدّي الحدث، ومعه حكم الوسيط v37 في `evidence` |
| `masdar` و`ism_fail` و`ism_maful` | hfn | RELEASE_CANDIDATE | الوحدات المعجمية: `M`، و`M2` وهو مصدر ثانٍ، و`AG`، و`PT` |
| `masdar_wasit_check` | hfn | RELEASE_CANDIDATE | مقابلة المصدر بالوسيط: AGREE أو DIFF_ATTESTED أو NO_WASIT |
| `form_meaning` | hfn | حالة الصفّ | معنى الصيغة المزيدة، نحو استفعل للطلب |
| `mutawaa` و`mutawaa_base` | wazn | MEASURED_ACCEPTED | المطاوع والأصل، مع الأثر والمسلك |
| `taadiya` | wazn | MEASURED_ACCEPTED | من اللازم إلى المتعدّي، بمسلك T_JAL وحده |
| `ahdath_effect` | ahdath | MEASURED_ACCEPTED | الفعل مؤثّر، ومسالكه R1 وR1W وT_JAL |
| `fail_jiha` | ahdath | MEASURED_ACCEPTED | الفاعل محلّ (MAHALL) في J_SAJIYYA وJ_DAA، ومعه `musabbib_verb` |
| `root_meaning` | roots | UNVERIFIED_OCR | نصّ كلّ معجم مربوط في `HFN_ROOTS_v3`، ومقاييس ابن فارس احتياطاً |
| `tahayyuz` | roots | CANDIDATE | توزيع أصناف التحيّز على معاني الجذر الاسمية |

**حقول كلّ سجلّ:**
- `feature` و`value` و`provider` و`status` و`route` و`measure` و`source` و`match` و`evidence`
- `rank` قيمته CANDIDATE دائماً، و`is_fact` قيمته False دائماً.

## القواعد

- **المطابقة:** الافتراض `match="exact"`، أي الحروف والحركات معاً بعد NFC، وهو حكم دستور sarf.
  - ما طابق بالحروف وحدها، أو لم يختلف إلا في السكون، يذهب إلى `excluded` ومعه سبب استبعاده.
  - `match="letters"` يُبقي الكلّ في `features`، وكلّ سجلّ معلَّم بنوع مطابقته.
- **غياب مصدر:** إذا غاب مصدر أو تعطّل لم يسقط الطلب كلّه، بل يُذكر في `missing`.
- **إصدار HFN:** يؤخذ من `ARABIC_NET_HFN_RELEASE`، ثم من `SARF_HFN`، فإن لم يوجدا أُخذ أحدث إصدار يتحقّق بملفّ MANIFEST.
  - يذكر `sources()["hfn"]` الإصدارَ الذي اختير ومن أين جاء اختياره (`pinned_by`).
  - ويذكر كذلك `behind_newest`، أي هل الإصدار المختار أقدم من أحدث إصدار متاح.
- **المسالك المحجوبة لا تُعرض:** R2 وT وT_TAD وJ_LAWN وJ_MUTAWAA، ومعها تعدّي المزيد من الوسيط.

## ما لم يُربط بعد

- **التصريف والاشتقاق من wazn-net** (`conjugate` و`derive_names`): يحتاجان نوع الجذر وبابه. وHFN يعطي المشتقّات المسموعة الآن.
- **علاقات WordNet** (`semantic_api.py` في `~/arabic-net`): ملفّ خارج git، وهو لعلاقات الأسماء لا للصرف.
- **مشاهد HFN والتكافؤ:** يُستدعيان من `hfn.api()` مباشرة، بالدالتين `event_scenes` و`valence`.
