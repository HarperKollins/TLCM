import json
import httpx
from typing import Optional, Dict, Any, Generator

class TLCMClient:
    """
    Official Python SDK for the TLCM (Temporal Layered Context Memory) Engine.
    Abstracts REST API calls and real-time Server-Sent Events (SSE) into a simple developer interface.
    """
    
    def __init__(self, api_base: str = "http://127.0.0.1:8000/api"):
        self.api_base = api_base.rstrip('/')
        self.http_client = httpx.Client(timeout=30.0)

    def remember(self, content: str, workspace: str = "default_workspace", epoch: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest a memory into the Tier 1 STM Queue. Non-blocking backend processing.
        Returns the temp_id immediately.
        """
        payload = {
            "content": content,
            "workspace_name": workspace,
            "epoch_name": epoch
        }
        res = self.http_client.post(f"{self.api_base}/memories/remember", json=payload)
        res.raise_for_status()
        return res.json()

    def remember_sync(self, content: str, workspace: str = "default_workspace", epoch: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest and block until Gemini completes biological memory evaluation (LTM).
        """
        payload = {
            "content": content,
            "workspace_name": workspace,
            "epoch_name": epoch
        }
        res = self.http_client.post(f"{self.api_base}/memories/remember/sync", json=payload)
        res.raise_for_status()
        return res.json()

    def search(self, query: str, workspace: str, limit: int = 5) -> list[Dict[str, Any]]:
        """Temporal Recall: Retrieve most relevant past items."""
        res = self.http_client.post(f"{self.api_base}/memories/recall", json={
            "query": query,
            "workspace_name": workspace,
            "limit": limit
        })
        res.raise_for_status()
        return res.json()

    def get_version_history(self, memory_id: str) -> list[Dict[str, Any]]:
        """Fetch the exact linear evolution of a specific memory block."""
        res = self.http_client.get(f"{self.api_base}/memories/{memory_id}/history")
        res.raise_for_status()
        return res.json()

    def temporal_jump(self, workspace: str, from_epoch: str, to_epoch: Optional[str] = None) -> Dict[str, Any]:
        """Calculates the Mathematical Semantic Delta vector."""
        payload = {
            "workspace": workspace,
            "from_epoch": from_epoch,
            "to_epoch": to_epoch
        }
        res = self.http_client.post(f"{self.api_base}/jump/delta", json=payload)
        res.raise_for_status()
        return res.json()

    def listen_for_events(self) -> Generator[Dict[str, Any], None, None]:
        """
        Listen to the SSE stream continuously.
        Yields real-time events including Cascade Orphaning notices and Proactive Recall bursts.
        """
        with httpx.stream("GET", f"{self.api_base}/events", timeout=None) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        yield data
                    except json.JSONDecodeError:
                        pass
