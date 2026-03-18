# Content Generation Pipeline: Comprehensive User Guide

Welcome to the Complete User Guide for the AI Content Generation Pipeline! This document covers *everything* that has been implemented across Phase 1 and Phase 2, explaining what features exist and exactly how to use them.

---

## 🏗️ 1. Core System Architecture

### What is implemented?
We have built an autonomous, stateful **Multi-Agent System** using LangGraph and LangChain. When you request content, it goes through an assembly line of 5 specialized "Agents":

1.  **Planner**: Parses your request, decides the target audience, tone, and generates a structured content brief and research queries.
2.  **Researcher**: Connects to the local vector database (RAG) to find factual documents matching the queries and synthesizes the findings.
3.  **Writer**: Drafts the initial content using the brief instructions and the research data.
4.  **Editor**: Reviews the draft against brand guidelines, fixes flow and grammar, and applies edits without changing core facts.
5.  **SEO Agent**: Analyzes the edited text, injects keywords naturally, and generates Metadata (Titles, Descriptions, URL Slugs).

### How to use it?
The multi-agent execution happens automatically whenever you run the pipeline. You don't have to manage them individually, but you *can* observe them using Debug mode.

---

## 🛠️ 2. The Command Line Interface (CLI)

### What is implemented?
A robust, user-friendly terminal interface built with `argparse` and styled with `rich`. It includes live progress bars, formatted tables, and rich error handling.

### How to use it?
Run the `cli.py` script from the project root. 

**Basic Usage:**
```bash
python cli.py --request "Write a blog post about the benefits of Python 3.13"
```

**Advanced Usage with Custom Settings:**
```bash
python cli.py --request "Introduction to Quantum Computing" \
  --word-count 1200 \
  --tone technical
```
*(Available tones: `professional`, `casual`, `friendly`, `technical`)*

---

## 🗂️ 3. Output Management & Formatting

### What is implemented?
Instead of just printing text to the console, the system professionally manages outputs.
- **Multi-format Exporters**: Content can be rendered into standard Markdown (with frontmatter), styled HTML files, and raw JSON data payloads.
- **Organized Output**: Can automatically create isolated, timestamped folders for every generation session to keep your workspace clean.

### How to use it?

**Export to specific formats:**
```bash
# Export as styled HTML
python cli.py --request "Coffee brewing methods" --format html

# Export as everything (Markdown, HTML, JSON)
python cli.py --request "Coffee brewing methods" --format all
```

**Organize the files cleanly:**
Using the `--organized-output` flag drops everything into a neat folder structure, such as `outputs/20260225_173000_coffee-brewing/`.
```bash
python cli.py --request "Best coffee grinders" --format all --organized-output
```
*Folder Structure Created:*
- `content/` -> Holds your `.md`, `.html`, and `.json` articles.
- `reports/` -> Holds brief, seo metadata, and logs.
- `README.md` -> A summary of the session.

---

## 📊 4. Quality Assurance & Metrics

### What is implemented?
A post-processing `QualityAnalyzer` that automatically reads the generated content and grades it.
- **Readability**: Calculates Flesch-Kincaid grade levels and reading ease.
- **SEO**: Checks keyword density, heading counts, and meta tag lengths.
- **Alignment**: Verifies if the Content Writer actually followed the word count limits set by the Planner.

### How to use it?
Add the `--quality-report` flag.
```bash
python cli.py --request "SEO for beginners" --quality-report
```
*Output:* You will see a "Quality Analysis" box in your terminal with a score out of 100, and actionable recommendations like *"Consider adding a clear introduction section"* or *"Simplify sentences"*. If you use `--organized-output`, this saves as `reports/quality_report.json`.

---

## 🔍 5. Auditing & Logging

### What is implemented?
Enterprise-grade observability.
- **Audit Trails**: Records token usage, agent execution times, and strict tracking of which agent did what via a unique `Request ID`.
- **System Logs**: Dual-format logs. Errors and debug events are written to rotating files (`logs/content_generation.log`) in JSON format for machines, and colorfully printed to the terminal for humans.

### How to use it?

**1. Generate an Audit Log file:**
Use the `--audit-log` flag to generate an `execution_summary.json` and a full `audit_log.json` detailing the hidden conversations between the AI agents.
```bash
python cli.py --request "Microservices Architecture" --audit-log --organized-output
```

**2. Verbose & Debug Modes:**
If you want to see the Agent's thought processes (like the Research findings or the Editor's notes) print onto the screen in real-time:
```bash
# Shows intermediate agent outputs
python cli.py --request "Testing" --verbose 

# Shows deep system logs (API calls, retries, path executions)
python cli.py --request "Testing" --debug
```

---

## 📚 6. Retrieval-Augmented Generation (RAG)

### What is implemented?
A local database (ChromaDB) that the Researcher Agent uses to pull facts so the AI doesn't hallucinate. It contains collections for:
- `research`: General facts and knowledge base.
- `style`: Brand voice guidelines.
- `seo`: Competitor data.

### How to use it?
You don't trigger this manually during generation; the Researcher does it automatically. However, you can manage the knowledge base using the `data/ingest.py` script.

To add new knowledge to the AI's brain:
1. Open `data/ingest.py` (or create a custom ingestion script).
2. Format your text as a LangChain `Document`.
3. Add it to the ChromaDB manager.
```python
from vector_stores.chroma import ChromaDBManager
from langchain_core.documents import Document

db = ChromaDBManager()
doc = Document(page_content="The new product 'SuperWidget' launches in 2027.", metadata={"topic": "products"})
db.add_documents("research", [doc])
```

---

## 🔄 7. Resilience & Error Handling

### What is implemented?
The system won't crash if OpenAI has a slight hiccup.
- **Retry Logic**: Failed API calls use exponential backoff and jitter to silently try again.
- **Workflow Fallbacks**: If the Writer Agent outputs terrible formatting, a conditional LangGraph edge can catch it and send it *back* to the Writer for a re-write.

### How to use it?
It is completely passive! Just run the CLI. If an error does break the pipeline, it will elegantly print a nicely formatted Error Box in the terminal showing you exactly which agent failed and why, rather than printing an ugly block of red Python traceback text to the user.

---

## 🚀 Quick Recipe: The Ultimate Run
To use absolutely everything implemented at once to generate a professional, audited, organized, and graded piece of content:

```bash
python cli.py \
  --request "The future of Agentic AI 2026" \
  --word-count 1500 \
  --tone professional \
  --format all \
  --organized-output \
  --quality-report \
  --audit-log \
  --verbose
```
