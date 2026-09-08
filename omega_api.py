"""Authenticated HTTP interface for the capability runtime."""
import asyncio
import hmac
import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse

from omega_runtime import MAX_REQUEST_BYTES


def create_router(runtime):
    router = APIRouter(prefix="/omega", tags=["capabilities"])

    def authenticate(authorization: str = Header(default="")):
        key = os.getenv("OMEGA_API_KEY", "")
        if not key:
            raise HTTPException(503, "Set OMEGA_API_KEY to enable the capability API")
        if not hmac.compare_digest(authorization.encode(), ("Bearer " + key).encode()):
            raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})
        return "api:operator"

    @router.get("/capabilities")
    async def capabilities(owner=Depends(authenticate)):
        return {"capabilities": runtime.list_capabilities(), "request_limit_bytes": MAX_REQUEST_BYTES,
                "timeout_seconds": runtime.timeout}

    @router.post("/run")
    async def run(request: Request, owner=Depends(authenticate)):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Request exceeds 12 MiB")
        try:
            data = json.loads(body)
            if not isinstance(data, dict) or set(data) - {"capability", "payload", "idempotency_key", "inputs"}:
                raise ValueError("Expected capability, payload, and optional idempotency_key/inputs")
            if not isinstance(data.get("capability"), str):
                raise ValueError("capability must be a string")
            result = await asyncio.to_thread(runtime.run, data["capability"], data.get("payload", {}), owner,
                                            idempotency_key=data.get("idempotency_key"), inputs=data.get("inputs"))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if result["status"] == "busy":
            raise HTTPException(429, result["error"]["message"], headers={"Retry-After": "2"})
        return result

    @router.get("/tasks/{task_id}")
    async def task(task_id: str, owner=Depends(authenticate)):
        result = await asyncio.to_thread(runtime.get_task, task_id, owner)
        if result is None:
            raise HTTPException(404, "Task not found")
        return result

    @router.get("/tasks/{task_id}/artifacts/{filename:path}")
    async def artifact(task_id: str, filename: str, owner=Depends(authenticate)):
        try:
            path = await asyncio.to_thread(runtime.artifact_path, task_id, owner, filename)
        except (FileNotFoundError, ValueError):
            raise HTTPException(404, "Artifact not found")
        return FileResponse(path, filename=path.name, media_type="application/octet-stream",
                            headers={"X-Content-Type-Options": "nosniff"})

    return router
