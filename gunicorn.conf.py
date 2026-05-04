"""
PinFlow AI — Gunicorn Production Config
Deploy with: gunicorn -c gunicorn.conf.py "app:create_app('production')"
"""

import multiprocessing

# ── Workers ───────────────────────────────────────────────────────────────────
workers     = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads     = 2

# ── Networking ────────────────────────────────────────────────────────────────
bind    = "0.0.0.0:8000"
timeout = 120
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog  = "-"   # stdout
errorlog   = "-"   # stderr
loglevel   = "info"

# ── Process Name ─────────────────────────────────────────────────────────────
proc_name = "pinflow_ai"
