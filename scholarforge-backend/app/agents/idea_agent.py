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


def _normalize_ideas(data: dict) -> dict:
    """Normalize result lists without substituting unrelated canned ideas."""
    for field in ("project_ideas", "thesis_suggestions", "publication_ideas", "startup_opportunities", "research_topics"):
        value = data.get(field)
        data[field] = value if isinstance(value, list) else []
    return data


async def run_idea_generation(state: ResearchState) -> dict:
    logger.info(f"Running Idea Generator Agent for papers {state['paper_ids']}")

    paper_ids = [str(pid) for pid in state.get("paper_ids", [])]
    if not paper_ids:
        raise ValueError("Idea generation requires at least one selected paper.")
    sections = []
    for index, paper_id in enumerate(paper_ids, start=1):
        paper_chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=8)
        if not paper_chunks:
            raise ValueError(f"No indexed text is available for selected paper {paper_id}.")
        sections.append(
            f"\n{'=' * 24} PAPER {index} (ID: {paper_id}) {'=' * 24}\n" +
            "\n\n".join(
                f"Page {c.get('metadata', {}).get('page_number', 'Unknown')}:\n{c.get('content', '')}"
                for c in paper_chunks if c.get("content")
            )
        )
    context = "\n\n".join(sections)

    prompt = PromptTemplate(
        template=IDEA_PROMPT,
        input_variables=["context"]
    )

    llm = get_llm(settings.LLM_MODEL_IDEA)
    structured_llm = llm.with_structured_output(IdeaOutput)
    chain = prompt | structured_llm

    try:
        result = await chain.ainvoke({"context": context})
        dumped = result.model_dump()
    except Exception as e:
        logger.exception("Idea LLM call failed")
        raise RuntimeError(f"Idea generation failed: {e}") from e

    return _normalize_ideas(dumped)
