import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db

# Import routers
from server.routers import workspaces, epochs, memories, jump

app = FastAPI(
    title="TLCM Engine API",
    description="API for the Temporal Layered Context Memory Engine",
    version="0.2.0"
)

# Enable CORS for the Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database on startup
@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(epochs.router, prefix="/api/epochs", tags=["Epochs"])
app.include_router(memories.router, prefix="/api/memories", tags=["Memories"])
app.include_router(jump.router, prefix="/api/jump", tags=["Temporal Jump"])

@app.get("/")
def read_root():
    return {"message": "TLCM Engine API is running"}
