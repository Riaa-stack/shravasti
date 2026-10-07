import logging
import uuid

from sqlalchemy import select

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

        # ---------------------------------------------------------------------
        # 1. FETCH PAPER
        # ---------------------------------------------------------------------
        stmt = select(Paper).where(
            Paper.id == uuid.UUID(paper_id)
        )

        result = await session.execute(stmt)
        paper = result.scalar_one_or_none()

        if not paper:
            logger.error(
                f"Paper {paper_id} not found in database."
            )
            return

        try:

            # -----------------------------------------------------------------
            # 2. UPDATE STATUS -> PROCESSING
            # -----------------------------------------------------------------
            paper.status = PaperStatus.processing

            session.add(paper)
            await session.commit()

            # -----------------------------------------------------------------
            # 3. EXTRACT TEXT FROM PDF
            # -----------------------------------------------------------------
            pages = extract_text_from_pdf(
                paper.file_path
            )

            if not pages:
                raise ValueError(
                    "No text could be extracted from PDF"
                )

            paper.page_count = len(pages)

            # -----------------------------------------------------------------
            # 4. EXTRACT PAPER METADATA
            # -----------------------------------------------------------------
            first_page_text = (
                pages[0]["text"]
                if pages
                else ""
            )

            full_text = " ".join(
                p["text"]
                for p in pages
            )

            metadata = await extract_metadata(
                first_page_text,
                full_text
            )

            logger.info(
                "Extracted metadata for paper %s: %s",
                paper_id,
                metadata
            )

            # -----------------------------------------------------------------
            # 5. UPDATE PAPER METADATA
            # -----------------------------------------------------------------

            # IMPORTANT:
            # The uploaded filename is initially stored in paper.title.
            # Previously this code checked:
            #
            #     not paper.title.endswith(".pdf")
            #
            # which prevented the extracted title from EVER replacing
            # the filename.
            #
            # We now directly use the extracted title when available.

            extracted_title = metadata.get("title")

            if extracted_title:
                extracted_title = str(
                    extracted_title
                ).strip()

                # Do not replace the title with an empty value.
                if extracted_title:
                    paper.title = extracted_title

            # Authors
            extracted_authors = metadata.get("authors")

            if extracted_authors:
                paper.authors = extracted_authors

            # Publication year
            extracted_year = metadata.get(
                "publication_year"
            )

            if extracted_year:
                paper.publication_year = extracted_year

            # Venue / journal / conference
            extracted_venue = metadata.get("venue")

            if extracted_venue:
                paper.venue = extracted_venue

            # DOI
            extracted_doi = metadata.get("doi")

            if extracted_doi:
                paper.doi = extracted_doi

            # Abstract
            extracted_abstract = metadata.get(
                "abstract"
            )

            if extracted_abstract:
                paper.abstract = extracted_abstract

            session.add(paper)

            await session.commit()

            logger.info(
                "Updated paper metadata successfully. "
                "Paper ID=%s, title=%s, authors=%s, year=%s, "
                "venue=%s, doi=%s",
                paper_id,
                paper.title,
                paper.authors,
                paper.publication_year,
                paper.venue,
                paper.doi,
            )

            # -----------------------------------------------------------------
            # 6. CHUNKING
            # -----------------------------------------------------------------
            chunks = chunk_paper(pages)

            # -----------------------------------------------------------------
            # 7. GENERATE EMBEDDINGS
            # -----------------------------------------------------------------
            texts_to_embed = [
                c["content"]
                for c in chunks
            ]

            embeddings = generate_embeddings(
                texts_to_embed
            )

            # -----------------------------------------------------------------
            # 8. STORE CHUNKS IN CHROMADB
            # -----------------------------------------------------------------
            vector_ids = add_chunks(
                user_id=str(paper.user_id),
                paper_id=str(paper.id),
                chunks=chunks,
                embeddings=embeddings,
            )

            # -----------------------------------------------------------------
            # 9. STORE CHUNKS IN POSTGRES
            # -----------------------------------------------------------------
            paper_chunks_db = []

            for i, chunk in enumerate(chunks):

                db_chunk = PaperChunk(
                    paper_id=paper.id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    section_title=chunk.get(
                        "section_title"
                    ),
                    page_number=chunk.get(
                        "page_number"
                    ),
                    chroma_vector_id=vector_ids[i],
                )

                paper_chunks_db.append(
                    db_chunk
                )

            session.add_all(
                paper_chunks_db
            )

            # -----------------------------------------------------------------
            # 10. KNOWLEDGE GRAPH SYNC
            # -----------------------------------------------------------------
            from app.services.knowledge_graph_builder import (
                build_graph_for_paper
            )

            await build_graph_for_paper(
                paper.id,
                metadata,
                chunks,
            )

            # -----------------------------------------------------------------
            # 11. MARK PROCESSING COMPLETE
            # -----------------------------------------------------------------
            paper.status = PaperStatus.processed

            session.add(paper)

            await session.commit()

            # -----------------------------------------------------------------
            # 12. WEBSOCKET PROGRESS UPDATE
            # -----------------------------------------------------------------
            await manager.broadcast(
                {
                    "paper_id": paper_id,
                    "status": "processed",
                    "message": "Paper processed successfully",
                    "progress": 100,
                },
                paper_id,
            )

            logger.info(
                f"Successfully processed paper {paper_id}"
            )

        except Exception as e:

            logger.exception(
                f"Error processing paper {paper_id}: {e}"
            )

            # -------------------------------------------------------------
            # MARK PAPER AS FAILED
            # -------------------------------------------------------------
            paper.status = PaperStatus.failed

            session.add(paper)

            await session.commit()

            # -------------------------------------------------------------
            # WEBSOCKET ERROR
            # -------------------------------------------------------------
            await manager.broadcast(
                {
                    "paper_id": paper_id,
                    "status": "failed",
                    "message": str(e),
                    "progress": 0,
                },
                paper_id,
            )