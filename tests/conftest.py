import hashlib
import time

import pytest


@pytest.fixture(autouse=True)
def _realistic_test_duration(request):
    """Deterministic per-test delay (1.5s-4.5s) derived from the test's node id,
    so the suite has real duration variance for Smart Tests to work with -- same
    pattern already proven necessary on the unify-ref-todo reference project."""
    digest = hashlib.sha256(request.node.nodeid.encode()).hexdigest()
    delay = 1.5 + (int(digest[:8], 16) % 3000) / 1000.0
    time.sleep(delay)
