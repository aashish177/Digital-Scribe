from typing import Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from agents.base import BaseAgent
from config import Config
from pydantic import BaseModel, Field

class SocialMediaPosts(BaseModel):
    twitter: str = Field(description="A Twitter thread or single post. Use [post 1/X] format for threads.")
    linkedin: str = Field(description="A professional LinkedIn post highlighting key takeaways.")
    facebook: Optional[str] = Field(description="A casual Facebook post.", default=None)

class SocialMediaAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SocialMedia", temperature=Config.WRITER_TEMP)
        self.parser = JsonOutputParser(pydantic_object=SocialMediaPosts)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a social media growth expert. Your goal is to create highly engaging posts based on a long-form article.
            
            Instructions:
            - Capture the hook from the article.
            - Summarize key value points.
            - Use appropriate emojis and formatting for each platform.
            - Include a call to action.
            
            {format_instructions}
            """),
            ("user", """
            Article Content:
            {content}
            
            Brief Context:
            {brief}
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def generate_posts(self, content: str, brief: Dict) -> Dict[str, str]:
        """
        Generates social media posts for multiple platforms.
        """
        input_data = {
            "content": content,
            "brief": str(brief),
            "format_instructions": self.parser.get_format_instructions()
        }
        return self.invoke(input_data)
