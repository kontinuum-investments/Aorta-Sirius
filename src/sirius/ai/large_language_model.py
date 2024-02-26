from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from typing import List, Callable, Dict, Any

from sirius.common import DataClass
from sirius.exceptions import OperationNotSupportedException


class LargeLanguageModel(Enum):
    GPT35_TURBO: str = "gpt-3.5-turbo"
    GPT35_TURBO_16K: str = "gpt-3.5-turbo-16k"
    GPT4: str = "gpt-4"
    GPT4_32K: str = "gpt-4-32k"
    GPT4_VISION: str = "gpt-4-vision-preview"
    GPT4_TURBO: str = "gpt-4-turbo-preview"
    GPT4_TURBO_VISION: str = "gpt-4-vision-preview"


open_ai_large_language_model_list: List["LargeLanguageModel"] = [
    LargeLanguageModel.GPT35_TURBO,
    LargeLanguageModel.GPT35_TURBO_16K,
    LargeLanguageModel.GPT4,
    LargeLanguageModel.GPT4_32K,
    LargeLanguageModel.GPT4_VISION,
    LargeLanguageModel.GPT4_TURBO,
    LargeLanguageModel.GPT4_TURBO_VISION,
]


class Context(DataClass, ABC):
    pass

    @staticmethod
    @abstractmethod
    def get_user_context(message: str) -> "Context":
        pass

    @staticmethod
    @abstractmethod
    def get_image_from_url_context(message: str, image_url: str) -> "Context":
        pass

    @staticmethod
    @abstractmethod
    def get_image_from_path_context(message: str, image_path: str) -> "Context":
        pass


class Function(DataClass, ABC):
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any]
    function_documentation: Dict[str, Any]


class Conversation(DataClass, ABC):
    large_language_model: LargeLanguageModel
    temperature: float
    context_list: List[Context] = []
    function_list: List[Function] = []
    max_tokens: int | None = None
    total_token_usage: int
    total_cost: Decimal = Decimal("0")

    @abstractmethod
    def add_system_prompt(self, system_prompt: str) -> None:
        pass

    @staticmethod
    def get_conversation(large_language_model: LargeLanguageModel,
                         temperature: float | None = 0.2,
                         context_list: List[Context] | None = None,
                         function_list: List[Function] | None = None) -> "Conversation":
        context_list = [] if context_list is None else context_list
        function_list = [] if function_list is None else function_list

        if large_language_model in open_ai_large_language_model_list:
            from sirius.ai.open_ai import ChatGPTConversation
            return ChatGPTConversation(large_language_model=large_language_model,
                                       temperature=temperature,
                                       context_list=context_list,
                                       function_list=function_list)

        raise OperationNotSupportedException(f"{large_language_model.value} is not yet supported")

    @abstractmethod
    async def say(self, message: str, image_url: str | None = None, image_path: str | None = None) -> str:
        pass
