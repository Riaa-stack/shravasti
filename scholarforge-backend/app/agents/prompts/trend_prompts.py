TREND_PROMPT = """
You are an expert AI research assistant. Your task is to perform a trend analysis on a collection of research papers based on the provided text excerpts and metadata.

Here are the excerpts from the papers:
{context}

Please extract and aggregate the following trends:
1. topics: A list of key research topics across the papers, each with a 'name' and an estimated 'count' or weight based on prevalence.
2. emerging_keywords: A list of emerging keywords, each with a 'term', a 'frequency' count, and a 'trend' indicator ("up", "down", "stable").
3. popular_methods: A list of the most commonly used methods or algorithms, each with a 'name' and a 'count'.
4. publication_timeline: A list representing the timeline of publications, each with a 'year' and a 'count'.

Return the data structured exactly as requested.

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not wrap it in markdown blockquotes like ```json. Output raw JSON only with exactly the keys listed above.
"""
