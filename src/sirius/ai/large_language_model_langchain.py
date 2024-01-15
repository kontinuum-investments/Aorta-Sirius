from enum import Enum
from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from sirius import common
from sirius.common import DataClass
from sirius.constants import EnvironmentSecret


class LargeLanguageModel(Enum):
    GPT35_TURBO: str = "gpt-3.5-turbo"
    GPT35_TURBO_16K: str = "gpt-3.5-turbo-16k"
    GPT4: str = "gpt-4"
    GPT4_32K: str = "gpt-4-32k"
    GPT4_VISION: str = "gpt-4-vision-preview"


class Assistant(DataClass):
    #   TODO: Fix this
    llm: BaseChatModel | None = None
    message_list: List[BaseMessage] | None = None

    def ask(self, question: str) -> str:
        self.message_list.append(HumanMessage(content=question))
        ai_message: AIMessage = self.llm(self.message_list)
        self.message_list.append(ai_message)
        return ai_message.content  # type: ignore[return-value]

    @staticmethod
    def get(large_language_model: LargeLanguageModel, temperature: float = 0.2, prompt_template: str = "") -> "Assistant":
        assistant: Assistant = Assistant()
        assistant.message_list = [SystemMessage(content=prompt_template)]
        assistant.llm = ChatOpenAI(model=large_language_model.value,
                                   openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY),
                                   temperature=temperature)  # type: ignore[call-arg]
        return assistant
