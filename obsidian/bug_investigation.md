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
