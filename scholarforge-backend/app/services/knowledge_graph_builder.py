import logging
import uuid
import re
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from app.db.postgres import async_session_maker
from app.models.knowledge_graph import GraphNode, GraphEdge
from app.services.external_apis.semantic_scholar import get_semantic_scholar_related

logger = logging.getLogger(__name__)

async def build_graph_for_paper(paper_id: uuid.UUID, metadata: dict, chunks: list[dict]) -> None:
    """
    Upserts nodes and relationships for a processed paper into PostgreSQL knowledge graph tables.
    Failures are logged but do not propagate to avoid blocking the ingestion pipeline.
    """
    try:
        async with async_session_maker() as session:
            # Create the main Paper node
            paper_node_id = f"paper_{paper_id}"
            stmt_paper = insert(GraphNode).values(
                id=paper_node_id,
                label="Paper",
                properties={
                    "title": metadata.get("title", "Unknown Title"),
                    "year": metadata.get("publication_year"),
                    "doi": metadata.get("doi")
                }
            ).on_conflict_do_update(
                index_elements=['id'],
                set_={"properties": insert(GraphNode).excluded.properties}
            )
            await session.execute(stmt_paper)

            # Process Authors
            authors = metadata.get("authors", [])
            for author_name in authors:
                author_node_id = f"author_{author_name}"
                stmt_author = insert(GraphNode).values(
                    id=author_node_id,
                    label="Author",
                    properties={"name": author_name}
                ).on_conflict_do_nothing(index_elements=['id'])
                await session.execute(stmt_author)

                stmt_author_edge = insert(GraphEdge).values(
                    source_id=author_node_id,
                    target_id=paper_node_id,
                    type="AUTHORED"
                ).on_conflict_do_nothing()
                await session.execute(stmt_author_edge)

            # Process Keywords
            abstract = metadata.get("abstract") or ""
            phrases = re.findall(r'\b(?:[A-Z][a-z]+\s*){2,}\b', abstract)
            keywords = list(set([p.strip().lower() for p in phrases if len(p.strip()) > 5]))[:10]

            for keyword in keywords:
                keyword_node_id = f"keyword_{keyword}"
                stmt_keyword = insert(GraphNode).values(
                    id=keyword_node_id,
                    label="Keyword",
                    properties={"term": keyword}
                ).on_conflict_do_nothing(index_elements=['id'])
                await session.execute(stmt_keyword)

                stmt_keyword_edge = insert(GraphEdge).values(
                    source_id=paper_node_id,
                    target_id=keyword_node_id,
                    type="HAS_KEYWORD"
                ).on_conflict_do_nothing()
                await session.execute(stmt_keyword_edge)

            # Fetch citations via Semantic Scholar if DOI is present
            doi = metadata.get("doi")
            if doi:
                try:
                    related = await get_semantic_scholar_related(doi)
                    if related:
                        citations = related.get("citations", [])
                        for citation_doi in citations:
                            if not citation_doi:
                                continue
                            citation_node_id = f"paper_doi_{citation_doi}"
                            stmt_citation = insert(GraphNode).values(
                                id=citation_node_id,
                                label="Paper",
                                properties={"doi": citation_doi}
                            ).on_conflict_do_nothing(index_elements=['id'])
                            await session.execute(stmt_citation)

                            stmt_citation_edge = insert(GraphEdge).values(
                                source_id=paper_node_id,
                                target_id=citation_node_id,
                                type="CITES"
                            ).on_conflict_do_nothing()
                            await session.execute(stmt_citation_edge)
                except Exception as e:
                    logger.error(f"Failed to create citation edges for {paper_id}: {e}")

            await session.commit()
            logger.info(f"Knowledge graph updated in Postgres for paper {paper_id}")
    except Exception as e:
        logger.error(f"Postgres Graph: Failed to build graph for {paper_id}: {e}")
