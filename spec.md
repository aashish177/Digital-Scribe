# Multi-Agent Content Creation Pipeline

## Project Description
An autonomous content creation system that uses five specialized AI agents orchestrated by LangGraph to produce high-quality, SEO-optimized content. Each agent focuses on a specific task (planning, research, writing, editing, SEO) and uses Retrieval-Augmented Generation (RAG) with ChromaDB to ground outputs in factual information and brand guidelines.

## Core Features

### 1. Intelligent Content Planning
- Analyzes user requests to create detailed content briefs
- Automatically determines content structure, tone, and target audience
- Generates strategic research queries for information gathering
- Outputs structured JSON briefs with sections, word counts, and specifications

### 2. RAG-Powered Research System
- Multi-collection vector database (research docs, writing samples, style guides, SEO data)
- Semantic search across indexed knowledge bases
- Parallel query execution for comprehensive information gathering
- Automatic synthesis of findings from multiple sources with citations
- Configurable retrieval strategies (top-k, similarity thresholds, metadata filtering)

### 3. Adaptive Content Generation
- Context-aware writing that follows brief specifications
- Learns from high-performing content examples via vector retrieval
- Natural incorporation of research findings with proper attribution
- Adjustable creativity levels for different content types
- Section-by-section generation with coherent flow

### 4. Multi-Stage Content Refinement
- Style guide compliance checking via RAG
- Automated fact verification against source documents
- Tone and voice consistency enforcement
- Grammar, clarity, and readability optimization
- Detailed change tracking and explanation

### 5. SEO Optimization Engine
- Keyword research and semantic analysis
- Competitor content analysis via vector search
- Meta tag generation (title, description, headers)
- URL slug recommendations
- Internal linking opportunity identification
- SERP-optimized content structure suggestions

### 6. Workflow Orchestration (LangGraph)
- State management across all agents
- Conditional routing based on quality checks
- Parallel agent execution capabilities
- Error handling and retry logic
- Progress tracking and observability
- Support for human-in-the-loop review points

### 7. Vector Store Management
- Four separate ChromaDB collections with optimized indexing
- Document chunking with configurable strategies
- Hybrid search (dense + sparse retrieval)
- Metadata filtering and tagging system
- Persistence and version control for knowledge bases
- Easy addition/update of documents

### 8. Output Management
- Multiple format exports (Markdown, JSON, HTML)
- Complete audit trail of all agent decisions
- SEO metadata packaging
- Version history of drafts
- Confidence scores and quality metrics

## Technical Architecture

### Stack
- **Orchestration**: LangGraph for agent workflow management
- **AI Framework**: LangChain for agent construction
- **LLM**: Claude Sonnet 4 (Anthropic)
- **Vector Database**: ChromaDB with persistent storage
- **Embeddings**: OpenAI text-embedding-3-small
- **Language**: Python 3.10+

### System Components

#### State Management
- TypedDict-based state shared across all agents
- Immutable state transitions tracked by LangGraph
- Complete conversation history preservation
- Error and metadata accumulation

#### Agent Architecture
Each agent is:
- Independently testable
- Configured with specialized prompts
- Temperature-tuned for its task
- Equipped with appropriate tools (some use RAG, some don't)

#### Vector Store Collections
1. **research_docs**: Articles, papers, factual content (1000 token chunks)
2. **writing_samples**: High-performing content templates (500 token chunks)
3. **style_guide**: Brand voice and guidelines (300 token chunks)
4. **seo_data**: Keywords, competitor analysis, SERP data (variable chunking)

#### Workflow Patterns
- **Linear**: Planning → Research → Writing → Editing → SEO → Output
- **Conditional**: Quality checks with retry loops
- **Parallel**: Multiple research agents for different domains
- **Human-in-loop**: Optional pause points for review

## User Interface / API

### CLI Interface
```bash
python main.py --request "Write a guide on indoor gardening" --output ./outputs
```

### Programmatic API
```python
from graph.workflow import create_content_workflow

app = create_content_workflow()
result = app.invoke({"content_request": "..."})
```

### Future: REST API
```
POST /api/generate
{
  "request": "content description",
  "settings": {
    "word_count": 1500,
    "tone": "professional",
    "include_seo": true
  }
}
```

## Data Flow

1. **Input**: User provides content request (plain text)
2. **Planning**: Agent analyzes and creates structured brief (JSON)
3. **Research**: Queries vector stores, retrieves 15-30 relevant documents
4. **Synthesis**: LLM combines research into coherent findings summary
5. **Writing**: Generates draft using brief + research (1000-3000 words)
6. **Editing**: Retrieves style guide, compares draft, produces refined version
7. **SEO**: Analyzes content, retrieves competitor data, optimizes + generates metadata
8. **Output**: Final content + metadata + audit trail saved to files

## Configuration

### Environment Variables
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
VECTORDB_PATH=./data/vectordb
```

### Configurable Parameters
- Model selection per agent
- Temperature settings per agent
- Chunk sizes and overlap for each collection
- Top-k retrieval counts
- Similarity thresholds
- Max retries and timeouts
- Output formats

## Error Handling

- Graceful degradation if vector store queries fail
- Retry logic for API timeouts
- Fallback to simpler workflows if agents fail
- Detailed error logging in state object
- Validation of agent outputs before proceeding
- Human escalation triggers for low-confidence outputs

## Extensibility

### Easy to Add
- New agent types (translation, image generation, fact-checking)
- New vector collections (legal docs, accessibility guidelines)
- Custom routing logic
- Integration with external APIs
- Webhook notifications
- Batch processing capabilities

### Plugin Architecture
Agents can be swapped out or extended:
```python
class CustomResearchAgent(BaseAgent):
    def research(self, queries):
        # Custom implementation
        pass
```

## Performance Targets

- End-to-end pipeline: 2-5 minutes for 1500-word content
- Planning agent: <10 seconds
- Research agent: 20-40 seconds (depends on queries)
- Writing agent: 60-120 seconds
- Editing agent: 30-60 seconds
- SEO agent: 15-30 seconds
- Vector search latency: <2 seconds per query
- Support concurrent pipelines: 3-5 simultaneous

## Monitoring & Observability

- LangGraph execution traces
- Token usage tracking per agent
- Cost estimation per pipeline run
- Quality scores at each stage
- Agent execution times
- Vector store query performance metrics
- Error rates and types

## Testing Strategy

### Unit Tests
- Each agent independently with mock inputs
- Vector store operations (CRUD)
- State transitions

### Integration Tests
- Two-agent workflows
- Full pipeline end-to-end
- Error scenarios

### Quality Tests
- Content quality evaluation
- Brief-to-content alignment
- Fact accuracy validation
- SEO metadata completeness

## Deployment

### Local Development
- Python venv with requirements.txt
- Local ChromaDB persistence
- File-based outputs

### Production (Future)
- Docker containerization
- Cloud vector database (Pinecone/Weaviate)
- Message queue for async processing (Celery + Redis)
- API gateway with authentication
- Monitoring with LangSmith/Prometheus
- S3/GCS for output storage

## Security & Privacy

- API keys in environment variables only
- No user data in vector stores without consent
- Audit logs for all operations
- Option to disable external API calls
- Local-only deployment option
- Content sanitization before storage

## Documentation

- README with quickstart
- API documentation
- Agent prompt engineering guide
- Vector store management guide
- Troubleshooting guide
- Example use cases and outputs

## Success Metrics

- Content quality score (8/10 or higher)
- Time savings vs manual creation (70%+ reduction)
- SEO effectiveness (keyword coverage, readability scores)
- Fact accuracy rate (95%+)
- User satisfaction with outputs
- Reduction in editing time needed

## Future Enhancements

### Phase 2
- Web UI for easier interaction
- Real-time streaming of agent progress
- A/B testing of multiple content variants
- Performance analytics dashboard

### Phase 3
- Multi-language support with translation agent
- Image generation and selection agent
- Video script generation
- Social media adaptation agent

### Phase 4
- Fine-tuned embeddings on domain-specific content
- Reinforcement learning from user feedback
- Automated performance tracking of published content
- Content calendar integration