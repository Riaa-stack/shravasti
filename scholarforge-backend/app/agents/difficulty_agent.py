"""Per-paper research difficulty prediction with consistent labels and real titles."""
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from sqlalchemy import select

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.db.chroma import retrieve_chunks
from app.db.postgres import async_session_maker
from app.models.paper import Paper, DifficultyLevel

logger = logging.getLogger(__name__)


class DifficultyOutput(BaseModel):
    level: DifficultyLevel = Field(description="One of easy, medium, or hard")
    rationale: str = Field(description="Evidence-based explanation for this paper's difficulty")


DIFFICULTY_ANALYSIS_PROMPT = """You are assessing the reading and implementation difficulty of ONE research paper.
Use only evidence in the excerpts. Consider:
- mathematical/statistical depth and specialized terminology
- algorithmic and implementation complexity
- dataset and experimental-design complexity
- prerequisite domain knowledge

Choose exactly one level:
- easy: mostly conceptual, little technical background or implementation
- medium: some technical terminology/methods and undergraduate-level background
- hard: advanced mathematics, complex systems/experiments, or substantial specialist knowledge

Do not rate all papers the same by default. Base this paper's assessment on its own evidence.
Give a concise rationale with concrete evidence. Do not mention an API error or invent details.

EXCERPTS:
{context}
"""

PROMPT = PromptTemplate(template=DIFFICULTY_ANALYSIS_PROMPT, input_variables=["context"])


def _text(chunk: dict[str, Any]) -> str:
    value = chunk.get("content") or chunk.get("text") or ""
    return value.strip() if isinstance(value, str) else ""


async def _paper_metadata(user_id: str, paper_id: Any) -> dict[str, Any]:
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Paper).where(
                    Paper.id == uuid.UUID(str(paper_id)),
                    Paper.user_id == uuid.UUID(str(user_id)),
                )
            )
            paper = result.scalar_one_or_none()
            if paper:
                return {"title": paper.title, "difficulty_level": paper.difficulty_level}
    except Exception:
        logger.exception("Could not load metadata for paper %s", paper_id)
    return {}


async def run_difficulty_prediction(state: ResearchState) -> dict:
    paper_ids = state.get("paper_ids") or []
    user_id = state.get("user_id")

    if not paper_ids:
        raise ValueError(
            "Difficulty predictor requires at least one selected paper."
        )
    if not user_id:
        raise ValueError(
            "Difficulty predictor requires an authenticated user."
        )

    llm = get_llm(
        settings.LLM_MODEL_DIFFICULTY,
        temperature=0.0,
        max_tokens=500,
    )
    chain = PROMPT | llm.with_structured_output(DifficultyOutput)
    paper_difficulties: list[dict[str, Any]] = []

    for idx, paper_id in enumerate(paper_ids):
        meta = await _paper_metadata(user_id, paper_id)
        title = str(meta.get("title") or "").strip() or f"Paper {idx + 1}"

        # Retrieve indexed content for this paper only.
        chunks = retrieve_chunks(user_id, [paper_id], n_results=12)
        chunks = sorted(
            chunks,
            key=lambda chunk: int(
                (chunk.get("metadata") or {}).get("chunk_index", 10**9)
            ),
        )

        context = "\n\n".join(
            f"[Page {(chunk.get('metadata') or {}).get('page_number', 'unknown')}]\n"
            f"{_text(chunk)[:3500]}"
            for chunk in chunks
            if _text(chunk)
        )[:16000]

        if not context.strip():
            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": title,
                "difficulty": "unknown",
                "rationale": (
                    "No readable indexed text was found for this paper. "
                    "Re-index or re-upload it before predicting difficulty."
                ),
            })
            continue

        try:
            prediction = await chain.ainvoke({"context": context})
            raw_level = prediction.level
            level = (
                raw_level.value
                if hasattr(raw_level, "value")
                else str(raw_level)
            ).strip().lower()

            rationale = str(prediction.rationale or "").strip()

            if level not in {"easy", "medium", "hard"}:
                raise ValueError(f"Unexpected difficulty label: {level}")

            if not rationale:
                rationale = (
                    "The model returned no rationale. Review the paper "
                    "content before relying on this difficulty assessment."
                )

            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": title,
                "difficulty": level,
                "rationale": rationale,
            })

        except Exception as exc:
            logger.exception(
                "Difficulty prediction failed for paper %s",
                paper_id,
            )
            paper_difficulties.append({
                "paper_id": str(paper_id),
                "title": title,
                "difficulty": "unknown",
                "rationale": (
                    f"Prediction could not be completed: "
                    f"{type(exc).__name__}. Check the model/provider logs "
                    "and retry; no default difficulty was fabricated."
                ),
            })

    valid_levels = [
        paper["difficulty"]
        for paper in paper_difficulties
        if paper["difficulty"] != "unknown"
    ]

    comparison = " | ".join(
        f"{paper['title']}: {paper['difficulty'].upper()}"
        for paper in paper_difficulties
    ) or (
        "No predictions could be generated because readable paper text "
        "was unavailable."
    )

    result: dict[str, Any] = {
        "paper_difficulties": paper_difficulties,
        "comparative_analysis": comparison,
        "summary": (
            f"Difficulty predicted for {len(valid_levels)} of "
            f"{len(paper_difficulties)} selected paper(s)."
        ),
    }

    # Preserve top-level fields for single-paper requests only.
    # Multi-paper requests use each entry in paper_difficulties.
    if len(paper_difficulties) == 1:
        result["difficulty"] = paper_difficulties[0]["difficulty"]
        result["rationale"] = paper_difficulties[0]["rationale"]

    return result
