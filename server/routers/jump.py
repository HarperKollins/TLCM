from fastapi import APIRouter, HTTPException
from core.temporal_jump import TemporalJumpEngine
from server.models import JumpReq

router = APIRouter()
jumper = TemporalJumpEngine()

@router.post("/")
def perform_jump(req: JumpReq):
    try:
        result = jumper.jump(
            workspace_name=req.workspace,
            from_epoch_name=req.from_epoch,
            to_epoch_name=req.to_epoch,
            query=req.query
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delta")
def get_jump_delta(req: JumpReq):
    try:
        delta = jumper.calculate_delta(
            workspace_name=req.workspace,
            from_epoch_name=req.from_epoch,
            to_epoch_name=req.to_epoch
        )
        return delta
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
