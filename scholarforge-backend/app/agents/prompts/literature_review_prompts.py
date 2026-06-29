LITERATURE_REVIEW_PROMPT = """
You are an expert AI research assistant. Your task is to write a comprehensive literature review based on the following research paper excerpts.

If multiple papers are provided, you must also provide a comparative review that contrasts their approaches and findings.

Here are the retrieved paper chunks:
{context}

Please extract and summarize the following:
1. summary: A high-level abstract of the provided papers.
2. key_findings: A list of the most important findings.
3. contributions: A list of the primary contributions made by the authors.
4. comparative_review: If multiple papers are present, a comparison of their methodologies, results, and perspectives. If only one paper is present, you may leave this null.

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not wrap it in markdown blockquotes like ```json. Output raw JSON only with exactly the keys listed above.
"""
