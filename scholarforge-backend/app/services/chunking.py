from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_paper(pages: list[dict], chunk_size: int = 800, chunk_overlap: int = 100) -> list[dict]:
    """
    Splits the extracted pages into semantic chunks.
    Preserves page number metadata.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = []
    chunk_index = 0
    
    # Simple heuristic to track section titles
    current_section = None
    
    for page in pages:
        page_num = page["page_number"]
        text = page["text"]
        
        # Attempt to find a section title (e.g., "1. Introduction", "Abstract", "Methodology")
        # Very simple heuristic: short lines that are uppercase or start with a number
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and len(line) < 50:
                if line.isupper() or (line and line[0].isdigit() and " " in line):
                    current_section = line
                    break
                    
        page_chunks = text_splitter.split_text(text)
        
        for content in page_chunks:
            chunks.append({
                "chunk_index": chunk_index,
                "content": content,
                "page_number": page_num,
                "section_title": current_section
            })
            chunk_index += 1
            
    return chunks
