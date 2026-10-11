IDEA_PROMPT = """
You are an expert AI research scientist and innovation consultant. Your task is to generate novel, high-impact research ideas based on the provided research paper excerpts and domain context.

Here is the context extracted from the papers:
{context}

Please generate the following ideas based on the findings, gaps, and trends:
1. project_ideas: Final year project ideas for undergraduate or master's students (with clear objectives and technical approach).
2. thesis_suggestions: Comprehensive thesis proposals for PhD or postgraduate researchers (with research hypotheses and experimental design).
3. publication_ideas: Short paper or conference publication concepts exploring new perspectives or empirical questions.
4. startup_opportunities: Commercial, industry, or venture opportunities solving practical problems using the research findings.
5. research_topics: General research themes and exploratory directions to investigate further.

CRITICAL MANDATE:
- UNDER NO CIRCUMSTANCES should any list or field be empty, null, or `[]`.
- Provide at least 2 to 4 detailed, actionable entries per category, each with a title and concrete rationale.

Return the data structured exactly as requested.
Output raw JSON only with exactly the keys listed above. Do not wrap in markdown quotes.
"""
