from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from core.interfaces import RelationalStoreProvider
import os

class PostgresProvider(RelationalStoreProvider):
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_DSN", "dbname=tlcm user=postgres password=secret host=localhost")

    def get_connection(self):
        return psycopg2.connect(self.dsn)

    def save_memory(self, memory_data: Dict[str, Any]):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO memories
                       (id, workspace_id, epoch_id, content, version, source, tags,
                        emotional_valence, urgency_score, semantic_impact, reconsolidation_flag)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        memory_data["id"], memory_data["workspace_id"], memory_data["epoch_id"],
                        memory_data["content"], memory_data.get("version", 1), memory_data.get("source", "user_stated"),
                        "[]", memory_data.get("emotional_valence", 0), memory_data.get("urgency_score", 5),
                        memory_data.get("semantic_impact", 5), memory_data.get("reconsolidation_flag", "append")
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def get_memory_chain(self, memory_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Postgres Recursive CTE for exact chain extraction
                cursor.execute("""
                    WITH RECURSIVE version_chain AS (
                      SELECT * FROM memories WHERE id = %s
                      UNION ALL
                      SELECT m.* FROM memories m
                      INNER JOIN version_chain vc ON m.parent_id = vc.id
                    )
                    SELECT * FROM version_chain ORDER BY version ASC
                """, (memory_id,))
                return cursor.fetchall()
        finally:
            conn.close()
