import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.research_gap_prompts import RESEARCH_GAP_PROMPT
from app.db.chroma import retrieve_chunks
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class ResearchGapOutput(BaseModel):
    limitations: list[str] = Field(description="A list of limitations")
    future_scope: list[str] = Field(description="A list of future scope/work")
    missing_areas: list[str] = Field(description="A list of missing research areas")
    unsolved_problems: list[str] = Field(description="A list of unsolved problems")
    improvement_opportunities: list[str] = Field(description="A list of improvement opportunities")


def _normalize_gap_fields(data: dict) -> dict:
    """Normalize output shape without inventing unsupported research gaps."""
    for field in ("limitations", "future_scope", "missing_areas", "unsolved_problems", "improvement_opportunities"):
        value = data.get(field)
        data[field] = value if isinstance(value, list) else []
    return data


async def run_research_gap_detection(state: ResearchState) -> dict:
    paper_ids = state.get("paper_ids", [])
    if not paper_ids:
        raise ValueError("Research gap agent requires at least one selected paper.")

    logger.info(f"Running Research Gap Agent for {len(paper_ids)} paper(s): {paper_ids}")

    llm = get_llm(settings.LLM_MODEL_GAP)
    structured_llm = llm.with_structured_output(ResearchGapOutput, method="json_mode")
    prompt = PromptTemplate(template=RESEARCH_GAP_PROMPT, input_variables=["context"])
    chain = prompt | structured_llm

    if len(paper_ids) == 1:
        pid = paper_ids[0]
        chunks = retrieve_chunks(state["user_id"], [pid], n_results=15)
        if not chunks:
            raise ValueError(f"No indexed text is available for selected paper {pid}.")

        context = "\n\n".join([
            f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}"
            for c in chunks
        ])
        try:
            res = await chain.ainvoke({"context": context})
            dumped = res.model_dump()
        except Exception as e:
            logger.exception("Research Gap LLM call failed for paper %s", pid)
            raise RuntimeError(f"Research Gap analysis failed for paper {pid}: {e}") from e

        dumped = _normalize_gap_fields(dumped)
        dumped["paper_gaps"] = [{
            "paper_id": str(pid),
            "title": "Selected Paper",
            **dumped
        }]
        return dumped

    # Multiple papers
    paper_gaps = []
    all_limitations = set()
    all_future = set()
    all_missing = set()
    all_unsolved = set()
    all_opportunities = set()

    for idx, pid in enumerate(paper_ids):
        chunks = retrieve_chunks(state["user_id"], [pid], n_results=10)
        if not chunks:
            raise ValueError(f"No indexed text is available for selected paper {pid}.")
        else:
            context = "\n\n".join([
                f"--- Paper {c['metadata'].get('paper_id')} (Page {c['metadata'].get('page_number')}) ---\n{c['content']}"
                for c in chunks
            ])
            try:
                res = await chain.ainvoke({"context": context})
                single = res.model_dump()
            except Exception as e:
                logger.exception("Gap detection failed for paper %s", pid)
                raise RuntimeError(f"Research Gap analysis failed for paper {pid}: {e}") from e

        single = _normalize_gap_fields(single)

        for item in single.get("limitations", []):
            all_limitations.add(item)
        for item in single.get("future_scope", []):
            all_future.add(item)
        for item in single.get("missing_areas", []):
            all_missing.add(item)
        for item in single.get("unsolved_problems", []):
            all_unsolved.add(item)
        for item in single.get("improvement_opportunities", []):
            all_opportunities.add(item)

        paper_gaps.append({
            "paper_id": str(pid),
            "title": f"Paper {idx + 1}",
            **single
        })

    comparative_analysis = (
        f"Cross-Paper Research Gap Synthesis across {len(paper_ids)} selected papers:\n\n"
        f"Key Shared Gaps & Opportunities:\n" +
        "\n".join([f"- {u}" for u in list(all_unsolved)[:4] or list(all_opportunities)[:4]])
    )

    combined_res = {
        "limitations": list(all_limitations),
        "future_scope": list(all_future),
        "missing_areas": list(all_missing),
        "unsolved_problems": list(all_unsolved),
        "improvement_opportunities": list(all_opportunities),
        "paper_gaps": paper_gaps,
        "comparative_analysis": comparative_analysis
    }
    return _normalize_gap_fields(combined_res)
