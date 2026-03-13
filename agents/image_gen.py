from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from agents.base import BaseAgent
from config import Config
from pydantic import BaseModel, Field

class ImagePrompt(BaseModel):
    prompt: str = Field(description="A highly detailed and descriptive prompt for image generation (DALL-E 3).")
    style: str = Field(description="The artistic style of the image (e.g. photorealistic, digital art, 3D render).")
    aspect_ratio: str = Field(description="Recommended aspect ratio (e.g. 16:9, 1:1).", default="16:9")

class ImageGenAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ImageGen", temperature=Config.WRITER_TEMP)
        self.parser = JsonOutputParser(pydantic_object=ImagePrompt)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a creative visual designer. Your goal is to create compelling visual concepts for articles.
            
            Instructions:
            - Analyze the article subject and tone.
            - Create a detailed prompt for an AI image generator like DALL-E 3.
            - Focus on a single, clear subject that represents the article's core message.
            - Specify colors, lighting, and style to match the brand.
            
            {format_instructions}
            """),
            ("user", """
            Article Title: {title}
            Article Summary: {summary}
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def generate_image_concept(self, title: str, summary: str) -> Dict[str, str]:
        """
        Generates an image prompt and concept.
        """
        input_data = {
            "title": title,
            "summary": summary,
            "format_instructions": self.parser.get_format_instructions()
        }
        return self.invoke(input_data)
        
    def generate_image(self, prompt: str) -> str:
        """
        Simulates calling an image generator. 
        In a real implementation, this would call DALL-E 3.
        """
        # Placeholder for real DALL-E call
        # return "https://images.example.com/generated-image.jpg"
        self.logger.info(f"Generating image with prompt: {prompt}")
        # For now, we'll return a placeholder that mentions the prompt
        return f"https://placehold.co/1200x675?text=Image+for:+{prompt[:20]}..."
