# Shared-code migration recipe

Use this when adding a new chart generator or refactoring an existing one to
import from `scripts/drawio_layout.py` and `scripts/parse_gedcom.py`. The
goal is single-source-of-truth for layout geometry and GEDCOM parsing
across all five chart generators.

## Step 1 — Capture the reference geometry

Before touching any code:

```bash
mkdir -p /tmp/migration_ref
cp /home/tv/<flagship_chart>.drawio /tmp/migration_ref/before.drawio
# (also copy any other saved charts the script produces, one per flagship
#  configuration: e.g. descendants-only, with-ancestors, full-tree, etc.)
```

You will diff against these after the migration.

## Step 2 — Audit the inline code

For each chart generator, look for:

- Inline `parse_gedcom`, `get_name`, `get_birth`, `get_parents`,
  `get_children`, `get_spouses`, `find_individual_by_name` — these all
  live in `scripts/parse_gedcom.py`.
- Inline `text_cell`, `hline`, `vrect`, `label_value` — these all live
  in `scripts/drawio_layout.py`.
- Inline constants `STROKE`, `MARRIAGE_GAP`, `MARRIAGE_Y_OFFSET`,
  `MARRIAGE_LINE_GAP`, `SIBLING_GAP`, `CHILD_DROP`, `DESCENDER_OFFSET`,
  `INTER_GEN_GAP` — all in `drawio_layout.py`.

For each, decide **preserve** or **fully migrate** (see "Two-class
migration decision" below) before swapping.

## Step 3 — Swap in shared imports

Replace the inline block with:

```python
from drawio_layout import (
    CHILD_DROP,
    DESCENDER_OFFSET,
    MARRIAGE_GAP,
    MARRIAGE_LINE_GAP,
    MARRIAGE_Y_OFFSET,
    SIBLING_GAP,
    STROKE,
    TEXT_W,
    TITLE_Y,
    # ... geometry helpers ...
    couple_descender_top,
    single_descender_top,
    connector_y_from_child,
    child_y_from_connector,
    resolve_connector_y,
    min_generation_height,
    compute_max_label_height,
    marriage_pair_people,
    marriage_pair_center,
)
from parse_gedcom import (
    find_individual_by_name,
    get_birth,
    get_children,
    get_name,
    get_parents,
    get_spouses,
    parse_gedcom,
)
```

If the script has chart-specific overrides for any of the shared constants
(e.g. the ancestor script's wider `TEXT_W=110`, or the vertical pedigree's
white-background labels), keep those as local constants **above the
imports** with a comment explaining the deviation. The shared imports only
apply to values that don't change the rendered output.

## Step 4 — Verify with `mxGeometry` diff

Regenerate the chart with the migrated script and diff:

```bash
python3 scripts/generate_<x>.py \
  --gedcom "/path/to/tree.ged" \
  --root-id "@I...@" \
  --output /tmp/migration_ref/after.drawio \
  [other flags matching the reference run]

diff <(grep -E 'mxGeometry' /tmp/migration_ref/before.drawio | sort) \
     <(grep -E 'mxGeometry' /tmp/migration_ref/after.drawio | sort)
```

Empty diff = byte-identical geometry. The migration is correct.

Non-empty diff with only style differences (`fontFamily`, `fontColor`,
etc.) is acceptable. Non-empty diff with pixel shifts in any `mxGeometry`
line means the migration changed the rendered output — that's a
regression unless the user explicitly approved a full migration.

```bash
python3 scripts/verify_family_tree.py /tmp/migration_ref/after.drawio
```

Must report "0 errors, 0 warnings".

## Two-class migration decision

The user's intent falls into one of two buckets:

| Class | When | What changes |
|---|---|---|
| **Preserve** | User says "make it use shared code" or "use shared conventions" with no mention of style | Use shared helpers/imports for **everything that doesn't change rendered output**. Keep the script's existing constants as local overrides with comments. Result: byte-identical chart. |
| **Full migrate** | User explicitly says "fully migrate to the shared helper style" or "use the shared helpers completely" | Adopt shared `text_cell`/`hline`/`vrect`/`label_value` and shared constants even if the chart's style shifts (e.g. vertical pedigree now has white background rect + `verticalAlign=top`). Accept the style delta. Confirm with the user before declaring done. |

Default to **Preserve**. When in doubt, ask. The four flagships generated
by the visit/descendants/line-of-descent scripts are byte-identical in
the Preserve mode; Full Migrate only happens for the vertical pedigree
where the user explicitly approved the style change.

## Pitfalls

### The buggy `for parent_id, _ in get_parents(...)` pattern

When migrating a script that walks a tree upward (ancestors), do not
write:

```python
for parent_id, _ in get_parents(iid, individuals, families):
    ...
```

`get_parents` returns `(husb, wife)` (a 2-tuple of strings), **not** an
iterable of pairs. The loop iterates the two strings individually, then
tries to unpack each string as `(parent_id, _)` and raises
`ValueError: too many values to unpack (expected 2)`. The correct
form is:

```python
dad, mum = get_parents(iid, individuals, families)
for parent_id in (dad, mum):
    if parent_id and parent_id not in seen:
        ...
```

This bug was introduced in an earlier session of the visit script and
went unnoticed because the saved Edward Grey chart was generated in
descendants-only mode, which skips the walk-up code path entirely. The
bug only fires when the script actually includes ancestors.

**Symptom:** `ValueError: too many values to unpack` raised from a walk-up
loop that uses `get_parents`.

**Test for it:** after any migration, run the script with ancestors
enabled (not descendants-only) and verify it produces a chart
including ancestor labels.

### The "first NAME" rule

`parse_gedcom` keeps the first `1 NAME` record per individual (GEDCOM
allows multiple — typically alternate names like a maiden name). The
shared parser implements this; an older shared version overwrote with
the last NAME, which the visit and descendants-with-steps scripts
were already guarding against inline. After migrating those scripts to
the shared parser, the rendered names may differ slightly for the ~80
individuals in the Short-family GEDCOM that have multiple NAME records
(e.g. Adam Short's wife appears as "Olivia O'Keeffe" instead of
"Margaret Olive O'Keeffe" because "Olivia" is the first NAME record).

**This is the correct GEDCOM convention.** If a saved chart shows a
different name than the new script produces, the saved chart was
generated by a script that overwrote (last-NAME-wins); the new chart
matches the canonical first-NAME.

### The `.strip()` rule in `get_name`

The shared `get_name` strips whitespace on both the parsed name and the
givn/surname fallback. The visit/descendants-with-steps inline versions
did this; the older shared version did not. After migration, ~3
individuals in the Short-family GEDCOM with leading/trailing whitespace
in their names render without those spaces (e.g. "Edward I Plantagenet
King of England" instead of " Edward I Plantagenet King of England ").

This is a cosmetic improvement — accept it. If you need to preserve
whitespace for an unusual source, file a separate request.

### Don't redefine `CHILD_DROP` locally

When migrating, search for `CHILD_DROP = 12.0` inside function bodies
in the chart script. Several scripts had a local redefinition that
shadowed the import; remove them. The single source of truth is
`drawio_layout.py:CHILD_DROP`.

### Don't reintroduce the legacy `CURRENT_GEN_H = 165` formula

The legacy formula `DEFAULT_GENERATION_HEIGHT + (MAX_LABEL_H - DEFAULT_TEXT_H)`
evaluates to 165 px for 90 px labels, which pins the sibling bar to the
child cap regardless of `DESCENDER_OFFSET`. Always set
`CURRENT_GEN_H = min_generation_height(MAX_LABEL_H)` instead. See
`dynamic-descender-height.md` for the full diagnosis.

### Don't recompute descender/connector math at the call site

If you find yourself writing `descender_top = parent.y + 18 + 3 + 1` at
the call site, replace with `couple_descender_top(parent.y)`. The
helper exists for the marriage-line-bottom offset. Same for
`connector_y = child.y - 12` → `connector_y_from_child(child.y)`.

## Multi-step bulk migration

When migrating several scripts at once, do them one at a time. For
each script:

1. Capture the reference (Step 1).
2. Audit inline code (Step 2).
3. Swap imports + remove inline block (Step 3).
4. Diff `mxGeometry` (Step 4).
5. Run the validator.

Only after one script is byte-identical and the validator passes should
you move to the next. If two scripts diverge in a way that requires
changing the shared module (e.g. the "first NAME" rule), make the
shared-module change once and re-verify every previously-migrated
script against its reference — small downstream differences are
expected and acceptable; just confirm with the user that the change is
intended.

---

_Moved here from SKILL.md (2026-08-20) to keep per-session skill load small. Load this reference whenever adding or refactoring a chart generator._

## Migrating an existing chart script to the shared layout module

`scripts/drawio_layout.py` is the single source of truth, but **not every
chart script should adopt every shared constant**. The rule, applied
whenever a new generator is added or an existing one is refactored to
import from `drawio_layout`:

1. **Always share**: `parse_gedcom.py` helpers (`parse_gedcom`, `get_name`,
   `get_parents`, `get_spouses`, `get_birth`, `get_children`,
   `find_individual_substring`, `find_individual_by_name`), `STROKE`,
   `TITLE_Y`, `min_generation_height`.
2. **Share if and only if it doesn't change the rendered output**: `MARRIAGE_*`,
   `SIBLING_GAP`, `CHILD_DROP`, `DESCENDER_OFFSET`, `INTER_GEN_GAP`. Capture
   the script's current values of these constants; if they match the shared
   ones, swap to the import. If they differ, leave them local with a comment
   explaining the deviation. Test by re-generating the chart and diffing
   `mxGeometry` lines against a saved reference — pixel-identical output
   means you've swapped correctly. **A geometry change is a regression** UNLESS
   the user has explicitly approved a full migration that changes the chart's
   visual style (in which case run all flagship charts and verify with the
   user before considering the migration done).
3. **Always keep local**: chart-specific layout values like `TEXT_W` (the
   ancestor script uses 110, the others use 75), `TEXT_H`, page margins,
   `MIN_SPOUSE_GAP`, `PAGE_CENTER_X`. These are visual conventions that vary
   by chart type and reflect the user's design choices for that chart style.
4. **The ancestor script has no sibling bar**, so `DESCENDER_OFFSET` and
   `CHILD_DROP` don't apply. It uses three named constants instead:
   `LINE_THICKNESS` (= 2.0), `DESCENDER_CLEARANCE` (= 1.0),
   `CHILD_CLEARANCE` (= 1.0). Treat these as the ancestor-script equivalent
   of the sibling-bar pair — never use `resolve_connector_y` or
   `connector_y_from_child` for it.
5. **The vertical pedigree has no sibling bar AND a different cell style**
   (shared `text_cell` with `_bg` background rect + `verticalAlign=top`,
   shared `hline` using `shape=line`). When asked to fully migrate it, adopt
   the shared helpers and expect a small style delta vs the prior script
   (background rect appears under each label; font alignment shifts from
   middle to top). Confirm with the user before considering the migration
   done.

Verification: regenerate the script's flagship chart before and after the
migration, then `diff <(grep -E 'mxGeometry' before | sort) <(grep -E 'mxGeometry' after | sort)`.
Non-geometry differences like extra `fontFamily=` attributes on `<mxCell>`
styles are cosmetic and acceptable; any pixel-level geometry diff is a
regression that must be fixed (typically by reverting one of the imports
and adding a comment explaining why the local value is different).

Current migration status (chart generators and their shared imports):

| Script | `parse_gedcom` shared | `drawio_layout` shared | Notes |
|---|---|---|---|
| `generate_visitation_tree.py` | yes | yes | First reference migration; uses shared `marriage_pair_people`/`marriage_pair_center` |
| `generate_descendants_with_steps.py` | yes | yes | Same as visit, plus step-parent handling via `is_step_parent` flag passed to `marriage_pair_people` |
| `generate_line_of_descent.py` | yes | yes | Reference migration; smallest script |
| `generate_ancestor_tree_recursive.py` | yes | yes (constants kept local with deviation comments) | Descender uses `LINE_THICKNESS`/`DESCENDER_CLEARANCE`/`CHILD_CLEARANCE` triple |
| `generate_vertical_pedigree.py` | yes | yes (full migration with shared `text_cell`/`hline`) | Chart style changed: labels now have white background rect and `verticalAlign=top` |

See `references/shared-code-migration.md` for the full migration recipe
including the reference-save-then-diff pattern, the
`for parent_id, _ in get_parents(...)` walk-up bug, and the
`parse_gedcom` first-NAME-rule / strip-name behavioural unification.

