# Digital Scribe

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

## Project Status

### ✅ Completed (Phase 1)

- [x] Core agent implementations (Planner, Researcher, Writer, Editor, SEO)
- [x] Base agent architecture with LLM integration
- [x] ChromaDB vector store manager with 4 collections
- [x] LangGraph workflow with conditional routing
- [x] State management system with TypedDict
- [x] Data ingestion pipeline with text chunking
- [x] Configuration management with environment variables
- [x] Mock data generation for testing

### ✅ Completed (Phase 2)

#### ✅ Phase 2A: Foundation
- [x] Error handling infrastructure with structured error classes
- [x] Retry utilities with exponential backoff and jitter
- [x] Comprehensive logging system (JSON and human-readable formats)
- [x] Request ID tracking across pipeline execution
- [x] Execution time measurement for all agents
- [x] Log rotation and multiple log handlers

#### ✅ Phase 2B: Basic CLI Interface
- [x] CLI argument parser for content generation
- [x] Progress indicators for agent execution
- [x] Verbose and debug modes
- [x] Basic output formatting

#### ✅ Phase 2C: Output Management & Quality Metrics
- [x] Multi-format exports (Markdown, JSON, HTML)
- [x] Audit trail system
- [x] Quality scoring and confidence metrics
- [x] Enhanced output organization

#### ✅ Phase 2D: Testing & Documentation
- [x] Comprehensive unit and integration test suite (pytest)
- [x] CLI usage guide with Recipes
- [x] Updated architecture documentation

### ✅ Completed (Phase 3: API & Modalities)
- [x] **REST API**: FastAPI implementation with async execution and Webhooks
- [x] **Web Dashboard**: Real-time progress tracking via SSE & glassmorphic UI
- [x] **HITL**: Manual approval flow for content briefs
- [x] **Advanced RAG**: Hybrid search (Vector + BM25) and FlashRank reranking
- [x] **New Modalities**: Translation, Social Media posts, and Image generation agents
- [x] **Batch Processing**: Simultaneous generation for multiple requests

### 📋 Planned (Phase 4+)
- [ ] Dockerization and deployment orchestration
- [ ] Multi-user authentication & workspace management
- [ ] Custom style guide training/fine-tuning
- [ ] Integration with CMS platforms (WordPress, Ghost, etc.)

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- UV package manager (recommended) or pip

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd content-generation
   ```

2. **Install dependencies**
   
   Using UV:
   ```bash
   uv sync
   ```
   
   Or using pip:
   ```bash
   pip install -e .
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   VECTORDB_PATH=./data/vectordb
   ```

4. **Ingest sample data**
   ```bash
   python data/ingest.py
   ```

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

result = app.invoke(state)
print(f"Request ID: {result['request_id']}")
print(f"Final Content: {result['final_content']}")
```

### Troubleshooting
- **No API response / AuthenticationError:** Verify your `OPENAI_API_KEY` value across environment configs.
- **Dependency Issues (e.g., ModuleNotFound ERROR):** Make sure `uv sync` or `pip install -e .` is applied correctly. Ensure `chromadb` has its compiled native dependencies via your OS requirements or conda.
- **Workflow getting stuck:** Turn on `--debug` to check where execution froze (useful for RAG connectivity issues).

## Project Structure

```
content-generation/
├── agents/              # AI agent implementations
│   ├── base.py         # Base agent class
│   ├── planner.py      # Planning agent
│   ├── researcher.py   # Research agent
│   ├── writer.py       # Writing agent
│   ├── editor.py       # Editing agent
│   └── seo.py          # SEO optimization agent
├── graph/              # LangGraph workflow
│   ├── state.py        # State management
│   ├── workflow.py     # Workflow definition
│   ├── nodes.py        # Agent nodes
│   └── edges.py        # Conditional routing
├── vector_stores/      # Vector database management
│   └── chroma.py       # ChromaDB manager
├── data/               # Data and vector storage
│   ├── ingest.py       # Data ingestion script
│   └── vectordb/       # ChromaDB persistent storage
├── skills/             # Agent skill documentation
├── outputs/            # Generated content outputs
├── config.py           # Configuration management
├── models.py           # Data models
└── main.py            # Entry point (WIP)
```

## Configuration

### Agent Temperature Settings

- **Planner**: 0.2 (focused and structured)
- **Researcher**: 0.0 (factual and precise)
- **Writer**: 0.7 (creative and engaging)
- **Editor**: 0.1 (consistent and accurate)
- **SEO**: 0.2 (strategic and analytical)

### RAG Settings

- **Chunk Size**: 1000 tokens
- **Chunk Overlap**: 200 tokens
- **Retrieval K**: 5 documents per query

## Development

### Running Tests

```bash
# Test individual agents
python test_planner.py

# Verify workflow
python verify_workflow.py
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

## Performance Targets

- **End-to-end pipeline**: 2-5 minutes for 1500-word content
- **Planning**: <10 seconds
- **Research**: 20-40 seconds
- **Writing**: 60-120 seconds
- **Editing**: 30-60 seconds
- **SEO**: 15-30 seconds

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) for agent framework
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [OpenAI](https://openai.com/) for LLM and embeddings

