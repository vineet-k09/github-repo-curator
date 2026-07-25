# 🛠️ GitHub Repo Curator (`github-repo-curator`)

> **User-agnostic, file-driven CLI toolkit to audit, filter, organize, and automate GitHub repository setup.**

`github-repo-curator` helps developers analyze their GitHub account, filter out clutter, and bulk-publish selected repositories with automated descriptions, topics, and initial `README.md` generation.

---

## ✨ Features

- 🔍 **User-Agnostic Audit**: Audit any GitHub account (`--user <username>`) or your authenticated `gh` CLI profile.
- 📊 **Smart Categorization**: Sorts repositories by size/scale, commit count (`< 5`, `5-20`, `> 20`), and team size (Solo vs Multi-contributor).
- 📋 **File-Driven Workflow**: Uses `target_repos.txt` as a single source of truth so you only publish/modify what you choose.
- 📋 **Clipboard Friendly**: Output raw repository lists (`--raw`) directly compatible with `wl-copy`, `xclip`, or text redirection.
- 🚀 **Automated Setup & Publishing**: Converts selected private repos to `PUBLIC`, generates default descriptions, adds topics, and bootstraps initial `README.md` files via GitHub REST API.

---

## 🚀 Quick Start

### 1. Run Repository Audit
```bash
# View interactive table summary of all your repositories
make audit

# Or audit another GitHub account
python3 audit.py --user octocat
```

### 2. Extract Target Repositories
```bash
# Extract repos with < 5 commits directly to target_repos.txt
make audit-5commits

# Or output raw list for copying via clipboard
python3 audit.py --raw | wl-copy
```

### 3. Bulk Publish & Setup Selected Repositories
Edit `target_repos.txt` to keep only the repos you want to modify/publish, then run:
```bash
make setup-repos
```

---

## 🛠️ Commands & Options

### `audit.py`
| Argument | Description |
| :--- | :--- |
| `--user <username>` | GitHub username to audit (default: authenticated `gh` user) |
| `--5commits` | Filter repositories with `< 5 commits` |
| `--solo` | Filter solo-contributor repositories |
| `--scale {scaffolding,small,full}` | Filter by scale category |
| `--raw` | Output line-separated repo names only |
| `-o <file>` | Output filtered repo names to specified file (e.g. `target_repos.txt`) |
| `--json-out <file>` | Save detailed JSON audit report |

### `setup_repos.py`
| Argument | Description |
| :--- | :--- |
| `--user <username>` | GitHub username |
| `-f <file>` | Source of truth file containing repo names (default: `target_repos.txt`) |
| `--repo <name>` | Single repository target override |

---

## 📄 License
Released under the [MIT License](LICENSE).
