import sys
import os

# Add parent directory to python path to import app logic
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as curator_app

# Set SQLite path to Vercel writable /tmp directory
if os.environ.get('VERCEL'):
    curator_app.DB_PATH = '/tmp/cache.db'

curator_app.init_db()

# Export BaseHTTPRequestHandler for Vercel Python Serverless Functions
class handler(curator_app.CuratorAPIHandler):
    pass

