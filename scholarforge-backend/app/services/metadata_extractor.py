import re
import httpx
import logging
from typing import Optional

from app.core.config import settings
from app.services.external_apis.crossref import get_crossref_metadata

logger = logging.getLogger(__name__)

# Lazy load spaCy model
_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            logger.info("Loading spaCy model...")
            _nlp = spacy.load("en_core_web_sm")
        except ImportError:
            logger.warning("spaCy not installed, ignoring...")
            _nlp = None
        except OSError:
            import spacy
            logger.warning("en_core_web_sm not found. Downloading...")
            spacy.cli.download("en_core_web_sm") # type: ignore
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

async def extract_metadata(first_page_text: str, full_text: str) -> dict:
    """
    Extracts metadata using GROBID (if enabled) or fallback regex/NLP.
    Tries to enrich with CrossRef if a DOI is found.
    """
    metadata = {
        "title": None,
        "authors": [],
        "publication_year": None,
        "venue": None,
        "doi": None,
        "abstract": None
    }
    
    # 1. Try to find a DOI in the text
    doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', first_page_text, re.IGNORECASE)
    if doi_match:
        doi = doi_match.group(1)
        # Clean trailing punctuation
        doi = doi.rstrip('.,;()')
        metadata["doi"] = doi
        
        # Enrich with CrossRef
        crossref_data = await get_crossref_metadata(doi)
        if crossref_data:
            return crossref_data
            
    # 2. If GROBID is enabled, we could call its API here
    # Since GROBID returns XML (TEI format), parsing it requires additional logic
    # For now, we fallback to NLP
    
    if not metadata["title"]:
        metadata.update(_extract_via_nlp(first_page_text))
        
    return metadata

def _extract_via_nlp(text: str) -> dict:
    """Fallback metadata extraction using spaCy and regex."""
    nlp = get_nlp()
    if nlp:
        doc = nlp(text[:2000])  # Process only the first part of the document
        
        # Authors heuristic: ORG or PERSON entities in the first few lines
        authors = []
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                authors.append(ent.text)
                if len(authors) >= 5: # Limit to avoid false positives
                    break
    else:
        authors = []
        
    # Title heuristic: First non-empty, reasonably long sentence or line
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    title = None
    for line in lines:
        if 10 < len(line) < 200:
            title = line
            break
            
    # Year heuristic: Find a 4-digit number that looks like a recent year
    year = None
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text[:1000])
    if year_match:
        year = int(year_match.group(1))
        
    # Abstract heuristic
    abstract = None
    abstract_match = re.search(r'Abstract[—\.\s-]+(.*?)(?:Introduction|1\.\s+Introduction)', text, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        
    return {
        "title": title,
        "authors": list(set(authors)), # Deduplicate
        "publication_year": year,
        "abstract": abstract
    }
