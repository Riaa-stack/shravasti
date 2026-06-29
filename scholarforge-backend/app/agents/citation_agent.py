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
    paper_id = state['paper_ids'][0]
    logger.info(f"Running Citation Agent for paper {paper_id}")
    
    chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=5)
    
    if not chunks:
        logger.warning(f"No chunks found for paper {paper_id}. Paper may not be processed yet.")
        # Return placeholder citations if no content is available
        placeholder = {
            "title": "[Paper not yet processed]",
            "authors": [],
            "year": None,
            "venue": None
        }
        return {
            "ieee": format_ieee(placeholder),
            "apa": format_apa(placeholder),
            "mla": format_mla(placeholder),
            "harvard": format_harvard(placeholder)
        }
    
    context = "\n\n".join([c["content"] for c in chunks])
    
    prompt = PromptTemplate(
        template=CITATION_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_CITATION)
    # Use json_mode for broad OpenRouter model compatibility instead of tool-calling structured output
    structured_llm = llm.with_structured_output(NormalizedMetadata, method="json_mode")
    chain = prompt | structured_llm
    
    try:
        metadata_obj = await chain.ainvoke({"context": context})
        metadata = metadata_obj.model_dump()
    except Exception as e:
        logger.error(f"Citation LLM call failed: {e}")
        metadata = {"title": None, "authors": [], "year": None, "venue": None}
    
    # Generate formats
    result = {
        "ieee": format_ieee(metadata),
        "apa": format_apa(metadata),
        "mla": format_mla(metadata),
        "harvard": format_harvard(metadata)
    }
    
    return result
