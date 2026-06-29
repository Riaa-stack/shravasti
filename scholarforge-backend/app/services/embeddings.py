import logging
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        try:
            logger.info(f"Loading embedding model {settings.EMBEDDING_MODEL}...")
            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning(f"Failed to load {settings.EMBEDDING_MODEL}, falling back to {settings.EMBEDDING_FALLBACK_MODEL}: {e}")
            _model = SentenceTransformer(settings.EMBEDDING_FALLBACK_MODEL)
    return _model

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a list of texts.
    Returns a list of float vectors.
    """
    if not texts:
        return []
        
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    
    # SentenceTransformer returns numpy arrays, convert to lists
    return embeddings.tolist()
