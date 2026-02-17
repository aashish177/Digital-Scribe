# Multi-Agent Content Generation Pipeline

An autonomous AI content creation system that orchestrates 5 specialized agents using LangGraph to produce high-quality, SEO-optimized content. The system leverages Retrieval-Augmented Generation (RAG) with ChromaDB to ground outputs in factual information and brand guidelines.

## Overview

This project implements a stateful, multi-agent workflow that automates the entire content creation process from planning through SEO optimization. Each agent specializes in a specific task and uses vector database retrieval to ensure accuracy and consistency.

### Key Features

- **5 Specialized AI Agents**: Planner, Researcher, Writer, Editor, and SEO Optimizer working in orchestrated sequence
- **RAG-Powered Research**: ChromaDB vector database with 4 specialized collections for semantic search
- **Stateful Workflow**: LangGraph-based orchestration with conditional routing and error handling
- **Context-Aware Generation**: Automated fact verification and style guide compliance
- **Production-Ready Architecture**: Comprehensive error handling, retry logic, and audit trails

## Architecture

### Tech Stack

- **Orchestration**: LangGraph for multi-agent workflow management
- **AI Framework**: LangChain for agent construction
- **LLM**: OpenAI GPT-4o
- **Vector Database**: ChromaDB with persistent storage
- **Embeddings**: OpenAI text-embedding-3-small
- **Language**: Python 3.11+

### Agent Pipeline

```
User Request → Planner → Researcher → Writer → Editor → SEO → Final Content
```

1. **Planner Agent**: Analyzes requests and creates structured content briefs
2. **Researcher Agent**: Queries vector stores and synthesizes findings with citations
3. **Writer Agent**: Generates drafts following brief specifications and research
4. **Editor Agent**: Refines content for style guide compliance and accuracy
5. **SEO Agent**: Optimizes content and generates metadata for search engines

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

### 🚧 In Progress (Phase 2)

#### ✅ Phase 2A: Foundation (Completed)
- [x] Error handling infrastructure with structured error classes
- [x] Retry utilities with exponential backoff and jitter
- [x] Comprehensive logging system (JSON and human-readable formats)
- [x] Request ID tracking across pipeline execution
- [x] Execution time measurement for all agents
- [x] Log rotation and multiple log handlers

#### 🔄 Phase 2B: Basic CLI Interface (Next)
- [ ] CLI argument parser for content generation
- [ ] Progress indicators for agent execution
- [ ] Verbose and debug modes
- [ ] Basic output formatting

#### 📋 Phase 2C: Output Management & Quality Metrics (Planned)
- [ ] Multi-format exports (Markdown, JSON, HTML)
- [ ] Audit trail system
- [ ] Quality scoring and confidence metrics
- [ ] Enhanced output organization

#### 📋 Phase 2D: Testing & Documentation (Planned)
- [ ] Comprehensive test suite
- [ ] CLI usage guide
- [ ] Updated documentation

### 📋 Planned (Phase 3+)

- [ ] REST API with FastAPI
- [ ] Web UI for easier interaction
- [ ] Real-time streaming of agent progress
- [ ] Performance analytics dashboard
- [ ] Batch processing capabilities
- [ ] Human-in-the-loop review points
- [ ] Advanced RAG features (hybrid search, reranking)
- [ ] Multi-language support
- [ ] Integration with external APIs

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

## Usage

### Command Line Interface (Recommended)

The easiest way to generate content is using the CLI:

```bash
# Basic usage
python cli.py --request "Write a guide on meditation for beginners"

# With custom options
python cli.py --request "Tech trends 2025" --word-count 1500 --tone professional

# Multiple output formats
python cli.py --request "Indoor gardening tips" --format all

# Verbose mode (shows research findings and edit notes)
python cli.py --request "Green tea benefits" --verbose

# Debug mode (full logging)
python cli.py --request "Test content" --debug

# Custom output directory
python cli.py --request "Productivity tips" --output-dir ./my-content
```

**Available Arguments:**
- `--request TEXT` (required): Content request description
- `--output-dir PATH`: Output directory (default: `./outputs`)
- `--word-count INT`: Target word count
- `--tone CHOICE`: Content tone (`professional`, `casual`, `friendly`, `technical`)
- `--format CHOICE`: Output format (`markdown`, `json`, `html`, `all`)
- `--verbose, -v`: Show detailed output
- `--debug, -d`: Enable debug mode
- `--version`: Show version
- `--help, -h`: Show help message

### Programmatic Usage

```python
from logging_config import setup_logging
from graph.workflow import create_content_workflow, initialize_state

# Setup logging
setup_logging(level="INFO", format_type="human")

# Create workflow
app = create_content_workflow()

# Initialize state with tracking
state = initialize_state(
    content_request="Write a comprehensive guide on green tea health benefits",
    settings={"word_count": 1000, "tone": "informative"}
)

# Run pipeline
result = app.invoke(state)

# Access results
print(f"Request ID: {result['request_id']}")
print(f"Final Content: {result['final_content']}")
print(f"SEO Metadata: {result['seo_metadata']}")
print(f"Execution Times: {result['execution_times']}")
```

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

