from enum import Enum

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSequence
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
    chain: RunnableSequence | None = None

    def __init__(self, large_language_model: LargeLanguageModel, temperature: float = 0.2, prompt_template: str = ""):
        super().__init__()
        chat_prompt_template: ChatPromptTemplate = ChatPromptTemplate.from_messages([
            ("system", prompt_template),
            ("user", "{input}")
        ])
        llm: ChatOpenAI = ChatOpenAI(model=large_language_model.value, openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY), temperature=temperature)  # type: ignore[call-arg]
        self.chain = chat_prompt_template | llm | StrOutputParser()  # type: ignore[assignment]

    def ask(self, question: str) -> str:
        return self.chain.invoke({"input": question})
