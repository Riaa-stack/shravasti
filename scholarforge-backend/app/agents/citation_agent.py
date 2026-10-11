import logging
from typing import Optional
from pydantic import BaseModel

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.citation_prompts import CITATION_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class NormalizedMetadata(BaseModel):
    title: Optional[str] = None
    authors: list[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

def _safe_str(val, default: str = '') -> str:
    """Convert a value to string, replacing None with default."""
    if val is None:
        return default
    return str(val)

def format_ieee(meta: dict) -> str:
    authors = meta.get('authors') or []
    author_str = ", ".join(authors) if authors else "Unknown"
    title = _safe_str(meta.get('title'), 'Unknown Title')
    venue = _safe_str(meta.get('venue'), 'Unknown Venue')
    year = _safe_str(meta.get('year'), 'n.d.')
    
    return f"{author_str}, \"{title},\" {venue}, {year}."

def format_apa(meta: dict) -> str:
    authors = meta.get('authors') or []
    author_str = ", ".join(authors) if authors else "Unknown"
    title = _safe_str(meta.get('title'), 'Unknown Title')
    venue = _safe_str(meta.get('venue'), 'Unknown Venue')
    year = _safe_str(meta.get('year'), 'n.d.')
    
    return f"{author_str} ({year}). {title}. {venue}."

def format_mla(meta: dict) -> str:
    authors = meta.get('authors') or []
    author_str = ", ".join(authors) if authors else "Unknown"
    title = _safe_str(meta.get('title'), 'Unknown Title')
    venue = _safe_str(meta.get('venue'), 'Unknown Venue')
    year = _safe_str(meta.get('year'), 'n.d.')
    
    return f"{author_str}. \"{title}.\" {venue} ({year})."

def format_harvard(meta: dict) -> str:
    authors = meta.get('authors') or []
    author_str = ", ".join(authors) if authors else "Unknown"
    title = _safe_str(meta.get('title'), 'Unknown Title')
    venue = _safe_str(meta.get('venue'), 'Unknown Venue')
    year = _safe_str(meta.get('year'), 'n.d.')
    
    return f"{author_str}, {year}. {title}. {venue}."

async def run_citation_generation(state: ResearchState) -> dict:
    paper_ids = state.get('paper_ids', [])
    if not paper_ids:
        raise ValueError("Citation agent requires at least one selected paper.")
        
    logger.info(f"Running Citation Agent for {len(paper_ids)} paper(s): {paper_ids}")
    
    llm = get_llm(settings.LLM_MODEL_CITATION)
    structured_llm = llm.with_structured_output(NormalizedMetadata, method="json_mode")
    prompt = PromptTemplate(template=CITATION_PROMPT, input_variables=["context"])
    chain = prompt | structured_llm
    
    paper_citations = []
    
    for idx, paper_id in enumerate(paper_ids):
        chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=5)
        if not chunks:
            placeholder = {
                "title": f"Paper {idx + 1}",
                "authors": [],
                "year": None,
                "venue": None
            }
            c_dict = {
                "paper_id": str(paper_id),
                "title": f"Paper {idx + 1}",
                "ieee": format_ieee(placeholder),
                "apa": format_apa(placeholder),
                "mla": format_mla(placeholder),
                "harvard": format_harvard(placeholder)
            }
        else:
            context = "\n\n".join([c["content"] for c in chunks])
            try:
                metadata_obj = await chain.ainvoke({"context": context})
                metadata = metadata_obj.model_dump()
            except Exception as e:
                logger.error(f"Citation LLM call failed for paper {paper_id}: {e}")
                metadata = {"title": f"Paper {idx + 1}", "authors": [], "year": None, "venue": None}

        # Check DB for verified paper metadata if any field is missing
        try:
            from app.db.postgres import async_session_maker
            from sqlalchemy import select
            from app.models.paper import Paper
            import uuid
            async with async_session_maker() as session:
                res = await session.execute(select(Paper).where(Paper.id == uuid.UUID(str(paper_id))))
                db_paper = res.scalar_one_or_none()
                if db_paper:
                    if not metadata.get("title") or metadata.get("title").startswith("Paper "):
                        metadata["title"] = db_paper.title
                    if not metadata.get("authors"):
                        metadata["authors"] = db_paper.authors if isinstance(db_paper.authors, list) else ([db_paper.authors] if db_paper.authors else [])
                    if not metadata.get("year"):
                        metadata["year"] = db_paper.publication_year
                    if not metadata.get("venue"):
                        metadata["venue"] = db_paper.venue
        except Exception as err:
            logger.debug(f"Could not load paper from DB for citation: {err}")

        # Ensure title is never empty
        if not metadata.get("title"):
            metadata["title"] = f"Research Paper {idx + 1}"

        c_dict = {
            "paper_id": str(paper_id),
            "title": metadata.get("title") or f"Paper {idx + 1}",
            "ieee": format_ieee(metadata),
            "apa": format_apa(metadata),
            "mla": format_mla(metadata),
            "harvard": format_harvard(metadata)
        }
        paper_citations.append(c_dict)
    
    first = paper_citations[0]
    return {
        "ieee": first["ieee"],
        "apa": first["apa"],
        "mla": first["mla"],
        "harvard": first["harvard"],
        "paper_citations": paper_citations,
        "comparative_analysis": f"Formatted citations across {len(paper_citations)} selected research paper(s)."
    }
