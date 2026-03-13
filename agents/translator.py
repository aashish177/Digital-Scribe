from typing import Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.base import BaseAgent
from config import Config

class TranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Translator", temperature=0.3) # Low temperature for factual translation
        self.parser = StrOutputParser()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator. Your goal is to translate the provided content accurately into the target language.
            
            - Maintain the original tone and voice of the article.
            - Ensure technical terms are translated correctly in context.
            - Preserve markdown formatting.
            - Do not add any commentary or extra text; only provide the translated content.
            """),
            ("user", """
            Target Language: {target_language}
            
            Content to Translate:
            {content}
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def translate(self, content: str, target_language: str) -> str:
        """
        Translates content into the target language.
        """
        input_data = {
            "content": content,
            "target_language": target_language
        }
        return self.invoke(input_data)
