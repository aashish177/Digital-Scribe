from typing import Any, Dict, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from config import Config

class BaseAgent:
    def __init__(self, name: str, temperature: float = 0.7):
        self.name = name
        self.llm = ChatAnthropic(
            model=Config.MODEL_NAME,
            temperature=temperature,
            api_key=Config.ANTHROPIC_API_KEY
        )
        self.prompt: Optional[ChatPromptTemplate] = None
        self.chain: Optional[RunnableSerializable] = None

    def get_chain(self) -> RunnableSerializable:
        if not self.chain:
            raise ValueError(f"Agent {self.name} has no chain defined")
        return self.chain

    def invoke(self, input_data: Dict[str, Any]) -> Any:
        try:
            print(f"[{self.name}] Processing...")
            chain = self.get_chain()
            result = chain.invoke(input_data)
            return result
        except Exception as e:
            print(f"[{self.name}] Error: {str(e)}")
            raise e
