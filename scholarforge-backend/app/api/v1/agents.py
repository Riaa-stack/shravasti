from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import CurrentUser, get_db
from app.schemas.agent_requests import TaskRequest, ChatRequest
from app.agents.graph import research_graph
from app.models.paper import Paper
from app.models.literature_review import LiteratureReview
from app.models.methodology import MethodologyAnalysis
from app.models.research_gap import ResearchGap
from app.models.trend_report import TrendReport
from app.models.research_idea import ResearchIdea, IdeaType
from app.models.citation import Citation, CitationStyle
from app.models.chat import ChatSession, ChatMessage, ChatRole

router = APIRouter()

async def verify_papers_exist(session: AsyncSession, user_id: str, paper_ids: list[str]):
    result = await session.execute(
        select(Paper).where(Paper.id.in_([uuid.UUID(pid) for pid in paper_ids]), Paper.user_id == uuid.UUID(user_id))
    )
    papers = result.scalars().all()
    if len(papers) != len(paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found or do not belong to user.")

@router.post("/literature-review")
async def generate_literature_review(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "literature_review",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    final_state = await research_graph.ainvoke(state)
    result = final_state["result"]
    
    # Save to DB
    lr = LiteratureReview(
        user_id=current_user.id,
        paper_ids=request.paper_ids,
        summary=result["summary"],
        key_findings=result["key_findings"],
        contributions=result["contributions"],
        comparative_review=result.get("comparative_review")
    )
    session.add(lr)
    await session.commit()
    await session.refresh(lr)
    
    return {"id": lr.id, "result": result}

@router.post("/methodology")
async def extract_methodology(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "methodology",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
    result = final_state["result"]
    
    try:
        for paper_id in request.paper_ids:
            ma = MethodologyAnalysis(
                paper_id=uuid.UUID(paper_id),
                algorithms=result.get("algorithms", []),
                models=result.get("models", []),
                datasets=result.get("datasets", []),
                evaluation_metrics=result.get("evaluation_metrics", []),
                experimental_setup=result.get("experimental_setup", "")
            )
            session.add(ma)
        await session.commit()
    except Exception as e:
        await session.rollback()
        # Log but don't fail — result is still valid
        import logging
        logging.getLogger(__name__).warning(f"Could not save methodology to DB: {e}")
    
    return {"result": result}

@router.post("/research-gap")
async def detect_research_gap(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "gap",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
    result = final_state["result"]
    
    try:
        for paper_id in request.paper_ids:
            rg = ResearchGap(
                paper_id=uuid.UUID(paper_id),
                limitations=result.get("limitations", []),
                future_scope=result.get("future_scope", []),
                missing_areas=result.get("missing_areas", []),
                unsolved_problems=result.get("unsolved_problems", []),
                improvement_opportunities=result.get("improvement_opportunities", [])
            )
            session.add(rg)
        await session.commit()
    except Exception as e:
        await session.rollback()
        import logging
        logging.getLogger(__name__).warning(f"Could not save research gap to DB: {e}")
    
    return {"result": result}

@router.post("/trend")
async def analyze_trends(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "trend",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    final_state = await research_graph.ainvoke(state)
    result = final_state["result"]
    
    tr = TrendReport(
        user_id=current_user.id,
        scope_paper_ids=request.paper_ids,
        topics=[t for t in result.get("topics", [])],
        emerging_keywords=[k for k in result.get("emerging_keywords", [])],
        popular_methods=[m for m in result.get("popular_methods", [])],
        publication_timeline=[p for p in result.get("publication_timeline", [])]
    )
    session.add(tr)
    await session.commit()
    
    return {"result": result}

@router.post("/idea")
async def generate_ideas(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "idea",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    final_state = await research_graph.ainvoke(state)
    result = final_state["result"]
    
    # Save a few ideas to DB
    for idea_text in result.get("project_ideas", []):
        ri = ResearchIdea(
            user_id=current_user.id,
            source_paper_ids=request.paper_ids,
            idea_type=IdeaType.project,
            title=idea_text[:100] + "...",
            description=idea_text,
            rationale="Generated by Agent"
        )
        session.add(ri)
    await session.commit()
    return {"result": result}

@router.post("/citation")
async def generate_citations(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "citation",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
    result = final_state["result"]
    
    if request.paper_ids:
        try:
            for style, text in result.items():
                citation = Citation(
                    paper_id=uuid.UUID(request.paper_ids[0]),
                    style=CitationStyle(style),
                    formatted_text=text
                )
                session.add(citation)
            await session.commit()
        except Exception as e:
            await session.rollback()
            import logging
            logging.getLogger(__name__).warning(f"Could not save citation to DB: {e}")
    
    return {"result": result}

@router.post("/difficulty")
async def evaluate_difficulty(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "difficulty",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    final_state = await research_graph.ainvoke(state)
    result = final_state["result"]
    
    if request.paper_ids and "difficulty" in result:
        from app.models.paper import DifficultyLevel
        for paper_id in request.paper_ids:
            paper_result = await session.execute(select(Paper).where(Paper.id == uuid.UUID(paper_id)))
            paper = paper_result.scalar_one_or_none()
            if paper:
                paper.difficulty_level = DifficultyLevel(result["difficulty"])
                session.add(paper)
        await session.commit()
        
    return {"result": result}

@router.post("/chat")
async def chat_with_papers(
    request: ChatRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    await verify_papers_exist(session, str(current_user.id), request.paper_ids)
    
    # Fetch or create session
    if request.session_id:
        chat_session_result = await session.execute(select(ChatSession).where(ChatSession.id == uuid.UUID(request.session_id), ChatSession.user_id == current_user.id))
        chat_session = chat_session_result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        chat_session = ChatSession(
            user_id=current_user.id,
            paper_ids=request.paper_ids,
            title=request.query[:50]
        )
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        
    # Fetch history
    history_result = await session.execute(select(ChatMessage).where(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at.asc()))
    history = history_result.scalars().all()
    
    chat_history = [{"role": msg.role.value, "content": msg.content} for msg in history]
    
    # Run Agent
    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "chat",
        "query": request.query,
        "chat_history": chat_history[-10:], # last 10 messages
        "retrieved_chunks": [],
        "result": {}
    }
    
    final_state = await research_graph.ainvoke(state)
    result = final_state["result"]
    
    # Save Messages
    user_msg = ChatMessage(session_id=chat_session.id, role=ChatRole.user, content=request.query)
    agent_msg = ChatMessage(session_id=chat_session.id, role=ChatRole.assistant, content=result["response"], sources=result["sources"])
    
    session.add(user_msg)
    session.add(agent_msg)
    await session.commit()
    
    return {
        "session_id": str(chat_session.id),
        "response": result["response"],
        "sources": result["sources"]
    }
