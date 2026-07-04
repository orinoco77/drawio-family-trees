# Extracting a nested skill to a standalone GitHub repository

This skill was originally developed as a sub-directory (`drawio-family-trees/`) inside the larger `drawio-skill` skill. This reference records how to extract such a nested skill into its own GitHub repository so it can be installed as a first-class Hermes skill under `~/.hermes/skills/<name>/`.

## When to use this recipe

- A skill has outgrown its parent skill or is conceptually separate.
- You want to version-control it independently.
- You want to install it directly from GitHub rather than as a sub-directory of another skill.

## Preconditions

1. The skill has its own `SKILL.md` at its root.
2. The skill is reasonably self-contained (scripts, references, templates, assets are inside its tree).
3. You can identify and remove any hard dependencies on files in the parent skill.

## Step-by-step extraction

### 1. Identify external dependencies

Search the skill tree for references to the parent skill's files or absolute paths that assume the nested location:

```bash
cd ~/.hermes/skills/<parent-skill>/<sub-skill>
grep -R "<parent-skill>/" . --include="*.py" --include="*.md"
grep -R "~/.hermes/skills/<parent-skill>" . --include="*.py" --include="*.md"
```

Common dependencies:
- A shared linter or validator (e.g. `validate.py`) referenced by absolute path.
- Documentation examples that use the old absolute install path.

### 2. Vendor or eliminate the dependency

If the parent skill provides a utility the sub-skill needs, copy it into the sub-skill's own `scripts/` directory and update internal references to use the local copy first.

Example: `verify_family_tree.py` originally looked for `validate.py` in the parent `drawio-skill/scripts/` directory. We copied `validate.py` into `drawio-family-trees/scripts/` and updated `verify_family_tree.py` to prefer the local copy, with a fallback to the parent location for backwards compatibility during transition.

### 3. Update absolute paths in documentation

After extraction, a standalone skill lives at `~/.hermes/skills/<sub-skill-name>/`. Replace absolute paths that assume the nested location:

```bash
# Before
~/.hermes/skills/<parent-skill>/<sub-skill>/scripts/...

# After
~/.hermes/skills/<sub-skill>/scripts/...
```

Use `grep -R` to find every occurrence in `.md` and `.py` files and update them consistently.

### 4. Add repo hygiene files

Create the files a GitHub repository should have:

- `README.md` — what the skill does, how to install it, and a quick usage example.
- `LICENSE` — MIT is the convention used by Hermes skills.
- `.gitignore` — exclude `__pycache__`, `*.pyc`, and generated outputs (`*.png`, `*.svg`, `*.drawio`) unless they are committed examples.

### 5. Clean generated artifacts

Remove `__pycache__/` directories and any temporary rendered files before the first commit:

```bash
find . -type d -name __pycache__ -exec rm -rf {} +
rm -f *.png *.svg *.drawio
```

### 6. Create and push the GitHub repository

```bash
mkdir -p ~/tmp/<sub-skill>
cp -r ~/.hermes/skills/<parent-skill>/<sub-skill>/. ~/tmp/<sub-skill>/
cd ~/tmp/<sub-skill>
git init
git add .
git commit -m "Initial commit: extracted <sub-skill> from <parent-skill>"
git branch -M main
git remote add origin https://github.com/<user>/<sub-skill>.git
git push -u origin main
```

### 7. Install the standalone skill

```bash
rm -rf ~/.hermes/skills/<sub-skill>
git clone https://github.com/<user>/<sub-skill>.git ~/.hermes/skills/<sub-skill>
```

Restart Hermes or refresh skills, then verify it loads:

```bash
hermes skills list
# or
skill_view(name='<sub-skill>')
```

### 8. Remove the nested copy

Once you have confirmed the standalone install works:

```bash
rm -rf ~/.hermes/skills/<parent-skill>/<sub-skill>
```

## Verification

After extraction, run a representative command end-to-end:

```bash
python3 ~/.hermes/skills/<sub-skill>/scripts/<representative-script>.py --help
python3 ~/.hermes/skills/<sub-skill>/scripts/<representative-script>.py ...
```

If the skill has a validation script, run it against a sample output to confirm the vendored dependencies work.

## Pitfalls

- **Hard-coded install paths in scripts.** Any script that builds an absolute path to a sibling skill's directory will break after extraction. Prefer relative paths or the `~/.hermes/skills/<sub-skill>/` convention.
- **Forgetting to vendor shared utilities.** If the sub-skill silently depends on a parent-skill script, the standalone install will fail with a missing-file error the first time it is used.
- **Committing `__pycache__` or rendered outputs.** These clutter the repo and can cause merge conflicts. Add a `.gitignore` before the first commit.
- **Leaving the nested copy in place.** Hermes may load the skill from the old nested location instead of the standalone directory, masking path errors. Delete the nested copy after verifying the standalone install.
- **Documentation still points to the old location.** Users (including future you) will copy-paste broken commands. Search-and-replace all absolute paths before committing.

## Example: this skill

`drawio-family-trees` was extracted from `drawio-skill/drawio-family-trees/` to its own repository. The only dependency removed was `validate.py`, which was copied into `scripts/`. All documentation paths were updated to `~/.hermes/skills/drawio-family-trees/`.
