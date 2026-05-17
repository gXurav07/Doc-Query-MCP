"""Manual Q&A smoke test.

Run this after indexing PDFs. Type questions at the prompt and type "exit"
when you are done.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from docquery_mcp.config import settings  # noqa: E402


def main() -> None:
    """Start a small interactive question-answer loop."""

    retriever = None
    answerer = None

    print("DocQuery manual Q&A test")
    print('Ask a question, or type "exit" to stop.')
    print()

    while True:
        question = input("Question: ").strip()
        if question.lower() == "exit":
            print("Goodbye.")
            break
        if not question:
            continue

        try:
            if retriever is None or answerer is None:
                from docquery_mcp.answerer import ExtractiveAnswerer
                from docquery_mcp.retriever import DocumentRetriever

                retriever = DocumentRetriever()
                answerer = ExtractiveAnswerer()

            retrieved_chunks = retriever.retrieve(question, top_k=settings.default_top_k)
            result = answerer.answer(question, retrieved_chunks)
        except Exception as exc:
            print(f"Error: {exc}")
            print()
            continue

        print()
        print(result.answer)
        print()

        if result.sources:
            print("Sources:")
            for source in result.sources:
                print(
                    f"- {source.document_name}, page {source.page_number}, "
                    f"score {source.score:.3f}"
                )
        else:
            print("Sources: none")

        print()


if __name__ == "__main__":
    main()
