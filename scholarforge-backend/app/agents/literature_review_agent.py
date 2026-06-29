import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.literature_review_prompts import LITERATURE_REVIEW_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class LiteratureReviewOutput(BaseModel):
    summary: str = Field(description="A comprehensive summary of the papers")
    key_findings: list[str] = Field(description="A list of key findings")
    contributions: list[str] = Field(description="A list of primary contributions")
    comparative_review: Optional[str] = Field(description="A comparative review if multiple papers, else null", default=None)

async def run_literature_review(state: ResearchState) -> dict:
    logger.info(f"Running Literature Review Agent for papers {state['paper_ids']}")
    
    # Retrieve chunks for the paper(s)
    # For literature review, we typically want introduction, conclusion, and abstract
    # We'll just grab the top 20 chunks generically for context
    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=20)
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=LITERATURE_REVIEW_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_LITERATURE_REVIEW)
    structured_llm = llm.with_structured_output(LiteratureReviewOutput)
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({"context": context})
    
    return result.model_dump()
