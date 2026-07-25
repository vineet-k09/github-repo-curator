#!/usr/bin/env python3
"""
GitHub Repo Curator - Web Application Server
Zero-dependency Python HTTP Server & REST API with progressive loading and automatic port fallback.
"""

import base64
import json
import os
import socket
import subprocess
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

DEFAULT_PORT = 8080
MAX_PORT_ATTEMPTS = 20

def run_gh(args):
    try:
        res = subprocess.run(['gh', 'api'] + args, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
        return None
    except Exception:
        return None

def get_authenticated_user():
    return run_gh(['/user'])

def get_single_repo_details(owner, name):
    full_name = f"{owner}/{name}"
    
    # 1. Tree check
    tree_data = run_gh([f"/repos/{full_name}/git/trees/HEAD?recursive=1"])
    has_tree = tree_data and 'tree' in tree_data
    files = [f['path'] for f in tree_data['tree'] if f['type'] == 'blob'] if has_tree else []
    
    code_files = [f for f in files if not any(x in f for x in ['node_modules/', '.next/', 'vendor/', 'dist/', 'build/', '.git/'])]
    src_files = [f for f in code_files if f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.html', '.css', '.gd', '.php', '.typ'))]

    # 2. Commits check
    commits = run_gh([f"/repos/{full_name}/commits?per_page=30"])
    commit_count = len(commits) if isinstance(commits, list) else 0

    has_readme = any('readme' in f.lower() for f in files)
    has_license = any('license' in f.lower() for f in files)

    return {
        'name': name,
        'full_name': full_name,
        'total_files': len(files),
        'code_files': len(code_files),
        'source_files': len(src_files),
        'commit_count': commit_count,
        'has_readme': has_readme,
        'has_license': has_license
    }

class CuratorAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'web'), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/user':
            self.send_json_response(get_authenticated_user() or {})

        elif path == '/api/repos':
            user = get_authenticated_user()
            if not user or 'login' not in user:
                self.send_json_response({'error': 'Unauthorized'}, status=401)
                return
            
            owner = user['login']
            # Using /user/repos?type=all to fetch ALL public AND private repos owned by user
            repos_raw = run_gh(['--paginate', '/user/repos?type=all&per_page=100']) or []
            owned = [r for r in repos_raw if r['owner']['login'].lower() == owner.lower()]

            # Instant metadata load without blocking sub-requests
            results = []
            for r in owned:
                topics = [t['name'] for t in (r.get('repositoryTopics') or [])] if isinstance(r.get('repositoryTopics'), list) else []
                results.append({
                    'name': r['name'],
                    'full_name': r['full_name'],
                    'description': r.get('description') or '',
                    'visibility': r.get('visibility') or ('PRIVATE' if r.get('private') else 'PUBLIC'),
                    'is_private': r.get('private', False),
                    'language': (r.get('primaryLanguage') or {}).get('name') or r.get('language') or 'N/A',
                    'homepage': r.get('homepageUrl') or r.get('homepage') or '',
                    'stargazers_count': r.get('stargazers_count', 0),
                    'forks_count': r.get('forks_count', 0),
                    'pushed_at': (r.get('pushed_at') or r.get('pushedAt') or '')[:10],
                    'topics': topics,
                    'has_readme': None,  # Computed on demand/progressive load
                    'has_license': bool(r.get('license')),
                    'commit_count': None,
                    'source_files': None,
                    'total_files': None
                })

            self.send_json_response({'owner': owner, 'repos': results})

        elif path == '/api/repo-details':
            repo_name = query.get('repo', [None])[0]
            user = get_authenticated_user()
            if not repo_name or not user:
                self.send_json_response({'error': 'Missing repo parameter'}, status=400)
                return
            
            details = get_single_repo_details(user['login'], repo_name)
            self.send_json_response(details)

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode('utf-8')) if length > 0 else {}

        user = get_authenticated_user()
        if not user or 'login' not in user:
            self.send_json_response({'error': 'Unauthorized'}, status=401)
            return
        owner = user['login']
        repos = body.get('repos', [])
        logs = []

        if path == '/api/actions/visibility':
            vis = body.get('visibility', 'public')
            for repo in repos:
                full_name = f"{owner}/{repo}"
                try:
                    subprocess.run(['gh', 'repo', 'edit', full_name, '--visibility', vis, '--accept-visibility-change-consequences'], capture_output=True, text=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Visibility set to {vis.upper()}'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

        elif path == '/api/actions/description':
            desc = body.get('description', '')
            for repo in repos:
                full_name = f"{owner}/{repo}"
                try:
                    subprocess.run(['gh', 'repo', 'edit', full_name, '--description', desc], capture_output=True, text=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Description updated.'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

        elif path == '/api/actions/topics':
            topics = body.get('topics', [])
            for repo in repos:
                full_name = f"{owner}/{repo}"
                try:
                    cmd = ['gh', 'repo', 'edit', full_name]
                    for t in topics:
                        cmd.extend(['--add-topic', t])
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Topics added: {topics}'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

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
                payload = json.dumps({"message": "docs: add MIT LICENSE", "content": encoded})
                try:
                    subprocess.run(['gh', 'api', '-X', 'PUT', f'/repos/{full_name}/contents/LICENSE', '--input', '-'], input=payload, text=True, capture_output=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': 'Created MIT LICENSE'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

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
                payload = json.dumps({"message": "docs: add initial README.md", "content": encoded})
                try:
                    subprocess.run(['gh', 'api', '-X', 'PUT', f'/repos/{full_name}/contents/README.md', '--input', '-'], input=payload, text=True, capture_output=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': 'Created README.md'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

        elif path == '/api/actions/delete':
            confirm = body.get('confirm', False)
            if not confirm:
                self.send_json_response({'error': 'Deletion requires explicit confirmation flag.'}, status=400)
                return
            
            for repo in repos:
                full_name = f"{owner}/{repo}"
                try:
                    res = subprocess.run(['gh', 'repo', 'delete', full_name, '--yes'], capture_output=True, text=True, check=True)
                    logs.append({'repo': repo, 'status': 'success', 'message': f'Deleted repository {full_name}'})
                except subprocess.CalledProcessError as e:
                    logs.append({'repo': repo, 'status': 'error', 'message': e.stderr.strip()})

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
    port = find_available_port(DEFAULT_PORT)
    if not port:
        print(f"❌ Error: Could not find an open port starting from {DEFAULT_PORT}.", file=sys.stderr)
        sys.exit(1)

    print(f"🚀 Starting GitHub Repo Curator Web Server on http://localhost:{port}")
    server = HTTPServer(('0.0.0.0', port), CuratorAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")

if __name__ == '__main__':
    main()
