---
name: drawio-family-trees
description: Generate clean, thin-line, book-print-ready family tree diagrams from GEDCOM
---

# Drawio Family Trees

Generate clean, thin-line, book-print-ready family tree diagrams from GEDCOM
files, as `.drawio`/`.svg`/`.png`. Pure no-box visitation style, and a
line-of-descent variant that focuses on one bloodline but includes siblings.

**Output location:** save generated charts to `/home/tv/family tree charts/`
(quote the path because of the space).

## Token-efficient workflow (always follow this)

The GEDCOM is ~12 MB and `.drawio` output can exceed 100 KB. Reading either
into context is what makes this skill expensive. The whole workflow runs on
compact tool output instead:

1. **Find the root person** with `scripts/gedcom_query.py` (parses once,
   caches to disk; repeat queries ~75 ms):

   ```bash
   python3 scripts/gedcom_query.py "<ged>" search "Thomas Finigan"
   python3 scripts/gedcom_query.py "<ged>" show "@I18915667319@"
   ```

   If more than one person matches, confirm which one with the user (one
   line: name, dates, ID) BEFORE generating.

2. **Preview scope before generating.** Show the user exactly who will be on
   the chart and agree depth/branches. This confirmation step is what
   eliminates expensive regenerate-and-compare loops:

   ```bash
   python3 scripts/gedcom_query.py "<ged>" tree "@I18915667319@" --down 3
   ```

3. **Generate + verify + render in ONE turn** with `scripts/make_chart.sh`
   (it appends `--output` itself, runs the terse verifier, renders, and
   short-circuits repeat requests whose chart is byte-identical to the
   existing file — verify/render are skipped and the existing PNG is reused):

   ```bash
   scripts/make_chart.sh "<out.drawio>" generate_descendants_with_steps.py \
     --gedcom "<ged>" --root-id "@I...@" --all-descendants
   ```

   Exit 0 = deliver; `UNCHANGED` = re-send the existing PNG; verify exit 1
   with warnings = compare against the known benign classes before deciding
   (do not spiral).

4. **Deliver tersely** (output tokens are the most expensive kind): title,
   people/generations count, file paths, `MEDIA:` line — five lines, no
   tables. Run a vision check ONLY on anomaly (verifier output differs from
   expectations, odd render size, or first-of-kind chart); the user eyeballs
   every chart anyway.

Rules that keep it cheap:

- NEVER `cat`/`read_file`/`grep` the `.ged` file — use `gedcom_query.py`.
- NEVER read the `.drawio` XML into context — verify via script, view via PNG.
- No speculative iteration: one generate → verify → render → user feedback.
- Only open generator scripts or the bug-history references when a verifier
  check actually fails or the user reports a layout bug.

See `references/token-efficient-workflow.md` for the rationale and the
fallback procedure when XML inspection is genuinely unavoidable.

### Long-session offload (delegation)

In a long conversation the biggest per-chart cost is resending the chat
history every turn. When the conversation is long, keep steps 1–2 (find root,
confirm scope) in the main chat — they cost ~100 tokens and need the user —
then delegate steps 3–5 (generate/verify/render) to a leaf subagent via
`delegate_task`. The subagent's context is tiny, so its per-turn cost is a
fraction of the main chat's.

Measured break-even (2026-08-20, K3 pricing): a subagent run costs a fixed
~$0.06–0.09 (its own system prompt + skill load are fresh input). Delegation
therefore only pays off when the main conversation is long — at ~85k tokens
of chat context the saving is small (~15–20%); at 200k+ it is ~50%+. In a
fresh session, do NOT delegate: the subagent's startup costs more than the
saving. Side benefit regardless of length: if a run goes wrong, the
subagent's debugging burns tokens in its own cheap context, not the main
chat's — delegation caps the worst case.

The delegation prompt MUST be self-contained and include:

- the exact `make_chart.sh` command with confirmed generator, `--root-id`,
  flags, title, and output path (the subagent cannot ask questions);
- "verifier may report warnings of the known pre-existing benign class for
  this chart style — do NOT debug or fix; report them verbatim";
- "if render fails with a connection error run `docker start drawio-renderer`
  and retry; NEVER use the `drawio` CLI — it hangs on this host";
- "never read the `.ged` or `.drawio` files into context";
- "report back: pipeline stdout and `ls -la` of the outputs".

Treat the subagent's report as a self-report: confirm the output files exist
(`ls -la`) before delivering to the user.

### Optional cheaper-model offload (user's choice, remembered)

The mechanical chart steps need almost no reasoning, so they can run on a
cheaper model than the main chat — but the skill MUST NOT hardcode one (it
is used by people on different providers). Instead:

1. When a chart request comes in, run `scripts/offload_model.sh get`.
2. **`UNSET`** — ask the user once, in one line: "I can run the mechanical
   chart steps on a cheaper model to save money — name a model you have
   configured (as you'd pass to `hermes chat -m`), or say no." Store the
   answer with `scripts/offload_model.sh set <model|off>` and never ask
   again (`offload_model.sh clear` re-asks).
3. **`off`** — run in-session (or delegate to a same-model subagent in long
   sessions, per the section above).
4. **A model name** — run the pipeline on that model as a one-off:

   ```bash
   hermes chat -m "$(scripts/offload_model.sh get)" -q "Run exactly:
   cd ~/.hermes/skills/drawio-family-trees && scripts/make_chart.sh '<out>' <generator> --gedcom '<ged>' --root-id '<id>' <flags>
   Reply with the command's stdout verbatim, nothing else."
   ```

   Then verify the outputs exist (`ls -la`) before delivering. If the
   one-off run fails (model unavailable, provider error), fall back to the
   in-session path, tell the user, and suggest `offload_model.sh clear` if
   the stored model is gone for good.

## Quick start

### `generate_visitation_tree.py` (descendants-only)

This script defaults to **descendants-only**. Do not pass `--descendants-only`;
use `--ancestors-only` if you want ancestor-only mode.

```bash
python3 scripts/generate_visitation_tree.py \
  --gedcom "/home/tv/Short Main Family Tree.ged" \
  --root-id "@I19544480083@" \
  --all-descendants \
  --title "Descendants of Edward Grey" \
  --font-family "Times New Roman" \
  --output "/home/tv/family tree charts/edward_grey_descendants.drawio"
```

### `generate_descendants_with_steps.py` (descendants-only, step-children supported)

This script now defaults to **descendants-only**. Do not pass `--descendants-only`;
use `--ancestors-only` if you want ancestor-only mode.

```bash
python3 scripts/generate_descendants_with_steps.py \
  --gedcom "/home/tv/Short Main Family Tree.ged" \
  --root-id "@I18915667319@" \
  --all-descendants \
  --output "/home/tv/family tree charts/thomas_finigan_1820_descendants.drawio"
```

```bash
python3 scripts/verify_family_tree.py "/home/tv/family tree charts/thomas_finigan_1820_descendants.drawio"
python3 scripts/flatten_export.py "/home/tv/family tree charts/thomas_finigan_1820_descendants.drawio"
```

If `flatten_export.py` fails with a connection error, the local draw.io renderer at
`http://localhost:8080/convert_file` is not running. Restart it with
`docker start drawio-renderer` (preferred). If docker is unavailable, use the installed
`drawio` CLI directly — but note the CLI's Electron process has been observed to hang
indefinitely on this host, so the docker renderer is strongly preferred:

```bash
drawio --export --format svg --output chart.svg chart.drawio
drawio --export --format png --output chart.png chart.drawio
```

The CLI may emit GPU/VAAPI warnings; they are harmless as long as the output file
is created.

### PNG export pitfall: wide charts come out stretched

For very wide diagrams, the draw.io CLI's direct PNG exporter can render a
small internal bitmap and stretch it to the page size, producing an unusable
elongated image. Export to PDF first, then convert to PNG:

```bash
scripts/export_png.sh chart.drawio chart.png 150
```

See `references/drawio-png-export-stretching.md` for details and manual
workarounds.

## Important: do not run these scripts in mixed mode

`generate_visitation_tree.py` and `generate_descendants_with_steps.py` default to
**descendants-only**. Running either script without `--ancestors-only` on a root
with siblings is the intended mode. The mixed/hourglass path (ancestors +
descendants without `--ancestors-only`) produces many overlapping connector
pairs because the mixed-mode connector code collides with the pre-existing
sibling-bar overlap bug. For both scripts the supported modes are:

- **default** — descendants only
- `--ancestors-only` — ancestors only

For a true hourglass chart, use a different workflow or script.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/gedcom_query.py` | **Compact GEDCOM queries (search/show/tree/stats) — the ONLY approved way to inspect a GEDCOM** |
| `scripts/parse_gedcom.py` | Minimal GEDCOM parser (individuals + families) |
| `scripts/generate_visitation_tree.py` | Descendant-only chart (use `--ancestors-only` for ancestors) |
| `scripts/generate_descendants_with_steps.py` | Descendant-only chart with explicit in-law/cousin steps |
| `scripts/generate_line_of_descent.py` | Single bloodline + siblings at every generation |
| `scripts/generate_ancestor_tree_recursive.py` | Pure ancestor fan-out (no sibling bar) |
| `scripts/generate_vertical_pedigree.py` | Vertical pedigree (different layout constants) |
| `scripts/verify_family_tree.py` | Structural linter + generational-separation + connector-overlap checks (`--terse` for one-line-per-check output) |
| `scripts/make_chart.sh` | **One-turn pipeline: generate → unchanged-short-circuit → verify --terse → render** |
| `scripts/flatten_export.py` | Renders the chart to SVG and PNG (scale=2) |
| `scripts/export_png.sh` | PNG export via PDF, avoids draw.io CLI wide-image stretching bug |
| `scripts/drawio_layout.py` | **Shared layout constants and helpers — read this first** |

## Layout rules

All spacing and descender conventions live in `scripts/drawio_layout.py`. Every
chart generator imports from there. See `references/layout-rules.md` for the
current constants and the reasoning behind the rule that *child labels are
positioned relative to the sibling bar, not the parent*.

To tighten or loosen the parent-to-sibling-bar drop:
- **Single knob:** change `DESCENDER_OFFSET` in `drawio_layout.py`.
- Always re-run both the descendant chart and the line-of-descent chart to
  verify the change is consistent across chart types.

## Migrating an existing chart script to the shared layout module

The full migration recipe (what to share, what to keep local, the
reference-save-then-diff verification pattern, and current per-script
migration status) lives in `references/shared-code-migration.md`. Load it
whenever you add a generator or refactor one to use `drawio_layout`.
Pixel-identical output is the acceptance test unless the user approves a
style change.

## References

- `references/token-efficient-workflow.md` — why the cheap path exists, measured costs, and the fallback when XML inspection is unavoidable

- `references/drawio-png-export-stretching.md` — draw.io CLI direct PNG export stretches very wide charts; PDF-to-PNG workaround
- `references/pre-delivery-checklist.md` — required checks before delivering a chart, including the no-stretch PNG export rule
- `references/shared-code-migration.md` — full migration recipe (reference-save-then-diff, common pitfalls)
- `references/layout-rules.md` — current constants, the core rule, and pitfalls
- `references/dynamic-descender-height.md` — `DESCENDER_OFFSET` ↔ `CURRENT_GEN_H` coupling, the "raise vs lower" trap, and the failure modes the old global-max approach produced
- `references/line-of-descent-chart.md` — how to invoke the line-of-descent script
- `references/default-to-descendants-only.md` — why `--descendants-only` was removed and the supported command patterns
- `references/single-parent-side-entry-bug.md` — single-parent child groups were offset sideways; fix and verification
- `references/multi-spouse-connector-stagger.md` — multi-spouse child connectors lost their vertical stagger; fix and verification
- `references/only-child-with-spouse-alignment.md` — asymmetric child groups (especially an only child with a spouse) were shifted left because the layout aligned the group's geometric centre instead of the blood-centre midpoint
- `references/descendants-sibling-bar-overlap-bug.md` — pre-existing layout bug in `generate_descendants_with_steps.py` (sibling bars overlap when one sibling's subtree is wider than its neighbour); which flagships trigger it, workarounds, and where the fix lives
