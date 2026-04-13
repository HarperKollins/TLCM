"""
TLCM Database Layer
SQLite schema implementing the full Temporal Layered Context Memory architecture.
Never overwrites. Always versions. Every memory knows its epoch and workspace.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "tlcm.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the TLCM database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- WORKSPACES: Separate cognitive contexts (HKAI, Screenplay, Personal, etc.)
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- EPOCHS: Temporal phases within a workspace
        -- e.g., "Pre-launch", "Early traction", "Post-Ella"
        CREATE TABLE IF NOT EXISTS epochs (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,          -- NULL = currently active epoch
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- MEMORIES: The core. NEVER deleted, always versioned.
        -- parent_id creates a version chain: v1 -> v2 -> v3
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            epoch_id TEXT NOT NULL REFERENCES epochs(id),
            content TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            parent_id TEXT REFERENCES memories(id),  -- NULL = original
            update_reason TEXT,                       -- WHY was this updated?
            is_current INTEGER DEFAULT 1,             -- Only one version is "current"
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'user_stated',        -- user_stated | inferred | updated
            tags TEXT,                                -- JSON array of tags
            recall_count INTEGER DEFAULT 0,           -- Biological decay: frequency
            last_recalled_at TEXT,                    -- Biological decay: recency
            -- Neuro-weighted fields (populated by Gemini Judge)
            emotional_valence INTEGER DEFAULT 0,      -- -10 (negative) to +10 (positive)
            urgency_score INTEGER DEFAULT 5,          -- 0 (trivial) to 10 (critical)
            semantic_impact INTEGER DEFAULT 5,        -- 0 (redundant) to 10 (paradigm shift)
            reconsolidation_flag TEXT DEFAULT 'append', -- strengthen | weaken | append | contradicts_core
            created_at TEXT DEFAULT (datetime('now')),
            archived_at TEXT                          -- Set when superseded
        );

        -- CROSS-WORKSPACE LINKS: Authorized connections ONLY
        -- The user must explicitly say "link these two workspaces"
        CREATE TABLE IF NOT EXISTS cross_workspace_links (
            id TEXT PRIMARY KEY,
            source_workspace_id TEXT REFERENCES workspaces(id),
            target_workspace_id TEXT REFERENCES workspaces(id),
            link_reason TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- TEMPORAL JUMPS LOG: Record every time a temporal jump was performed
        CREATE TABLE IF NOT EXISTS temporal_jumps (
            id TEXT PRIMARY KEY,
            workspace_id TEXT REFERENCES workspaces(id),
            from_epoch_id TEXT REFERENCES epochs(id),
            to_epoch_id TEXT REFERENCES epochs(id),
            query TEXT,
            result TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Indexes for fast retrieval
        CREATE INDEX IF NOT EXISTS idx_memories_workspace ON memories(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_memories_epoch ON memories(epoch_id);
        CREATE INDEX IF NOT EXISTS idx_memories_current ON memories(is_current);
        CREATE INDEX IF NOT EXISTS idx_memories_parent ON memories(parent_id);
        CREATE INDEX IF NOT EXISTS idx_epochs_workspace ON epochs(workspace_id);

        -- ASYNC QUEUE: Persistent Tier 1 STM queue
        CREATE TABLE IF NOT EXISTS async_queue (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
            retry_count INTEGER DEFAULT 0,
            error_msg TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Safely try to add new columns to an existing DB (migration)
    migrations = [
        "ALTER TABLE memories ADD COLUMN recall_count INTEGER DEFAULT 0",
        "ALTER TABLE memories ADD COLUMN last_recalled_at TEXT",
        "ALTER TABLE memories ADD COLUMN emotional_valence INTEGER DEFAULT 0",
        "ALTER TABLE memories ADD COLUMN urgency_score INTEGER DEFAULT 5",
        "ALTER TABLE memories ADD COLUMN semantic_impact INTEGER DEFAULT 5",
        "ALTER TABLE memories ADD COLUMN reconsolidation_flag TEXT DEFAULT 'append'",
    ]
    for migration in migrations:
        try:
            cursor.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.commit()
    conn.close()
    print("[TLCM] Database initialized.")


def new_id() -> str:
    return str(uuid.uuid4())


if __name__ == "__main__":
    init_db()
