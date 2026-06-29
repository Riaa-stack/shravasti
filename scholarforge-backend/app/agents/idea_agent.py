import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.idea_prompts import IDEA_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class IdeaOutput(BaseModel):
    project_ideas: list[str] = Field(description="A list of project ideas with rationales")
    thesis_suggestions: list[str] = Field(description="A list of thesis suggestions with rationales")
    publication_ideas: list[str] = Field(description="A list of publication ideas with rationales")
    startup_opportunities: list[str] = Field(description="A list of startup opportunities with rationales")
    research_topics: list[str] = Field(description="A list of general research topics with rationales")

async def run_idea_generation(state: ResearchState) -> dict:
    logger.info(f"Running Idea Generator Agent for papers {state['paper_ids']}")
    
    # Retrieve chunks (focusing broadly on the text)
    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=20)
    
    context = "\n\n".join([f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    prompt = PromptTemplate(
        template=IDEA_PROMPT,
        input_variables=["context"]
    )
    
    llm = get_llm(settings.LLM_MODEL_IDEA)
    structured_llm = llm.with_structured_output(IdeaOutput)
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({"context": context})
    
    return result.model_dump()
