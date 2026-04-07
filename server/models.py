from pydantic import BaseModel
from typing import Optional, List

# Workspace Models
class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class WorkspaceLink(BaseModel):
    source: str
    target: str
    reason: str

# Epoch Models
class EpochCreate(BaseModel):
    workspace: str
    name: str
    description: Optional[str] = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# Memory Models
class MemoryStoreReq(BaseModel):
    workspace: str
    content: str
    epoch: Optional[str] = None
    source: Optional[str] = "user_stated"

class MemoryUpdateReq(BaseModel):
    workspace: str
    new_content: str
    reason: str

class MemoryRecallReq(BaseModel):
    query: str
    workspace: str
    epoch: Optional[str] = None
    limit: Optional[int] = 5

# Jump Models
class JumpReq(BaseModel):
    workspace: str
    from_epoch: str
    to_epoch: Optional[str] = None
    query: Optional[str] = None
