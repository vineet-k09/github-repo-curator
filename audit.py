#!/usr/bin/env python3
"""
GitHub Repository Auditor & Summarizer
User-agnostic CLI tool to audit, filter, and summarize GitHub repositories.
"""

import argparse
import json
import os
import subprocess
import sys

def run_gh(args):
    try:
        res = subprocess.run(['gh', 'api'] + args, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
        return None
    except Exception:
        return None

def get_authenticated_user():
    user_data = run_gh(['/user'])
    if user_data and 'login' in user_data:
        return user_data['login']
    return None

def get_user_repos(username):
    # Fetch all public and private repos using /user/repos?type=all
    repos = run_gh(['--paginate', '/user/repos?type=all&per_page=100'])
    if not repos:
        repos = run_gh(['--paginate', f'/users/{username}/repos?per_page=100'])
    
    if not repos:
        print(f"Error: Could not fetch repositories for user '{username}'.", file=sys.stderr)
        sys.exit(1)
        
    return repos

def audit_repo(owner, name):
    full_name = f"{owner}/{name}"
    
    tree_data = run_gh([f"/repos/{full_name}/git/trees/HEAD?recursive=1"])
    if not tree_data or 'tree' not in tree_data:
        return {
            'name': name,
            'full_name': full_name,
            'status': 'EMPTY',
            'commit_count': 0,
            'commit_category': '< 5 commits',
            'source_files': 0,
            'total_files': 0
        }
        
    files = [f['path'] for f in tree_data['tree'] if f['type'] == 'blob']
    code_files = [f for f in files if not any(x in f for x in ['node_modules/', '.next/', 'vendor/', 'dist/', 'build/', '.git/'])]
    src_files = [f for f in code_files if f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.html', '.css', '.gd', '.php', '.typ'))]

    commits = run_gh([f"/repos/{full_name}/commits?per_page=30"])
    commit_count = len(commits) if isinstance(commits, list) else 0
    if commit_count >= 30:
        commit_cat = '> 20 commits'
    elif commit_count >= 5:
        commit_cat = '5-20 commits'
    else:
        commit_cat = '< 5 commits'

    return {
        'name': name,
        'full_name': full_name,
        'total_files': len(files),
        'code_files': len(code_files),
        'source_files': len(src_files),
        'commit_count': commit_count,
        'commit_category': commit_cat
    }

def main():
    parser = argparse.ArgumentParser(description="Audit and filter GitHub repositories for any user.")
    parser.add_argument('--user', type=str, help="Target GitHub username (defaults to current gh user)")
    parser.add_argument('--5commits', '--less-than-5-commits', action='store_true', dest='five_commits', help="Filter repositories with < 5 commits")
    parser.add_argument('--private', action='store_true', help="Filter private repositories only")
    parser.add_argument('--public', action='store_true', help="Filter public repositories only")
    parser.add_argument('--raw', '--list-only', action='store_true', dest='raw', help="Output line-separated repo names only (great for piping/clipboard)")
    parser.add_argument('-o', '--out-file', type=str, help="Save repo names list to specified text file (e.g. target_repos.txt)")
    parser.add_argument('--json-out', type=str, help="Save full audit details to JSON file")

    args = parser.parse_args()

    target_user = args.user or get_authenticated_user()
    if not target_user:
        print("Error: Could not determine GitHub user. Specify --user <username> or run `gh auth login`.", file=sys.stderr)
        sys.exit(1)

    if not args.raw:
        print(f"🔍 Auditing repositories for GitHub user: @{target_user}...", file=sys.stderr)

    raw_repos = get_user_repos(target_user)
    owned_repos = [r for r in raw_repos if r['owner']['login'].lower() == target_user.lower()]

    audited = []
    for idx, r in enumerate(owned_repos, 1):
        name = r['name']
        if not args.raw:
            print(f"  [{idx}/{len(owned_repos)}] Auditing {name}...", end="\r", file=sys.stderr)
        info = audit_repo(target_user, name)
        info['description'] = r.get('description') or ''
        info['visibility'] = r.get('visibility') or ('PRIVATE' if r.get('private') else 'PUBLIC')
        info['language'] = (r.get('primaryLanguage') or {}).get('name', 'N/A')
        audited.append(info)

    # Filter logic
    filtered = audited
    if args.five_commits:
        filtered = [r for r in filtered if r['commit_count'] < 5]
    if args.private:
        filtered = [r for r in filtered if r['visibility'] == 'PRIVATE']
    if args.public:
        filtered = [r for r in filtered if r['visibility'] == 'PUBLIC']

    repo_names = [r['name'] for r in filtered]

    if args.out_file:
        with open(args.out_file, 'w') as f:
            f.write("\n".join(repo_names) + ("\n" if repo_names else ""))
        if not args.raw:
            print(f"\n📝 Saved {len(repo_names)} repo names to '{args.out_file}'.", file=sys.stderr)

    if args.json_out:
        with open(args.json_out, 'w') as f:
            json.dump(filtered, f, indent=2)
        if not args.raw:
            print(f"✅ Saved detailed JSON report to '{args.json_out}'.", file=sys.stderr)

    if args.raw:
        for name in repo_names:
            print(name)
    else:
        print("\n" + "=" * 80, file=sys.stderr)
        print(f"📊 GITHUB REPOSITORY AUDIT SUMMARY FOR @{target_user} ({len(filtered)} repos match)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"{'Repository Name':<32} | {'Visibility':<8} | {'Language':<12} | {'Commits':<13} | {'Source Files':<12}", file=sys.stderr)
        print("-" * 80, file=sys.stderr)
        for a in filtered:
            print(f"{a['name']:<32} | {a['visibility']:<8} | {a['language']:<12} | {a['commit_category']:<13} | {a['source_files']} / {a['total_files']}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

if __name__ == '__main__':
    main()
