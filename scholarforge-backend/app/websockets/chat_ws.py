import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.websockets.connection_manager import manager
from app.models.chat import ChatSession, ChatMessage, ChatRole
from app.agents.graph import research_graph

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket, 
    session_id: str,
    # In a real app we'd verify the JWT token via query param or initial message for Auth
):
    await manager.connect(websocket, session_id)
    
    # Normally get db session from a dependency, but in WS we can manage it
    # For simplicity, we just use a generator to get a session
    from app.db.postgres import async_session_maker
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            query = payload.get("query")
            paper_ids = payload.get("paper_ids", [])
            user_id = payload.get("user_id") # Must be provided by client since WS auth is tricky
            
            if not query or not user_id:
                await websocket.send_json({"type": "error", "message": "Missing query or user_id"})
                continue
                
            async with async_session_maker() as session:
                chat_session_result = await session.execute(select(ChatSession).where(ChatSession.id == uuid.UUID(session_id), ChatSession.user_id == uuid.UUID(user_id)))
                chat_session = chat_session_result.scalar_one_or_none()
                if not chat_session:
                    await websocket.send_json({"type": "error", "message": "Session not found"})
                    continue
                    
                # Fetch history
                history_result = await session.execute(select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at.asc()))
                history = history_result.scalars().all()
                chat_history = [{"role": msg.role.value, "content": msg.content} for msg in history]
                
                # Save User message
                user_msg = ChatMessage(session_id=chat_session.id, role=ChatRole.user, content=query)
                session.add(user_msg)
                await session.commit()
                
                # Setup Agent state
                state = {
                    "user_id": user_id,
                    "paper_ids": chat_session.paper_ids,
                    "task_type": "chat",
                    "query": query,
                    "chat_history": chat_history[-10:],
                    "retrieved_chunks": [],
                    "result": {}
                }
                
                # Inform client we are processing
                await websocket.send_json({"type": "status", "message": "Processing..."})
                
                # Await Graph
                final_state = await research_graph.ainvoke(state)
                result = final_state["result"]
                
                # Save Agent message
                agent_msg = ChatMessage(session_id=chat_session.id, role=ChatRole.assistant, content=result["response"], sources=result["sources"])
                session.add(agent_msg)
                await session.commit()
                
                # Simulate streaming response for now (since graph invoke is blocking)
                words = result["response"].split(" ")
                for word in words:
                    await websocket.send_json({"type": "token", "token": word + " "})
                    await asyncio.sleep(0.02)
                    
                # Send sources
                for source in result["sources"]:
                    await websocket.send_json({"type": "source", "source": source})
                    
                await websocket.send_json({"type": "complete"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)
