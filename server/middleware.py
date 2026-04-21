from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os

class TLCMAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow unprotected pathways
        if request.url.path.startswith("/dashboard") or request.url.path == "/":
            return await call_next(request)
            
        expected_key = os.getenv("TLCM_API_KEY")
        if expected_key:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Missing Authorization Header"})
                
            token = auth_header.split(" ")[1]
            if token != expected_key:
                return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
                
        return await call_next(request)
