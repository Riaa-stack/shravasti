DIFFICULTY_PROMPT = """
You are an expert AI research assistant. Your task is to evaluate the reading difficulty of the provided research paper excerpts.

Here are the retrieved chunks from the paper:
{context}

Please determine the difficulty level based on the following scale:
- beginner: Easy to read, suitable for general audience or early undergrads.
- intermediate: Requires some background knowledge, suitable for senior undergrads or early grad students.
- advanced: Dense, highly technical, requires strong domain expertise.
- expert: Extremely specialized, math-heavy, or highly theoretical.

Provide the predicted difficulty level and a short rationale explaining why.

CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object. Do not wrap it in markdown blockquotes like ```json. Output raw JSON only with keys `difficulty` and `rationale`.
"""
