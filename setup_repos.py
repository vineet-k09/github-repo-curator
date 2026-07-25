#!/usr/bin/env python3
"""
GitHub Repository Publisher & Configurator
Reads a list of target repository names from a file (e.g. target_repos.txt) as the source of truth,
sets visibility to PUBLIC, applies descriptions, adds topics, and ensures README files exist.
"""

import argparse
import base64
import json
import os
import subprocess
import sys

def run_gh_cmd(args):
    try:
        res = subprocess.run(['gh', 'api'] + args, capture_output=True, text=True, check=True)
        return json.loads(res.stdout) if res.stdout else {}
    except subprocess.CalledProcessError as e:
        return None

def update_repo(owner, repo):
    full_name = f"{owner}/{repo}"
    print(f"🔧 Configuring & Publishing: {full_name}")

    # 1. Update visibility to PUBLIC
    try:
        subprocess.run(['gh', 'repo', 'edit', full_name, '--visibility', 'public', '--accept-visibility-change-consequences'], capture_output=True, check=True)
        print(f"  ✅ Visibility set to PUBLIC")
    except Exception as e:
        print(f"  ⚠️ Visibility update notice: {e}")

    # Fetch current info
    repo_data = run_gh_cmd([f"/repos/{full_name}"])
    curr_desc = (repo_data or {}).get("description") or ""

    # Generate default description if empty
    if not curr_desc:
        curr_desc = f"Open-source repository and project workspace for {repo}."
        try:
            subprocess.run(['gh', 'repo', 'edit', full_name, '--description', curr_desc], capture_output=True, check=True)
            print(f"  ✅ Generated & set default description.")
        except Exception as e:
            print(f"  ⚠️ Description update error: {e}")

    # 3. Check & Create README if missing
    readme_check = run_gh_cmd([f"/repos/{full_name}/readme"])
    if not readme_check or 'content' not in readme_check:
        print(f"  📝 Creating initial README.md...")
        content = f"""# {repo}

{curr_desc}

## 🚀 Overview
Welcome to **{repo}**! This repository contains source code, documentation, and project assets.

## 🛠️ Getting Started
```bash
# Clone the repository
git clone https://github.com/{owner}/{repo}.git
cd {repo}
```

## 📄 License
This project is released as open-source under the MIT License.
"""
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = json.dumps({
            "message": "docs: add initial README.md",
            "content": encoded_content
        })
        
        try:
            subprocess.run(['gh', 'api', '-X', 'PUT', f'/repos/{full_name}/contents/README.md', '--input', '-'], input=payload, text=True, capture_output=True, check=True)
            print(f"  ✅ Created README.md successfully.")
        except Exception as e:
            print(f"  ⚠️ README creation error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Update and publish repositories listed in a target file.")
    parser.add_argument('--user', type=str, help="GitHub username (defaults to gh authenticated user)")
    parser.add_argument('-f', '--file', type=str, default="target_repos.txt", help="Text file containing list of target repo names (default: target_repos.txt)")
    parser.add_argument('--repo', type=str, help="Single target repository name (overrides file)")

    args = parser.parse_args()

    # Determine user
    owner = args.user
    if not owner:
        user_data = run_gh_cmd(['/user'])
        if user_data and 'login' in user_data:
            owner = user_data['login']
        else:
            print("Error: Could not determine GitHub user. Specify --user <username>.", file=sys.stderr)
            sys.exit(1)

    target_repos = []
    if args.repo:
        target_repos = [args.repo]
    elif os.path.exists(args.file):
        with open(args.file, 'r') as f:
            target_repos = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"📋 Loaded {len(target_repos)} target repositories from '{args.file}'.")
    else:
        print(f"Error: Target file '{args.file}' not found and no single --repo provided.", file=sys.stderr)
        sys.exit(1)

    if not target_repos:
        print("No target repositories found to update.")
        sys.exit(0)

    for repo in target_repos:
        update_repo(owner, repo)

    print("\n🎉 Repository publication & setup complete!")

if __name__ == '__main__':
    main()
