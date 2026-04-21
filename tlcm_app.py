from fastapi import FastAPI
from core.config import TLCMConfig
from server.main import app as _default_app
from core.database import init_db
from core.async_bus import MemoryBus
from server.middleware import TLCMAuthMiddleware

class TLCMApp:
    """
    Standard programmatic initialization for plugging TLCM into any Python application.
    Allows easy overriding of the configuration via code.
    """
    def __init__(self, config: TLCMConfig = None):
        self.config = config or TLCMConfig.load_from_env()
        self.fastapi_app = _default_app
        
    def get_asgi_app(self) -> FastAPI:
        """Return the core FastAPI app for mounting into standard web servers (uvicorn/hypercorn)."""
        return self.fastapi_app
        
    def start_background_workers(self):
        """Initialize the async bus if running outside of a standard ASGI lifecycle."""
        init_db()
        bus = MemoryBus.get_instance()
        bus.start_worker()
