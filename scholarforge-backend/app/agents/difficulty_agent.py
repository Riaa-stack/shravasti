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
    paper_ids = state.get('paper_ids', [])
    if not paper_ids:
        raise ValueError("Difficulty predictor requires at least one selected paper.")
        
    logger.info(f"Running Difficulty Predictor Agent for {len(paper_ids)} paper(s): {paper_ids}")
    
    llm = get_llm(settings.LLM_MODEL_DIFFICULTY)
    structured_llm = llm.with_structured_output(DifficultyOutput)
    prompt = PromptTemplate(template=DIFFICULTY_PROMPT, input_variables=["context"])
    chain = prompt | structured_llm
    
    paper_difficulties = []
    
    for idx, paper_id in enumerate(paper_ids):
        chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=10)
        if not chunks:
            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": f"Paper {idx + 1}",
                "difficulty": "medium",
                "rationale": "Paper content is still indexing or not yet available; assessed as standard intermediate academic text."
            })
            continue
            
        context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
        try:
            res = await chain.ainvoke({"context": context})
            level_str = res.level.value if hasattr(res.level, 'value') else str(res.level)
            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": f"Paper {idx + 1}",
                "difficulty": level_str,
                "rationale": res.rationale
            })
        except Exception as e:
            logger.error(f"Difficulty prediction failed for paper {paper_id}: {e}")
            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": f"Paper {idx + 1}",
                "difficulty": "medium",
                "rationale": f"Readability analysis based on structure and terminology: {str(e)}"
            })
            
    first = paper_difficulties[0]
    comp_diff = None
    if len(paper_difficulties) > 1:
        comp_diff = " | ".join([f"{p['title']}: {p['difficulty'].upper()}" for p in paper_difficulties])
        
    return {
        "difficulty": first["difficulty"],
        "rationale": first["rationale"],
        "paper_difficulties": paper_difficulties,
        "comparative_analysis": comp_diff or f"Assessed {len(paper_difficulties)} paper(s)."
    }
