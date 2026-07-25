#!/usr/bin/env python3
"""
GitHub Repo Curator - Web Application Server & SQLite Cache Engine
Supports both GitHub CLI (`gh`) and direct GitHub REST API using Personal Access Tokens (PAT).
"""

import base64
import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, SimpleHTTPRequestHandler

DEFAULT_PORT = 8080
MAX_PORT_ATTEMPTS = 20
DB_PATH = os.path.join(os.path.dirname(__file__), 'cache.db')
PAT_CREATE_URL = "https://github.com/settings/tokens/new?scopes=repo,delete_repo&description=GitHub-Repo-Curator"

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repo_cache (
            name TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            description TEXT,
            visibility TEXT,
            is_private INTEGER,
            language TEXT,
            homepage TEXT,
            stargazers_count INTEGER,
            forks_count INTEGER,
            pushed_at TEXT,
            topics TEXT,
            has_readme INTEGER,
            has_license INTEGER,
            commit_count INTEGER,
            source_files INTEGER,
            total_files INTEGER,
            last_synced TEXT
        )
    ''')
    conn.commit()
    conn.close()

def run_github_api(endpoint, method='GET', payload=None, token=None):
    auth_token = token or GITHUB_TOKEN

    if auth_token:
        url = f"https://api.github.com{endpoint}" if endpoint.startswith('/') else endpoint
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHub-Repo-Curator"
        }
        data_bytes = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    return json.loads(resp.read().decode('utf-8'))
                elif resp.status == 204:
                    return {}
                return {}
        except Exception:
            return None

    try:
        cmd = ['gh', 'api']
        if method != 'GET':
            cmd.extend(['-X', method])
        cmd.append(endpoint)
        
        input_str = json.dumps(payload) if payload else None
        res = subprocess.run(cmd, input=input_str, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
        return None
    except Exception:
        return None

def get_authenticated_user(token=None):
    return run_github_api('/user', token=token)

def get_single_repo_details(owner, name, token=None):
    full_name = f"{owner}/{name}"
    
    tree_data = run_github_api(f"/repos/{full_name}/git/trees/HEAD?recursive=1", token=token)
    has_tree = tree_data and 'tree' in tree_data
    files = [f['path'] for f in tree_data['tree'] if f['type'] == 'blob'] if has_tree else []
    
    code_files = [f for f in files if not any(x in f for x in ['node_modules/', '.next/', 'vendor/', 'dist/', 'build/', '.git/'])]
    src_files = [f for f in code_files if f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.html', '.css', '.gd', '.php', '.typ'))]

    commits = run_github_api(f"/repos/{full_name}/commits?per_page=30", token=token)
    commit_count = len(commits) if isinstance(commits, list) else 0

    has_readme = any('readme' in f.lower() for f in files)
    has_license = any('license' in f.lower() for f in files)

    return {
        'total_files': len(files),
        'code_files': len(code_files),
        'source_files': len(src_files),
        'commit_count': commit_count,
        'has_readme': 1 if has_readme else 0,
        'has_license': 1 if has_license else 0
    }

def get_all_cached_repos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM repo_cache ORDER BY pushed_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        item = dict(r)
        item['is_private'] = bool(item['is_private'])
        item['has_readme'] = bool(item['has_readme']) if item['has_readme'] is not None else None
        item['has_license'] = bool(item['has_license']) if item['has_license'] is not None else None
        try:
            if isinstance(item['topics'], str):
                item['topics'] = json.loads(item['topics'])
            elif not item['topics']:
                item['topics'] = []
        except Exception:
            item['topics'] = []
        results.append(item)
    return results

def deep_sync_single_repo(owner, name, token=None):
    try:
        details = get_single_repo_details(owner, name, token=token)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE repo_cache SET
                has_readme=?, has_license=?, commit_count=?, source_files=?, total_files=?
            WHERE name=?
        ''', (details['has_readme'], details['has_license'], details['commit_count'], details['source_files'], details['total_files'], name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Deep sync error for {name}: {e}", file=sys.stderr)

def sync_surface_repos(owner, force=False, token=None):
    repos_raw = run_github_api('/user/repos?type=all&per_page=100', token=token) or []
    owned = [r for r in repos_raw if r['owner']['login'].lower() == owner.lower()]

    conn = get_db()
    cursor = conn.cursor()

    existing = {r['name']: dict(r) for r in cursor.execute('SELECT name, pushed_at, commit_count FROM repo_cache').fetchall()}
    current_names = set()
    to_deep_sync = []

    for r in owned:
        name = r['name']
        current_names.add(name)
        full_name = r['full_name']
        description = r.get('description') or ''
        is_private = 1 if r.get('private') else 0
        visibility = (r.get('visibility') or ('PRIVATE' if is_private else 'PUBLIC')).upper()
        language = (r.get('primaryLanguage') or {}).get('name') or r.get('language') or 'N/A'
        homepage = r.get('homepage') or r.get('homepageUrl') or ''
        stargazers = r.get('stargazers_count', 0)
        forks = r.get('forks_count', 0)
        pushed_at = (r.get('pushed_at') or r.get('pushedAt') or '')[:10]
        
        raw_topics = r.get('topics') or []
        topics = raw_topics if isinstance(raw_topics, list) else []
        topics_json = json.dumps(topics)
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')

        cached = existing.get(name)
        needs_deep = force or not cached or cached.get('pushed_at') != pushed_at or cached.get('commit_count') is None
        if needs_deep:
            to_deep_sync.append((owner, name))

        cursor.execute('''
            INSERT INTO repo_cache (
                name, full_name, description, visibility, is_private, language, homepage,
                stargazers_count, forks_count, pushed_at, topics, last_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                full_name=excluded.full_name,
                description=excluded.description,
                visibility=excluded.visibility,
                is_private=excluded.is_private,
                language=excluded.language,
                homepage=excluded.homepage,
                stargazers_count=excluded.stargazers_count,
                forks_count=excluded.forks_count,
                pushed_at=excluded.pushed_at,
                topics=excluded.topics,
                last_synced=excluded.last_synced
        ''', (name, full_name, description, visibility, is_private, language, homepage, stargazers, forks, pushed_at, topics_json, now_str))

    for old_name in list(existing.keys()):
        if old_name not in current_names:
            cursor.execute('DELETE FROM repo_cache WHERE name=?', (old_name,))

    conn.commit()
    conn.close()

    if to_deep_sync:
        executor = ThreadPoolExecutor(max_workers=8)
        for o, n in to_deep_sync:
            executor.submit(deep_sync_single_repo, o, n, token)

class CuratorAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'web'), **kwargs)

    def get_req_token(self):
        auth_hdr = self.headers.get('Authorization')
        if auth_hdr and auth_hdr.startswith('Bearer '):
            return auth_hdr.split(' ')[1].strip()
        return GITHUB_TOKEN

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        token = self.get_req_token()

        if path == '/api/user':
            user = get_authenticated_user(token=token)
            if not user or 'login' not in user:
                self.send_json_response({
                    'error': 'Unauthorized',
                    'pat_url': PAT_CREATE_URL,
                    'message': 'No GitHub authentication detected. Set GITHUB_TOKEN or use gh auth login.'
                }, status=401)
                return
            self.send_json_response(user)

        elif path == '/api/repos':
            user = get_authenticated_user(token=token)
            if not user or 'login' not in user:
                self.send_json_response({
                    'error': 'Unauthorized',
                    'pat_url': PAT_CREATE_URL,
                    'message': 'No GitHub authentication detected.'
                }, status=401)
                return
            
            owner = user['login']
            cached = get_all_cached_repos()

            if not cached:
                sync_surface_repos(owner, force=True, token=token)
                cached = get_all_cached_repos()

            self.send_json_response({'owner': owner, 'repos': cached})

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        token = self.get_req_token()
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode('utf-8')) if length > 0 else {}

        user = get_authenticated_user(token=token)
        if not user or 'login' not in user:
            self.send_json_response({'error': 'Unauthorized'}, status=401)
            return
        owner = user['login']
        repos = body.get('repos', [])
        logs = []
        conn = get_db()
        cursor = conn.cursor()

        if path == '/api/refresh':
            sync_surface_repos(owner, force=body.get('force', False), token=token)
            cached = get_all_cached_repos()
            conn.close()
            self.send_json_response({'owner': owner, 'repos': cached, 'message': 'Smart sync completed.'})
            return

        elif path == '/api/actions/visibility':
            vis = body.get('visibility', 'public').lower()
            vis_upper = vis.upper()
            is_priv = 1 if vis == 'private' else 0
            is_private_bool = (vis == 'private')
            for repo in repos:
                full_name = f"{owner}/{repo}"
                res = run_github_api(f"/repos/{full_name}", method='PATCH', payload={'private': is_private_bool}, token=token)
                if res is not None:
                    cursor.execute('UPDATE repo_cache SET visibility=?, is_private=? WHERE name=?', (vis_upper, is_priv, repo))
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Visibility set to {vis_upper}'})
                else:
                    logs.append({'repo': repo, 'status': 'error', 'message': f'Failed to update visibility for {repo}'})

        elif path == '/api/actions/description':
            desc = body.get('description', '')
            for repo in repos:
                full_name = f"{owner}/{repo}"
                res = run_github_api(f"/repos/{full_name}", method='PATCH', payload={'description': desc}, token=token)
                if res is not None:
                    cursor.execute('UPDATE repo_cache SET description=? WHERE name=?', (desc, repo))
                    logs.append({'repo': repo, 'status': 'success', 'message': 'Description updated.'})
                else:
                    logs.append({'repo': repo, 'status': 'error', 'message': f'Failed to update description for {repo}'})

        elif path == '/api/actions/topics':
            topics = body.get('topics', [])
            topics_json = json.dumps(topics)
            for repo in repos:
                full_name = f"{owner}/{repo}"
                res = run_github_api(f"/repos/{full_name}/topics", method='PUT', payload={'names': topics}, token=token)
                if res is not None:
                    cursor.execute('UPDATE repo_cache SET topics=? WHERE name=?', (topics_json, repo))
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Topics added: {topics}'})
                else:
                    logs.append({'repo': repo, 'status': 'error', 'message': f'Failed to update topics for {repo}'})

        elif path == '/api/actions/license':
            mit_content = f"""MIT License

Copyright (c) 2026 {user.get('name') or owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
            encoded = base64.b64encode(mit_content.encode('utf-8')).decode('utf-8')
            for repo in repos:
                full_name = f"{owner}/{repo}"
                payload = {"message": "docs: add MIT LICENSE", "content": encoded}
                res = run_github_api(f"/repos/{full_name}/contents/LICENSE", method='PUT', payload=payload, token=token)
                if res is not None:
                    cursor.execute('UPDATE repo_cache SET has_license=1 WHERE name=?', (repo,))
                    logs.append({'repo': repo, 'status': 'success', 'message': 'Created MIT LICENSE'})
                else:
                    logs.append({'repo': repo, 'status': 'error', 'message': f'Failed to create LICENSE for {repo}'})

        elif path == '/api/actions/readme':
            for repo in repos:
                full_name = f"{owner}/{repo}"
                content = f"""# {repo}

Open-source project workspace and repository.

## 🚀 Getting Started
```bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
```

## 📄 License
This project is licensed under the MIT License.
"""
                encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                payload = {"message": "docs: add initial README.md", "content": encoded}
                res = run_github_api(f"/repos/{full_name}/contents/README.md", method='PUT', payload=payload, token=token)
                if res is not None:
                    cursor.execute('UPDATE repo_cache SET has_readme=1 WHERE name=?', (repo,))
                    logs.append({'repo': repo, 'status': 'success', 'message': 'Created README.md'})
                else:
                    logs.append({'repo': repo, 'status': 'error', 'message': f'Failed to create README for {repo}'})

        elif path == '/api/actions/delete':
            confirm = body.get('confirm', False)
            if not confirm:
                self.send_json_response({'error': 'Deletion requires explicit confirmation flag.'}, status=400)
                conn.close()
                return
            
            for repo in repos:
                full_name = f"{owner}/{repo}"
                res = run_github_api(f"/repos/{full_name}", method='DELETE', token=token)
                cursor.execute('DELETE FROM repo_cache WHERE name=?', (repo,))
                logs.append({'repo': repo, 'status': 'success', 'message': f'Deleted repository {full_name}'})

        conn.commit()
        conn.close()
        self.send_json_response({'logs': logs})

    def send_json_response(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

def find_available_port(start_port, max_attempts=MAX_PORT_ATTEMPTS):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return None

def main():
    init_db()
    port = find_available_port(DEFAULT_PORT)
    if not port:
        print(f"❌ Error: Could not find an open port starting from {DEFAULT_PORT}.", file=sys.stderr)
        sys.exit(1)

    user = get_authenticated_user()
    print("=" * 70)
    print(f"🚀 GitHub Repo Curator Web Server: http://localhost:{port}")
    print("=" * 70)
    
    if user and 'login' in user:
        print(f"✅ Authenticated GitHub User: @{user['login']} ({user.get('name') or ''})")
    else:
        print("⚠️  NOTICE: No active GitHub authentication detected!")
        print("-------------------------------------------------------------")
        print("👉 Option 1 (CLI): Run 'gh auth login' or export a token:")
        print('   export GITHUB_TOKEN="ghp_yourPersonalAccessToken"')
        print("\n👉 Option 2 (Web UI): Clickable Token Generator Link:")
        print(f"   🔗 {PAT_CREATE_URL}")
        print("\n💡 Open http://localhost:{} to configure token interactively in the browser UI.".format(port))
        print("-------------------------------------------------------------")

    server = HTTPServer(('0.0.0.0', port), CuratorAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")

if __name__ == '__main__':
    main()
