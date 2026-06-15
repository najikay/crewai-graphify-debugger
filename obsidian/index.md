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
