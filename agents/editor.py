from typing import Tuple, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.base import BaseAgent
from config import Config
from vector_stores.chroma import ChromaDBManager

class EditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Editor", temperature=Config.EDITOR_TEMP)
        
        self.db = ChromaDBManager()
        self.parser = StrOutputParser()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Content Editor. Your goal is to refine content to perfection.
            
            Inputs:
            1. Draft Content
            2. Content Brief (requirements, including target word count)
            3. Style Guide (brand rules)
            
            Instructions:
            - Check against the Style Guide (voice, formatting).
            - Ensure all requirements in the Brief are met, including the target word count.
            - Fix grammar, flow, and clarity issues.
            - Do NOT change the core facts or meaning.
            - PRESERVE WORD COUNT: Do not remove significant content. The article should remain close to the target word count specified in the brief.
            - If a section is thin or underdeveloped, note it in your changes summary but do NOT cut other sections to compensate.
            - Only remove content that is genuinely redundant or factually wrong.
            
            Output Format:
            Provide two sections separated by '---DIVIDER---':
            1. The Polished Content (Markdown)
            2. A summary of Changes Made (Bullet points)
            """),
            ("user", """
            Brief:
            {brief}
            
            Style Guide:
            {style_guide}
            
            Draft Content:
            {draft}
            """)
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def edit(self, draft: str, brief: Dict) -> Tuple[str, str]:
        """
        Edits the draft content.
        
        Returns:
            Tuple containing:
            1. Edited content
            2. Notes on changes made
        """
        # Retrieve Style Guide info
        # In a real scenario, we might query based on specific sections needed
        # For now, retrieve general voice/formatting guidelines
        style_docs = self.db.query("style", "brand voice formatting", k=2)
        style_guide_text = "\n\n".join([d.page_content for d in style_docs])
        
        input_data = {
            "draft": draft,
            "brief": str(brief),
            "style_guide": style_guide_text
        }
        
        result_text = self.invoke(input_data)
        
        # Parse logic to separate content from notes
        if "---DIVIDER---" in result_text:
            parts = result_text.split("---DIVIDER---")
            edited_content = parts[0].strip()
            notes = parts[1].strip()
        else:
            # Fallback if model forgets format
            edited_content = result_text
            notes = "Editor provided no specific notes."
            
        return edited_content, notes
