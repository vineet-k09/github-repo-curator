# 🛠️ GitHub Repo Curator (`github-repo-curator`)

> **User-agnostic, interactive Web Dashboard & CLI toolkit to audit, filter, organize, and bulk-manage GitHub repositories.**

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvineet-k09%2Fgithub-repo-curator)

`github-repo-curator` replaces manual command-line copy-pasting with a clean, interactive Web Dashboard where you can filter repositories by visibility (Public/Private), commit count, or documentation status, multi-select targets, and perform bulk actions (Public/Private toggle, Edit Descriptions, Add Topics, Generate MIT License, Generate README.md, or Bulk Delete).

---

## ✨ Features

- 🌐 **Deploy Anywhere (Vercel & Local)**: 1-Click deploy to Vercel or run locally with zero npm/pip dependencies!
- 🔑 **Dual Authentication (gh CLI or Personal Access Token)**:
  - Auto-detects `gh` CLI login if available locally.
  - If unauthenticated or deployed to cloud (Vercel), displays an interactive step-by-step onboarding card in the UI with a direct link to generate a Personal Access Token (PAT).
  - Terminal logs provide explicit error notices, token export commands, and a clickable PAT creation link.
- 💾 **SQLite Local Persistence (`cache.db`)**: Stores repository metadata locally/in `/tmp` so dashboard loads instantly (< 100ms) without hitting GitHub API rate limits.
- ⚡ **Smart Delta Sync & Parallel Workers**: Only re-audits deep details for repos whose push date changed, using parallel multi-threaded background workers.
- 🔍 **Interactive Filters**:
  - **Visibility**: All / Public 🌐 / Private 🔒
  - **Commits**: All / `< 5 Commits` ⚡ / `5-20 Commits` 📦 / `> 20 Commits` 🔥
  - **Quick Filters**: Deployed Apps 🚀 / Missing README 📄 / Missing License 📜
  - **Live Search**: Instant keyword search on repo names, languages, topics, and descriptions.
- ⚡ **Bulk Operations**:
  - 🌐 **Set Visibility** (Public / Private)
  - 📝 **Bulk Edit Descriptions**
  - 🏷️ **Bulk Add Topics & Tags** (`#typescript`, `#nextjs`)
  - 📜 **Generate MIT License** (`LICENSE`)
  - 📄 **Generate Initial README** (`README.md`)
  - 🗑️ **Bulk Repository Deletion** (with explicit text confirmation modal to prevent accidents).
- 🧪 **Automated Test Suite**: Built-in test suite (`make test`) verifying database schema, API responses, and token handling.

---

## 🚀 Deployment Options

### Option 1: 🌐 1-Click Deploy to Vercel
Deploy the entire application as a cloud web app in seconds:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvineet-k09%2Fgithub-repo-curator)

Once deployed, open your Vercel URL and enter your GitHub Personal Access Token (PAT) into the interactive onboarding card to manage your account from anywhere!

---

### Option 2: 💻 Local Web Dashboard
```bash
git clone https://github.com/vineet-k09/github-repo-curator.git
cd github-repo-curator

# Launch the Web GUI locally
make gui
```
Open **http://localhost:8080** in your browser!

---

## 🔑 Authentication Options

### A. GitHub CLI (`gh`)
If you have `gh` CLI installed and authenticated locally:
```bash
gh auth login
make gui
```

### B. Personal Access Token (PAT)
If deployed to cloud or running without `gh` CLI:
1. Generate a token on GitHub: [Click to Create Token (pre-filled scopes)](https://github.com/settings/tokens/new?scopes=repo,delete_repo&description=GitHub-Repo-Curator)
2. Export the token in your terminal:
   ```bash
   export GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere"
   make gui
   ```
3. Or paste the token directly into the interactive onboarding card in the Web GUI!

---

## 🧪 Running Tests

```bash
make test
```

---

## 📄 License
Released under the [MIT License](LICENSE).
