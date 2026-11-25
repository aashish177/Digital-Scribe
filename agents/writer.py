from typing import Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agents.base import BaseAgent
from config import Config


class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Writer", temperature=Config.WRITER_TEMP)

        self.parser = StrOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Content Writer. Your goal is to write high-quality, engaging, long-form content that is accurate.

            Instructions:
            - Follow the outline in the content brief.
            - Adopt the tone and voice specified in the brief.
            - Build the article from the research findings. Keep their [n] citations after every fact you use, e.g. "... three to four units of heat [1]."
            - Only cite numbers that appear in the Sources list.
            - Do NOT invent statistics, figures, dates, quotes or studies. Any number in the article must come from the research.
            - You may add general explanation, examples and transitions, but no new factual claims without a citation.
            - Aim for about {word_count} words. If the research is too thin for that length, write a shorter accurate article rather than padding it.
            - Use markdown formatting (# for H1 title, ## for H2 sections, ### for H3 subsections).
            - Do not add a references section; the sources are listed separately.
            """),
            ("user", """
            Content Brief:
            {brief}

            Sources:
            {sources}

            Research Findings:
            {research}

            Target Word Count: {word_count} words
            Tone: {tone}

            Write the full article now.
            """)
        ])

        self.chain = self.prompt | self.llm | self.parser

    def write(self, brief: Dict, research: str, sources: Optional[List[Dict]] = None) -> str:
        """
        Generates content draft based on brief and research.
        """
        source_lines = "\n".join(f"[{s['n']}] {s['title']}" for s in sources or []) or "None"
        input_data = {
            "brief": str(brief),
            "research": research,
            "sources": source_lines,
            "word_count": brief.get("word_count_target", 800),
            "tone": brief.get("tone", "professional"),
        }
        return self.invoke(input_data)
