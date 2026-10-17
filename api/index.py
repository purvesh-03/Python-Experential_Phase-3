"""
api/index.py - Vercel Serverless Function Entry Point
Phase 3: Social Network Friend Recommendation System

Exposes the Flask WSGI application instance `app` to Vercel's Python runtime.
"""

import sys
import os

# Ensure the root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Vercel looks for the WSGI application callable (e.g. app)
# Export app as handler if required by specific serverless setups
app = app
