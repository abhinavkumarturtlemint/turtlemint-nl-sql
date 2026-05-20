"""Isolate tests from the live app: use a private data dir and seed it once,
so the test chdb store never collides with a running backend's locked store.
"""
import os
import tempfile

os.environ.setdefault("NLSQL_DATA_DIR", tempfile.mkdtemp(prefix="nlsql_test_"))

from app.data import seed  # noqa: E402

seed.seed()
