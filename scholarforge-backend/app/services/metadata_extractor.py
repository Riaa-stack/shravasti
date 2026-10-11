import re
import httpx
import logging
from typing import Optional, List
import fitz  # PyMuPDF

from app.core.config import settings
from app.services.external_apis.crossref import get_crossref_metadata

logger = logging.getLogger(__name__)

# Lazy load spaCy model if available
_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = None
    return _nlp


def clean_author_candidate(name: str) -> Optional[str]:
    """Clean and validate an author name candidate."""
    if not name:
        return None
    # Strip leading markers like 'by', 'and', '&'
    name = re.sub(r'^(?:by|and|&)\s+', '', name, flags=re.IGNORECASE).strip()
    # Strip emails and URLs
    name = re.sub(r'[\w\.-]+@[\w\.-]+', '', name).strip()
    name = re.sub(r'https?://\S+', '', name).strip()
    # Strip trailing footnote symbols, numbers, asterisks
    name = re.sub(r'[\d\*\†\‡\§\©\*]+$', '', name).strip()
    # Strip academic credentials / degree suffixes often trailing names
    name = re.sub(r'\b(MD|PhD|FASGE|PA-C|MS|BS|MA|MBBS|FRCP|MSc|BSc)\b', '', name).strip()
    # Clean edge punctuation
    name = re.sub(r'^[,\s\-:]+|[,\s\-:]+$', '', name).strip()

    # Exclude common affiliations or stop words
    stop_words = {
        'university', 'institute', 'department', 'school', 'faculty', 'college', 'hospital',
        'center', 'centre', 'laboratory', 'division', 'press', 'springer', 'elsevier', 'wiley',
        'nature', 'ieee', 'acm', 'abstract', 'introduction', 'review', 'article', 'editor',
        'correspondence', 'received', 'accepted', 'copyright', 'vol', 'volume', 'issue', 'page'
    }
    name_lower = name.lower()
    if any(sw in name_lower for sw in stop_words):
        return None

    words = name.split()
    if 2 <= len(words) <= 4:
        valid_words = [w for w in words if w.lower() not in ['de', 'van', 'von', 'der', 'la', 'le', 'da', 'di']]
        if valid_words and all(w[0].isupper() for w in valid_words if len(w) > 1):
            return name
    return None


def extract_authors_from_doc(doc: Optional[fitz.Document], first_page_text: str) -> List[str]:
    """
    Extract authors with high accuracy by analyzing PyMuPDF text spans
    (excluding superscripts/footnotes), doc metadata, and text heuristics.
    """
    authors = []

    # 1. Structural extraction from page 0 text spans (filters out superscripts cleanly)
    if doc is not None and len(doc) > 0:
        try:
            page0 = doc[0]
            blocks = page0.get_text('dict').get('blocks', [])
            clean_lines = []
            found_abstract = False

            for b in blocks:
                if 'lines' not in b or found_abstract:
                    continue
                for l in b['lines']:
                    parts = []
                    for s in l['spans']:
                        flags = s.get('flags', 0)
                        size = s.get('size', 12)
                        # Skip superscripts: flags bit 0 or small font size
                        if (flags & 1) or size < 8.5:
                            continue
                        parts.append(s.get('text', ''))
                    line_str = ''.join(parts).strip()
                    if not line_str:
                        continue
                    if re.match(r'^(?:abstract|a\s+b\s+s\s+t\s+r\s+a\s+c\s+t|introduction|1\.\s+introduction)\b', line_str, re.IGNORECASE):
                        found_abstract = True
                        break
                    clean_lines.append(line_str)

            skip_kw = ['university', 'institute', 'department', 'school', 'faculty', 'college',
                       'hospital', 'journal', 'volume', 'issue', 'issn', 'doi:', 'http', '@',
                       'correspondence', 'received', 'accepted', 'copyright', 'editor', 'press']

            # Lines between title (line 0/1) and abstract often contain authors
            for line in clean_lines[1:]:
                if any(k in line.lower() for k in skip_kw):
                    continue
                tokens = re.split(r'[,;]|\s+and\s+|\s*&\s*', line)
                for tok in tokens:
                    cand = clean_author_candidate(tok)
                    if cand and cand.lower() not in [a.lower() for a in authors]:
                        authors.append(cand)
            if authors:
                return authors
        except Exception as e:
            logger.debug(f"Span extraction error: {e}")

    # 2. Check PDF Document Metadata author field
    if doc is not None:
        meta_author = doc.metadata.get('author', '').strip()
        generic = ['word', 'microsoft', 'acrobat', 'distiller', 'latex', 'author', 'unknown', 'admin', 'user', 'untitled', 'temp']
        if meta_author and not any(g in meta_author.lower() for g in generic):
            tokens = re.split(r'[,;]|\s+and\s+', meta_author)
            for tok in tokens:
                cand = clean_author_candidate(tok)
                if cand and cand.lower() not in [a.lower() for a in authors]:
                    authors.append(cand)
            if authors:
                return authors

    # 3. Fallback to raw first_page_text lines before Abstract
    match = re.search(r'^(.*?)(?:\n\s*(?:Abstract|ABSTRACT|A B S T R A C T|Introduction|1\.\s+Introduction))', first_page_text, re.DOTALL | re.MULTILINE)
    pre_abstract = match.group(1) if match else first_page_text[:1500]
    lines = [l.strip() for l in pre_abstract.split('\n') if l.strip()]
    skip_kw = ['university', 'institute', 'department', 'school', 'faculty', 'college',
               'hospital', 'journal', 'volume', 'issue', 'issn', 'doi:', 'http', '@',
               'correspondence', 'received', 'accepted', 'copyright', 'editor', 'press']
    for line in lines[1:]:
        if any(k in line.lower() for k in skip_kw):
            continue
        tokens = re.split(r'[,;]|\s+and\s+|\s*&\s*', line)
        for tok in tokens:
            cand = clean_author_candidate(tok)
            if cand and cand.lower() not in [a.lower() for a in authors]:
                authors.append(cand)

    # 4. SpaCy NER fallback if installed
    if not authors:
        nlp = get_nlp()
        if nlp:
            doc_nlp = nlp(first_page_text[:2000])
            for ent in doc_nlp.ents:
                if ent.label_ == "PERSON":
                    cand = clean_author_candidate(ent.text)
                    if cand and cand.lower() not in [a.lower() for a in authors]:
                        authors.append(cand)
                    if len(authors) >= 5:
                        break

    return authors


def extract_title(doc: Optional[fitz.Document], first_page_text: str) -> Optional[str]:
    """Extract paper title, accounting for multi-line titles with subtitles."""
    # 1. From PDF spans
    if doc is not None and len(doc) > 0:
        try:
            page0 = doc[0]
            blocks = page0.get_text('dict').get('blocks', [])
            candidate_lines = []
            for b in blocks:
                if 'lines' not in b:
                    continue
                for l in b['lines']:
                    parts = [s.get('text', '') for s in l['spans'] if not (s.get('flags', 0) & 1) and s.get('size', 12) >= 8.5]
                    line_str = ''.join(parts).strip()
                    if line_str and not re.match(r'^(?:abstract|a\s+b\s+s\s+t\s+r\s+a\s+c\s+t|introduction)\b', line_str, re.IGNORECASE):
                        candidate_lines.append(line_str)
                    if len(candidate_lines) >= 4:
                        break
                if len(candidate_lines) >= 4:
                    break

            # Filter out top banners like 'REVIEW ARTICLE' or 'ORIGINAL PAPER'
            banner_labels = {'review article', 'original research', 'original article', 'research article', 'working paper', 'conference paper'}
            lines_to_check = [c for c in candidate_lines if c.lower() not in banner_labels]

            if lines_to_check:
                t0 = lines_to_check[0]
                # If title ends with ':' or '-' or is short, check next line for subtitle
                if (t0.endswith((':', '-', '—')) or len(t0) < 45) and len(lines_to_check) > 1:
                    t1 = lines_to_check[1]
                    # Make sure t1 is not an institution or author listing
                    if not any(k in t1.lower() for k in ['university', 'department', 'institute', 'hospital', 'school', '@', 'email']):
                        return f"{t0.rstrip(':- ')}: {t1}".strip()
                return t0
        except Exception as e:
            logger.debug(f"Error extracting title from spans: {e}")

    # 2. Check doc.metadata title
    if doc is not None:
        meta_title = doc.metadata.get('title', '').strip()
        generic_patterns = [r'\.docx?$', r'\.pdf$', r'^microsoft word', r'^untitled', r'^input']
        if meta_title and not any(re.search(pat, meta_title, re.IGNORECASE) for pat in generic_patterns):
            if len(meta_title) > 5:
                return meta_title

    # 3. Fallback to raw text
    lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
    banner_labels = {'review article', 'original research', 'original article', 'research article', 'working paper', 'conference paper'}
    for i, line in enumerate(lines):
        if line.lower() in banner_labels:
            continue
        if 10 < len(line) < 200:
            if (line.endswith((':', '-', '—')) or len(line) < 40) and i + 1 < len(lines):
                next_line = lines[i + 1]
                if 5 < len(next_line) < 150 and not any(k in next_line.lower() for k in ['university', '@', 'abstract']):
                    return f"{line.rstrip(':- ')}: {next_line}".strip()
            return line

    return None


async def extract_metadata(first_page_text: str, full_text: str, file_path: Optional[str] = None) -> dict:
    """
    Extracts metadata using CrossRef (if DOI found), PyMuPDF document structural spans,
    document metadata, and robust regex fallbacks.
    """
    metadata = {
        "title": None,
        "authors": [],
        "publication_year": None,
        "venue": None,
        "doi": None,
        "abstract": None
    }

    doc = None
    if file_path:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.warning(f"Could not open PDF file {file_path} with fitz: {e}")

    # 1. Search for DOI in first_page_text and PDF metadata
    doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', first_page_text, re.IGNORECASE)
    if not doi_match and doc is not None:
        subject = doc.metadata.get('subject', '') + ' ' + doc.metadata.get('keywords', '')
        doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', subject, re.IGNORECASE)

    if doi_match:
        doi = doi_match.group(1).rstrip('.,;()')
        metadata["doi"] = doi

        # Enrich with CrossRef
        crossref_data = await get_crossref_metadata(doi)
        if crossref_data:
            for k, v in crossref_data.items():
                if v:
                    metadata[k] = v

    # 2. Extract / fill in Title if not set by CrossRef
    if not metadata["title"]:
        metadata["title"] = extract_title(doc, first_page_text)

    # 3. Extract / fill in Authors if not set by CrossRef
    if not metadata.get("authors"):
        metadata["authors"] = extract_authors_from_doc(doc, first_page_text)

    # 4. Extract / fill in Year
    if not metadata.get("publication_year"):
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', first_page_text[:1200])
        if year_match:
            metadata["publication_year"] = int(year_match.group(1))
        elif doc is not None:
            cdate = doc.metadata.get('creationDate', '')
            cdate_match = re.search(r'D:(20\d{2}|19\d{2})', cdate)
            if cdate_match:
                metadata["publication_year"] = int(cdate_match.group(1))

    # 5. Extract Abstract
    if not metadata.get("abstract"):
        abstract_match = re.search(
            r'(?:Abstract|ABSTRACT|A B S T R A C T)[\s—\.\-:]+(.*?)(?:\n\s*(?:Introduction|1\.\s+Introduction|Keywords|INDEX TERMS)\b)',
            full_text[:4000],
            re.IGNORECASE | re.DOTALL
        )
        if abstract_match:
            metadata["abstract"] = abstract_match.group(1).strip()

    if doc is not None:
        try:
            doc.close()
        except Exception:
            pass

    return metadata
