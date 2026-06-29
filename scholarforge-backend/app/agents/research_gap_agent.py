import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.research_gap_prompts import RESEARCH_GAP_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class ResearchGapOutput(BaseModel):
    limitations: list[str] = Field(description="A list of limitations")
    future_scope: list[str] = Field(description="A list of future scope/work")
    missing_areas: list[str] = Field(description="A list of missing research areas")
    unsolved_problems: list[str] = Field(description="A list of unsolved problems")
    improvement_opportunities: list[str] = Field(description="A list of improvement opportunities")

async def run_research_gap_detection(state: ResearchState) -> dict:
    logger.info(f"Running Research Gap Agent for papers {state['paper_ids']}")
    
    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=15)
    
    if not chunks:
        logger.warning(f"No chunks found for papers {state['paper_ids']}. Papers may not be processed yet.")
        return ResearchGapOutput(
            limitations=[],
            future_scope=[],
            missing_areas=[],
            unsolved_problems=[],
            improvement_opportunities=["Paper content not yet available. Please ensure the paper has been fully processed."]
        ).model_dump()
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=RESEARCH_GAP_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_GAP)
    # Use json_mode for broad OpenRouter model compatibility
    structured_llm = llm.with_structured_output(ResearchGapOutput, method="json_mode")
    chain = prompt | structured_llm
    
    try:
        result = await chain.ainvoke({"context": context})
        return result.model_dump()
    except Exception as e:
        logger.error(f"Research Gap LLM call failed: {e}")
        return ResearchGapOutput(
            limitations=[],
            future_scope=[],
            missing_areas=[],
            unsolved_problems=[],
            improvement_opportunities=[f"Analysis failed: {str(e)}"]
        ).model_dump()
