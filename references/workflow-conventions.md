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

**Always output to the family-tree folder:**
```bash
--output "/home/tv/family tree charts/<descriptive_name>.drawio"
```

The folder name contains a space; quote the path in shell commands. If the
folder does not exist, create it first:

```bash
mkdir -p "/home/tv/family tree charts"
```

**Do not** scatter `.drawio`, `.png`, or `.svg` files directly in `/home/tv` or
in unrelated project directories unless explicitly requested. Keep all generated
family-tree artifacts in this single folder.

## Testing Changes

When modifying the step-children generator or other scripts:

1. Edit in place at `~/.hermes/skills/drawio-family-trees/scripts/`
2. Test with the cached GEDCOM:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/generate_descendants_with_steps.py \
       --gedcom "/home/tv/Short Main Family Tree.ged" \
       --root "Adam Jonathan Short" \
       --generations 3 \
       --include-step-children \
       --output "/home/tv/family tree charts/test_step_children.drawio"
   ```
3. Render and verify visually:
   ```bash
   python3 ~/.hermes/skills/drawio-family-trees/scripts/flatten_export.py "/home/tv/family tree charts/test_step_children.drawio"
   ```

## Git Status

Check git status before committing:
```bash
cd ~/.hermes/skills/drawio-family-trees
git status
```

Commit completed work when the user is happy with it. If the working tree
already contains unrelated uncommitted changes from earlier work, ask the user
before mixing them into a new commit.
