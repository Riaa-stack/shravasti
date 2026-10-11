import logging
import uuid
import re
from typing import Any
from sqlalchemy import select
from app.db.postgres import async_session_maker
from app.models.knowledge_graph import GraphNode, GraphEdge
from app.services.external_apis.semantic_scholar import get_semantic_scholar_related

logger = logging.getLogger(__name__)

KNOWN_METHODOLOGIES = [
    "deep learning", "machine learning", "transformer", "neural network",
    "convolutional neural network", "recurrent neural network", "reinforcement learning",
    "supervised learning", "unsupervised learning", "self-supervised learning",
    "transfer learning", "large language model", "empirical study", "statistical analysis",
    "comparative analysis", "survey", "graph neural network", "bayesian optimization",
    "monte carlo simulation", "attention mechanism", "fine-tuning", "prompt engineering",
    "contrastive learning", "ablation study", "qualitative analysis", "quantitative analysis"
]

KNOWN_DOMAINS = [
    "artificial intelligence", "natural language processing", "computer vision",
    "data science", "robotics", "bioinformatics", "cybersecurity", "human-computer interaction",
    "software engineering", "distributed systems", "information retrieval", "speech recognition",
    "healthcare ai", "machine translation", "knowledge representation"
]

def slugify(text: str) -> str:
    """Generate a clean identifier from a text string."""
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', text.strip().lower()).strip('_')
    return clean[:60] if clean else "unknown"

async def _upsert_node(session: Any, node_id: str, label: str, properties: dict) -> None:
    stmt = select(GraphNode).where(GraphNode.id == node_id)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        existing.label = label
        existing.properties = properties
    else:
        new_node = GraphNode(id=node_id, label=label, properties=properties)
        session.add(new_node)

async def _upsert_edge(session: Any, source_id: str, target_id: str, edge_type: str) -> None:
    stmt = select(GraphEdge).where(
        GraphEdge.source_id == source_id,
        GraphEdge.target_id == target_id,
        GraphEdge.type == edge_type
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if not existing:
        new_edge = GraphEdge(source_id=source_id, target_id=target_id, type=edge_type)
        session.add(new_edge)

def extract_entities_from_text(text: str, metadata: dict) -> dict[str, list[str]]:
    """Extract methodologies, domains, concepts, and datasets from paper text and metadata."""
    lower_text = text.lower()
    
    # Methodologies
    methods_found = []
    for method in KNOWN_METHODOLOGIES:
        if method in lower_text:
            methods_found.append(method.title())
            if len(methods_found) >= 5:
                break
    if not methods_found:
        methods_found = ["Empirical Evaluation", "Statistical Analysis"]

    # Domains / Topics
    domains_found = []
    for domain in KNOWN_DOMAINS:
        if domain in lower_text:
            domains_found.append(domain.title())
            if len(domains_found) >= 3:
                break
    category = metadata.get("category")
    if category and category.title() not in domains_found:
        domains_found.insert(0, category.title())
    if not domains_found:
        domains_found = ["Artificial Intelligence"]

    # Concepts / Keywords
    concepts = []
    abstract = metadata.get("abstract") or text[:1500]
    words = re.findall(r'\b[A-Za-z]{4,}\b', abstract)
    stop_words = {"this", "that", "with", "from", "were", "have", "been", "their", "paper", "which", "study", "using", "these", "result", "proposed", "method"}
    freq = {}
    for w in words:
        w_lower = w.lower()
        if w_lower not in stop_words and len(w_lower) > 3:
            freq[w_lower] = freq.get(w_lower, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    concepts = [w.title() for w, _ in sorted_words[:6]]
    if not concepts:
        concepts = ["Research Methodology", "Empirical Findings"]

    # Datasets
    dataset_matches = re.findall(r'\b(?:dataset|benchmark|corpus)\b\s*:\s*([A-Za-z0-9_-]+)', text, re.IGNORECASE)
    common_datasets = ["ImageNet", "GLUE", "SQuAD", "MNIST", "CIFAR-10", "CoNLL", "WikiText"]
    datasets_found = []
    for ds in common_datasets:
        if ds.lower() in lower_text:
            datasets_found.append(ds)
    datasets_found.extend([d.strip() for d in dataset_matches if len(d.strip()) > 2])
    datasets_found = list(set(datasets_found))[:3]

    return {
        "methods": methods_found,
        "domains": domains_found,
        "concepts": concepts,
        "datasets": datasets_found
    }

async def build_graph_for_paper(
    paper_id: uuid.UUID,
    metadata: dict,
    chunks: list[dict],
    session: Any = None
) -> None:
    """
    Upserts nodes and relationships for a processed paper into knowledge graph tables.
    Extracts Paper, Author, Methodology, Domain, Concept, and Dataset nodes.
    Interconnects with existing nodes across papers.
    """
    try:
        combined_text = (metadata.get("abstract") or "") + " " + " ".join([c.get("content", "") for c in chunks[:10]])
        entities = extract_entities_from_text(combined_text, metadata)

        async def _populate(db_sess: Any):
            paper_node_id = f"paper_{paper_id}"
            await _upsert_node(
                db_sess,
                node_id=paper_node_id,
                label="Paper",
                properties={
                    "title": metadata.get("title", "Untitled Paper"),
                    "year": metadata.get("publication_year"),
                    "doi": metadata.get("doi"),
                    "venue": metadata.get("venue"),
                    "category": metadata.get("category"),
                    "paper_id": str(paper_id),
                }
            )

            # 2. Authors
            authors = metadata.get("authors") or []
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(",") if a.strip()]
            for author_name in authors:
                clean_author = str(author_name).strip()
                if not clean_author:
                    continue
                author_node_id = f"author_{slugify(clean_author)}"
                await _upsert_node(
                    db_sess,
                    node_id=author_node_id,
                    label="Author",
                    properties={"name": clean_author}
                )
                await _upsert_edge(
                    db_sess,
                    source_id=author_node_id,
                    target_id=paper_node_id,
                    edge_type="AUTHORED"
                )

            # 3. Methodologies
            for method in entities["methods"]:
                method_node_id = f"method_{slugify(method)}"
                await _upsert_node(
                    db_sess,
                    node_id=method_node_id,
                    label="Methodology",
                    properties={"name": method}
                )
                await _upsert_edge(
                    db_sess,
                    source_id=paper_node_id,
                    target_id=method_node_id,
                    edge_type="USES_METHOD"
                )

            # 4. Domains / Topics
            for domain in entities["domains"]:
                domain_node_id = f"domain_{slugify(domain)}"
                await _upsert_node(
                    db_sess,
                    node_id=domain_node_id,
                    label="Domain",
                    properties={"name": domain}
                )
                await _upsert_edge(
                    db_sess,
                    source_id=paper_node_id,
                    target_id=domain_node_id,
                    edge_type="IN_DOMAIN"
                )

            # 5. Concepts / Keywords
            for concept in entities["concepts"]:
                concept_node_id = f"concept_{slugify(concept)}"
                await _upsert_node(
                    db_sess,
                    node_id=concept_node_id,
                    label="Concept",
                    properties={"name": concept}
                )
                await _upsert_edge(
                    db_sess,
                    source_id=paper_node_id,
                    target_id=concept_node_id,
                    edge_type="EXPLORES"
                )

            # 6. Datasets
            for dataset in entities["datasets"]:
                dataset_node_id = f"dataset_{slugify(dataset)}"
                await _upsert_node(
                    db_sess,
                    node_id=dataset_node_id,
                    label="Dataset",
                    properties={"name": dataset}
                )
                await _upsert_edge(
                    db_sess,
                    source_id=paper_node_id,
                    target_id=dataset_node_id,
                    edge_type="EVALUATED_ON"
                )

            # 7. Semantic Scholar citations if DOI present
            doi = metadata.get("doi")
            if doi:
                try:
                    related = await get_semantic_scholar_related(doi)
                    if related:
                        citations = related.get("citations", [])
                        for citation_doi in citations[:5]:
                            if not citation_doi:
                                continue
                            citation_node_id = f"paper_doi_{slugify(citation_doi)}"
                            await _upsert_node(
                                db_sess,
                                node_id=citation_node_id,
                                label="Paper",
                                properties={"doi": citation_doi, "title": f"Citation {citation_doi}"}
                            )
                            await _upsert_edge(
                                db_sess,
                                source_id=paper_node_id,
                                target_id=citation_node_id,
                                edge_type="CITES"
                            )
                except Exception as e:
                    logger.debug(f"Optional citation fetch skipped: {e}")

        if session is not None:
            await _populate(session)
            await session.commit()
        else:
            async with async_session_maker() as s:
                await _populate(s)
                await s.commit()
        logger.info(f"Knowledge graph successfully built for paper {paper_id}")
    except Exception as e:
        logger.error(f"Failed to build graph for paper {paper_id}: {e}", exc_info=True)
