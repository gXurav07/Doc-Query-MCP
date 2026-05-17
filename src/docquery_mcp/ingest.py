"""Document ingestion pipeline.

Ingestion turns PDFs into searchable vectors:

PDF pages -> text chunks -> embeddings -> ChromaDB collection
"""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from docquery_mcp.chunking import chunk_pages
from docquery_mcp.config import settings
from docquery_mcp.embeddings import EmbeddingModel
from docquery_mcp.pdf_loader import load_pdf_directory
from docquery_mcp.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class IngestionResult:
    """Summary of one indexing run."""

    pdf_count: int
    page_count: int
    chunk_count: int
    index_dir: Path


def ingest_documents(
    pdf_dir: Path = settings.pdf_dir,
    index_dir: Path = settings.index_dir,
    reset_index: bool = True,
    progress: Callable[[str], None] | None = None,
) -> IngestionResult:
    """Parse PDFs, create embeddings, and persist them in ChromaDB."""

    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory does not exist: {pdf_dir}")

    pdf_paths = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_paths:
        raise ValueError(f"No PDF files found in: {pdf_dir}")

    index_dir.mkdir(parents=True, exist_ok=True)

    report(f"Found {len(pdf_paths)} PDF file(s) in {pdf_dir}")
    report("Extracting page text from PDFs...")
    pages = load_pdf_directory(pdf_dir)
    report(f"Extracted text from {len(pages)} page(s)")

    report(
        f"Chunking pages with size={settings.chunk_size}, overlap={settings.chunk_overlap}..."
    )
    chunks = chunk_pages(
        pages=pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    report(f"Created {len(chunks)} searchable chunk(s)")

    report(f"Loading embedding model: {settings.embedding_model_name}")
    embedding_model = EmbeddingModel()
    report(f"Creating embeddings for {len(chunks)} chunk(s)...")
    embeddings = embedding_model.embed_chunks(chunks)
    report("Embeddings created")

    report(f"Opening Chroma index at {index_dir}")
    vector_store = ChromaVectorStore(persist_dir=str(index_dir))
    if reset_index:
        report("Resetting existing Chroma collection...")
        vector_store.reset()

    report("Writing chunks and embeddings to Chroma...")
    vector_store.add_chunks(chunks, embeddings)
    report("Chroma index updated")

    return IngestionResult(
        pdf_count=len(pdf_paths),
        page_count=len(pages),
        chunk_count=len(chunks),
        index_dir=index_dir,
    )
