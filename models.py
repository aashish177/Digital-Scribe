from typing import TypedDict, Optional, List, Dict
from pydantic import BaseModel, Field

class ContentBrief(BaseModel):
    title: str = Field(description="Proposed title for the content")
    target_audience: str = Field(description="Description of the target audience")
    tone: str = Field(description="Tone and voice of the article (e.g. professional, casual)")
    word_count_target: int = Field(description="Target word count")
    outline: List[str] = Field(description="List of main section headers")
    seo_keywords: List[str] = Field(description="Primary and secondary keywords to target", default_factory=list)
    specifications: str = Field(description="Any specific instructions or requirements", default="")

class ContentState(TypedDict):
    content_request: str
    content_brief: Optional[Dict]  # Serialized ContentBrief
    research_data: Optional[List[Dict]]
    draft_content: Optional[str]
    refined_content: Optional[str]
    seo_metadata: Optional[Dict]
    status: str
    errors: List[str]
