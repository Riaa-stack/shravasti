from fastapi import APIRouter, Depends
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import CurrentUser, get_db
from app.models.paper import Paper, PaperStatus


router = APIRouter()

@router.get("/overview")
async def get_analytics_overview(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    # Get paper counts by status
    status_query = await session.execute(
        select(Paper.status, func.count(Paper.id)).where(Paper.user_id == current_user.id).group_by(Paper.status)
    )
    status_counts = {status.value: count for status, count in status_query.all()}
    
    # Get total papers
    total_papers = sum(status_counts.values())
    
    # For a real application, you might also query the number of generated ideas, reports, etc.
    return {
        "total_papers": total_papers,
        "processed_papers": status_counts.get(PaperStatus.processed.value, 0),
        "failed_papers": status_counts.get(PaperStatus.failed.value, 0),
        "processing_papers": status_counts.get(PaperStatus.processing.value, 0),
        "status_distribution": status_counts
    }

@router.get("/reading-patterns")
async def get_reading_patterns(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    # A simple timeline of papers added
    timeline_query = await session.execute(
        select(func.date(Paper.created_at).label('date'), func.count(Paper.id))
        .where(Paper.user_id == current_user.id)
        .group_by(func.date(Paper.created_at))
        .order_by(func.date(Paper.created_at))
    )
    timeline = [{"date": str(date), "count": count} for date, count in timeline_query.all()]
    
    return {
        "timeline": timeline
    }

@router.get("/topic-clusters")
async def get_topic_clusters(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    from app.models.knowledge_graph import GraphNode, GraphEdge
    # We find keywords linked to papers authored by "anyone"
    # We will simulate a simple cluster using PostgreSQL Graph tables
    query = await session.execute(
        select(
            GraphNode.properties['term'].astext.label('topic'),
            func.count(GraphEdge.id).label('frequency')
        )
        .join(GraphEdge, GraphEdge.target_id == GraphNode.id)
        .where(GraphEdge.type == "HAS_KEYWORD")
        .group_by(GraphNode.properties['term'].astext)
        .order_by(func.count(GraphEdge.id).desc())
        .limit(20)
    )
    
    clusters = [{"topic": r.topic, "size": r.frequency} for r in query.all()]
    
    return {"clusters": clusters}

@router.get("/admin")
async def get_admin_analytics(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    from app.models.user import UserRole
    if current_user.role != UserRole.admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Get total papers
    status_query = await session.execute(
        select(Paper.status, func.count(Paper.id)).group_by(Paper.status)
    )
    status_counts = {status.value: count for status, count in status_query.all()}
    total_papers = sum(status_counts.values())
    
    # Get total users
    from app.models.user import User
    user_count_query = await session.execute(select(func.count(User.id)))
    total_users = user_count_query.scalar_one_or_none() or 0
    
    # Active users (simple heuristic, maybe users created recently or all active)
    active_users = total_users # simplified
    
    # Agent invocations (mocked for now, or queried from models)
    from app.models.literature_review import LiteratureReview
    lr_count_query = await session.execute(select(func.count(LiteratureReview.id)))
    lr_count = lr_count_query.scalar_one_or_none() or 0
    
    from app.models.methodology import MethodologyAnalysis
    methodology_count_query = await session.execute(select(func.count(MethodologyAnalysis.id)))
    methodology_count = methodology_count_query.scalar_one_or_none() or 0
    
    from app.models.research_gap import ResearchGap
    gap_count_query = await session.execute(select(func.count(ResearchGap.id)))
    gap_count = gap_count_query.scalar_one_or_none() or 0

    return {
        "platform_stats": {
            "active_users": active_users,
            "total_papers_processed": status_counts.get(PaperStatus.processed.value, 0),
            "processing_failure_rate": (status_counts.get(PaperStatus.failed.value, 0) / total_papers * 100) if total_papers > 0 else 0
        },
        "agent_invocations": {
            "literature_review": lr_count,
            "methodology": methodology_count,
            "research_gap": gap_count,
            "trend": 0,
            "idea": 0,
            "citation": 0,
            "difficulty": 0,
            "chat": 0
        }
    }

