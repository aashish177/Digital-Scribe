from typing import List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.base import BaseAgent
from vector_stores.chroma import ChromaDBManager
from config import Config

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Research", temperature=Config.RESEARCHER_TEMP)
        
        # Initialize Vector DB access
        self.db = ChromaDBManager()
        
        # Output parser
        self.parser = StrOutputParser()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Research Analyst. Your goal is to provide accurate, factual information based ONLY on the provided context.
            
            You will be given a set of queries and numbered sources retrieved for them.
            
            Synthesize these findings into a coherent research summary.
            - Cite every fact with its source number in square brackets, e.g. [1] or [2][3].
            - Only use the numbers given in the context. Never invent a source.
            - Keep exact figures, dates and names as they appear in the sources.
            - If the information is conflicting, note the discrepancy.
            - If the retrieved documents do not answer the query, state: "Insufficient information in current knowledge base."
            
            Format your output as markdown.
            """),
            ("user", """
            Queries: {queries}
            
            Retrieved Context:
            {context}
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def research(self, queries: List[str]) -> Tuple[str, List[Dict]]:
        """
        Conducts research by querying the vector store and synthesizing findings.
        
        Returns:
            Tuple containing:
            1. Synthesized summary string
            2. List of unique retrieved documents (dictionaries)
        """
        all_docs = []
        context_parts = []
        citations: Dict[str, int] = {}
        
        # 1. Retrieve documents for each query in parallel
        def run_query(q):
            try:
                # Query the 'research' collection
                return q, self.db.query_multireturn("research", q, k=Config.RETRIEVAL_K)
            except Exception as e:
                self.logger.warning(f"Error querying DB for '{q}': {e}")
                return q, []

        with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
            query_results = list(executor.map(run_query, queries))

        seen_content = set()
        for q, results in query_results:
            if results:
                context_parts.append(f"--- Results for query: '{q}' ---")
                for r in results:
                    meta = r.get("metadata") or {}
                    key = meta.get("source") or r.get("source") or meta.get("title") or "Unknown"
                    n = citations.setdefault(key, len(citations) + 1)
                    title = meta.get("title") or key
                    content = r.get("content", "").strip()
                    context_parts.append(f"[{n}] {title}\n{content}\n")
                    
                    if content not in seen_content:
                        seen_content.add(content)
                        all_docs.append({**r, "metadata": {**meta, "citation": n}})
        
        if not context_parts:
            return "No relevant documents found in the knowledge base.", []
            
        full_context = "\n".join(context_parts)
        
        # 2. Synthesize with LLM
        input_data = {
            "queries": "\n- ".join(queries),
            "context": full_context
        }
        
        summary = self.invoke(input_data)
        
        return summary, all_docs
