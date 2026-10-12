"""Paper-aware literature review and comparative synthesis agent.

Each paper is analyzed independently. A separate synthesis call compares the
individual reviews, preventing the same aggregate text from being copied into
all paper cards.
"""
import logging
from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.literature_review_prompts import LITERATURE_REVIEW_PROMPT
from app.db.chroma import retrieve_chunks

logger = logging.getLogger(__name__)


class SinglePaperReview(BaseModel):
    summary: str = Field(description="Summary based only on this paper's supplied text")
    methodology: str = Field(description="Methodology or approach described in this paper; state when not available")
    key_findings: list[str] = Field(description="Findings supported by this paper's supplied text")
    contributions: list[str] = Field(description="Contributions supported by this paper's supplied text")
    limitations: list[str] = Field(description="Limitations explicitly stated or directly supported by this paper")
    research_gaps: list[str] = Field(description="Research gaps supported by this paper's supplied text")
    future_directions: list[str] = Field(description="Future work stated or supported by this paper's supplied text")


class LiteratureReviewSynthesis(BaseModel):
    summary: str = Field(description="Cross-paper synthesis that accurately represents all individual reviews")
    key_findings: list[str] = Field(description="Synthesis of findings, clearly attributing differences to papers")
    contributions: list[str] = Field(description="Combined contributions without misattributing them")
    comparative_review: Optional[str] = Field(default=None, description="Evidence-based comparison of all selected papers")


def _paper_context(chunks: list[dict], paper_id: str, index: int) -> str:
    sections = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        # Retrieval for a paper should be scoped to its ID. Still guard against
        # accidental cross-paper chunks if the vector store returns them.
        chunk_paper_id = str(metadata.get("paper_id") or paper_id)
        if chunk_paper_id != str(paper_id):
            logger.warning("Ignoring cross-paper chunk: expected=%s got=%s", paper_id, chunk_paper_id)
            continue
        page = str(metadata.get("page_number") or "Unknown")
        key = (page, content)
        if key in seen:
            continue
        seen.add(key)
        sections.append(f"--- Paper {index} | Page {page} ---\n{content}")
    if not sections:
        raise ValueError(f"No usable text chunks were retrieved for selected paper {paper_id}.")
    return "\n\n".join(sections)


async def run_literature_review(state: ResearchState) -> dict:
    paper_ids = [str(pid) for pid in state.get("paper_ids", [])]
    user_id = str(state["user_id"])
    paper_titles = state.get("paper_titles") or {}

    if not paper_ids:
        raise ValueError("Literature Review requires at least one selected paper.")

    logger.info("Running paper-specific literature review for user=%s papers=%s", user_id, paper_ids)
    llm = get_llm(settings.LLM_MODEL_LITERATURE_REVIEW)
    single_chain = llm.with_structured_output(SinglePaperReview)

    reviews = []
    for index, paper_id in enumerate(paper_ids, start=1):
        chunks = retrieve_chunks(user_id, [paper_id], n_results=20)
        context = _paper_context(chunks, paper_id, index)
        title = str(paper_titles.get(paper_id) or f"Paper {index}")
        prompt = PromptTemplate(
            template=LITERATURE_REVIEW_PROMPT,
            input_variables=["title", "paper_id", "context"],
        )
        result = await (prompt | single_chain).ainvoke({
            "title": title,
            "paper_id": paper_id,
            "context": context,
        })
        review = result.model_dump()
        reviews.append({"paper_id": paper_id, "title": title, **review})

    if len(reviews) == 1:
        only = reviews[0]
        return {
            "summary": only["summary"],
            "key_findings": only["key_findings"],
            "contributions": only["contributions"],
            "comparative_review": None,
            "paper_reviews": reviews,
        }

    synthesis_input = "\n\n".join(
        f"PAPER {i}: {review['title']} (ID: {review['paper_id']})\n"
        f"SUMMARY: {review['summary']}\n"
        f"METHODOLOGY: {review['methodology']}\n"
        f"KEY FINDINGS: {review['key_findings']}\n"
        f"CONTRIBUTIONS: {review['contributions']}\n"
        f"LIMITATIONS: {review['limitations']}\n"
        f"RESEARCH GAPS: {review['research_gaps']}\n"
        f"FUTURE DIRECTIONS: {review['future_directions']}"
        for i, review in enumerate(reviews, start=1)
    )
    synthesis_prompt = PromptTemplate(
        template=(
            "You are synthesizing independent reviews of {paper_count} research papers. "
            "Each labeled block is a distinct paper and its analysis. Do not treat the blocks as one paper. "
            "Produce a grounded cross-paper summary, key findings, contributions, and comparative_review. "
            "Attribute findings to the relevant paper when they differ. Compare objectives, methods, results, "
            "contributions, limitations, and future directions only when the supplied reviews support it. "
            "Do not add generic claims or outside knowledge. comparative_review must be meaningful.\n\n"
            "INDIVIDUAL REVIEWS:\n{reviews}"
        ),
        input_variables=["paper_count", "reviews"],
    )
    synthesis_chain = synthesis_prompt | llm.with_structured_output(LiteratureReviewSynthesis)
    synthesis_result = await synthesis_chain.ainvoke({
        "paper_count": len(reviews),
        "reviews": synthesis_input,
    })
    synthesis = synthesis_result.model_dump()

    return {
        **synthesis,
        "paper_reviews": reviews,
    }
