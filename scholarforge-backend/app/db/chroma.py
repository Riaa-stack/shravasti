import chromadb
from chromadb.config import Settings
import uuid

from app.core.config import settings

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client

# We use a single collection for all paper chunks
# and isolate data using metadata filtering (user_id, paper_id)
COLLECTION_NAME = "paper_chunks"

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

def add_chunks(user_id: str, paper_id: str, chunks: list[dict], embeddings: list[list[float]]) -> list[str]:
    """
    Adds chunks and their embeddings to ChromaDB.
    Returns the list of generated vector IDs.
    """
    collection = get_collection()
    
    ids = []
    documents = []
    metadatas = []
    
    for idx, chunk in enumerate(chunks):
        vector_id = str(uuid.uuid4())
        ids.append(vector_id)
        documents.append(chunk["content"])
        
        # Build metadata for filtering and retrieval
        metadata = {
            "user_id": user_id,
            "paper_id": paper_id,
            "chunk_index": chunk["chunk_index"],
        }
        if chunk.get("section_title"):
            metadata["section_title"] = chunk["section_title"]
        if chunk.get("page_number") is not None:
            metadata["page_number"] = chunk["page_number"]
            
        metadatas.append(metadata)
        
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    return ids

def delete_paper_chunks(user_id: str, paper_id: str) -> None:
    """Deletes all chunks for a specific paper from ChromaDB."""
    collection = get_collection()
    collection.delete(
        where={"$and": [{"user_id": user_id}, {"paper_id": paper_id}]}
    )

def retrieve_chunks(user_id: str, paper_ids: list[str], query_embedding: list[float] = None, n_results: int = 10, section_filter: str = None) -> list[dict]:
    """Retrieves relevant chunks from ChromaDB for specific papers."""
    collection = get_collection()
    
    where_clause = {"$and": [{"user_id": user_id}]}
    if len(paper_ids) == 1:
        where_clause["$and"].append({"paper_id": paper_ids[0]})
    elif len(paper_ids) > 1:
        where_clause["$and"].append({"paper_id": {"$in": paper_ids}})
        
    if section_filter:
        where_clause["$and"].append({"section_title": {"$contains": section_filter}}) # Simple approximation
        
    if len(where_clause["$and"]) == 1:
        where_clause = where_clause["$and"][0]
        
    results = None
    if query_embedding:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
    else:
        # If no query, just get first N chunks from the paper
        results = collection.get(
            where=where_clause,
            limit=n_results
        )
        
    retrieved = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0] if query_embedding else results["documents"]
        metas = results["metadatas"][0] if query_embedding else results["metadatas"]
        
        for doc, meta in zip(docs, metas):
            retrieved.append({
                "content": doc,
                "metadata": meta
            })
            
    return retrieved
