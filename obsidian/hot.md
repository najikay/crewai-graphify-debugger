# hot.md — צמתים בעלי Centrality גבוה (אזור היעד לדיבוג)

> **הסבר (עברית):** הצמתים שמתחת הם ה-**high-centrality nodes** של ה-knowledge
> graph — אזור היעד (target area) שעליו מתמקד ה-**Graph-Guided Debugging**.
> ה-**Navigator** קורא אותם תחילה כדי להתחיל את החקירה סמוך ל-**Root Cause**,
> מבלי לסרוק קבצים שלמים. שימו לב במיוחד ל-`[[__main__]]` (נקודת הכניסה,
> module entry point) ול-`[[Polygon]]` (המחלקה הבאגית שתוקנה).
> לתיעוד המלא של ההרצה ראו `[[bug_investigation]]`.

---

# hot.md — High-Centrality Nodes (Debugging Hot Path)

Seed context for the Navigator Agent. Read these nodes first.

**Primary Target File:** `workspace/target/broken-python/polygons/polygons.py`
**Root-Cause Node:** `calc_polygon_details` (1 incoming edges)

## Top Hot Nodes (by degree centrality)

1. **[[__main__]]** `module` — centrality `0.667` (L1–69) `workspace/target/broken-python/polygons/polygons.py`

2. **[[calc_polygon_details]]** `function` — centrality `0.667` (L13–36) `workspace/target/broken-python/polygons/polygons.py`

3. **[[Polygon]]** `class` — centrality `0.333` (L3–8) `workspace/target/broken-python/polygons/polygons.py`

4. **[[draw_polygon]]** `function` — centrality `0.333` (L41–53) `workspace/target/broken-python/polygons/polygons.py`

5. **[[Polygon.__init__]]** `method` — centrality `0.000` (L5–8) `workspace/target/broken-python/polygons/polygons.py`

## Bug Call Chain

```text
__main__  [L1–69, module]
    → calc_polygon_details  [L13–36, function]
    → Polygon  [L3–8, class]
```

## Nodes in Primary Target File

- `Polygon` (class) L3–8
- `Polygon.__init__` (method) L5–8
- `calc_polygon_details` (function) L13–36
- `draw_polygon` (function) L41–53

