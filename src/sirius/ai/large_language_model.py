from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List

from sirius.common import DataClass
from sirius.exceptions import OperationNotSupportedException


class LargeLanguageModel(Enum):
    GPT35_TURBO: str = "gpt-3.5-turbo"
    GPT35_TURBO_16K: str = "gpt-3.5-turbo-16k"
    GPT4: str = "gpt-4"
    GPT4_32K: str = "gpt-4-32k"
    GPT4_VISION: str = "gpt-4-vision-preview"


open_ai_large_language_model_list: List["LargeLanguageModel"] = [
    LargeLanguageModel.GPT35_TURBO,
    LargeLanguageModel.GPT35_TURBO_16K,
    LargeLanguageModel.GPT4,
    LargeLanguageModel.GPT4_32K,
    LargeLanguageModel.GPT4_VISION,
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


class Conversation(DataClass, ABC):
    large_language_model: LargeLanguageModel
    context_list: List[Context]

    @staticmethod
    def get_conversation(large_language_model: LargeLanguageModel) -> "Conversation":
        if large_language_model in open_ai_large_language_model_list:
            from sirius.ai.open_ai import ChatGPTConversation
            return ChatGPTConversation(large_language_model=large_language_model, context_list=[])

        raise OperationNotSupportedException(f"{large_language_model.value} is not yet supported")

    @abstractmethod
    async def say(self, message: str, image_url: str | None = None, image_path: str | None = None, options: Dict[str, Any] | None = None) -> str:
        pass
