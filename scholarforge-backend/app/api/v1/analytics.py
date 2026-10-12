
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.paper import Paper, PaperStatus

router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return live dashboard analytics for the authenticated user."""

    # 1. Paper counts grouped by status
    status_query = await session.execute(
        select(Paper.status, func.count(Paper.id))
        .where(Paper.user_id == current_user.id)
        .group_by(Paper.status)
    )

    status_counts = {
        status.value: count
        for status, count in status_query.all()
    }

    total_papers = sum(status_counts.values())

    # 2. Dynamic topic distribution
    # IMPORTANT: Reuse the same expression in SELECT and GROUP BY.
    topic_name = func.coalesce(
        func.nullif(func.trim(Paper.category), ""),
        "Uncategorized",
    )

    topic_query = await session.execute(
        select(
            topic_name.label("name"),
            func.count(Paper.id).label("value"),
        )
        .where(Paper.user_id == current_user.id)
        .group_by(topic_name)
        .order_by(func.count(Paper.id).desc())
        .limit(8)
    )

    top_topics = [
        {"name": name, "value": count}
        for name, count in topic_query.all()
    ]

    # 3. Reading activity for the last seven calendar days
    today = date.today()
    start_date = today - timedelta(days=6)

    start_datetime = datetime.combine(
        start_date, datetime.min.time()
    )
    end_datetime = datetime.combine(
        today + timedelta(days=1), datetime.min.time()
    )

    activity_query = await session.execute(
        select(
            func.date(Paper.created_at).label("day"),
            func.count(Paper.id).label("papers"),
        )
        .where(
            Paper.user_id == current_user.id,
            Paper.created_at >= start_datetime,
            Paper.created_at < end_datetime,
        )
        .group_by(func.date(Paper.created_at))
        .order_by(func.date(Paper.created_at))
    )

    activity_by_date = {
        (
            day.isoformat()
            if hasattr(day, "isoformat")
            else str(day)
        ): count
        for day, count in activity_query.all()
    }

    reading_activity = [
        {
            "date": (
                start_date + timedelta(days=offset)
            ).isoformat(),
            "name": (
                start_date + timedelta(days=offset)
            ).strftime("%a"),
            "papers": activity_by_date.get(
                (
                    start_date + timedelta(days=offset)
                ).isoformat(),
                0,
            ),
        }
        for offset in range(7)
    ]

    # 4. Count generated research outputs
    from app.models.literature_review import LiteratureReview
    from app.models.research_idea import ResearchIdea
    from app.models.trend_report import TrendReport
    from app.models.methodology import MethodologyAnalysis
    from app.models.research_gap import ResearchGap

    literature_count = await session.scalar(
        select(func.count(LiteratureReview.id)).where(
            LiteratureReview.user_id == current_user.id
        )
    ) or 0

    idea_count = await session.scalar(
        select(func.count(ResearchIdea.id)).where(
            ResearchIdea.user_id == current_user.id
        )
    ) or 0

    trend_count = await session.scalar(
        select(func.count(TrendReport.id)).where(
            TrendReport.user_id == current_user.id
        )
    ) or 0

    methodology_count = await session.scalar(
        select(func.count(MethodologyAnalysis.id))
        .join(
            Paper,
            MethodologyAnalysis.paper_id == Paper.id,
        )
        .where(Paper.user_id == current_user.id)
    ) or 0

    gap_count = await session.scalar(
        select(func.count(ResearchGap.id))
        .join(
            Paper,
            ResearchGap.paper_id == Paper.id,
        )
        .where(Paper.user_id == current_user.id)
    ) or 0

    total_insights = sum(
        int(count)
        for count in (
            literature_count,
            idea_count,
            trend_count,
            methodology_count,
            gap_count,
        )
    )

    return {
        "total_papers": total_papers,
        "processed_papers": status_counts.get(
            PaperStatus.processed.value, 0
        ),
        "failed_papers": status_counts.get(
            PaperStatus.failed.value, 0
        ),
        "processing_papers": status_counts.get(
            PaperStatus.processing.value, 0
        ),
        "status_distribution": status_counts,
        "top_topics": top_topics,
        "reading_activity": reading_activity,
        "total_insights": total_insights,
    }


@router.get("/reading-patterns")
async def get_reading_patterns(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return the user's paper upload timeline."""

    timeline_query = await session.execute(
        select(
            func.date(Paper.created_at).label("date"),
            func.count(Paper.id).label("count"),
        )
        .where(Paper.user_id == current_user.id)
        .group_by(func.date(Paper.created_at))
        .order_by(func.date(Paper.created_at))
    )

    timeline = [
        {"date": str(day), "count": count}
        for day, count in timeline_query.all()
    ]

    return {"timeline": timeline}


@router.get("/topic-clusters")
async def get_topic_clusters(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return keyword clusters from the knowledge graph."""

    from app.models.knowledge_graph import GraphNode, GraphEdge

    query = await session.execute(
        select(
            GraphNode.properties["term"].astext.label("topic"),
            func.count(GraphEdge.id).label("frequency"),
        )
        .join(
            GraphEdge,
            GraphEdge.target_id == GraphNode.id,
        )
        .where(GraphEdge.type == "HAS_KEYWORD")
        .group_by(GraphNode.properties["term"].astext)
        .order_by(func.count(GraphEdge.id).desc())
        .limit(20)
    )

    clusters = [
        {"topic": row.topic, "size": row.frequency}
        for row in query.all()
    ]

    return {"clusters": clusters}


@router.get("/admin")
async def get_admin_analytics(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Return platform-wide analytics for administrators."""

    from app.models.user import User, UserRole
    from app.models.literature_review import LiteratureReview
    from app.models.methodology import MethodologyAnalysis
    from app.models.research_gap import ResearchGap

    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
        )

    status_query = await session.execute(
        select(Paper.status, func.count(Paper.id))
        .group_by(Paper.status)
    )

    status_counts = {
        status.value: count
        for status, count in status_query.all()
    }

    total_papers = sum(status_counts.values())

    total_users = await session.scalar(
        select(func.count(User.id))
    ) or 0

    lr_count = await session.scalar(
        select(func.count(LiteratureReview.id))
    ) or 0

    methodology_count = await session.scalar(
        select(func.count(MethodologyAnalysis.id))
    ) or 0

    gap_count = await session.scalar(
        select(func.count(ResearchGap.id))
    ) or 0

    return {
        "platform_stats": {
            "active_users": total_users,
            "total_papers_processed": status_counts.get(
                PaperStatus.processed.value, 0
            ),
            "processing_failure_rate": (
                status_counts.get(PaperStatus.failed.value, 0)
                / total_papers
                * 100
            ) if total_papers else 0,
        },
        "agent_invocations": {
            "literature_review": lr_count,
            "methodology": methodology_count,
            "research_gap": gap_count,
            "trend": 0,
            "idea": 0,
            "citation": 0,
            "difficulty": 0,
            "chat": 0,
        },
    }