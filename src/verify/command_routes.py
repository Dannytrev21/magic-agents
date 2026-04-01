"""FastAPI router exposing the command registry as REST endpoints."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from verify.commands import CommandRegistry


def create_command_router(registry: CommandRegistry) -> APIRouter:
    """Return an :class:`APIRouter` wired to *registry*."""

    router = APIRouter()

    @router.get("/api/commands")
    async def list_commands() -> JSONResponse:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for descriptor in registry.list():
            grouped[descriptor.category].append(asdict(descriptor))
        return JSONResponse(content=dict(grouped))

    @router.post("/api/commands/{name}")
    async def execute_command(name: str, request: Request) -> JSONResponse:
        entry = registry.find(name)
        if entry is None:
            return JSONResponse(
                content={"error": f"Command '{name}' not found"},
                status_code=404,
            )
        descriptor, handler = entry
        body: dict[str, Any] = await request.json()
        result = handler(body)
        return JSONResponse(content=asdict(result))

    return router
