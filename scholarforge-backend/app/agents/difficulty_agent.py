import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.difficulty_prompts import DIFFICULTY_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate
from app.models.paper import DifficultyLevel

logger = logging.getLogger(__name__)

class DifficultyOutput(BaseModel):
    level: DifficultyLevel = Field(description="The predicted difficulty level")
    rationale: str = Field(description="The rationale for the prediction")

async def run_difficulty_prediction(state: ResearchState) -> dict:
    logger.info(f"Running Difficulty Predictor Agent for paper {state['paper_ids'][0]}")
    paper_id = state['paper_ids'][0]
    
    # Retrieve random/distributed chunks to assess readability
    chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=10)
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=DIFFICULTY_PROMPT,
        input_variables=["context"]
    )
    
    # We can use a simpler/faster model for classification tasks
    llm = get_llm(settings.LLM_MODEL_DIFFICULTY)
    structured_llm = llm.with_structured_output(DifficultyOutput)
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({"context": context})
    
    return {
        "difficulty": result.level.value,
        "rationale": result.rationale
    }
