"""
PhishGuard SSE Router — Server-Sent Events for real-time dashboard
"""
import asyncio
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.auth import get_current_user
from app.models import User
from app.services.notification_queue import subscribe_sse, unsubscribe_sse

router = APIRouter(prefix="/api/sse", tags=["SSE"])


@router.get("/events")
async def event_stream(user: User = Depends(get_current_user)):
    """
    SSE endpoint — streams real-time campaign events to the admin dashboard.
    The client connects with EventSource and receives JSON event payloads.
    """

    async def _generate():
        queue = await subscribe_sse()
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25)
                    yield {
                        "event": data.get("type", "event"),
                        "data": json.dumps(data),
                    }
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {"event": "heartbeat", "data": json.dumps({"type": "heartbeat"})}
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_sse(queue)

    return EventSourceResponse(_generate())
