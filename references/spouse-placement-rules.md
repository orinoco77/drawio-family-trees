# Spouse Placement Rules for Family Tree Charts

These rules govern how multiple spouses are arranged in descendant charts, based on whether the person is a descendant in the tree or a spouse who married into the family.

## The Three Cases

### 1. Descendants (People with Ancestors in the Chart)

**Rule:** All spouses extend to the **right** of the descendant.

**Rationale:** The descendant is the focus of the tree. All relationships flow from them, so extending all spouses to one side is unambiguous.

**Example:** James Finigan (son of Thomas Finigan) has three spouses. All three appear to his right because he is the descendant being traced.

```
Thomas Finigan
     │
James Finigan — Spouse 1 — Spouse 2 — Spouse 3
```

### 2. Non-Descendants (Spouses Who Married Into the Family)

**Rule:** The **other** spouses (from previous marriages) must appear on the **opposite side** from the descendant they married.

**Rationale:** This makes it visually clear that these other spouses are NOT married to the descendant. The current spouse stays adjacent to the descendant; previous spouses extend away.

**Example:** Olivia O'Keeffe married Adam Short (the descendant being traced). Olivia's previous spouses (Michael, Douglas) appear on the opposite side from Adam.

```
Adam Short — Olivia O'Keeffe — Michael — Douglas
     │              │
  (current)    (previous spouses extend RIGHT, away from Adam)
```

### 3. Special Case: Exactly Two Spouses

**Rule:** Place **one spouse on each side** of the person.

**Rationale:** With only two spouses, putting one on each side is the least ambiguous layout. It clearly shows two distinct relationships without suggesting a chain of marriages.

**Example:** Patricia has two partners. One appears on her left, one on her right.

```
Partner 1 — Patricia — Partner 2
     │          │
   Child 1    Child 2
```

## Application to Blended Family Charts

When generating a chart for a descendant (e.g., "Descendants of Brian Short"):

| Person | Status | Spouse Placement |
|--------|--------|------------------|
| Brian Short | Root descendant | Spouses to the right |
| Adam Short | Descendant (Brian's son) | Spouses to the right |
| Olivia O'Keeffe | Non-descendant (married Adam) | Other spouses opposite from Adam |
| Patricia | Descendant (Olivia's daughter) | If 2 partners: one each side |

## Implementation Notes

For step-children support in `generate_descendants_with_steps.py`:

1. Track whether each person is a descendant of the root (has `FAMC` link to someone in the chart)
2. For descendants: append all spouses to the right
3. For non-descendants with multiple spouses:
   - Current spouse (married to descendant) stays adjacent to descendant
   - Other spouses inserted after current spouse (extending away)
4. For exactly 2 spouses: alternate left/right regardless of descendant status

## Marriage-line pairing

The placement rules above only describe *where* names sit. The marriage lines must also reflect *who* is married to whom:

- **Descendant with multiple spouses:** each spouse is married to the descendant. Draw a line from the descendant (`people[0]`) to each spouse.
- **Non-descendant with multiple spouses (step-parent case):** the additional spouses are married to the non-descendant's current spouse, not to each other. Draw lines from the current spouse to each additional spouse; do not chain them `(A, B), (B, C)`.
- **Exactly two spouses:** draw both marriage lines from the central person to each spouse.

## Visual Verification

A correctly laid out chart should pass this visual test:

- [ ] Descendants have all spouses extending to their right
- [ ] Non-descendants' other spouses extend away from the descendant they married
- [ ] People with exactly 2 spouses have one on each side
- [ ] Child connector lines clearly descend from the correct marriage
