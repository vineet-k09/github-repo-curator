# 🛠️ GitHub Repo Curator (`github-repo-curator`)

> **User-agnostic, interactive Web Dashboard & CLI toolkit to audit, filter, organize, and bulk-manage GitHub repositories.**

`github-repo-curator` replaces manual command-line copy-pasting with a clean, interactive Web Dashboard where you can filter repositories by visibility (Public/Private), commit count, or documentation status, multi-select targets, and perform bulk actions (Public/Private toggle, Edit Descriptions, Add Topics, Generate MIT License, Generate README.md, or Bulk Delete).

---

## ✨ Features

- 🖥️ **Interactive Web Dashboard**: Beautiful dark glassmorphism UI running locally (`http://localhost:8080`). Zero external npm/pip dependencies required!
- 🔑 **Dual Authentication (gh CLI or Personal Access Token)**:
  - Auto-detects `gh` CLI login if available.
  - If unauthenticated, displays an interactive step-by-step onboarding card in the UI with a direct link to generate a Personal Access Token (PAT).
  - Terminal logs provide explicit error notices, token export commands, and a clickable PAT creation link.
- 💾 **SQLite Local Persistence (`cache.db`)**: Stores repository metadata locally so dashboard loads instantly (< 100ms) without hitting GitHub API rate limits.
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

## 🚀 Quick Start

### 1. Launch Interactive Web Dashboard
```bash
git clone https://github.com/vineet-k09/github-repo-curator.git
cd github-repo-curator

# Launch the Web GUI
make gui
```
Open **http://localhost:8080** in your browser!

---

### 🔑 Authentication Options

#### Option A: GitHub CLI (`gh`)
If you have `gh` CLI installed and authenticated:
```bash
gh auth login
make gui
```

#### Option B: Personal Access Token (PAT)
If you don't have `gh` CLI installed:
1. Generate a token on GitHub: [Click to Create Token (pre-filled scopes)](https://github.com/settings/tokens/new?scopes=repo,delete_repo&description=GitHub-Repo-Curator)
2. Export the token in your terminal:
   ```bash
   export GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere"
   make gui
   ```
3. Or paste the token directly into the interactive onboarding card in the Web GUI!

---

### 🧪 Running Tests

```bash
make test
```

---

## 📄 License
Released under the [MIT License](LICENSE).
