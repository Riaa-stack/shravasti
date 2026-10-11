TREND_PROMPT = """
You are an expert AI research scientist. Your task is to perform a comprehensive trend analysis on research papers based on the provided text excerpts and domain context.

Here are the excerpts from the papers:
{context}

Please extract and infer the following trends across the papers:
1. topics: A list of key research topics across the papers, each with a 'name' (string) and an estimated 'count' (integer >= 1).
2. emerging_keywords: A list of emerging keywords, each with a 'term' (string), a 'frequency' (integer >= 1), and a 'trend' indicator ("up", "down", or "stable").
3. popular_methods: A list of commonly used methods, frameworks, or algorithms, each with a 'name' (string) and a 'count' (integer >= 1).
4. publication_timeline: A list representing publication or milestone timelines, each with a 'year' (string, e.g. "2020", "2023", "2024") and a 'count' (integer >= 1).

CRITICAL MANDATE:
- NEVER return empty lists for any field.
- If explicit timeline years or method names are sparse in the excerpts, infer the dominant methodological paradigms, contemporary keywords, and recent timeline milestones for the research domains presented.
- Provide at least 3 to 6 items for each list.

Return the data structured exactly as requested.
Output raw JSON only with exactly the keys listed above. Do not wrap in markdown quotes.
"""
