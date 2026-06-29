from typing import Any
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.api.deps import CurrentUser, get_db
from app.models.knowledge_graph import GraphNode, GraphEdge

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/paper/{paper_id}")
async def get_paper_neighborhood(
    paper_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Returns the local neighborhood for a specific paper."""
    paper_node_id = f"paper_{paper_id}"
    
    try:
        # Get edges connected to this paper
        edges_query = await session.execute(
            select(GraphEdge).where(
                or_(
                    GraphEdge.source_id == paper_node_id,
                    GraphEdge.target_id == paper_node_id
                )
            )
        )
        edges = edges_query.scalars().all()
        
        # Collect all unique node IDs
        node_ids = set([paper_node_id])
        for edge in edges:
            node_ids.add(edge.source_id)
            node_ids.add(edge.target_id)
            
        # Fetch the nodes
        nodes_query = await session.execute(
            select(GraphNode).where(GraphNode.id.in_(node_ids))
        )
        nodes_db = nodes_query.scalars().all()
        
    except Exception as e:
        logger.error(f"Postgres query failed for paper graph {paper_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph service is unavailable."
        )
    
    result_nodes = []
    for node in nodes_db:
        result_nodes.append({
            "id": node.id,
            "labels": [node.label],
            "properties": node.properties or {}
        })
        
    result_edges = []
    for edge in edges:
        result_edges.append({
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.type
        })
            
    return {
        "nodes": result_nodes,
        "edges": result_edges
    }

@router.get("/overview")
async def get_graph_overview(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> Any:
    """Returns a graph summary for the user's library."""
    try:
        # Top Authors
        # Edge type AUTHORED, source is author, target is paper
        author_query = await session.execute(
            select(
                GraphNode.properties['name'].astext.label('author'),
                func.count(GraphEdge.id).label('paper_count')
            )
            .join(GraphEdge, GraphEdge.source_id == GraphNode.id)
            .where(GraphEdge.type == "AUTHORED")
            .group_by(GraphNode.properties['name'].astext)
            .order_by(func.count(GraphEdge.id).desc())
            .limit(10)
        )
        author_records = author_query.all()
        
        # Top Keywords
        # Edge type HAS_KEYWORD, source is paper, target is keyword
        keyword_query = await session.execute(
            select(
                GraphNode.properties['term'].astext.label('keyword'),
                func.count(GraphEdge.id).label('paper_count')
            )
            .join(GraphEdge, GraphEdge.target_id == GraphNode.id)
            .where(GraphEdge.type == "HAS_KEYWORD")
            .group_by(GraphNode.properties['term'].astext)
            .order_by(func.count(GraphEdge.id).desc())
            .limit(10)
        )
        keyword_records = keyword_query.all()
        
    except Exception as e:
        logger.error(f"Postgres graph overview query failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph service is unavailable."
        )
    
    return {
        "top_authors": [{"author": r.author, "count": r.paper_count} for r in author_records],
        "top_keywords": [{"keyword": r.keyword, "count": r.paper_count} for r in keyword_records]
    }
