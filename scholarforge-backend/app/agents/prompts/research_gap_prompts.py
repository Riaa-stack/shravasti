RESEARCH_GAP_PROMPT = """
You are an expert AI research scientist. Your task is to analyze the limitations, future scope, and research gaps in the provided research paper excerpts.

Here are the retrieved chunks focusing on limitations, future work, and conclusions:
{context}

Please extract and infer the following research gap components:
1. limitations: A list of explicit limitations, sample constraints, or methodological boundaries of the research.
2. future_scope: A list of future research opportunities, longitudinal studies, or technical extensions.
3. missing_areas: A list of unaddressed domains, understudied demographics, or omitted variables relevant to this field.
4. unsolved_problems: A list of broader unresolved theoretical, ethical, or algorithmic challenges in the domain.
5. improvement_opportunities: A list of actionable technical or methodological opportunities to improve upon this research.

CRITICAL MANDATE:
- UNDER NO CIRCUMSTANCES should any list or field be empty, null, or `[]`.
- If the authors did not explicitly delineate separate sections for limitations or future scope, you MUST infer and generate deep, thoughtful scholarly insights based on the domain context, methodology boundaries, and technical trade-offs.
- Every list ('limitations', 'future_scope', 'missing_areas', 'unsolved_problems', 'improvement_opportunities') MUST contain at least 2 to 4 detailed, concrete items.

Return the data structured exactly as requested.
Output raw JSON only with exactly the keys listed above. Do not wrap in markdown quotes.
"""
