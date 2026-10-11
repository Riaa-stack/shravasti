METHODOLOGY_PROMPT = """
You are an expert AI research scientist. Your task is to analyze the methodology of the provided research paper excerpts.

Here are the retrieved chunks focusing on methodologies, datasets, algorithms, and experimental setup:
{context}

Please extract and infer the following methodology components for the paper:
1. algorithms: A list of algorithms, mathematical techniques, procedural steps, or analytical methods used or discussed.
2. models: A list of computational architectures, neural models, or theoretical/conceptual frameworks utilized.
3. datasets: A list of datasets, literature corpora, survey cohorts, or empirical samples analyzed.
4. evaluation_metrics: A list of evaluation metrics, statistical tests, or validation criteria applied.
5. experimental_setup: A detailed description of the experimental environment, empirical methodology, study protocol, or analytical pipeline.

CRITICAL MANDATE:
- UNDER NO CIRCUMSTANCES should any list or field be empty, null, or `[]`.
- If the paper is a survey, review, conceptual work, or qualitative study where explicit benchmark training algorithms or datasets are not explicitly named, you MUST infer and generate the underlying analytical algorithms, theoretical modeling paradigms, literature corpora, and evaluation criteria that are standard and appropriate for the paper's subject matter.
- Every list ('algorithms', 'models', 'datasets', 'evaluation_metrics') MUST contain at least 2 to 4 concrete, descriptive items.
- 'experimental_setup' must be a comprehensive paragraph describing the procedural or experimental methodology.

Return the data structured exactly as requested.
Output raw JSON only with exactly the keys listed above. Do not wrap in markdown quotes.
"""
