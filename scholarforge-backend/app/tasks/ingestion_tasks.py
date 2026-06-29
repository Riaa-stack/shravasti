import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import async_session_maker
from app.models.paper import Paper, PaperStatus
from app.models.chunk import PaperChunk
from app.services.pdf_processor import extract_text_from_pdf
from app.services.metadata_extractor import extract_metadata
from app.services.chunking import chunk_paper
from app.services.embeddings import generate_embeddings
from app.db.chroma import add_chunks
from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)

async def process_paper_task(paper_id: str) -> None:
    logger.info(f"Starting async processing for paper {paper_id}")
    
    async with async_session_maker() as session:
        # 1. Fetch paper
        stmt = select(Paper).where(Paper.id == uuid.UUID(paper_id))
        result = await session.execute(stmt)
        paper = result.scalar_one_or_none()
        
        if not paper:
            logger.error(f"Paper {paper_id} not found in database.")
            return
            
        try:
            # Update status
            paper.status = PaperStatus.processing
            session.add(paper)
            await session.commit()
            
            # 2. Extract text
            pages = extract_text_from_pdf(paper.file_path)
            if not pages:
                raise ValueError("No text could be extracted from PDF")
                
            paper.page_count = len(pages)
            
            # 3. Extract Metadata
            first_page_text = pages[0]["text"] if pages else ""
            full_text = " ".join([p["text"] for p in pages])
            metadata = await extract_metadata(first_page_text, full_text)
            
            # Update paper metadata
            if metadata.get("title") and not paper.title.endswith(".pdf"):
                paper.title = metadata["title"]
            if metadata.get("authors"):
                paper.authors = metadata["authors"]
            if metadata.get("publication_year"):
                paper.publication_year = metadata["publication_year"]
            if metadata.get("venue"):
                paper.venue = metadata["venue"]
            if metadata.get("doi"):
                paper.doi = metadata["doi"]
            if metadata.get("abstract"):
                paper.abstract = metadata["abstract"]
                
            session.add(paper)
            await session.commit()
            
            # 4. Chunking
            chunks = chunk_paper(pages)
            
            # 5. Embeddings
            texts_to_embed = [c["content"] for c in chunks]
            embeddings = generate_embeddings(texts_to_embed)
            
            # 6. Store in ChromaDB
            vector_ids = add_chunks(
                user_id=str(paper.user_id),
                paper_id=str(paper.id),
                chunks=chunks,
                embeddings=embeddings
            )
            
            # 7. Store chunks in Postgres
            paper_chunks_db = []
            for i, chunk in enumerate(chunks):
                db_chunk = PaperChunk(
                    paper_id=paper.id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    section_title=chunk.get("section_title"),
                    page_number=chunk.get("page_number"),
                    chroma_vector_id=vector_ids[i]
                )
                paper_chunks_db.append(db_chunk)
                
            session.add_all(paper_chunks_db)
            
            # 8. Knowledge Graph Sync
            from app.services.knowledge_graph_builder import build_graph_for_paper
            await build_graph_for_paper(paper.id, metadata, chunks)
            
            # 9. Mark complete
            paper.status = PaperStatus.processed
            session.add(paper)
            await session.commit()
            
            # Emit WebSocket progress update
            await manager.broadcast({
                "paper_id": paper_id,
                "status": "processed",
                "message": "Paper processed successfully",
                "progress": 100
            }, paper_id)
            
            logger.info(f"Successfully processed paper {paper_id}")
            
        except Exception as e:
            logger.exception(f"Error processing paper {paper_id}: {e}")
            paper.status = PaperStatus.failed
            session.add(paper)
            await session.commit()
            
            # Emit WebSocket error
            await manager.broadcast({
                "paper_id": paper_id,
                "status": "failed",
                "message": str(e),
                "progress": 0
            }, paper_id)
