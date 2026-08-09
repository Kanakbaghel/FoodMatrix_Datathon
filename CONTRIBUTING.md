# Contributing Guide — Team FoodMatrix

This document outlines how we'll work together on this repository to keep things organized and conflict-free.

---

## 🌿 Branching Strategy

- **`main`** — always contains stable, working code/files only. Nobody pushes directly to `main`.
- **Feature branches** — every team member works on their own branch:
  ```bash
  git checkout -b <yourname>-<short-task-description>
  ```
  
---

## 🔄 Workflow

1. **Pull the latest changes** before starting new work:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create your branch:**
   ```bash
   git checkout -b yourname-task
   ```

3. **Work, then commit with clear messages:**
   ```bash
   git add .
   git commit -m "Add: cleaned trade dataset for 2015-2024"
   ```
   Use prefixes like `Add:`, `Fix:`, `Update:`, `Remove:` for clarity.

4. **Push your branch:**
   ```bash
   git push origin yourname-task
   ```

5. **Open a Pull Request (PR)** on GitHub into `main`, with a short description of what you did.

6. **Get at least one review** from another team member before merging (helps catch errors early and keeps everyone in the loop).

---

## 📂 Where to Put What

| Type of file | Folder |
|---|---|
| Raw downloaded data | `data/raw/` |
| Cleaned/processed data | `data/processed/` |
| Jupyter notebooks (EDA, modeling) | `notebooks/` |
| Reusable Python scripts | `scripts/` |
| Dashboard exports, charts | `visualizations/` |
| Final video, slides | `presentation/` |
| Meeting notes, references | `docs/` |

---

## ⚠️ Important Notes

- **Do not commit large files** (raw datasets, videos) directly — they're excluded via `.gitignore`. Use Google Drive/shared storage for those and link them in `docs/`.
- **Do not commit secrets** (API keys, passwords) — use a `.env` file (already gitignored).
- **Keep notebooks clean** — clear output cells before committing if they contain large outputs, to keep the repo lightweight.
- **Communicate in the WhatsApp group** if you're stuck or your branch has merge conflicts — better to ask than to force-push over someone else's work.

---

## 🗓️ Suggested Weekly Rhythm

- **Check-in:** Once a week (day/time to be decided by team) — quick status update from everyone
- **PR reviews:** Try to review teammates' PRs within 24-48 hours so work doesn't get blocked

---

Questions? Ask in the group — we're all figuring this out together! 🙌
