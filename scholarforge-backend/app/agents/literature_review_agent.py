import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.literature_review_prompts import LITERATURE_REVIEW_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class LiteratureReviewOutput(BaseModel):
    summary: str = Field(
        description=(
            "A comprehensive synthesis of ALL selected papers. "
            "Every selected paper must be represented in the summary."
        )
    )

    key_findings: list[str] = Field(
        description=(
            "Key findings extracted from ALL selected papers. "
            "Do not omit findings from any selected paper."
        )
    )

    contributions: list[str] = Field(
        description=(
            "Primary contributions of ALL selected papers. "
            "Do not omit contributions from any selected paper."
        )
    )

    comparative_review: Optional[str] = Field(
        default=None,
        description=(
            "A detailed comparative review when two or more papers are selected. "
            "Compare the papers by topic, objectives, methodology, findings, "
            "contributions, strengths, limitations, and research direction. "
            "Must not be null when multiple papers are provided."
        ),
    )


def _group_chunks_by_paper(chunks: list[dict]) -> dict[str, list[dict]]:
    """
    Group retrieved Chroma chunks by paper_id.

    This prevents the Literature Review agent from treating the entire
    retrieval result as one undifferentiated document.
    """

    grouped: dict[str, list[dict]] = {}

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}

        paper_id = metadata.get("paper_id")

        if not paper_id:
            paper_id = "unknown"

        grouped.setdefault(str(paper_id), []).append(chunk)

    return grouped


def _build_balanced_context(
    chunks: list[dict],
    paper_ids: list[str],
) -> str:
    """
    Build a paper-aware context.

    The old implementation simply joined the top N chunks globally.
    That can cause one paper to dominate the context.

    This implementation explicitly separates every selected paper.
    """

    grouped_chunks = _group_chunks_by_paper(chunks)

    sections: list[str] = []

    for index, paper_id in enumerate(paper_ids, start=1):

        paper_chunks = grouped_chunks.get(str(paper_id), [])

        sections.append(
            f"\n{'=' * 80}\n"
            f"PAPER {index}\n"
            f"PAPER ID: {paper_id}\n"
            f"{'=' * 80}\n"
        )

        if not paper_chunks:
            sections.append(
                "No retrieved text chunks were available for this paper."
            )
            continue

        # Remove accidental duplicate chunks while preserving order.
        seen: set[tuple] = set()

        for chunk in paper_chunks:
            metadata = chunk.get("metadata") or {}
            content = (chunk.get("content") or "").strip()

            if not content:
                continue

            page_number = metadata.get("page_number")

            dedup_key = (
                str(page_number),
                content,
            )

            if dedup_key in seen:
                continue

            seen.add(dedup_key)

            sections.append(
                f"\n--- Paper {index} | "
                f"Page {page_number if page_number is not None else 'Unknown'} ---\n"
                f"{content}"
            )

    return "\n".join(sections)


async def run_literature_review(state: ResearchState) -> dict:
    """
    Run the Literature Review agent for ALL selected papers.

    Important:
    - state["paper_ids"] may contain one or many paper IDs.
    - Every selected paper is explicitly represented in the prompt.
    - When multiple papers are selected, comparative_review is required.
    """

    paper_ids = [str(paper_id) for paper_id in state.get("paper_ids", [])]

    user_id = str(state["user_id"])

    logger.info(
        "Running Literature Review Agent | user_id=%s | paper_count=%d | paper_ids=%s",
        user_id,
        len(paper_ids),
        paper_ids,
    )

    if not paper_ids:
        raise ValueError(
            "Literature Review requires at least one selected paper."
        )

    # ------------------------------------------------------------------
    # RETRIEVE CHUNKS
    # ------------------------------------------------------------------
    #
    # Keep the retrieval call compatible with the existing ChromaDB
    # implementation.
    #
    # The important difference is that the returned chunks are now
    # explicitly grouped by paper before being sent to the LLM.
    # ------------------------------------------------------------------

    retrieval_count = max(20, len(paper_ids) * 20)

    chunks = retrieve_chunks(
        user_id,
        paper_ids,
        n_results=retrieval_count,
    )

    if not chunks:
        raise ValueError(
            "No content could be retrieved from the selected papers."
        )

    logger.info(
        "Literature Review retrieval returned %d chunks for %d selected papers.",
        len(chunks),
        len(paper_ids),
    )

    # ------------------------------------------------------------------
    # BUILD PAPER-AWARE CONTEXT
    # ------------------------------------------------------------------

    context = _build_balanced_context(
        chunks=chunks,
        paper_ids=paper_ids,
    )

    # ------------------------------------------------------------------
    # EXPLICIT MULTI-PAPER INSTRUCTIONS
    # ------------------------------------------------------------------

    if len(paper_ids) == 1:

        analysis_instruction = """
You are analyzing ONE selected research paper.

Analyze the complete available evidence for this paper.

Generate:
1. A comprehensive summary.
2. Key findings.
3. Primary contributions.

Because only one paper is selected, comparative_review may be null.
"""

    else:

        analysis_instruction = f"""
You are analyzing {len(paper_ids)} SELECTED RESEARCH PAPERS.

THIS IS A MULTI-PAPER LITERATURE REVIEW.

You MUST analyze EVERY paper listed in the context.

Do NOT analyze only the first paper.

For EACH paper:
- Identify its main topic/objective.
- Identify its methodology or approach when available.
- Identify its important findings.
- Identify its primary contributions.
- Identify relevant limitations or research gaps when supported by the text.

Then synthesize the papers together.

The final response MUST contain:

1. SUMMARY
   Provide a comprehensive synthesis covering ALL selected papers.

2. KEY FINDINGS
   Include findings from ALL selected papers.
   Clearly distinguish findings when necessary.

3. CONTRIBUTIONS
   Include contributions from ALL selected papers.

4. COMPARATIVE REVIEW
   Because multiple papers were selected, comparative_review MUST NOT be null.

   Compare the selected papers using the available evidence, including:
   - research objectives
   - research topics
   - methodologies/approaches
   - datasets or study populations when available
   - major findings
   - contributions
   - similarities
   - differences
   - limitations
   - research gaps/future directions

IMPORTANT:
- Never silently ignore a selected paper.
- Do not produce a review based only on PAPER 1.
- If information is unavailable for a particular comparison category,
  explicitly say that the available paper text does not provide enough
  information instead of inventing details.
- Do not use outside knowledge.
- Use ONLY the supplied paper context.
"""

    # ------------------------------------------------------------------
    # COMBINE EXISTING PROJECT PROMPT + MULTI-PAPER INSTRUCTIONS
    # ------------------------------------------------------------------

    final_template = f"""
{LITERATURE_REVIEW_PROMPT}

{analysis_instruction}

The selected paper IDs are:

{chr(10).join(f"- {paper_id}" for paper_id in paper_ids)}

Below is the retrieved content.

You MUST treat the boundaries marked PAPER 1, PAPER 2, etc.
as separate research papers.

-------------------- START PAPER CONTEXT --------------------

{{context}}

--------------------- END PAPER CONTEXT ---------------------

Return a structured response matching the required schema exactly.
"""

    prompt = PromptTemplate(
        template=final_template,
        input_variables=["context"],
    )

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    llm = get_llm(
        settings.LLM_MODEL_LITERATURE_REVIEW
    )

    structured_llm = llm.with_structured_output(
        LiteratureReviewOutput
    )

    chain = prompt | structured_llm

    logger.info(
        "Sending Literature Review request to LLM for %d paper(s).",
        len(paper_ids),
    )

    result = await chain.ainvoke(
        {
            "context": context,
        }
    )

    # ------------------------------------------------------------------
    # VALIDATE MULTI-PAPER RESULT
    # ------------------------------------------------------------------

    output = result.model_dump()

    if len(paper_ids) > 1:

        comparative_review = output.get("comparative_review")

        if not comparative_review or not str(comparative_review).strip():

            logger.warning(
                "LLM returned an empty comparative_review for %d papers.",
                len(paper_ids),
            )

            # We don't fabricate a comparison here.
            # Instead, make the problem visible to the caller.
            output["comparative_review"] = (
                "The selected papers were retrieved successfully, "
                "but the language model did not return a comparative "
                "review. Please run the Literature Review again."
            )

    logger.info(
        "Literature Review completed successfully for paper_ids=%s",
        paper_ids,
    )

    return output