"""
TLCM Test Configuration
Sets TLCM_TEST_MODE and patches DB paths to temp directory.
"""
import pytest
import os
from pathlib import Path
import tempfile

import core.database
import core.embeddings

# Activate test mode BEFORE any test runs
os.environ["TLCM_TEST_MODE"] = "1"


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """
    Redirect DB + Chroma to a temp directory so tests never touch real data.
    TLCM_TEST_MODE=1 is already set above, so _embed() and jump() skip Ollama.
    """
    temp_dir = tempfile.TemporaryDirectory()
    test_db_path = Path(temp_dir.name) / "test_tlcm.db"
    test_chroma_path = Path(temp_dir.name) / "test_chroma"

    core.database.DB_PATH = test_db_path
    core.embeddings.CHROMA_PATH = test_chroma_path

    core.database.init_db()

    yield

    try:
        temp_dir.cleanup()
    except PermissionError:
        pass  # Windows file locks from ChromaDB
