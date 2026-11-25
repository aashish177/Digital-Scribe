from typing import Tuple, Dict
from langchain_core.prompts import ChatPromptTemplate
from agents.base import BaseAgent
from config import Config
from vector_stores.chroma import ChromaDBManager
from pydantic import BaseModel, Field


class SEOMetadata(BaseModel):
    title: str = Field(description="SEO optimized title (max 60 chars)")
    meta_description: str = Field(description="Meta description (max 160 chars)")
    keywords_used: list[str] = Field(description="Target keywords that already appear in the content")
    confidence: float = Field(description="Confidence score 0-1")
    url_slug: str = Field(description="Recommended URL slug")


class SEOAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SEO", temperature=Config.SEO_TEMP)

        self.db = ChromaDBManager()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SEO Specialist.

            Inputs:
            1. Content (already written and edited)
            2. Target Keywords (from the brief)
            3. Competitor Data (context)

            Instructions:
            - Write an SEO title tag (max 60 characters) and meta description (max 160 characters) that match the content.
            - Suggest a clean, lowercase, hyphenated URL slug.
            - List which target keywords already appear in the content.
            - Do not rewrite the content.
            """),
            ("user", """
            Brief Keywords: {keywords}

            Competitor Data: {competitor_data}

            Content:
            {content}
            """)
        ])

        self.chain = self.prompt | self.llm.with_structured_output(SEOMetadata)

    def optimize(self, content: str, brief: Dict) -> Tuple[str, Dict]:
        """
        Generates SEO metadata for the content.
        Returns: (Content String, Metadata Dictionary)
        """
        keywords = brief.get("seo_keywords", [])
        keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

        seo_docs = self.db.query("seo", keywords_str or brief.get("title", ""), k=2)
        competitor_data = "\n".join([d.page_content for d in seo_docs])

        result = self.invoke({
            "content": content,
            "keywords": keywords_str,
            "competitor_data": competitor_data,
        })
        metadata = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        return content, metadata
