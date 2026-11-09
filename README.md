# Digital Scribe

[![Tests](https://github.com/aashish177/Digital-Scribe/actions/workflows/tests.yml/badge.svg)](https://github.com/aashish177/Digital-Scribe/actions/workflows/tests.yml)

An autonomous AI content creation system that orchestrates 5 specialized agents using LangGraph to produce high-quality, SEO-optimized content. The system leverages Retrieval-Augmented Generation (RAG) with ChromaDB to ground outputs in factual information and brand guidelines.

## Overview

This project implements a stateful, multi-agent workflow that automates the entire content creation process from planning through SEO optimization. Each agent specializes in a specific task and uses vector database retrieval to ensure accuracy and consistency.

### Key Features

- **5 Specialized AI Agents**: Planner, Researcher, Writer, Editor, and SEO Optimizer working in orchestrated sequence
- **Web UI & Dashboard**: Premium glassmorphic interface for launching pipelines and reviewing results
- **REST API (FastAPI)**: Fully asynchronous backend with SSE streaming and background processing
- **New Modalities**: Integrated Translation (multi-language), Social Media (Twitter/LinkedIn), and Image Generation (DALL-E prompts)
- **Advanced RAG**: Hybrid Search (Dense + Sparse/BM25) and FlashRank reranking for superior fact retrieval
- **Human-in-the-Loop**: Interactive interrupt points for brief approval via the UI or API
- **Stateful Workflow**: LangGraph-based orchestration with persistent checkpointing

## Architecture

### Tech Stack

- **Orchestration**: LangGraph for multi-agent workflow management
- **AI Framework**: LangChain for agent construction
- **Backend API**: FastAPI with Server-Sent Events (SSE)
- **Frontend**: Vanilla JS/CSS with glassmorphic design
- **LLM**: OpenAI GPT-4o
- **Vector Database**: ChromaDB with persistent storage
- **Embeddings**: OpenAI text-embedding-3-small
- **Language**: Python 3.11+

### Agent Pipeline

```
User Request → Planner → [Approval] → Researcher → Writer → Editor → SEO → [Translator/Social/Image] → Final Content
```

1. **Planner Agent**: Analyzes requests and creates structured content briefs
2. **Researcher Agent**: Queries vector stores and synthesizes findings with citations
3. **Writer Agent**: Generates drafts following brief specifications and research
4. **Editor Agent**: Refines content for style guide compliance and accuracy
5. **SEO Agent**: Optimizes content and generates metadata for search engines
6. **New Modalities**: Optional translation, social media post creation, and visual concept generation

### Vector Store Collections

- `research_docs`: Articles, papers, and factual content
- `writing_samples`: High-performing content templates
- `style_guide`: Brand voice and formatting guidelines
- `seo_data`: Keywords, competitor analysis, and SERP data

### Knowledge Base

The `research_docs` collection is built from 20 Wikipedia articles across 4 topics, stored as plain text in `data/sources/`:

| Topic | Articles |
|---|---|
| Tea and coffee | Green tea, Coffee, Caffeine, Theanine, Catechin |
| Renewable energy | Solar power, Wind power, Heat pump, Lithium-ion battery, Grid energy storage |
| Sleep | Sleep, Circadian rhythm, Melatonin, Insomnia, Sleep deprivation |
| Space exploration | James Webb Space Telescope, Exoplanet, Mars rover, Artemis program, SpaceX Starship |

Each file records its source URL and revision ID. Run `python scripts/fetch_sources.py` to refresh them. Article text is from [Wikipedia](https://en.wikipedia.org/) under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

The style guide, writing samples and SEO data are small sample documents in `data/ingest.py`.

## Status

The pipeline, CLI, REST API and web UI are in place. Unit tests run in CI with mocked LLM calls.

**In progress:** an evaluation suite that measures faithfulness to sources, citation accuracy and retrieval recall, and compares the full pipeline against a single-prompt baseline. Results will be added here.

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- UV package manager (recommended) or pip

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/aashish177/Digital-Scribe.git
   cd Digital-Scribe
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Then set `OPENAI_API_KEY` in `.env`.

4. **Load the knowledge base into ChromaDB**
   ```bash
   uv run python data/ingest.py
   ```

5. **Start the web UI (optional)**
   ```bash
   uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```
   Open http://127.0.0.1:8000/. Run this from the repo root so the UI files are found.

## Usage Guide

The Content Generation Pipeline exposes a powerful Command Line Interface for end-to-end processing. Ensure you have activated your environment with the proper `OPENAI_API_KEY` defined in `.env`.

### Basic Usage

```bash
python cli.py --request "Write a guide on meditation for beginners"
```

### CLI Flags & Arguments
- `--request TEXT` **(Required)**: The core prompt for content generation.
- `--output-dir PATH`: Directory where session outputs will be saved (Default: `./outputs`).
- `--word-count INT`: Approximate word count instruction for WriterAgent (Default: `800`).
- `--tone CHOICE`: Sets the style constraint (`professional`, `casual`, `friendly`, `technical`).
- `--format CHOICE`: Output export file formats (`markdown`, `json`, `html`, `all`) (Default: `markdown`).
- `--organized-output`: Groups the outputs in a designated timestamp-slug session directory. (e.g. `outputs/20260218.../`).
- `--quality-report`: Triggers a comprehensive content grade based on SEO and Readability via `textstat`, printing it.
- `--audit-log`: Produces a detailed `audit_log.json` and metric profile over the generated pipeline step.
- `--verbose, -v`: Displays rich outputs like brief and research stages.
- `--debug, -d`: Changes logging verbosity.
- `--version`: Print CLI version.
- `--help, -h`: Shows extensive parameter details.

### Recipes

**Create a fully production-ready SEO Blog Post:**
```bash
python cli.py --request "Tech trends 2026" \
    --word-count 1500 \
    --tone professional \
    --format all \
    --organized-output \
    --quality-report \
    --audit-log
```

**Generate Bulk Raw Data via JSON formats:**
```bash
python cli.py --request "Artificial Intelligence Impact on Finance" \
    --format json \
    --output-dir ./finance_data
```

### Programmatic Usage

You can hook into the core logic dynamically via Python:

```python
from logging_config import setup_logging
from graph.workflow import create_content_workflow, initialize_state

setup_logging(level="INFO")

app = create_content_workflow()
state = initialize_state(
    content_request="Write a comprehensive guide on green tea health benefits",
    settings={"word_count": 1000, "tone": "informative"}
)

result = app.invoke(state, config={"configurable": {"thread_id": state["request_id"]}})
print(f"Request ID: {result['request_id']}")
print(f"Final Content: {result['final_content']}")
```

### Troubleshooting
- **No API response / AuthenticationError:** Verify your `OPENAI_API_KEY` value across environment configs.
- **Dependency Issues (e.g., ModuleNotFound ERROR):** Make sure `uv sync` or `pip install -e .` is applied correctly. Ensure `chromadb` has its compiled native dependencies via your OS requirements or conda.
- **Workflow getting stuck:** Turn on `--debug` to check where execution froze (useful for RAG connectivity issues).

## Project Structure

```
Digital-Scribe/
├── agents/             # Planner, researcher, writer, editor, SEO, translator, social media, image prompts
├── graph/              # LangGraph state, nodes, edges and workflow
├── vector_stores/      # ChromaDB manager with hybrid search and reranking
├── api/                # FastAPI app with SSE status streaming
├── frontend/           # Web UI served by the API
├── data/
│   ├── sources/        # Knowledge base articles (Wikipedia)
│   └── ingest.py       # Loads all collections into ChromaDB
├── scripts/            # Source fetcher and smoke scripts that call real LLMs
├── tests/              # Unit tests (pytest)
├── utils/              # Quality metrics, exporters, audit log, retries
├── cli.py              # Command line interface
└── config.py           # Settings and environment variables
```

## Configuration

### Agent Temperature Settings

- **Planner**: 0.2 (focused and structured)
- **Researcher**: 0.0 (factual and precise)
- **Writer**: 0.7 (creative and engaging)
- **Editor**: 0.1 (consistent and accurate)
- **SEO**: 0.2 (strategic and analytical)

### RAG Settings

- **Chunking**: 500 characters with 50 characters of overlap (`data/ingest.py`)
- **Retrieval**: dense and BM25 candidates are merged, reranked with FlashRank, and the top 4 are returned per query

## Development

### Running Tests

```bash
# Unit tests, no API key needed
uv run pytest

# Include tests that call real LLMs
RUN_INTEGRATION=1 uv run pytest

# End-to-end smoke runs (call real LLMs)
uv run python -m scripts.smoke_workflow
uv run python scripts/smoke_cli.py
```

### Adding New Documents to Vector Store

```python
from vector_stores.chroma import ChromaDBManager
from langchain_core.documents import Document

db = ChromaDBManager()

# Add research documents
docs = [
    Document(
        page_content="Your content here...",
        metadata={"source": "example.txt", "topic": "health"}
    )
]

db.add_documents("research", docs)
```

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) for agent framework
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [OpenAI](https://openai.com/) for LLM and embeddings

