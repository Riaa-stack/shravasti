import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.connection_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/progress/{paper_id}")
async def websocket_progress_endpoint(websocket: WebSocket, paper_id: str):
    await manager.connect(websocket, paper_id)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, paper_id)
