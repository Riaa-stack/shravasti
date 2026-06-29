import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.methodology_prompts import METHODOLOGY_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class MethodologyOutput(BaseModel):
    algorithms: list[str] = Field(description="A list of algorithms used")
    models: list[str] = Field(description="A list of models used")
    datasets: list[str] = Field(description="A list of datasets used")
    evaluation_metrics: list[str] = Field(description="A list of evaluation metrics used")
    experimental_setup: str = Field(description="A description of the experimental setup")

async def run_methodology_analysis(state: ResearchState) -> dict:
    logger.info(f"Running Methodology Analysis Agent for papers {state['paper_ids']}")
    
    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=15)
    
    if not chunks:
        logger.warning(f"No chunks found for papers {state['paper_ids']}. Papers may not be processed yet.")
        return MethodologyOutput(
            algorithms=[],
            models=[],
            datasets=[],
            evaluation_metrics=[],
            experimental_setup="No content available. Please ensure the paper has been fully processed before running analysis."
        ).model_dump()
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=METHODOLOGY_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_METHODOLOGY)
    # Use json_mode for broad OpenRouter model compatibility
    structured_llm = llm.with_structured_output(MethodologyOutput, method="json_mode")
    chain = prompt | structured_llm
    
    try:
        result = await chain.ainvoke({"context": context})
        return result.model_dump()
    except Exception as e:
        logger.error(f"Methodology LLM call failed: {e}")
        return MethodologyOutput(
            algorithms=[],
            models=[],
            datasets=[],
            evaluation_metrics=[],
            experimental_setup=f"Analysis failed: {str(e)}"
        ).model_dump()
