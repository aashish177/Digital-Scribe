from typing import Dict, List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from agents.base import BaseAgent
from config import Config
from vector_stores.chroma import ChromaDBManager


class EditResult(BaseModel):
    content: str = Field(description="The full polished article in Markdown")
    changes: List[str] = Field(description="Short bullet points describing the changes made")


class EditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Editor", temperature=Config.EDITOR_TEMP)

        self.db = ChromaDBManager()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Content Editor. Your goal is to refine content to perfection.

            Inputs:
            1. Draft Content
            2. Content Brief (requirements, including target word count)
            3. Style Guide (brand rules)

            Instructions:
            - Check against the Style Guide (voice, formatting).
            - Ensure all requirements in the Brief are met.
            - Fix grammar, flow, and clarity issues.
            - Do NOT change the core facts or meaning, and do NOT add new facts or figures.
            - Keep every [n] citation attached to the claim it supports.
            - Keep the article close to its current length. Only remove content that is genuinely redundant.
            - If a section is thin or underdeveloped, note it in your changes instead of inventing material.
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

        self.chain = self.prompt | self.llm.with_structured_output(EditResult)

    def edit(self, draft: str, brief: Dict) -> Tuple[str, str]:
        """
        Edits the draft content.

        Returns:
            Tuple containing:
            1. Edited content
            2. Notes on changes made
        """
        style_docs = self.db.query("style", "brand voice formatting", k=2)
        style_guide_text = "\n\n".join([d.page_content for d in style_docs])

        result = self.invoke({
            "draft": draft,
            "brief": str(brief),
            "style_guide": style_guide_text,
        })

        content = (result.content or "").strip() or draft
        notes = "\n".join(f"- {c}" for c in result.changes) or "Editor provided no specific notes."
        return content, notes
