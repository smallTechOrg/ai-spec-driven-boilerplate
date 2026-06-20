import pytest

# Shadow the root async autouse `_fresh_db` fixture with a SYNC no-op for the e2e tier. The e2e tests drive
# the LIVE HTTP server (their own DB), not the in-process engine, and pytest-playwright's sync `page` fixture
# runs its own event loop via greenlet — a co-resident async autouse fixture collides at Runner teardown
# ("Cannot run the event loop while another loop is running"). A sync override removes the async runner here.


@pytest.fixture(autouse=True)
def _fresh_db():
    yield
