# 🛠️ GitHub Repo Curator (`github-repo-curator`)

> **User-agnostic, zero-backend-state Web Dashboard & CLI toolkit to audit, filter, organize, and bulk-manage GitHub repositories.**

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvineet-k09%2Fgithub-repo-curator)

`github-repo-curator` replaces manual command-line copy-pasting with a clean, interactive Web Dashboard where you can filter repositories by visibility (Public/Private), commit count, or documentation status, multi-select targets, and perform bulk actions (Public/Private toggle, Edit Descriptions, Add Topics, Generate MIT License, Generate README.md, or Bulk Delete).

---

## 🔒 100% Privacy & Client-Side LocalStorage Architecture

When deployed to Vercel (or hosted anywhere), **no user data or tokens are stored on a server**. 
- Every visitor gets their own **isolated `localStorage` cache** directly in their web browser!
- API requests communicate directly from the browser to `https://api.github.com`.
- Zero setup time for anyone: deploy ONCE to Vercel and share the URL. Anyone can connect their account safely without data mixing.

---

## ✨ Features

- 🌐 **Deploy Anywhere (Vercel & Local)**: Deploy once on Vercel or run locally with zero npm/pip dependencies.
- 🔑 **Dual Authentication (gh CLI or Personal Access Token)**:
  - Auto-detects `gh` CLI login if available locally.
  - Interactive step-by-step onboarding card in the UI with a direct link to generate a Personal Access Token (PAT).
- 💾 **Client-Side `localStorage` Persistence**: Stores repository metadata locally per user so dashboard loads instantly (< 10ms) without hitting rate limits.
- ⚡ **Smart Delta Sync & Parallel Workers**: Only re-audits deep details for repos whose push date changed, using parallel background workers.
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
  - 🗑️ **Bulk Repository Deletion** (with explicit text confirmation modal).
- 🧪 **Automated Test Suite**: Built-in test suite (`make test`) verifying database schema, API responses, and token handling.

---

## 🚀 Deployment Options

### Option 1: 🌐 Deploy Once on Vercel
Deploy to Vercel so anyone can use it without setup:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvineet-k09%2Fgithub-repo-curator)

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

## 🧪 Running Tests

```bash
make test
```

---

## 📄 License
Released under the [MIT License](LICENSE).
