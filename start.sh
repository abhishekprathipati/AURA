#!/bin/bash
exec gunicorn --bind 0.0.0.0:${PORT:-10000} --worker-class gthread --workers 1 --threads 4 --timeout 120 app:app
