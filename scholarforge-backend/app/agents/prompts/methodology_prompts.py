METHODOLOGY_PROMPT = """
You are an expert research assistant extracting methodology from ONE selected
research paper. Use only the supplied excerpts; do not infer that a method,
dataset, algorithm, or metric was used unless the text supports that claim.

Paper excerpts:
{context}

Return these fields:
1. algorithms: algorithms or analytical techniques actually used or discussed.
2. models: models, architectures, or frameworks actually used or discussed.
3. datasets: datasets, literature corpora, cohorts, or samples named in the text.
4. evaluation_metrics: evaluation metrics or validation criteria actually applied.
5. experimental_setup: describe the reported setup; state when the excerpts do not specify it.

Do not invent standard methods to fill empty fields. Empty lists and an empty
experimental_setup are valid when evidence is unavailable. Return JSON only.
"""
