# Escaping double quotes in draw.io value attributes

## Problem

GEDCOM names sometimes contain literal double quotes, usually for nicknames:

```gedcom
1 NAME John Henry "Jack" /Irvine/
```

If the generator emits this name directly inside a double-quoted XML attribute,
the resulting `.drawio` file is malformed:

```xml
<mxCell id="..." value="John Henry "Jack" Irvine&#xa;(b. 28 June 1890)" ... />
```

Parsers such as `xml.etree.ElementTree` then fail with:

```
xml.etree.ElementTree.ParseError: not well-formed (invalid token): line 4055, column 56
```

`verify_family_tree.py` will also fail at the generation-counting step because
it cannot parse the file.

## Root cause

`generate_visitation_tree.py` builds `value="..."` attributes with f-strings and
does not XML-escape the person name, birth string, or title. A name containing
`"` therefore terminates the attribute early.

## Fix in the generator

`scripts/generate_visitation_tree.py` now:

1. Keeps the **first** `NAME` record for each individual and ignores later
   `NAME` lines, which GEDCOM treats as alternate names. This prevents a root
   person from being rendered under a variant spelling (e.g. "James Robison"
   instead of "James Robinson").
2. Escapes `&`, `"`, `<`, and `>` in person names, birth strings, and the
diagram title before writing them into XML attributes.

## Post-hoc repair

If you have an existing `.drawio` file with this problem, run:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/fix_drawio_value_quotes.py \
    family_tree.drawio
```

The script rewrites `value="..."` attributes in place, escaping any raw double
quotes as `&quot;`. It is idempotent.

## Verification

After fixing, re-run:

```bash
python3 ~/.hermes/skills/drawio-family-trees/scripts/verify_family_tree.py \
    family_tree.drawio
```

A successful run reports:

```
All checks passed. The chart is safe to deliver.
```
