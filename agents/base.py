from typing import Any, Dict, Optional
from contextvars import ContextVar
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import ValidationError
from config import Config
import logging
import time

# Set while building a fallback copy of an agent on the strong model.
_force_strong: ContextVar[bool] = ContextVar("force_strong", default=False)
PARSE_ERRORS = (OutputParserException, ValidationError)


def model_settings(model: str, tier: str, temperature: float) -> Dict[str, Any]:
    """Older models take a temperature; newer ones reject it and take reasoning_effort."""
    if any(model == m or model.startswith(m + "-") for m in Config.TEMPERATURE_MODELS):
        return {"temperature": temperature}
    effort = Config.FAST_REASONING_EFFORT if tier == "fast" else Config.STRONG_REASONING_EFFORT
    return {"reasoning_effort": effort} if effort else {}

class BaseAgent:
    def __init__(self, name: str, temperature: float = 0.7):
        self.name = name
        self.temperature = temperature
        strong = _force_strong.get()
        self.model = Config.STRONG_MODEL if strong else Config.model_for(name)
        self.tier = "strong" if strong else Config.tier_for(name)
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=Config.OPENAI_API_KEY,
            max_retries=Config.MAX_RETRIES,
            timeout=Config.REQUEST_TIMEOUT,
            **model_settings(self.model, self.tier, temperature),
        )
        self.prompt: Optional[ChatPromptTemplate] = None
        self.chain: Optional[RunnableSerializable] = None
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.usage_by_model: Dict[str, Dict[str, int]] = {}
        self.fallback_used = False
        
        # Initialize logger
        self.logger = logging.getLogger(f"agents.{self.name}")
        self.logger.info(
            f"Initialized {self.name} agent",
            extra={"extra_data": {"temperature": temperature, "model": self.model}}
        )

    def _record_usage(self, usage_cb: UsageMetadataCallbackHandler) -> None:
        for model, usage in usage_cb.usage_metadata.items():
            entry = self.usage_by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
            for key in ("input_tokens", "output_tokens"):
                entry[key] += usage.get(key, 0)
                self.usage[key] += usage.get(key, 0)

    def _invoke_strong_fallback(self, input_data: Dict[str, Any], error: Exception) -> Any:
        """Retry once on the strong model when a fast model's output can't be parsed."""
        self.logger.warning(f"{self.name} output from {self.model} was invalid ({type(error).__name__}), "
                            f"retrying on {Config.STRONG_MODEL}")
        token = _force_strong.set(True)
        try:
            strong = type(self)()
        finally:
            _force_strong.reset(token)
        try:
            return strong.invoke(input_data)
        finally:
            for model, usage in strong.usage_by_model.items():
                entry = self.usage_by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
                for key in ("input_tokens", "output_tokens"):
                    entry[key] += usage[key]
                    self.usage[key] += usage[key]
            self.fallback_used = True

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
            usage_cb = UsageMetadataCallbackHandler()
            try:
                result = chain.invoke(input_data, config={"callbacks": [usage_cb]})
            except PARSE_ERRORS as e:
                self._record_usage(usage_cb)
                if self.tier != "fast":
                    raise
                result = self._invoke_strong_fallback(input_data, e)
            else:
                self._record_usage(usage_cb)
            
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
