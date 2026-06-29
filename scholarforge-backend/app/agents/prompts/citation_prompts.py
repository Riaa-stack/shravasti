CITATION_PROMPT = """
You are an expert AI research assistant. Your task is to extract normalized metadata from the following text to help generate accurate citations.

Here is the extracted text from the paper (usually the first page):
{context}

Please extract the following:
1. title: The full title of the paper.
2. authors: A list of author names.
3. year: The publication year (as an integer).
4. venue: The journal, conference, or publication venue.
5. volume: The volume number (if applicable).
6. issue: The issue number (if applicable).
7. pages: The page numbers (if applicable).

If any piece of information is not found, leave it as null.

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not wrap it in markdown blockquotes like ```json. Output raw JSON only with exactly the keys listed above.
"""
