CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(text: str, filename: str, page_number: int) -> list[dict]:
    """Split text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(
                {
                    "text": chunk,
                    "filename": filename,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
            )
        start += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_index += 1
    return chunks
