# Workflow Conventions for Family Tree Development

## Development Location

All family tree generator development happens in the git repository at:
```
~/.hermes/skills/drawio-family-trees/
```

This is a proper git repo with remote origin. Use standard git workflow:
- Edit files in place
- Test changes
- Commit when ready

## Output Locations

**Always output to the home folder (`/home/tv/`):**
```bash
--output /home/tv/family_tree.drawio
```

**Never** put output in the clawd folder or other project directories unless explicitly requested.

## Testing Changes

When modifying the step-children generator or other scripts:

1. Edit in place at `~/.hermes/skills/drawio-family-trees/scripts/`
2. Test with the cached GEDCOM:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
       --gedcom "/home/tv/.hermes/cache/documents/doc_e98a9d0410ca_Short Main Family Tree (1).ged" \
       --root "Adam Jonathan Short" \
       --generations 3 \
       --descendants-only \
       --include-step-children \
       --output /home/tv/test_step_children.drawio
   ```
3. Render and verify visually:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py /home/tv/test_step_children.drawio
   ```

## Git Status

Check git status before committing:
```bash
cd ~/.hermes/skills/drawio-family-trees
git status
```

Currently there are uncommitted changes:
- `SKILL.md` modified
- `references/step-children-gedcom.md` (new)
- `references/dynamic-descender-height.md` (new)
- `references/duplicate-person-markers.md` (new)
- `scripts/generate_descendants_with_steps.py` (new)

These should be committed when the step-children feature is finalized.
