#!/usr/bin/env python3
"""
GitHub Repository Auditor & Summarizer
User-agnostic CLI tool to audit, filter, and extract repository lists for any GitHub user.
"""

import argparse
import json
import os
import subprocess
import sys

def run_gh(args):
    try:
        out = subprocess.check_output(['gh', 'api'] + args, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception:
        return None

def get_authenticated_user():
    user_data = run_gh(['/user'])
    if user_data and 'login' in user_data:
        return user_data['login']
    return None

def get_user_repos(username):
    endpoint = f'/users/{username}/repos?per_page=100'
    repos = run_gh(['--paginate', endpoint])
    if not repos:
        endpoint = '/user/repos?per_page=100'
        repos = run_gh(['--paginate', endpoint])
    
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
            'contributor_category': 'Solo',
            'code_files': 0,
            'total_files': 0,
            'scale_category': 'Scaffolding / Assets'
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

    contributors = run_gh([f"/repos/{full_name}/contributors?per_page=10"])
    contrib_count = len(contributors) if isinstance(contributors, list) else 1
    contrib_cat = 'Solo' if contrib_count <= 1 else f'Multi-contributor ({contrib_count})'

    if len(src_files) == 0:
        scale_cat = 'Scaffolding / Assets'
    elif len(src_files) <= 5:
        scale_cat = 'Small Application / Script'
    else:
        scale_cat = 'Full Application'

    return {
        'name': name,
        'full_name': full_name,
        'total_files': len(files),
        'code_files': len(code_files),
        'source_files': len(src_files),
        'commit_count': commit_count,
        'commit_category': commit_cat,
        'contributor_category': contrib_cat,
        'scale_category': scale_cat
    }

def main():
    parser = argparse.ArgumentParser(description="Audit and filter GitHub repositories for any user.")
    parser.add_argument('--user', type=str, help="Target GitHub username (defaults to current gh user)")
    parser.add_argument('--5commits', '--less-than-5-commits', action='store_true', dest='five_commits', help="Filter repositories with < 5 commits")
    parser.add_argument('--solo', action='store_true', help="Filter solo contributor repositories")
    parser.add_argument('--scale', type=str, choices=['scaffolding', 'small', 'full'], help="Filter by scale (scaffolding, small, full)")
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
    if args.solo:
        filtered = [r for r in filtered if r['contributor_category'] == 'Solo']
    if args.scale:
        scale_map = {
            'scaffolding': 'Scaffolding / Assets',
            'small': 'Small Application / Script',
            'full': 'Full Application'
        }
        target_scale = scale_map[args.scale]
        filtered = [r for r in filtered if r['scale_category'] == target_scale]

    repo_names = [r['name'] for r in filtered]

    # Handle output file
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

    # Output to stdout
    if args.raw:
        for name in repo_names:
            print(name)
    else:
        print("\n" + "=" * 90, file=sys.stderr)
        print(f"📊 GITHUB REPOSITORY AUDIT SUMMARY FOR @{target_user} ({len(filtered)} repos match)", file=sys.stderr)
        print("=" * 90, file=sys.stderr)
        print(f"{'Repository Name':<30} | {'Visibility':<8} | {'Scale':<24} | {'Commits':<13} | {'Team':<6}", file=sys.stderr)
        print("-" * 90, file=sys.stderr)
        for a in filtered:
            print(f"{a['name']:<30} | {a['visibility']:<8} | {a['scale_category']:<24} | {a['commit_category']:<13} | {a['contributor_category']:<6}", file=sys.stderr)
        print("=" * 90, file=sys.stderr)

if __name__ == '__main__':
    main()
