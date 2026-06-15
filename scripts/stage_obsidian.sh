#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# stage_obsidian.sh — build the assignment-submission obsidian/ folder.
#
#   1. copies the generated vault (graph.json + hot.md + index.md) into obsidian/
#   2. prepends a Hebrew header to hot.md (preserving the generated wikilinks)
#   3. overwrites index.md with the Hebrew main entry point
#   4. writes bug_investigation.md documenting run_20260615_100601
#
# Docs are written primarily in Hebrew with English technical terms inline.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

# 1) Create obsidian/ and copy the generated vault artifacts into it.
mkdir -p obsidian
cp workspace/vault/graph.json workspace/vault/hot.md workspace/vault/index.md obsidian/

# 2) hot.md — prepend a Hebrew header, preserving the generated body
#    (including the [[__main__]] and [[Polygon]] wikilinks).
cat > obsidian/.hot_header.md <<'HOT_HEADER'
# hot.md — צמתים בעלי Centrality גבוה (אזור היעד לדיבוג)

> **הסבר (עברית):** הצמתים שמתחת הם ה-**high-centrality nodes** של ה-knowledge
> graph — אזור היעד (target area) שעליו מתמקד ה-**Graph-Guided Debugging**.
> ה-**Navigator** קורא אותם תחילה כדי להתחיל את החקירה סמוך ל-**Root Cause**,
> מבלי לסרוק קבצים שלמים. שימו לב במיוחד ל-`[[__main__]]` (נקודת הכניסה,
> module entry point) ול-`[[Polygon]]` (המחלקה הבאגית שתוקנה).
> לתיעוד המלא של ההרצה ראו `[[bug_investigation]]`.

---

HOT_HEADER
cat obsidian/.hot_header.md obsidian/hot.md > obsidian/hot.md.tmp
mv obsidian/hot.md.tmp obsidian/hot.md
rm obsidian/.hot_header.md

# 3) index.md — overwrite with the Hebrew main entry point.
cat > obsidian/index.md <<'INDEX_MD'
# index.md — שער הכניסה ל-Vault (Graph-Guided Debugging)

מסמך זה הוא נקודת הכניסה הראשית ל-**Obsidian Vault** של פרויקט הדיבוג
האוטונומי. ה-Vault מתעד כיצד מערכת **Agentic** מבוססת CrewAI מתקנת באגים
ב-repo היעד `broken-python` באמצעות ניווט ממוקד ב-**knowledge graph**, במקום
הזרקת קבצים שלמים ל-context.

## ארכיטקטורת היעד — `broken-python`

`broken-python` הוא אוסף סקריפטים לימודיים עם באגים מכוונים. שני המודולים
המרכזיים:

- **`polygons/polygons.py`** — קוד **OOP** עם המחלקה `Polygon` והפונקציות
  `calc_polygon_details` ו-`draw_polygon`. כאן נמצא ה-**Root Cause** של ההרצה
  הירוקה שלנו (ראו `[[bug_investigation]]`).
- **`mathsquiz/`** — סקריפטים שטוחים (flat scripts) של חידון מתמטי, ללא מבנה
  מחלקות.

## ה-Agentic Workflow

ה-**AST** (Abstract Syntax Tree) של היעד מנותח ל-`graph.json` (‏8 nodes,
‏6 edges), וממנו נגזרים ה-**high-centrality nodes** (`[[hot]]`). ארבעה agents
פועלים ברצף (sequential process):

1. **Navigator** — קורא את `[[hot]]` כדי לאתר את אזור הבאג.
2. **Reader** — מושך רק את שורות הקוד הרלוונטיות (targeted slices).
3. **Reasoner** — מפיק Hypothesis JSON ובו ה-**Root Cause** וה-`target_file`.
4. **Patcher** — מחיל את ה-fix המינימלי ומאמת שינוי פיזי על הדיסק.

## ניווט ב-Vault

- `[[hot]]` — ה-high-centrality nodes (אזור היעד לדיבוג).
- `[[bug_investigation]]` — תיעוד מלא של ההרצה הירוקה `run_20260615_100601`.
- `graph.json` — ה-knowledge graph המלא (nodes + edges) שנגזר מה-AST.
INDEX_MD

# 4) bug_investigation.md — document the verified green run.
cat > obsidian/bug_investigation.md <<'BUG_MD'
# bug_investigation.md — חקירת באג: ההרצה `run_20260615_100601`

מסמך זה מתעד הרצה ירוקה (‏✅ VALIDATION PASSED) של ה-**Agentic Workflow**
שתיקנה **NameError** אמיתי ב-`broken-python/polygons/polygons.py`.

## הבאג (Bug)

בקובץ `polygons/polygons.py`, שורה 3:

```python
class Polygon(Object):
```

זהו **NameError**: ב-Python אין built-in בשם `Object` (באות גדולה); הבסיס
התקין למחלקה הוא `object` (באות קטנה). ה-`Object` הלא-מוגדר מפיל את הסקריפט
כבר בזמן טעינת המודול (import time).

## ה-Root Cause (זוהה על-ידי ה-Reasoner)

ה-**Reasoner** ניתח את ה-slice הממוקד של המחלקה `Polygon` (שסופק על-ידי
ה-Reader) וזיהה שה-**Root Cause** הוא ירושה מ-base class לא-קיים בשם `Object`.
ה-Hypothesis JSON כלל את ה-`target_file` המדויק
(`broken-python/polygons/polygons.py`) ו-`confidence_score` ≥ 0.7, מה שאישר
ל-**Patcher** לפעול.

## ה-Fix (הוחל על-ידי ה-Patcher)

ה-**Patcher** החיל diff מינימלי דרך הכלי `apply_patch` — שינוי `Object` ל-`object`:

```diff
-class Polygon(Object):
+class Polygon(object):
```

פלט הכלי: `Patch applied to broken-python/polygons/polygons.py: replaced 218 chars.`
שער ה-**validation** השווה את היעד מול ה-fixture הנקי, זיהה שינוי פיזי אמיתי
על הדיסק, וארכב את ההרצה אל `workspace/results/run_20260615_100601/`.

## חיסכון ב-Tokens באמצעות בידוד Context ב-AST graph

הערך המרכזי של **Graph-Guided Debugging**: במקום להזריק את כל הקובץ
(`polygons.py` ‏≈ 75 שורות) ל-context, ה-**AST graph** מזהה את ה-hot nodes
`Polygon` (‏L3–8) ו-`calc_polygon_details` (‏L13–36), וה-**Reader** מושך **רק**
את ה-slices האלה (‏≈ 24 שורות):

- **Naive approach:** הזרקת 75 שורות מלאות → בזבוז tokens על boilerplate ועל
  קוד לא-רלוונטי.
- **Graph-Guided:** ‏≈ 24 שורות ממוקדות בלבד → **כ-68% פחות input tokens**.

בנוסף, כל קריאות ה-LLM (כולל provider מסוג DeepSeek) מנותבות דרך ה-
**`ApiGatekeeper`**, כך שצריכת ה-tokens וה-cost נרשמות ב-`BudgetTracker`;
ה-telemetry אישר צריכה נמוכה התואמת את ה-targeted slices.

---

קישורים: `[[index]]` · `[[hot]]` · `[[Polygon]]` · `[[__main__]]`
BUG_MD

echo "✅ obsidian/ staged:"
ls -1 obsidian/
