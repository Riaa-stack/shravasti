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


def _normalize_trends(data: dict) -> dict:
    """Normalize fields while keeping the result grounded in retrieved papers."""
    for field in ("topics", "emerging_keywords", "popular_methods", "publication_timeline"):
        value = data.get(field)
        data[field] = value if isinstance(value, list) else []
    return data


async def run_trend_analysis(state: ResearchState) -> dict:
    logger.info(f"Running Trend Analysis Agent for papers {state['paper_ids']}")

    paper_ids = [str(pid) for pid in state.get("paper_ids", [])]
    if not paper_ids:
        raise ValueError("Trend analysis requires at least one selected paper.")
    sections = []
    for index, paper_id in enumerate(paper_ids, start=1):
        paper_chunks = retrieve_chunks(state["user_id"], [paper_id], n_results=10)
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
        template=TREND_PROMPT,
        input_variables=["context"]
    )

    llm = get_llm(settings.LLM_MODEL_TREND)
    structured_llm = llm.with_structured_output(TrendOutput)
    chain = prompt | structured_llm

    try:
        result = await chain.ainvoke({"context": context})
        dumped = result.model_dump()
    except Exception as e:
        logger.exception("Trend LLM call failed")
        raise RuntimeError(f"Trend analysis failed: {e}") from e

    return _normalize_trends(dumped)
