
"""Generate citations independently for each selected paper, preferring stored metadata."""

import logging
import re
import uuid
from typing import Optional, Any

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from sqlalchemy import select

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.db.chroma import retrieve_chunks
from app.db.postgres import async_session_maker
from app.models.paper import Paper

logger = logging.getLogger(__name__)


class NormalizedMetadata(BaseModel):
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None


CITATION_EXTRACTION_PROMPT = """Extract bibliographic metadata from the FIRST-PAGE/FRONT-MATTER excerpts of exactly one research paper.
Return metadata for this paper only. Do not reuse names, title, year, or venue from another paper.
Prefer the paper's own title page, byline, journal/conference header, DOI/copyright line.
Authors must be person names only; omit credentials such as MD, PhD, FASGE, PA-C.
Do not infer missing values. Use null for unknown scalar fields and [] for unknown authors.
Return JSON with keys: title, authors, year, venue, volume, issue, pages.

EXCERPTS:
{context}
"""

PROMPT = PromptTemplate(
    template=CITATION_EXTRACTION_PROMPT,
    input_variables=["context"],
)


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or default


def _authors(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, str):
        value = re.split(r"\s*;\s*|\s*\|\s*", value)

    if not isinstance(value, (list, tuple)):
        return []

    cleaned = []

    for author in value:
        name = _clean(author)
        name = re.sub(
            r",?\s*(MD|PhD|Ph\.D\.|M\.D\.|FASGE|PA-C|MSc|BSc)\b.*$",
            "",
            name,
            flags=re.I,
        ).strip(" ,")

        if name and name.casefold() not in {
            existing.casefold() for existing in cleaned
        }:
            cleaned.append(name)

    return cleaned


def format_ieee(meta: dict) -> str:
    authors = ", ".join(_authors(meta.get("authors")))
    authors = authors or "Author information unavailable"

    title = _clean(meta.get("title"), "Title unavailable")
    venue = _clean(meta.get("venue"))
    year = _clean(meta.get("year"), "n.d.")

    extras = []

    if meta.get("volume"):
        extras.append(f"vol. {_clean(meta['volume'])}")
    if meta.get("issue"):
        extras.append(f"no. {_clean(meta['issue'])}")
    if meta.get("pages"):
        extras.append(f"pp. {_clean(meta['pages'])}")

    tail = ", ".join(
        item for item in [venue, *extras, year] if item
    )

    return f'{authors}, "{title}," {tail}.'.replace("  ", " ")


def format_apa(meta: dict) -> str:
    authors = ", ".join(_authors(meta.get("authors")))
    authors = authors or "Author information unavailable"

    year = _clean(meta.get("year"), "n.d.")
    title = _clean(meta.get("title"), "Title unavailable")
    venue = _clean(meta.get("venue"))

    details = ""

    if meta.get("volume"):
        details = _clean(meta["volume"])

        if meta.get("issue"):
            details += f"({_clean(meta['issue'])})"

        if meta.get("pages"):
            details += f", {_clean(meta['pages'])}"

    return (
        f"{authors} ({year}). {title}. {venue}"
        f"{', ' + details if details else ''}."
    ).replace("..", ".")


def format_mla(meta: dict) -> str:
    authors = ", ".join(_authors(meta.get("authors")))
    authors = authors or "Author information unavailable"

    title = _clean(meta.get("title"), "Title unavailable")
    venue = _clean(meta.get("venue"))
    year = _clean(meta.get("year"), "n.d.")

    return f'{authors}. "{title}." {venue}, {year}.'.replace("..", ".")


def format_harvard(meta: dict) -> str:
    authors = ", ".join(_authors(meta.get("authors")))
    authors = authors or "Author information unavailable"

    year = _clean(meta.get("year"), "n.d.")
    title = _clean(meta.get("title"), "Title unavailable")
    venue = _clean(meta.get("venue"))

    return f"{authors}, {year}. {title}. {venue}.".replace("..", ".")


async def _load_paper(
    user_id: str,
    paper_id: Any,
) -> Optional[Paper]:
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Paper).where(
                    Paper.id == uuid.UUID(str(paper_id)),
                    Paper.user_id == uuid.UUID(str(user_id)),
                )
            )
            return result.scalar_one_or_none()

    except Exception:
        logger.exception(
            "Could not load stored metadata for paper %s",
            paper_id,
        )
        return None


def _valid_llm_title(
    llm_title: Any,
    stored_title: Any,
) -> bool:
    title = _clean(llm_title)

    if not title or title.lower().startswith(
        ("paper ", "research paper", "unknown")
    ):
        return False

    # Reject a title unrelated to the title stored in the database.
    if stored_title:
        normalized_title = re.sub(
            r"\W+", "", title.casefold()
        )
        normalized_stored = re.sub(
            r"\W+", "", _clean(stored_title).casefold()
        )

        if (
            normalized_title != normalized_stored
            and normalized_title not in normalized_stored
            and normalized_stored not in normalized_title
        ):
            return False

    return True


async def run_citation_generation(
    state: ResearchState,
) -> dict:
    paper_ids = state.get("paper_ids") or []
    user_id = state.get("user_id")

    if not paper_ids:
        raise ValueError(
            "Citation agent requires at least one selected paper."
        )

    if not user_id:
        raise ValueError(
            "Citation agent requires an authenticated user."
        )

    llm = get_llm(
        settings.LLM_MODEL_CITATION,
        temperature=0.0,
        max_tokens=700,
    )

    chain = PROMPT | llm.with_structured_output(
        NormalizedMetadata,
        method="json_mode",
    )

    paper_citations: list[dict[str, Any]] = []

    for idx, paper_id in enumerate(paper_ids):
        # Load metadata independently for each selected paper.
        db_paper = await _load_paper(user_id, paper_id)

        stored_title = (
            _clean(getattr(db_paper, "title", None))
            if db_paper
            else ""
        )

        stored_authors = (
            _authors(getattr(db_paper, "authors", None))
            if db_paper
            else []
        )

        stored_year = (
            getattr(db_paper, "publication_year", None)
            if db_paper
            else None
        )

        stored_venue = (
            _clean(getattr(db_paper, "venue", None))
            if db_paper
            else ""
        )

        # Retrieve chunks for this paper ID only.
        chunks = retrieve_chunks(
            user_id,
            [paper_id],
            n_results=8,
        )

        chunks = sorted(
            chunks,
            key=lambda chunk: int(
                (chunk.get("metadata") or {}).get(
                    "chunk_index",
                    10**9,
                )
            ),
        )

        # Prefer early chunks containing bibliographic information.
        context = "\n\n".join(
            _clean(chunk.get("content"))[:2500]
            for chunk in chunks[:4]
            if _clean(chunk.get("content"))
        )[:8000]

        extracted: dict[str, Any] = {}

        if context:
            try:
                response = await chain.ainvoke(
                    {"context": context}
                )

                extracted = (
                    response.model_dump()
                    if hasattr(response, "model_dump")
                    else dict(response)
                )

            except Exception:
                logger.exception(
                    "Citation metadata extraction failed for paper %s",
                    paper_id,
                )

        llm_title = extracted.get("title")

        title = stored_title or (
            _clean(llm_title)
            if _valid_llm_title(llm_title, stored_title)
            else ""
        )

        if not title:
            title = (
                f"Paper {idx + 1} "
                "(title not found in indexed text)"
            )

        authors = stored_authors or _authors(
            extracted.get("authors")
        )

        year = stored_year or extracted.get("year")
        venue = stored_venue or _clean(
            extracted.get("venue")
        )

        metadata = {
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "volume": extracted.get("volume"),
            "issue": extracted.get("issue"),
            "pages": extracted.get("pages"),
        }

        # Generate all citation styles from this paper's metadata.
        paper_citations.append({
            "paper_id": str(paper_id),
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "ieee": format_ieee(metadata),
            "apa": format_apa(metadata),
            "mla": format_mla(metadata),
            "harvard": format_harvard(metadata),
        })

    # Return individual paper citations as the primary result.
    # Do not expose Paper 1's citation as the global citation
    # when multiple papers have been selected.
    result: dict[str, Any] = {
        "paper_citations": paper_citations,
        "comparative_analysis": (
            f"Generated citations independently for "
            f"{len(paper_citations)} selected paper(s). "
            "Verify any fields marked unavailable against "
            "the publisher's official record."
        ),
    }

    # Preserve top-level fields for existing single-paper requests.
    if len(paper_citations) == 1:
        first = paper_citations[0]

        result.update({
            "ieee": first["ieee"],
            "apa": first["apa"],
            "mla": first["mla"],
            "harvard": first["harvard"],
        })

    return result
