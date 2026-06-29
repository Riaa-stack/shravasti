RESEARCH_GAP_PROMPT = """
You are an expert AI research assistant. Your task is to analyze the limitations, future scope, and missing research areas in the provided research paper excerpts.

Here are the retrieved chunks focusing on limitations, future work, and conclusions:
{context}

Please extract and infer the following:
1. limitations: A list of the explicit limitations mentioned by the authors.
2. future_scope: A list of future work proposed by the authors.
3. missing_areas: A list of areas not addressed in the research that are relevant to the topic.
4. unsolved_problems: A list of broader unsolved problems highlighted in the text.
5. improvement_opportunities: A list of opportunities to improve upon the paper's methodology or results.

Return the data structured exactly as requested.

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not wrap it in markdown blockquotes like ```json. Output raw JSON only with exactly the keys listed above.
"""
