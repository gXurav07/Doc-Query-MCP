# DocQuery MCP

DocQuery MCP is a local Model Context Protocol server that answers natural language questions over a folder of PDF documents. On startup, it parses the PDFs, rebuilds a ChromaDB index, and exposes a `query_documents` MCP tool with source citations.

The implementation is intentionally local-first: no hosted vector database, no required LLM API key, and no cloud deployment needed.

## Tech Stack

- **Language:** Python 3.11+
- **MCP framework:** `mcp` Python SDK with FastMCP
- **PDF parsing:** PyMuPDF
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vector store:** ChromaDB persistent local store
- **Answering:** extractive grounded answerer using retrieved document chunks
- **Tests:** pytest

## Setup

1. Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the project.

```bash
pip install -e ".[dev]"
```

3. Put the provided PDFs in:

```text
data/pdfs/
```

4. Run tests.

```bash
pytest
```

5. Start the MCP server.

```bash
python -m docquery_mcp.server
```

The server rebuilds the document index during startup. The first run may take longer because `sentence-transformers` downloads and caches the embedding model.

For MCP clients that require a single executable command, use:

```bash
scripts/run_mcp_server.sh
```

## Optional Manual QA

You can test retrieval without an MCP client:

```bash
python scripts/build_index.py
python scripts/qa_loop.py
```

Type a question, then type `exit` to stop.

## Architecture

```text
data/pdfs/*.pdf
    |
    v
pdf_loader.py
    Extract page-level text with document name and page number
    |
    v
chunking.py
    Split page text into overlapping searchable chunks
    |
    v
embeddings.py
    Convert chunks and questions into normalized embedding vectors
    |
    v
vector_store.py
    Persist chunks, embeddings, and metadata in ChromaDB
    |
    v
retriever.py
    Retrieve the most relevant chunks for a question
    |
    v
answerer.py
    Build a grounded answer with document/page citations
    |
    v
server.py
    Expose query_documents through MCP
```

Key design choices:

- The server rebuilds the PDF index at startup to satisfy the assignment requirement that documents be parsed and indexed at startup or on demand.
- Every chunk stores `document_name`, `page_number`, and text so answers can cite sources.
- ChromaDB is persisted under `index/`, which is generated and can be rebuilt.
- The answerer is conservative and extractive. It returns relevant excerpts instead of fabricating a synthesized answer.

## MCP Tool

### `query_documents`

Answers a natural language question using the indexed PDF documents.

Input schema:

```json
{
  "question": "string",
  "top_k": 5
}
```

`top_k` is optional and controls how many chunks are retrieved from ChromaDB.

Output shape:

```json
{
  "answer": "Relevant document excerpts...",
  "answering_instructions": "Answer using only the retrieved_context. Cite document_name and page_number...",
  "retrieved_context": [
    {
      "document_name": "20220630.pdf",
      "page_number": 1,
      "score": 0.244,
      "excerpt": "..."
    }
  ],
  "sources": [
    {
      "document_name": "20220630.pdf",
      "page_number": 1,
      "score": 0.244,
      "excerpt": "..."
    }
  ]
}
```

Example questions:

```text
What companies or organizations are mentioned in these documents?
What is the main topic of the documents?
What dates are referenced by the document filenames?
Which documents mention Russia or China?
```

## Recommended Client Prompt

Some MCP clients expose tools but do not expose MCP prompt templates. In that case, use this prompt in the chat before asking document questions:

```text
You have access to an MCP tool named query_documents.

When I ask a question about the indexed PDFs:
1. Call query_documents with my question. Use top_k=5 unless I ask for broader coverage.
2. Read the returned answer and sources.
3. Synthesize a concise answer in your own words using only the retrieved evidence.
4. Do not simply paste the raw retrieved excerpts unless I explicitly ask for excerpts.
5. If the retrieved context is weak, conflicting, or does not answer the question, say that clearly.
6. Include citations for important claims.

Format your response like this:

Answer:
<direct synthesized answer>

Sources:
- <document_name>, page <page_number>, score <score>: <why this source supports the answer>
- <document_name>, page <page_number>, score <score>: <why this source supports the answer>

Keep the answer grounded. Do not use outside knowledge.
```

Example user question after setting the prompt:

```text
Which organizations are involved in the documents, and what roles do they appear to play?
```

## MCP Client Configuration

Example Codex MCP configuration:

```toml
[mcp_servers.nexla_docquery_mcp]
command = "/absolute/path/to/DocQuery-MCP/scripts/run_mcp_server.sh"
args = []
cwd = "/absolute/path/to/DocQuery-MCP"
```

Or add it with the Codex CLI:

```bash
codex mcp add nexla_docquery_mcp -- /absolute/path/to/DocQuery-MCP/scripts/run_mcp_server.sh
```

## Example Interaction Log

The following examples were tested through an MCP-compatible client connected to the
`query_documents` tool. The client was instructed to call the tool first, synthesize an
answer only from retrieved evidence, and include source attribution.

### Example 1: Multi-document synthesis

**Question**

> How does the coverage of Russia and Ukraine evolve across the April 5, June 6, and June 30 documents?

**Answer**

The documents show a shift from direct battlefield and civilian-harm reporting to broader
geopolitical coverage. The April 5 document focuses on Russian attacks, Bucha killings,
civilian harm, and fighting around places like Kharkiv and Donbas. By June 30, the coverage
shifts toward NATO's response to Russia's invasion, including NATO's new mission framing,
support for Ukraine, and the strategic challenge posed by Russia and China.

**Sources**

- `20220405.pdf`, page 1: Coverage of Bucha, civilian deaths, Russian attacks, and fighting in Ukraine.
- `20220630.pdf`, page 1: Coverage of NATO's response to Russia's invasion and broader geopolitical consequences.

### Example 2: Food and wheat supply

**Question**

> What connection do the documents make between the Ukraine war and global food or wheat supply issues?

**Answer**

The June 6 document links the Ukraine war to global food insecurity. It says Russia and
Ukraine normally supply a large share of Africa's wheat needs, while the war disrupted
Ukraine's grain production and exports. The document also discusses accusations that Russia
was selling stolen Ukrainian grain, creating a dilemma for African countries facing hunger and
high food prices.

**Sources**

- `20220606.pdf`, page 1: Explains that Russia and Ukraine supply about 40% of Africa's wheat needs.
- `20220606.pdf`, page 1: Describes Russia allegedly bombing, blockading, plundering, and selling Ukrainian grain.

### Example 3: Specific factual retrieval

**Question**

> What did the June 6 document say about Suffolk County's use of red flag laws?

**Answer**

The June 6 document presents Suffolk County, New York, as an example of red flag laws being
used to prevent gun violence. It describes a case where a teenager made violent and suicidal
threats, after which police applied to remove his access to guns and a judge issued a red flag
order. The article says Suffolk County used red flag orders more often than any other county in
New York State.

**Sources**

- `20220606.pdf`, page 1: Describes the Suffolk County case involving threats, police action, and removal of guns.
- `20220606.pdf`, page 1: States that Suffolk County used red flag orders more often than any other county in the state.

### Example 4: Map / visual retrieval

**Question**

> Based on the abortion access map, why was Illinois described as an "island of access"?

**Answer**

Illinois was described as an "island of access" because many surrounding states had abortion
bans, six-week restrictions, or uncertain future access after Roe v. Wade was reversed. The map
shows Illinois as a remaining access point while nearby states such as Arkansas, Kentucky,
Missouri, and Wisconsin had bans in effect.

**Sources**

- `20220630.pdf`, page 1: Shows Illinois expecting an influx of patients as neighboring states restrict abortion.
- `20220630.pdf`, page 1: Shows surrounding abortion bans and restrictions across nearby states.

## Repository Layout

```text
src/docquery_mcp/
  server.py        MCP server and query_documents tool
  ingest.py        Startup/manual indexing pipeline
  pdf_loader.py    PDF text extraction
  chunking.py      Page-to-chunk splitting
  embeddings.py    SentenceTransformer wrapper
  vector_store.py  ChromaDB persistence and search
  retriever.py     Question-to-context retrieval
  answerer.py      Grounded extractive answer formatting
  schemas.py       Shared dataclasses

scripts/
  build_index.py       Optional manual index builder
  qa_loop.py           Optional interactive local smoke test
  run_mcp_server.sh    Stable launcher for MCP clients

tests/
  Unit tests for chunking, PDF loading, answer formatting, and tool registration
```

## Generated Files

These are intentionally not committed:

- `.venv/` or other virtual environments
- `index/` ChromaDB data
- `*.egg-info/`
- `__pycache__/`
- local editor/MCP config files

## Vibe Coding Setup

I used Codex as an AI coding partner while building this project. I worked file by file so I could understand the system instead of generating a large codebase all at once.

What worked well:

- Asking Codex to propose the architecture first helped me keep the implementation small and aligned with the assignment.
- Building one module at a time made the flow easier to reason about: schemas, PDF loading, chunking, embeddings, vector store, retrieval, answer formatting, then MCP.
- Codex was useful for catching practical issues, such as Python import paths, Pylance typing warnings, MCP command configuration, and reviewer-facing README structure.

Where I corrected or directed the AI:

- I switched the vector store choice to ChromaDB because it is simple and assignment-friendly.
- I asked for startup indexing after re-reading the requirement that documents must be indexed at startup or on demand.
- I kept the answerer extractive for reliability rather than adding an LLM synthesis layer that could hallucinate.
- I renamed scripts and clarified command names to make the repo more understandable for a reviewer.

My view on AI-assisted engineering:

AI tools are strongest when used as a fast collaborator for scaffolding, debugging, and explaining tradeoffs. They do not replace engineering judgment. I still had to decide what to optimize for: local runnability, source attribution, MCP compliance, and an implementation a reviewer can understand quickly.

## Tradeoffs and Future Improvements

- **Better document filtering:** If the user mentions a specific file, date, page, or section, the retriever should filter to that document first instead of relying only on semantic similarity.
- **Hybrid search:** Combine vector search with keyword search so exact names, dates, numbers, and technical terms are not missed.
- **Smarter chunking:** Use headings, paragraphs, sections, and page boundaries where possible instead of only fixed-size chunks.
- **Reranking:** Retrieve more chunks initially, then rerank them to keep only the most relevant evidence.
- **More document coverage:** Scanned PDFs would need OCR support, and future versions could support additional document types beyond PDFs.
- **Incremental indexing:** Startup indexing rebuilds the local Chroma collection for predictability. A future version could add safe incremental indexing by storing file fingerprints.
