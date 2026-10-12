import logging
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.db.chroma import retrieve_chunks

logger = logging.getLogger(__name__)

# This project stores each paper's chunks with string user_id and paper_id metadata.
# Keep retrieval compatible with the existing app/db/chroma.py API.
CHUNKS_PER_PAPER = 18
MAX_CHARS_PER_CHUNK = 1800
MAX_CONTEXT_CHARS = 18000

METHODOLOGY_EXTRACTION_PROMPT = """
You are an academic research analyst. Analyze ONLY the paper excerpts supplied below.
The excerpts are from one selected paper. Never mix information from another paper.
Do not claim that the paper's authors performed an experiment unless the excerpts say so.

IMPORTANT DISTINCTION:
For a review/history paper, some fields describe the methods the review authors used,
while other fields describe AI methods/models discussed in the reviewed subject. Do not
leave fields empty merely because the paper is a review. Label the distinction explicitly.

Extract these fields:
1. algorithms:
   - Include analytical/review procedures actually used by the authors, if reported.
   - Also include algorithmic approaches explicitly discussed in the paper, but label them
     "Discussed in paper; not reported as an experiment by these authors."
   - Examples only if present in the excerpts: rule-based/if-then systems, machine learning,
     deep learning, neural networks, computer vision, NLP, search/screening/coding methods.
2. models:
   - Include named AI systems, model families, architectures, and conceptual frameworks
     explicitly mentioned in the excerpts.
   - For historical AI-in-medicine papers, a system discussed as an example can be listed
     as "historical system discussed", not as a model evaluated by the authors.
   - Do not infer a model name that is not present in the excerpts.
3. datasets:
   - Include named datasets, cohorts, samples, databases, or reviewed literature corpus only
     if the excerpts explicitly identify them.
   - For a review, state "Not specified in supplied excerpts" only if appropriate; do not
     mislabel PubMed as a dataset if it is merely mentioned as a resource.
4. evaluation_metrics:
   - Include metrics explicitly reported or discussed as metrics in the excerpts.
   - Do not assume sensitivity, specificity, accuracy, or other metrics were evaluated just
     because the paper is about medicine.
5. experimental_setup:
   - Write 2-4 concise sentences about the paper type, scope, and what the authors did.
   - If it is a narrative/historical review without a formal experimental method, say so,
     then summarize the actual scope and applications covered.
   - If details such as search databases, criteria, sample size, or experiments are absent
     from these excerpts, say they are not specified in the supplied excerpts.

Keep each list to at most 6 concise items. Use evidence from the text. If a field truly has
no supported information, return an empty list. Do not put a long generic disclaimer in
every field.

Return valid JSON with exactly these keys:
{{
  "algorithms": ["..."],
  "models": ["..."],
  "datasets": ["..."],
  "evaluation_metrics": ["..."],
  "experimental_setup": "..."
}}

PAPER EXCERPTS:
{context}
"""

METHODOLOGY_PROMPT = PromptTemplate(
    template=METHODOLOGY_EXTRACTION_PROMPT,
    input_variables=["context"],
)


class MethodologyOutput(BaseModel):
    algorithms: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    evaluation_metrics: list[str] = Field(default_factory=list)
    experimental_setup: str = Field(default="")


def _chunk_text(chunk: dict[str, Any]) -> str:
    content = chunk.get("content") or chunk.get("text") or ""
    return content.strip() if isinstance(content, str) else ""


def _normalize_fields(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    for field in ("algorithms", "models", "datasets", "evaluation_metrics"):
        value = result.get(field)
        if not isinstance(value, list):
            value = []
        cleaned = []
        seen = set()
        for item in value:
            if item is None:
                continue
            item = str(item).strip()
            if item and item.casefold() not in seen:
                cleaned.append(item)
                seen.add(item.casefold())
        result[field] = cleaned[:6]

    setup = result.get("experimental_setup")
    result["experimental_setup"] = setup.strip() if isinstance(setup, str) else ""
    if len(result["experimental_setup"]) > 1400:
        result["experimental_setup"] = (
            result["experimental_setup"][:1397].rsplit(" ", 1)[0] + "..."
        )
    return result


def _build_context(chunks: list[dict[str, Any]], paper_id: Any) -> str:
    parts: list[str] = []
    total_chars = 0
    for index, chunk in enumerate(chunks):
        content = _chunk_text(chunk)
        if not content:
            continue
        metadata = chunk.get("metadata") or {}
        actual_paper_id = metadata.get("paper_id")
        if actual_paper_id is not None and str(actual_paper_id) != str(paper_id):
            logger.warning(
                "Ignoring chunk from other paper: expected=%s actual=%s",
                paper_id, actual_paper_id,
            )
            continue

        page = metadata.get("page_number", "unknown")
        chunk_index = metadata.get("chunk_index", index)
        content = content[:MAX_CHARS_PER_CHUNK]
        section = metadata.get("section_title", "")
        label = f"[Selected paper ID: {paper_id}; chunk: {chunk_index}; page: {page}"
        if section:
            label += f"; section: {section}"
        label += "]"
        part = f"{label}\n{content}"
        available = MAX_CONTEXT_CHARS - total_chars
        if available <= 0:
            break
        part = part[:available]
        parts.append(part)
        total_chars += len(part)
    return "\n\n".join(parts)


async def _analyze_paper(chain: Any, user_id: str, paper_id: Any) -> dict[str, Any]:
    # Chroma's existing no-query path returns chunks filtered by BOTH user_id and paper_id.
    # Do not use multi-paper retrieval here: each model call must see only one paper.
    chunks = retrieve_chunks(
        user_id=str(user_id),
        paper_ids=[str(paper_id)],
        n_results=CHUNKS_PER_PAPER,
    ) or []

    if not chunks:
        raise ValueError(
            f"No indexed chunks found for paper ID {paper_id}. "
            "Check this paper's ChromaDB paper_id and re-index it if needed."
        )

    context = _build_context(chunks, paper_id)
    if not context:
        raise ValueError(f"Retrieved chunks for paper {paper_id} contain no readable text.")

    try:
        response = await chain.ainvoke({"context": context})
        if hasattr(response, "model_dump"):
            response = response.model_dump()
        elif not isinstance(response, dict):
            raise TypeError(f"Unexpected LLM response type: {type(response).__name__}")
        if not isinstance(response, dict):
            raise TypeError("Methodology model did not return a JSON object.")
    except Exception as exc:
        logger.exception("Methodology analysis failed for paper_id=%s", paper_id)
        raise RuntimeError(f"Methodology analysis failed for paper {paper_id}: {exc}") from exc

    result = _normalize_fields(response)
    logger.info(
        "Methodology paper_id=%s chunks=%s algorithms=%s models=%s datasets=%s metrics=%s",
        paper_id, len(chunks), len(result["algorithms"]), len(result["models"]),
        len(result["datasets"]), len(result["evaluation_metrics"]),
    )
    return result


def _unique_merged(papers: list[dict[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for paper in papers:
        for item in paper.get(field, []):
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                values.append(item)
    return values


def _brief_comparison(papers: list[dict[str, Any]]) -> str:
    # Keep this deliberately short; detailed analysis belongs in paper_analyses.
    lines = []
    for index, paper in enumerate(papers, start=1):
        setup = paper.get("experimental_setup", "")
        first_sentence = setup.split(".")[0].strip() if setup else ""
        if len(first_sentence) > 180:
            first_sentence = first_sentence[:177].rsplit(" ", 1)[0] + "..."
        if first_sentence:
            lines.append(f"Paper {index}: {first_sentence}")
    return " | ".join(lines) if lines else "See the individual paper analyses."


async def run_methodology_analysis(state: ResearchState) -> dict:
    paper_ids = list(dict.fromkeys(state.get("paper_ids") or []))
    user_id = state.get("user_id")
    if not paper_ids:
        raise ValueError("Methodology analysis requires at least one selected paper.")
    if not user_id:
        raise ValueError("Methodology analysis requires user_id.")

    logger.info("Starting methodology analysis for paper IDs: %s", paper_ids)

    llm = get_llm(settings.LLM_MODEL_METHODOLOGY)
    structured_llm = llm.with_structured_output(MethodologyOutput, method="json_mode")
    chain = METHODOLOGY_PROMPT | structured_llm

    paper_analyses: list[dict[str, Any]] = []
    for index, paper_id in enumerate(paper_ids, start=1):
        try:
            result = await _analyze_paper(chain, str(user_id), paper_id)
            error = None
        except Exception as exc:
            logger.exception("Could not analyze paper_id=%s", paper_id)
            result = {
                "algorithms": [],
                "models": [],
                "datasets": [],
                "evaluation_metrics": [],
                "experimental_setup": "",
            }
            error = str(exc)[:400]

        item = {
            "paper_id": str(paper_id),
            "title": f"Paper {index}",
            **result,
        }
        if error:
            item["analysis_error"] = error
            item["experimental_setup"] = (
                "Analysis failed for this paper. Check the backend log for details. "
                + error[:250]
            )
        paper_analyses.append(item)

    if len(paper_analyses) == 1:
        single = dict(paper_analyses[0])
        return {
            **single,
            "paper_analyses": paper_analyses,
            "comparative_analysis": "",
        }

    # Aggregate fields are retained for API compatibility; frontend hides them when
    # paper_analyses exists. Each paper card is populated only by that paper's result.
    return {
        "algorithms": _unique_merged(paper_analyses, "algorithms"),
        "models": _unique_merged(paper_analyses, "models"),
        "datasets": _unique_merged(paper_analyses, "datasets"),
        "evaluation_metrics": _unique_merged(paper_analyses, "evaluation_metrics"),
        "experimental_setup": "",
        "paper_analyses": paper_analyses,
        "comparative_analysis": _brief_comparison(paper_analyses),
    }
