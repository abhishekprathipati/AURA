"""Vercel serverless entry point — exposes the Flask app as a WSGI handler."""
import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app import app

# Vercel looks for a variable named `app` (WSGI) or `handler` (ASGI)
# Flask's app object is WSGI-compatible, so this works directly.
