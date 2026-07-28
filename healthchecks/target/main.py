#!/usr/bin/env python3
import sys
import os
from wsgiref.simple_server import make_server

# Add target/ to sys.path
target_dir = os.path.dirname(os.path.abspath(__file__))
if target_dir not in sys.path:
    sys.path.insert(0, target_dir)

from app import application
from db import init_db

def run_server(port=8011):
    init_db()
    print(f"Healthchecks server listening on http://0.0.0.0:{port}...")
    server = make_server('0.0.0.0', port, application)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    port = 8011
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
