from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.base import BaseAgent
from config import Config
from vector_stores.chroma import ChromaDBManager

class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Writer", temperature=Config.WRITER_TEMP)
        
        # We can use RAG here to find writing samples if needed
        self.db = ChromaDBManager()
        
        self.parser = StrOutputParser()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Content Writer. Your goal is to write high-quality, engaging, long-form content.
            
            Instructions:
            - Follow the outline in the content brief EXACTLY.
            - Adopt the tone and voice specified in the brief.
            - Integrate any research findings naturally into the article.
            - Use markdown formatting (# for H1 title, ## for H2 sections, ### for H3 subsections).
            - YOU MUST WRITE APPROXIMATELY {word_count} WORDS. This is mandatory.
            - Do NOT stop early. Fill each section with in-depth explanations, real-world examples, statistics, trends, and expert insights.
            - You may supplement sparse research with your own knowledge to reach the target length.
            - If a section is covered, go deeper: add a "Key Takeaways" subsection, a practical example, or a forward-looking analysis.
            - Write the complete, full-length article from start to finish without truncating or summarizing.
            """),
            ("user", """
            Content Brief:
            {brief}
            
            Research Findings:
            {research}
            
            Target Word Count: {word_count} words
            Tone: {tone}
            
            Write the full article now, ensuring you reach {word_count} words.
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def write(self, brief: Dict, research: str) -> str:
        """
        Generates content draft based on brief and research.
        """
        # Extract target values from brief
        word_count = brief.get("word_count_target", 800)
        tone = brief.get("tone", "professional")
        
        # Convert brief dict to string representation for the prompt
        brief_str = str(brief)
        
        input_data = {
            "brief": brief_str,
            "research": research,
            "word_count": word_count,
            "tone": tone,
        }
        
        return self.invoke(input_data)
