from typing import List, Optional
import requests

class TLCMArchivalMemoryAdapter:
    """
    Adapter bridging Letta/MemGPT's Archival Memory interface with TLCM.
    Instead of flat vector records, chunks are mapped to Temporal Epochs,
    and updates natively trigger Cascade Orphaning mathematically.
    """
    
    def __init__(self, api_base: str = "http://localhost:8000/api", workspace_name: str = "letta_agent_memory"):
        self.api_base = api_base
        self.workspace_name = workspace_name
        self.ensure_workspace()

    def ensure_workspace(self):
        try:
            requests.post(f"{self.api_base}/workspaces/", json={
                "name": self.workspace_name,
                "description": "Letta Agent Core Workspace"
            })
        except Exception:
            pass

    def insert(self, memory_string: str) -> None:
        """Letta's Archival Memory Insert → TLCM memory ingestion via Bus."""
        requests.post(f"{self.api_base}/memories/remember", json={
            "content": memory_string,
            "workspace_name": self.workspace_name,
            "source": "letta_archival",
        })

    def search(self, query: str, count: int = 5) -> List[str]:
        """Letta's Archival Memory Search → TLCM temporal recall pipeline."""
        res = requests.post(f"{self.api_base}/memories/recall", json={
            "query": query,
            "workspace_name": self.workspace_name,
            "limit": count
        })
        if res.status_code == 200:
            data = res.json()
            return [hit["content"] for hit in data]
        return []
