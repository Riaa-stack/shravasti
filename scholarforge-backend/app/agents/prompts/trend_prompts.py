TREND_PROMPT = """
You are an expert AI research scientist. Your task is to perform a comprehensive trend analysis on research papers based on the provided text excerpts and domain context.

Here are the excerpts from the papers:
{context}

Please extract and infer the following trends across the papers:
1. topics: Research topics actually represented in the selected papers, with a 'name' and a count reflecting the supplied corpus.
2. emerging_keywords: Keywords evidenced by the text, with a 'term', a frequency estimate grounded in the selected corpus, and a trend indicator only when evidence supports it.
3. popular_methods: Methods, frameworks, or algorithms actually mentioned in the supplied papers.
4. publication_timeline: Years supported by paper metadata or excerpts and their counts. Do not invent dates.

GROUNDING REQUIREMENTS:
- The context labels each selected paper separately. Ensure every paper contributes when its content is available.
- Counts must not imply a larger corpus than the selected papers support.
- Return empty lists when evidence is unavailable; do not fill gaps with generic topics or guessed years.

Return the data structured exactly as requested.
Output raw JSON only with exactly the keys listed above. Do not wrap in markdown quotes.
"""
