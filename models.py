from typing import List
from pydantic import BaseModel, Field

class ContentBrief(BaseModel):
    title: str = Field(description="Proposed title for the content")
    target_audience: str = Field(description="Description of the target audience")
    tone: str = Field(description="Tone and voice of the article (e.g. professional, casual)")
    word_count_target: int = Field(description="Target word count")
    outline: List[str] = Field(description="List of main section headers")
    seo_keywords: List[str] = Field(description="Primary and secondary keywords to target", default_factory=list)
    research_queries: List[str] = Field(description="3 to 5 short search queries for researching this topic in the knowledge base", default_factory=list)
    specifications: str = Field(description="Any specific instructions or requirements", default="")
