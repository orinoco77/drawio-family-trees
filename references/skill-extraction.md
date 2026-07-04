# Extracting this skill to a standalone GitHub repo

The `drawio-family-trees` skill was originally developed as a sub-directory of the larger `drawio-skill` skill. It is now self-contained and can live in its own repository.

## Why extraction is clean

- All generator scripts embed their own minimal GEDCOM parser; there are no imports from the parent `drawio-skill`.
- `scripts/validate.py` is bundled inside this skill, so the structural linter travels with it.
- `scripts/verify_family_tree.py` prefers the local `validate.py` and only falls back to a parent-skill location if the local copy is missing.
- All documentation paths point to `~/.hermes/skills/drawio-family-trees/...`, the standalone install location.

## Files that make it a standalone repo

- `SKILL.md` — Hermes skill manifest.
- `README.md` — human-facing repo readme.
- `LICENSE` — MIT license.
- `.gitignore` — ignores `__pycache__`, rendered outputs, and cached charts.
- `scripts/` — all runnable tools.
- `references/` — documentation and pitfall notes.

## Extraction steps

1. Create an empty repository on GitHub, e.g. `YOUR_USERNAME/drawio-family-trees`.
2. Copy the skill directory into the new repo root:
   ```bash
   mkdir -p ~/tmp/drawio-family-trees-extract
   cp -r ~/.hermes/skills/drawio-skill/drawio-family-trees/. ~/tmp/drawio-family-trees-extract/
   cd ~/tmp/drawio-family-trees-extract
   git init
   git add .
   git commit -m "Initial commit: draw.io family tree generator from GEDCOM"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/drawio-family-trees.git
   git push -u origin main
   ```
3. Install the extracted skill into Hermes:
   ```bash
   rm -rf ~/.hermes/skills/drawio-family-trees
   git clone https://github.com/YOUR_USERNAME/drawio-family-trees.git ~/.hermes/skills/drawio-family-trees
   ```
4. Restart or refresh Hermes so the skill is discovered from `~/.hermes/skills/drawio-family-trees/SKILL.md`.

## What to update after extraction

- If you move the repo to a non-standard install path, update the absolute paths in `SKILL.md` and `references/*.md`.
- If you rename the skill, update the `name:` field in `SKILL.md` frontmatter.

## What to leave behind

Do not carry over the parent `drawio-skill` repository's tracked changes. They are unrelated to this family-tree work.
