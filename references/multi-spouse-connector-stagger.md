# Multi-spouse child-connector stagger

## Symptom

A parent with multiple spouses has all child connectors drawn at the same horizontal
y-level. The children of different spouses share a single long sibling bar, making it
hard to see which children belong to which marriage. In wide trees this also produces
overlapping horizontal connector pairs in the validator.

## Intended behaviour

Each spouse's child group gets its own horizontal connector. The **rightmost** group's
connector is highest (closest to the children), and each group to the left steps down
by `CHILD_CONNECTOR_STAGGER` pixels. This keeps the descenders visually separated and
prevents overlap.

## Root cause

The connector-drawing loop contained a guard meant to keep staggered connectors from
rising above the child-driven cap:

```python
base_connector_y = connector_y_from_child(child_y)
stagger = CHILD_CONNECTOR_STAGGER
if base_connector_y + (n_groups - 1) * stagger > connector_y_from_child(child_y) and n_groups > 1:
    available = max(0.0, connector_y_from_child(child_y) - base_connector_y)
    stagger = available / (n_groups - 1)
```

Because `base_connector_y` is exactly `connector_y_from_child(child_y)`, `available`
is always `0`, so `stagger` collapses to `0`. All groups end up at the same y.

## Fix

Remove the guard. The per-group `resolve_connector_y(...)` call already clamps each
connector to the parent-driven minimum, so staggered connectors cannot fall below the
required bar position:

```python
base_connector_y = connector_y_from_child(child_y)
stagger = CHILD_CONNECTOR_STAGGER

for stagger_idx, gi in enumerate(group_infos):
    candidate_y = base_connector_y + (n_groups - 1 - stagger_idx) * stagger
    resolved_y = resolve_connector_y(
        descender_top=gi["descender_top"],
        max_label_h=MAX_LABEL_H,
        child_y=child_y,
    )
    connector_y = max(candidate_y, resolved_y)
```

`group_infos` is sorted left-to-right, so `stagger_idx == 0` is the leftmost group and
gets the lowest (largest y) connector.

## Verification

After the fix, generate a chart for a root with multi-spouse descendants (e.g.
Thomas Finigan b. abt 1820). Look for a parent with multiple spouses, such as
James Finigan (b. 1846): his two wives' child groups now have separate horizontal
connectors staggered by `CHILD_CONNECTOR_STAGGER` (4 px by default).

The validator should report:

```text
Connector overlap check
OK: no overlapping horizontal child connectors
```

## Related

- `references/connector-geometry.md`
- `references/descendants-sibling-bar-overlap-bug.md` — the separate wide-vs-narrow sibling overlap issue
