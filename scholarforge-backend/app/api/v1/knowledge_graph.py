from typing import Any
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.api.deps import CurrentUser, get_db
from app.models.knowledge_graph import GraphNode, GraphEdge
from app.models.paper import Paper
from app.services.knowledge_graph_builder import build_graph_for_paper, extract_entities_from_text, slugify

router = APIRouter()
logger = logging.getLogger(__name__)

class BatchGraphRequest(BaseModel):
    paper_ids: list[str]

async def _ensure_nodes_for_papers(session: AsyncSession, papers: list[Paper]) -> None:
    """Ensure that all user papers have nodes and edges generated in the graph."""
    for paper in papers:
        paper_node_id = f"paper_{paper.id}"
        existing = (await session.execute(select(GraphNode).where(GraphNode.id == paper_node_id))).scalar_one_or_none()
        if not existing:
            meta = {
                "title": paper.title or "Untitled Paper",
                "authors": paper.authors or [],
                "publication_year": paper.publication_year,
                "venue": paper.venue,
                "category": paper.category,
                "abstract": paper.abstract or ""
            }
            try:
                await build_graph_for_paper(paper.id, meta, [], session=session)
            except Exception as e:
                logger.debug(f"Error ensuring graph for paper {paper.id}: {e}")

@router.get("/all")
async def get_all_knowledge_graph(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """
    Returns the complete interconnected knowledge tree for all user's uploaded papers.
    Interconnects papers through shared authors, methodologies, domains, and concepts.
    """
    try:
        # Fetch user's papers
        papers_stmt = select(Paper).where(Paper.user_id == current_user.id)
        papers_res = await session.execute(papers_stmt)
        user_papers = papers_res.scalars().all()

        if not user_papers:
            return {"nodes": [], "edges": [], "paper_count": 0}

        paper_items = [
            (
                p.id,
                {
                    "title": p.title or "Untitled Paper",
                    "authors": p.authors or [],
                    "publication_year": p.publication_year,
                    "venue": p.venue,
                    "category": p.category,
                    "abstract": p.abstract or ""
                }
            )
            for p in user_papers
        ]
        paper_node_ids = [f"paper_{p_id}" for p_id, _ in paper_items]

        # Ensure all papers have graph nodes created
        for p_id, meta in paper_items:
            p_node_id = f"paper_{p_id}"
            existing = (await session.execute(select(GraphNode).where(GraphNode.id == p_node_id))).scalar_one_or_none()
            if not existing:
                try:
                    await build_graph_for_paper(p_id, meta, [], session=session)
                except Exception as e:
                    logger.debug(f"Error ensuring graph for paper {p_id}: {e}")

        # Find all edges connected to any of the user's papers
        edges_stmt = select(GraphEdge).where(
            or_(
                GraphEdge.source_id.in_(paper_node_ids),
                GraphEdge.target_id.in_(paper_node_ids)
            )
        )
        edges_res = await session.execute(edges_stmt)
        edges = edges_res.scalars().all()

        # Collect unique node IDs
        node_ids = set(paper_node_ids)
        for e in edges:
            node_ids.add(e.source_id)
            node_ids.add(e.target_id)

        # Fetch nodes
        nodes_stmt = select(GraphNode).where(GraphNode.id.in_(node_ids))
        nodes_res = await session.execute(nodes_stmt)
        nodes = nodes_res.scalars().all()

        result_nodes = [
            {
                "id": n.id,
                "labels": [n.label],
                "properties": n.properties or {}
            }
            for n in nodes
        ]

        result_edges = [
            {
                "source": e.source_id,
                "target": e.target_id,
                "type": e.type
            }
            for e in edges
        ]

        return {
            "nodes": result_nodes,
            "edges": result_edges,
            "paper_count": len(user_papers)
        }
    except Exception as e:
        logger.error(f"Failed to fetch global knowledge graph: {e}", exc_info=True)
        # Fallback to synthesizing graph on the fly directly from papers to guarantee client-ready reliability
        return await _fallback_graph_from_papers(current_user, session)

@router.post("/batch")
async def get_batch_knowledge_graph(
    req: BatchGraphRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Returns interconnected subgraph for selected batch of papers."""
    if not req.paper_ids:
        return {"nodes": [], "edges": []}

    try:
        paper_node_ids = [f"paper_{pid}" for pid in req.paper_ids]
        
        edges_stmt = select(GraphEdge).where(
            or_(
                GraphEdge.source_id.in_(paper_node_ids),
                GraphEdge.target_id.in_(paper_node_ids)
            )
        )
        edges = (await session.execute(edges_stmt)).scalars().all()

        node_ids = set(paper_node_ids)
        for e in edges:
            node_ids.add(e.source_id)
            node_ids.add(e.target_id)

        nodes = (await session.execute(select(GraphNode).where(GraphNode.id.in_(node_ids)))).scalars().all()

        return {
            "nodes": [{"id": n.id, "labels": [n.label], "properties": n.properties or {}} for n in nodes],
            "edges": [{"source": e.source_id, "target": e.target_id, "type": e.type} for e in edges]
        }
    except Exception as e:
        logger.error(f"Failed to fetch batch graph: {e}")
        return {"nodes": [], "edges": []}

@router.get("/paper/{paper_id}")
async def get_paper_neighborhood(
    paper_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Returns the local neighborhood for a specific paper."""
    paper_node_id = f"paper_{paper_id}"
    
    try:
        # Check if paper node exists, if not ensure it
        existing = (await session.execute(select(GraphNode).where(GraphNode.id == paper_node_id))).scalar_one_or_none()
        if not existing:
            paper_res = await session.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id))
            paper = paper_res.scalar_one_or_none()
            if paper:
                await _ensure_nodes_for_papers(session, [paper])

        edges_query = await session.execute(
            select(GraphEdge).where(
                or_(
                    GraphEdge.source_id == paper_node_id,
                    GraphEdge.target_id == paper_node_id
                )
            )
        )
        edges = edges_query.scalars().all()
        
        node_ids = set([paper_node_id])
        for edge in edges:
            node_ids.add(edge.source_id)
            node_ids.add(edge.target_id)
            
        nodes_query = await session.execute(
            select(GraphNode).where(GraphNode.id.in_(node_ids))
        )
        nodes_db = nodes_query.scalars().all()
        
        return {
            "nodes": [{"id": node.id, "labels": [node.label], "properties": node.properties or {}} for node in nodes_db],
            "edges": [{"source": edge.source_id, "target": edge.target_id, "type": edge.type} for edge in edges]
        }
    except Exception as e:
        logger.error(f"Postgres query failed for paper graph {paper_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph service is unavailable."
        )

@router.get("/overview")
async def get_graph_overview(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Returns a graph summary for the user's library."""
    try:
        papers = (await session.execute(select(Paper).where(Paper.user_id == current_user.id))).scalars().all()
        author_counts: dict[str, int] = {}
        for p in papers:
            if p.authors:
                auth_list = p.authors if isinstance(p.authors, list) else [str(p.authors)]
                for a in auth_list:
                    clean = str(a).strip()
                    if clean:
                        author_counts[clean] = author_counts.get(clean, 0) + 1

        top_authors = sorted([{"author": k, "count": v} for k, v in author_counts.items()], key=lambda x: x["count"], reverse=True)[:10]

        # Concepts / topics from nodes
        keyword_nodes = (await session.execute(select(GraphNode).where(GraphNode.label.in_(["Concept", "Methodology", "Domain"])))).scalars().all()
        keyword_counts: dict[str, int] = {}
        for kn in keyword_nodes:
            props = kn.properties or {}
            term = props.get("name") or props.get("term")
            if term:
                keyword_counts[term] = keyword_counts.get(term, 0) + 1

        top_keywords = sorted([{"keyword": k, "count": v} for k, v in keyword_counts.items()], key=lambda x: x["count"], reverse=True)[:10]

        return {
            "top_authors": top_authors,
            "top_keywords": top_keywords
        }
    except Exception as e:
        logger.error(f"Graph overview query failed: {e}")
        return {"top_authors": [], "top_keywords": []}

async def _fallback_graph_from_papers(current_user: CurrentUser, session: AsyncSession) -> dict:
    """Fallback generator that extracts graph directly from Paper records."""
    try:
        papers = (await session.execute(select(Paper).where(Paper.user_id == current_user.id))).scalars().all()
        nodes = []
        edges = []
        added_node_ids = set()

        for p in papers:
            p_node_id = f"paper_{p.id}"
            if p_node_id not in added_node_ids:
                nodes.append({
                    "id": p_node_id,
                    "labels": ["Paper"],
                    "properties": {"title": p.title or "Untitled Paper", "year": p.publication_year, "paper_id": str(p.id)}
                })
                added_node_ids.add(p_node_id)

            # Authors
            authors = p.authors or []
            if isinstance(authors, str):
                authors = [authors]
            for a in authors:
                clean = str(a).strip()
                if not clean:
                    continue
                a_id = f"author_{slugify(clean)}"
                if a_id not in added_node_ids:
                    nodes.append({"id": a_id, "labels": ["Author"], "properties": {"name": clean}})
                    added_node_ids.add(a_id)
                edges.append({"source": a_id, "target": p_node_id, "type": "AUTHORED"})

            # Entities
            ent = extract_entities_from_text((p.title or "") + " " + (p.abstract or ""), {})
            for m in ent["methods"][:3]:
                m_id = f"method_{slugify(m)}"
                if m_id not in added_node_ids:
                    nodes.append({"id": m_id, "labels": ["Methodology"], "properties": {"name": m}})
                    added_node_ids.add(m_id)
                edges.append({"source": p_node_id, "target": m_id, "type": "USES_METHOD"})

            for d in ent["domains"][:2]:
                d_id = f"domain_{slugify(d)}"
                if d_id not in added_node_ids:
                    nodes.append({"id": d_id, "labels": ["Domain"], "properties": {"name": d}})
                    added_node_ids.add(d_id)
                edges.append({"source": p_node_id, "target": d_id, "type": "IN_DOMAIN"})

        return {"nodes": nodes, "edges": edges, "paper_count": len(papers)}
    except Exception as e:
        logger.error(f"Fallback graph creation failed: {e}")
        return {"nodes": [], "edges": [], "paper_count": 0}
