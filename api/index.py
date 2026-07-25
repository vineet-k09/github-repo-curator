import sys
import os

# Add parent directory to python path to import app logic
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app

# Set SQLite path to Vercel writable /tmp directory
if os.environ.get('VERCEL'):
    app.DB_PATH = '/tmp/cache.db'

app.init_db()

# Export BaseHTTPRequestHandler for Vercel Python Serverless Functions
handler = app.CuratorAPIHandler
