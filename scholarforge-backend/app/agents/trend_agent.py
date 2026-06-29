import logging
from pydantic import BaseModel, Field
from typing import Any

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.trend_prompts import TREND_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class TopicCount(BaseModel):
    name: str
    count: int

class KeywordTrend(BaseModel):
    term: str
    frequency: int
    trend: str

class MethodCount(BaseModel):
    name: str
    count: int

class TimelineCount(BaseModel):
    year: str
    count: int

class TrendOutput(BaseModel):
    topics: list[TopicCount]
    emerging_keywords: list[KeywordTrend]
    popular_methods: list[MethodCount]
    publication_timeline: list[TimelineCount]

async def run_trend_analysis(state: ResearchState) -> dict:
    logger.info(f"Running Trend Analysis Agent for papers {state['paper_ids']}")
    
    # Retrieve chunks
    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=30)
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=TREND_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_TREND)
    structured_llm = llm.with_structured_output(TrendOutput)
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({"context": context})
    
    # Dump the pydantic model to a dict, which will naturally serialize nested models
    return result.model_dump()
