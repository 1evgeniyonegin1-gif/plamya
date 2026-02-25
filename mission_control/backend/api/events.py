"""
SSE Events API — real-time updates via Server-Sent Events.
"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/stream")
async def event_stream(request: Request):
    """SSE endpoint — streams file change events to the frontend."""
    event_bus = request.app.state.event_bus

    async def generate():
        async for event in event_bus.subscribe():
            # Check if client disconnected
            if await request.is_disconnected():
                break
            data = json.dumps({"type": event.type, **event.data}, ensure_ascii=False)
            yield f"event: {event.type}\ndata: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
