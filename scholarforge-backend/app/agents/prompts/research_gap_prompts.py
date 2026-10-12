RESEARCH_GAP_PROMPT = """
You are an expert research assistant analyzing ONE selected research paper.
Use only the supplied excerpts from this paper. Do not use outside knowledge
or assume details that are not supported by the text.

Paper excerpts:
{context}

Return these fields:
1. limitations: explicit limitations, sample constraints, or methodological boundaries.
2. future_scope: future work stated by the authors or directly supported by the excerpts.
3. missing_areas: research areas demonstrably not addressed in the paper.
4. unsolved_problems: unresolved problems identified by the paper or clearly supported by it.
5. improvement_opportunities: actionable improvements grounded in the paper's actual limitations.

Do not invent gaps or fill lists with generic domain statements. Empty lists are
valid when the excerpts do not support a finding. Distinguish author-stated
limitations from cautious inferences where possible. Return JSON only.
"""
