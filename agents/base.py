from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from config import Config
import logging
import time

class BaseAgent:
    def __init__(self, name: str, temperature: float = 0.7):
        self.name = name
        self.temperature = temperature
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=temperature,
            api_key=Config.OPENAI_API_KEY
        )
        self.prompt: Optional[ChatPromptTemplate] = None
        self.chain: Optional[RunnableSerializable] = None
        
        # Initialize logger
        self.logger = logging.getLogger(f"agents.{self.name}")
        self.logger.info(
            f"Initialized {self.name} agent",
            extra={"extra_data": {"temperature": temperature, "model": Config.MODEL_NAME}}
        )

    def get_chain(self) -> RunnableSerializable:
        if not self.chain:
            raise ValueError(f"Agent {self.name} has no chain defined")
        return self.chain

    def invoke(self, input_data: Dict[str, Any]) -> Any:
        """
        Invoke the agent with input data.
        
        Logs execution time and any errors that occur.
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"{self.name} processing started")
            chain = self.get_chain()
            result = chain.invoke(input_data)
            
            duration = time.time() - start_time
            self.logger.info(
                f"{self.name} completed successfully in {duration:.2f}s",
                extra={"extra_data": {"duration_seconds": duration}}
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"{self.name} failed after {duration:.2f}s: {str(e)}",
                extra={
                    "extra_data": {
                        "duration_seconds": duration,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                },
                exc_info=True
            )
            raise
