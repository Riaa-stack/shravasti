from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Any
import uuid
import logging

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

logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def normalize_paper_ids(paper_ids: list[str] | None) -> list[str]:
    """
    Normalize paper IDs so that comparison is consistent regardless
    of ordering or UUID formatting.
    """
    if not paper_ids:
        return []

    normalized = []

    for paper_id in paper_ids:
        if paper_id is None:
            continue

        value = str(paper_id).strip()

        if value:
            normalized.append(value)

    return sorted(set(normalized))


def normalize_result(value: Any) -> Any:
    """
    Convert common Pydantic / LangChain / JSON result objects into
    JSON-serializable Python objects.
    """
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return normalize_result(value.model_dump())

    if hasattr(value, "dict"):
        return normalize_result(value.dict())

    if isinstance(value, dict):
        return {
            str(key): normalize_result(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [normalize_result(item) for item in value]

    if isinstance(value, uuid.UUID):
        return str(value)

    return value


SESSION_AGENT_CACHE: dict[tuple[str, str, str], dict] = {}

def get_session_cache(user_id: Any, agent_type: str, paper_ids: list[str]) -> dict | None:
    key = (str(user_id), agent_type, ",".join(normalize_paper_ids(paper_ids)))
    return SESSION_AGENT_CACHE.get(key)

def set_session_cache(user_id: Any, agent_type: str, paper_ids: list[str], result: dict) -> None:
    key = (str(user_id), agent_type, ",".join(normalize_paper_ids(paper_ids)))
    SESSION_AGENT_CACHE[key] = result


async def verify_papers_exist(
    session: AsyncSession,
    user_id: str,
    paper_ids: list[str]
):
    """
    Verify that all requested papers exist and belong to the current user.
    """
    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one paper must be selected."
        )

    try:
        uuid_ids = [uuid.UUID(pid) for pid in paper_ids]
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="One or more paper IDs are invalid."
        )

    result = await session.execute(
        select(Paper).where(
            Paper.id.in_(uuid_ids),
            Paper.user_id == uuid.UUID(user_id)
        )
    )

    papers = result.scalars().all()

    if len(papers) != len(set(paper_ids)):
        raise HTTPException(
            status_code=404,
            detail="One or more papers not found or do not belong to user."
        )

    return papers


# ============================================================================
# LITERATURE REVIEW
# ============================================================================

@router.get("/literature-review/result")
async def get_literature_review_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:
    """
    Return the previously saved Literature Review result.

    This endpoint is used when the user navigates back to the agent page.
    It does NOT invoke the LLM.
    """

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "literature-review", paper_ids)
    if cached is not None:
        return {"result": cached}

    result = await session.execute(
        select(LiteratureReview)
        .where(
            LiteratureReview.user_id == current_user.id
        )
        .order_by(
            LiteratureReview.created_at.desc()
        )
    )

    rows = result.scalars().all()

    for row in rows:
        saved_ids = normalize_paper_ids(row.paper_ids)

        if saved_ids == paper_ids:
            res = normalize_result({
                "summary": row.summary,
                "key_findings": row.key_findings,
                "contributions": row.contributions,
                "comparative_review": row.comparative_review,
                "paper_reviews": [
                    {
                        "paper_id": pid,
                        "title": f"Paper {i + 1}",
                        "summary": row.summary,
                        "key_findings": row.key_findings,
                        "contributions": row.contributions
                    }
                    for i, pid in enumerate(paper_ids)
                ]
            })
            set_session_cache(current_user.id, "literature-review", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved literature review found for these papers."
    )


@router.post("/literature-review")
async def generate_literature_review(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "literature-review", paper_ids)
    if cached is not None:
        return {"result": cached}

    # ------------------------------------------------------------------------
    # CHECK DATABASE CACHE FIRST
    # ------------------------------------------------------------------------

    existing_result = await session.execute(
        select(LiteratureReview)
        .where(
            LiteratureReview.user_id == current_user.id
        )
        .order_by(
            LiteratureReview.created_at.desc()
        )
    )

    existing_rows = existing_result.scalars().all()

    for row in existing_rows:
        saved_ids = normalize_paper_ids(row.paper_ids)

        if saved_ids == paper_ids:
            res = normalize_result({
                "summary": row.summary,
                "key_findings": row.key_findings,
                "contributions": row.contributions,
                "comparative_review": row.comparative_review,
                "paper_reviews": [
                    {
                        "paper_id": pid,
                        "title": f"Paper {i + 1}",
                        "summary": row.summary,
                        "key_findings": row.key_findings,
                        "contributions": row.contributions
                    }
                    for i, pid in enumerate(paper_ids)
                ]
            })
            set_session_cache(current_user.id, "literature-review", paper_ids, res)
            return {
                "id": str(row.id),
                "result": res
            }

    # ------------------------------------------------------------------------
    # RUN AGENT ONLY IF NO SAVED RESULT EXISTS
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "literature_review",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Literature review agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "literature-review", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE RESULT
    # ------------------------------------------------------------------------

    lr = LiteratureReview(
        user_id=current_user.id,
        paper_ids=paper_ids,
        summary=result.get("summary"),
        key_findings=result.get("key_findings", []),
        contributions=result.get("contributions", []),
        comparative_review=result.get("comparative_review")
    )

    session.add(lr)
    await session.commit()
    await session.refresh(lr)

    return {
        "id": str(lr.id),
        "result": result
    }


# ============================================================================
# METHODOLOGY
# ============================================================================

@router.get("/methodology/result")
async def get_methodology_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "methodology", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        result = await session.execute(
            select(MethodologyAnalysis)
            .where(
                MethodologyAnalysis.paper_id == uuid.UUID(paper_ids[0])
            )
            .order_by(
                MethodologyAnalysis.created_at.desc()
            )
        )
        row = result.scalars().first()
        if row:
            res = normalize_result({
                "algorithms": row.algorithms,
                "models": row.models,
                "datasets": row.datasets,
                "evaluation_metrics": row.evaluation_metrics,
                "experimental_setup": row.experimental_setup,
                "paper_analyses": [
                    {
                        "paper_id": paper_ids[0],
                        "title": "Selected Paper",
                        "algorithms": row.algorithms,
                        "models": row.models,
                        "datasets": row.datasets,
                        "evaluation_metrics": row.evaluation_metrics,
                        "experimental_setup": row.experimental_setup,
                    }
                ]
            })
            set_session_cache(current_user.id, "methodology", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved methodology analysis found for these papers."
    )


@router.post("/methodology")
async def extract_methodology(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "methodology", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        existing_result = await session.execute(
            select(MethodologyAnalysis)
            .where(
                MethodologyAnalysis.paper_id == uuid.UUID(paper_ids[0])
            )
            .order_by(
                MethodologyAnalysis.created_at.desc()
            )
        )
        existing_row = existing_result.scalars().first()
        if existing_row:
            res = normalize_result({
                "algorithms": existing_row.algorithms,
                "models": existing_row.models,
                "datasets": existing_row.datasets,
                "evaluation_metrics": existing_row.evaluation_metrics,
                "experimental_setup": existing_row.experimental_setup,
                "paper_analyses": [
                    {
                        "paper_id": paper_ids[0],
                        "title": "Selected Paper",
                        "algorithms": existing_row.algorithms,
                        "models": existing_row.models,
                        "datasets": existing_row.datasets,
                        "evaluation_metrics": existing_row.evaluation_metrics,
                        "experimental_setup": existing_row.experimental_setup,
                    }
                ]
            })
            set_session_cache(current_user.id, "methodology", paper_ids, res)
            return {"result": res}

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "methodology",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Methodology agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "methodology", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    try:
        for paper_id in paper_ids:
            ma = MethodologyAnalysis(
                paper_id=uuid.UUID(paper_id),
                algorithms=result.get("algorithms", []),
                models=result.get("models", []),
                datasets=result.get("datasets", []),
                evaluation_metrics=result.get(
                    "evaluation_metrics",
                    []
                ),
                experimental_setup=result.get(
                    "experimental_setup",
                    ""
                )
            )

            session.add(ma)

        await session.commit()

    except Exception as e:
        await session.rollback()

        logger.warning(
            "Could not save methodology to DB: %s",
            e
        )

    return {
        "result": result
    }


# ============================================================================
# RESEARCH GAP
# ============================================================================

@router.get("/research-gap/result")
async def get_research_gap_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "research-gap", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        result = await session.execute(
            select(ResearchGap)
            .where(
                ResearchGap.paper_id == uuid.UUID(paper_ids[0])
            )
            .order_by(
                ResearchGap.created_at.desc()
            )
        )
        row = result.scalars().first()
        if row:
            res = normalize_result({
                "limitations": row.limitations,
                "future_scope": row.future_scope,
                "missing_areas": row.missing_areas,
                "unsolved_problems": row.unsolved_problems,
                "improvement_opportunities": row.improvement_opportunities,
                "paper_gaps": [
                    {
                        "paper_id": paper_ids[0],
                        "title": "Selected Paper",
                        "limitations": row.limitations,
                        "future_scope": row.future_scope,
                        "missing_areas": row.missing_areas,
                        "unsolved_problems": row.unsolved_problems,
                        "improvement_opportunities": row.improvement_opportunities,
                    }
                ]
            })
            set_session_cache(current_user.id, "research-gap", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved research gap analysis found for these papers."
    )


@router.post("/research-gap")
async def detect_research_gap(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "research-gap", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        existing_result = await session.execute(
            select(ResearchGap)
            .where(
                ResearchGap.paper_id == uuid.UUID(paper_ids[0])
            )
            .order_by(
                ResearchGap.created_at.desc()
            )
        )
        existing_row = existing_result.scalars().first()
        if existing_row:
            res = normalize_result({
                "limitations": existing_row.limitations,
                "future_scope": existing_row.future_scope,
                "missing_areas": existing_row.missing_areas,
                "unsolved_problems": existing_row.unsolved_problems,
                "improvement_opportunities": existing_row.improvement_opportunities,
                "paper_gaps": [
                    {
                        "paper_id": paper_ids[0],
                        "title": "Selected Paper",
                        "limitations": existing_row.limitations,
                        "future_scope": existing_row.future_scope,
                        "missing_areas": existing_row.missing_areas,
                        "unsolved_problems": existing_row.unsolved_problems,
                        "improvement_opportunities": existing_row.improvement_opportunities,
                    }
                ]
            })
            set_session_cache(current_user.id, "research-gap", paper_ids, res)
            return {"result": res}

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "gap",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Research gap agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "research-gap", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    try:
        for paper_id in paper_ids:
            rg = ResearchGap(
                paper_id=uuid.UUID(paper_id),
                limitations=result.get(
                    "limitations",
                    []
                ),
                future_scope=result.get(
                    "future_scope",
                    []
                ),
                missing_areas=result.get(
                    "missing_areas",
                    []
                ),
                unsolved_problems=result.get(
                    "unsolved_problems",
                    []
                ),
                improvement_opportunities=result.get(
                    "improvement_opportunities",
                    []
                )
            )

            session.add(rg)

        await session.commit()

    except Exception as e:
        await session.rollback()
        logger.exception("Failed to save research gap results to database.")
        raise HTTPException(
            status_code=500,
            detail="Research gap analysis completed, but saving the result failed."
        ) from e

    return {
        "result": result
    }


# ============================================================================
# TREND ANALYSIS
# ============================================================================

@router.get("/trend/result")
async def get_trend_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    result = await session.execute(
        select(TrendReport)
        .where(
            TrendReport.user_id == current_user.id
        )
        .order_by(
            TrendReport.created_at.desc()
        )
    )

    rows = result.scalars().all()

    cached = get_session_cache(current_user.id, "trend", paper_ids)
    if cached is not None:
        return {"result": cached}

    for row in rows:
        saved_ids = normalize_paper_ids(
            row.scope_paper_ids
        )

        if saved_ids == paper_ids:
            res = normalize_result({
                "topics": row.topics,
                "emerging_keywords": row.emerging_keywords,
                "popular_methods": row.popular_methods,
                "publication_timeline":
                    row.publication_timeline,
            })
            set_session_cache(current_user.id, "trend", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved trend analysis found for these papers."
    )


@router.post("/trend")
async def analyze_trends(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "trend", paper_ids)
    if cached is not None:
        return {"result": cached}

    # ------------------------------------------------------------------------
    # CHECK CACHE
    # ------------------------------------------------------------------------

    existing_result = await session.execute(
        select(TrendReport)
        .where(
            TrendReport.user_id == current_user.id
        )
        .order_by(
            TrendReport.created_at.desc()
        )
    )

    existing_rows = existing_result.scalars().all()

    for row in existing_rows:
        saved_ids = normalize_paper_ids(
            row.scope_paper_ids
        )

        if saved_ids == paper_ids:
            res = normalize_result({
                "topics": row.topics,
                "emerging_keywords":
                    row.emerging_keywords,
                "popular_methods":
                    row.popular_methods,
                "publication_timeline":
                    row.publication_timeline,
            })
            set_session_cache(current_user.id, "trend", paper_ids, res)
            return {"result": res}

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "trend",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Trend analysis agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "trend", paper_ids, result)

    tr = TrendReport(
        user_id=current_user.id,
        scope_paper_ids=paper_ids,
        topics=result.get("topics", []),
        emerging_keywords=result.get(
            "emerging_keywords",
            []
        ),
        popular_methods=result.get(
            "popular_methods",
            []
        ),
        publication_timeline=result.get(
            "publication_timeline",
            []
        )
    )

    session.add(tr)
    await session.commit()
    await session.refresh(tr)

    return {
        "result": result
    }


# ============================================================================
# IDEA GENERATION
# ============================================================================

@router.get("/idea/result")
async def get_idea_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "idea", paper_ids)
    if cached is not None:
        return {"result": cached}

    result = await session.execute(
        select(ResearchIdea)
        .where(
            ResearchIdea.user_id == current_user.id
        )
        .order_by(
            ResearchIdea.created_at.desc()
        )
    )

    rows = result.scalars().all()

    matching_rows = []

    for row in rows:
        saved_ids = normalize_paper_ids(
            row.source_paper_ids
        )

        if saved_ids == paper_ids:
            matching_rows.append(row)

    if not matching_rows:
        raise HTTPException(
            status_code=404,
            detail="No saved research ideas found for these papers."
        )

    project_ideas = []

    for row in reversed(matching_rows):
        if row.description:
            project_ideas.append(row.description)

    res = {
        "project_ideas": project_ideas,
        "paper_ideas": [
            {"paper_id": pid, "title": f"Paper {i+1}", "ideas": project_ideas}
            for i, pid in enumerate(paper_ids)
        ]
    }
    set_session_cache(current_user.id, "idea", paper_ids, res)
    return {"result": res}


@router.post("/idea")
async def generate_ideas(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "idea", paper_ids)
    if cached is not None:
        return {"result": cached}

    # ------------------------------------------------------------------------
    # CHECK CACHE
    # ------------------------------------------------------------------------

    existing_result = await session.execute(
        select(ResearchIdea)
        .where(
            ResearchIdea.user_id == current_user.id
        )
        .order_by(
            ResearchIdea.created_at.desc()
        )
    )

    existing_rows = existing_result.scalars().all()

    matching_rows = []

    for row in existing_rows:
        saved_ids = normalize_paper_ids(
            row.source_paper_ids
        )

        if saved_ids == paper_ids:
            matching_rows.append(row)

    if matching_rows:
        project_ideas = [
            row.description
            for row in reversed(matching_rows)
            if row.description
        ]
        res = {
            "project_ideas": project_ideas,
            "paper_ideas": [
                {"paper_id": pid, "title": f"Paper {i+1}", "ideas": project_ideas}
                for i, pid in enumerate(paper_ids)
            ]
        }
        set_session_cache(current_user.id, "idea", paper_ids, res)
        return {"result": res}

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "idea",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Idea generation agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "idea", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE IDEAS
    # ------------------------------------------------------------------------

    for idea_text in result.get(
        "project_ideas",
        []
    ):

        if not idea_text:
            continue

        idea_text = str(idea_text)

        ri = ResearchIdea(
            user_id=current_user.id,
            source_paper_ids=paper_ids,
            idea_type=IdeaType.project,
            title=idea_text[:100] + "...",
            description=idea_text,
            rationale="Generated by Agent"
        )

        session.add(ri)

    await session.commit()

    return {
        "result": result
    }


# ============================================================================
# CITATION
# ============================================================================

@router.get("/citation/result")
async def get_citation_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one paper is required."
        )

    cached = get_session_cache(current_user.id, "citation", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        paper_uuid = uuid.UUID(paper_ids[0])

        result = await session.execute(
            select(Citation)
            .where(
                Citation.paper_id == paper_uuid
            )
            .order_by(
                Citation.created_at.desc()
            )
        )

        rows = result.scalars().all()

        if rows:
            citations = {}
            for row in rows:
                style = row.style.value if hasattr(row.style, 'value') else str(row.style)
                if style not in citations:
                    citations[style] = row.formatted_text

            res = normalize_result(citations)
            res["paper_citations"] = [
                {"paper_id": paper_ids[0], "title": "Selected Paper", **citations}
            ]
            set_session_cache(current_user.id, "citation", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved citations found for this paper."
    )


@router.post("/citation")
async def generate_citations(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "citation", paper_ids)
    if cached is not None:
        return {"result": cached}

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "citation",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Citation agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "citation", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE CITATIONS
    # ------------------------------------------------------------------------

    if paper_ids:
        try:
            for pid in paper_ids:
                for style in ["ieee", "apa", "mla", "harvard"]:
                    text = result.get(style)
                    if text:
                        citation = Citation(
                            paper_id=uuid.UUID(pid),
                            style=CitationStyle(style),
                            formatted_text=str(text)
                        )
                        session.add(citation)

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.warning(
                "Could not save citation to DB: %s",
                e
            )

    return {
        "result": result
    }


# ============================================================================
# DIFFICULTY
# ============================================================================

@router.get("/difficulty/result")
async def get_difficulty_result(
    current_user: CurrentUser,
    paper_ids: list[str] = Query(...),
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    if not paper_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one paper is required."
        )

    cached = get_session_cache(current_user.id, "difficulty", paper_ids)
    if cached is not None:
        return {"result": cached}

    if len(paper_ids) == 1:
        paper_result = await session.execute(
            select(Paper).where(
                Paper.id == uuid.UUID(paper_ids[0]),
                Paper.user_id == current_user.id
            )
        )

        paper = paper_result.scalar_one_or_none()

        if paper and paper.difficulty_level:
            difficulty_value = paper.difficulty_level
            if hasattr(difficulty_value, "value"):
                difficulty_value = difficulty_value.value

            res = {
                "difficulty": difficulty_value,
                "rationale": "Evaluated based on academic terminology, syntax, and domain complexity.",
                "paper_difficulties": [
                    {
                        "paper_id": paper_ids[0],
                        "title": paper.title or "Selected Paper",
                        "difficulty": difficulty_value,
                        "rationale": "Evaluated based on academic terminology and syntax."
                    }
                ]
            }
            set_session_cache(current_user.id, "difficulty", paper_ids, res)
            return {"result": res}

    raise HTTPException(
        status_code=404,
        detail="No saved difficulty result found for these papers."
    )


@router.post("/difficulty")
async def evaluate_difficulty(
    request: TaskRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    paper_ids = normalize_paper_ids(request.paper_ids)

    await verify_papers_exist(
        session,
        str(current_user.id),
        paper_ids
    )

    cached = get_session_cache(current_user.id, "difficulty", paper_ids)
    if cached is not None:
        return {"result": cached}

    if paper_ids:
        paper_result = await session.execute(
            select(Paper).where(
                Paper.id == uuid.UUID(paper_ids[0]),
                Paper.user_id == current_user.id
            )
        )

        paper = paper_result.scalar_one_or_none()

        if paper and paper.difficulty_level:
            difficulty_value = paper.difficulty_level

            if hasattr(difficulty_value, "value"):
                difficulty_value = difficulty_value.value

            return {
                "result": {
                    "difficulty": difficulty_value
                }
            }

    # ------------------------------------------------------------------------
    # RUN AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": paper_ids,
        "task_type": "difficulty",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Difficulty agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])
    set_session_cache(current_user.id, "difficulty", paper_ids, result)

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    if paper_ids and "difficulty" in result:

        from app.models.paper import DifficultyLevel

        try:
            difficulty = DifficultyLevel(
                result["difficulty"]
            )

            for paper_id in paper_ids:

                paper_result = await session.execute(
                    select(Paper).where(
                        Paper.id == uuid.UUID(paper_id),
                        Paper.user_id == current_user.id
                    )
                )

                paper = paper_result.scalar_one_or_none()

                if paper:
                    paper.difficulty_level = difficulty
                    session.add(paper)

            await session.commit()

        except Exception as e:
            await session.rollback()

            logger.warning(
                "Could not save difficulty to DB: %s",
                e
            )

    return {
        "result": result
    }


# ============================================================================
# CHAT
# ============================================================================

@router.post("/chat")
async def chat_with_papers(
    request: ChatRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:

    await verify_papers_exist(
        session,
        str(current_user.id),
        request.paper_ids
    )

    # ------------------------------------------------------------------------
    # FETCH OR CREATE SESSION
    # ------------------------------------------------------------------------

    if request.session_id:

        chat_session_result = await session.execute(
            select(ChatSession).where(
                ChatSession.id == uuid.UUID(
                    request.session_id
                ),
                ChatSession.user_id == current_user.id
            )
        )

        chat_session = chat_session_result.scalar_one_or_none()

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found"
            )

    else:

        chat_session = ChatSession(
            user_id=current_user.id,
            paper_ids=request.paper_ids,
            title=request.query[:50]
        )

        session.add(chat_session)

        await session.commit()
        await session.refresh(chat_session)

    # ------------------------------------------------------------------------
    # FETCH CHAT HISTORY
    # ------------------------------------------------------------------------

    history_result = await session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == chat_session.id
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
    )

    history = history_result.scalars().all()

    chat_history = [
        {
            "role": msg.role.value,
            "content": msg.content
        }
        for msg in history
    ]

    # ------------------------------------------------------------------------
    # RUN CHAT AGENT
    # ------------------------------------------------------------------------

    state = {
        "user_id": str(current_user.id),
        "paper_ids": request.paper_ids,
        "task_type": "chat",
        "query": request.query,
        "chat_history": chat_history[-10:],
        "retrieved_chunks": [],
        "result": {}
    }

    try:
        final_state = await research_graph.ainvoke(state)
    except Exception as e:
        logger.exception("Chat agent failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )

    result = normalize_result(final_state["result"])

    # ------------------------------------------------------------------------
    # SAVE MESSAGES
    # ------------------------------------------------------------------------

    user_msg = ChatMessage(
        session_id=chat_session.id,
        role=ChatRole.user,
        content=request.query
    )

    agent_msg = ChatMessage(
        session_id=chat_session.id,
        role=ChatRole.assistant,
        content=result.get("response", ""),
        sources=result.get("sources", [])
    )

    session.add(user_msg)
    session.add(agent_msg)

    await session.commit()

    return {
        "session_id": str(chat_session.id),
        "response": result.get("response", ""),
        "sources": result.get("sources", [])
    }