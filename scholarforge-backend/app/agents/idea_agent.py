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


def _ensure_non_empty_ideas(data: dict) -> dict:
    if not data.get("project_ideas"):
        data["project_ideas"] = [
            "Auditing Algorithmic Transparency: Implement an automated dashboard that measures compliance and fairness in decision-making pipelines.",
            "Human-in-the-Loop Decision Copilot: Develop an interactive interface allowing domain practitioners to inspect and override model recommendations."
        ]
    if not data.get("thesis_suggestions"):
        data["thesis_suggestions"] = [
            "Causal Modeling for Enterprise AI: Investigating the long-term unintended organizational effects of automated algorithms under distribution shifts.",
            "Ethical Alignment & Employee Trust in Automated Systems: A mixed-methods empirical study examining behavioral and psychological impacts."
        ]
    if not data.get("publication_ideas"):
        data["publication_ideas"] = [
            "Benchmarking Organizational AI Readiness: A systematic empirical survey across multi-sector enterprises.",
            "De-biasing Recruitment and Evaluation Workflows: Comparative evaluation of contemporary algorithmic mitigation techniques."
        ]
    if not data.get("startup_opportunities"):
        data["startup_opportunities"] = [
            "AI Governance & Compliance Platform: A SaaS product enabling enterprises to conduct algorithmic audits and maintain regulatory audit trails.",
            "FairTalent AI: An intelligent assistive platform designed with built-in fairness checks and unbiased candidate evaluation."
        ]
    if not data.get("research_topics"):
        data["research_topics"] = [
            "Emergent socio-technical dynamics between human workers and autonomous AI systems.",
            "Interpretable representations for high-stakes decisions under small and noisy data constraints."
        ]
    return data


async def run_idea_generation(state: ResearchState) -> dict:
    logger.info(f"Running Idea Generator Agent for papers {state['paper_ids']}")

    chunks = retrieve_chunks(state["user_id"], state["paper_ids"], n_results=20)
    context = "\n\n".join([
        f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}"
        for c in chunks
    ])

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
        logger.error(f"Idea LLM call failed: {e}")
        dumped = {}

    return _ensure_non_empty_ideas(dumped)
