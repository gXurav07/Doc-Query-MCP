"""MCP server exposing document Q&A tools."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if __package__ is None or __package__ == "":
    src_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(src_dir))

from mcp.server.fastmcp import FastMCP

from docquery_mcp.config import settings
from docquery_mcp.schemas import QueryResult

if TYPE_CHECKING:
    from docquery_mcp.answerer import ExtractiveAnswerer
    from docquery_mcp.retriever import DocumentRetriever


mcp = FastMCP("docquery-mcp")

_retriever: DocumentRetriever | None = None
_answerer: ExtractiveAnswerer | None = None


def get_retriever() -> DocumentRetriever:
    """Create the retriever only when the first query arrives."""

    global _retriever
    if _retriever is None:
        from docquery_mcp.retriever import DocumentRetriever

        _retriever = DocumentRetriever()
    return _retriever


def get_answerer() -> ExtractiveAnswerer:
    """Create the answerer only when the first query arrives."""

    global _answerer
    if _answerer is None:
        from docquery_mcp.answerer import ExtractiveAnswerer

        _answerer = ExtractiveAnswerer()
    return _answerer


def serialize_result(result: QueryResult) -> dict[str, Any]:
    """Convert a QueryResult dataclass into an MCP-friendly dictionary."""

    return asdict(result)


ANSWERING_INSTRUCTIONS = (
    "Answer using only the retrieved_context. Cite document_name and page_number. "
    "If the context is insufficient or weakly relevant, make up to 2 additional "
    "query_documents calls with rewritten/search-expanded questions before giving "
    "the final answer. If the context is still insufficient, say the indexed "
    "documents do not contain enough information."
)


def log_startup_progress(message: str) -> None:
    """Write startup progress to stderr so stdout remains valid MCP transport."""

    print(f"[docquery-mcp] {message}", file=sys.stderr, flush=True)


def build_index_on_startup() -> None:
    """Parse PDFs and rebuild the search index before serving MCP requests."""

    log_startup_progress("Building document index before server startup...")
    from docquery_mcp.ingest import ingest_documents

    result = ingest_documents(reset_index=True, progress=log_startup_progress)
    log_startup_progress(
        "Index ready: "
        f"{result.pdf_count} PDF(s), "
        f"{result.page_count} page(s), "
        f"{result.chunk_count} chunk(s)"
    )


@mcp.tool()
def query_documents(question: str, top_k: int = settings.default_top_k) -> dict:
    """
    Retrieve relevant PDF excerpts for answering a user question.

    The caller should synthesize the final answer using only the returned excerpts.
    Every factual claim should cite the document_name and page_number from the
    retrieved_context.
    If the retrieved excerpts do not contain enough evidence, the caller should
    say that the indexed documents do not provide enough information.
    """

    retrieved_chunks = get_retriever().retrieve(question=question, top_k=top_k)
    result = get_answerer().answer(question=question, retrieved_chunks=retrieved_chunks)
    payload = serialize_result(result)
    payload["retrieved_context"] = payload["sources"]
    payload["answering_instructions"] = ANSWERING_INSTRUCTIONS
    return payload


def main() -> None:
    """Run the MCP server over stdio for local MCP clients."""

    try:
        build_index_on_startup()
        log_startup_progress("Starting MCP server over stdio...")
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        print("DocQuery MCP server stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
