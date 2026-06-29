import httpx
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_semantic_scholar_related(doi: str) -> Optional[dict]:
    """
    Fetches citation graph and related papers from Semantic Scholar.
    """
    if not settings.OPENALEX_ENABLED: # Assuming using OpenAlex fallback flag or similar
        return None
        
    # Endpoint for Paper: https://api.semanticscholar.org/graph/v1/paper/{paper_id}
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=citations,citations.externalIds,references,references.externalIds"
    headers = {}
    if settings.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                citations = []
                # Extract citing DOIs
                for cit in data.get("citations", []):
                    ext_ids = cit.get("externalIds", {})
                    if ext_ids and "DOI" in ext_ids:
                        citations.append(ext_ids["DOI"])
                return {"citations": citations}
            return None
        except Exception as e:
            logger.error(f"Semantic Scholar API error: {e}")
            return None
