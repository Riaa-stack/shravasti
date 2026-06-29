import httpx
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_crossref_metadata(doi: str) -> Optional[dict]:
    if not settings.CROSSREF_ENABLED:
        return None
        
    url = f"https://api.crossref.org/works/{doi}"
    headers = {}
    if settings.CROSSREF_MAILTO:
        headers["User-Agent"] = f"ScholarForgeAI/0.1.0 (mailto:{settings.CROSSREF_MAILTO})"
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                item = data.get("message", {})
                
                # Extract key fields
                title = item.get("title", [""])[0] if item.get("title") else None
                authors = []
                for author in item.get("author", []):
                    if "given" in author and "family" in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif "family" in author:
                        authors.append(author["family"])
                        
                published = item.get("published-print", item.get("published-online", {}))
                year = None
                if "date-parts" in published and published["date-parts"]:
                    year = published["date-parts"][0][0]
                    
                venue = item.get("container-title", [""])[0] if item.get("container-title") else None
                
                return {
                    "title": title,
                    "authors": authors,
                    "publication_year": year,
                    "venue": venue,
                    "doi": doi
                }
            return None
        except Exception as e:
            logger.error(f"CrossRef API error: {e}")
            return None
