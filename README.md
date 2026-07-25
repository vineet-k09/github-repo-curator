# 🛠️ GitHub Repo Curator (`github-repo-curator`)

> **User-agnostic, interactive Web Dashboard & CLI toolkit to audit, filter, organize, and bulk-manage GitHub repositories.**

`github-repo-curator` replaces manual command-line copy-pasting with a clean, interactive Web Dashboard where you can filter repositories by visibility (Public/Private), commit count, scale, or team size, multi-select targets, and perform bulk actions (Public/Private toggle, Edit Descriptions, Add Topics, Generate MIT License, Generate README.md, or Bulk Delete).

---

## ✨ Features

- 🖥️ **Interactive Web Dashboard**: Beautiful dark glassmorphism UI running locally (`http://localhost:8080`). Zero external npm/pip dependencies required!
- 🔍 **Interactive Filters**:
  - **Visibility**: All / Public 🌐 / Private 🔒
  - **Commits**: All / `< 5 Commits` ⚡ / `5-20 Commits` 📦 / `> 20 Commits` 🔥
  - **Scale**: All / Scaffolding 🏗️ / Small App 📄 / Full Application 🚀
  - **Live Search**: Instant keyword search on repo names, languages, and descriptions.
- ⚡ **Bulk Operations**:
  - 🌐 **Set Visibility** (Public / Private)
  - 📝 **Bulk Edit Descriptions**
  - 🏷️ **Bulk Add Topics & Tags**
  - 📜 **Generate MIT License** (`LICENSE`)
  - 📄 **Generate Initial README** (`README.md`)
  - 🗑️ **Bulk Repository Deletion** (with explicit text confirmation modal to prevent accidents).
- 📜 **Real-Time Execution Logs**: Modal showing live step-by-step API responses and status for all operations.

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

### 2. Alternative CLI Workflow

```bash
# View interactive ASCII table summary in terminal
make audit

# Extract repos with < 5 commits directly to target_repos.txt
make audit-5commits

# Bulk publish and setup repos listed in target_repos.txt
make setup-repos
```

---

## 📄 License
Released under the [MIT License](LICENSE).
