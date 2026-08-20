# Token-efficient workflow

Why this exists: the Short GEDCOM is ~12.6 MB (14,099 individuals). A single
careless `read_file` or `grep -C` on it can pull tens of thousands of tokens
into context, and generated `.drawio` files run 100–500 KB of XML. Historically
the cost of this skill came from three places:

1. **GEDCOM in context** — grepping/reading the raw `.ged` to find person IDs.
2. **Verbose XML in context** — reading `.drawio` output to "check" it.
3. **Regenerate-and-compare loops** — generating a chart, eyeballing the XML,
   tweaking, regenerating, often several times per chart.

All three are eliminated by process, not by changing the generators (the
generator scripts are untouched — the rendered charts are pixel-identical to
before).

## The cheap path

| Step | Tool | Typical output |
|---|---|---|
| Find a person | `gedcom_query.py <ged> search "Name"` | ~5–20 lines |
| Confirm identity | `gedcom_query.py <ged> show "@I…@"` | ~10 lines |
| Agree chart scope | `gedcom_query.py <ged> tree "@I…@" --down N` | 1 line/person |
| Generate | `generate_*.py` | 2–3 lines |
| Verify | `verify_family_tree.py` | ~10 lines |
| Render | `export_png.sh` / `flatten_export.py` | file paths only |

`gedcom_query.py` caches the parsed GEDCOM in `~/.cache/drawio-family-trees/`
(keyed by path+mtime+size). First query on a fresh GEDCOM parses it (~1 s for
12 MB); every query after that is ~75 ms. The cache invalidates itself when
the file changes. Subcommands: `stats`, `search <words> [--limit N]`,
`show <id>`, `tree <id> [--down N | --up N]`. Search is word-based and
case-insensitive, so "Brian Short" matches "Brian Stanley Short".

## Killing the regen loop

The most expensive pattern is: generate → send → user says "wrong person /
wrong depth" → regenerate. The fix is to confirm **before** generating:

1. `search` → if multiple matches, ask the user which one (name, dates, ID —
   one line).
2. `tree --down N` → show the user the exact roster the chart will contain
   and agree the depth and which branches are in/out.
3. Only then generate. One shot.

## When the verifier fails

- Paste only the verifier output (it is compact by design).
- Fix via generator flags/arguments, not by hand-editing XML.
- Open generator scripts or the bug-history references only when the failure
  matches a known bug or needs a code change.

## If XML inspection is genuinely unavoidable

Never read the whole file. Target it:

```bash
grep -o 'value="[^"]*"' chart.drawio | head -50        # labels only
grep -n 'mxGeometry' chart.drawio | sed -n '1,20p'      # geometry spot-check
python3 scripts/verify_family_tree.py chart.drawio      # structural truth
```

For "is person X on the chart?" use `grep -c "Their Name" chart.drawio` —
one line of output, not 100 KB of XML.

## What was deliberately NOT changed

- Generator scripts, layout constants, verifier checks: untouched. Charts are
  byte-identical to the pre-optimisation skill.
- `SKILL.md` grew by one section; all bug-history references remain for
  debugging sessions (they are loaded on demand, not by default).
