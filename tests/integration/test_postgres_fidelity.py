import os
import pytest
from core.providers.postgres import PostgresProvider

# Skip if Postgres isn't running
POSTGRES_AVAILABLE = os.getenv("POSTGRES_DSN") is not None

@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Requires live Postgres connection.")
def test_postgres_version_chaining():
    provider = PostgresProvider()
    
    # 1. Setup mock memory data
    root_id = "mem-pg-1"
    data = {
        "id": root_id,
        "workspace_id": "ws-1",
        "epoch_id": "ep-1",
        "content": "Initial baseline belief.",
        "version": 1
    }
    
    # 2. Insert and fetch chain
    provider.save_memory(data)
    chain = provider.get_memory_chain(root_id)
    
    assert len(chain) > 0
    assert chain[0]["content"] == "Initial baseline belief."
