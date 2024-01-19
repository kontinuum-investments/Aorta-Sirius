import os
from typing import List

from langchain import hub
from langchain.agents import AgentExecutor
from langchain.agents import create_openai_functions_agent
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.tools import Tool
from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.vectorstores import FAISS
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from sirius import common
from sirius.common import DataClass
from sirius.constants import EnvironmentSecret
from sirius.database import ConfigurationEnum


class LargeLanguageModel(ConfigurationEnum):
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


class Loader(DataClass):
    loader: BaseLoader
    name: str
    description: str

    def get_retriever_tool(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> Tool:
        docs = self.loader.load()
        documents = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(docs)
        vector = FAISS.from_documents(documents, OpenAIEmbeddings())
        return create_retriever_tool(vector.as_retriever(), self.name, self.description)

    @staticmethod
    def get_web_loader(name: str, description: str, url: str) -> "Loader":
        return Loader(loader=WebBaseLoader(url), name=name, description=description)


class Agent(DataClass):
    #   TODO: This should not be None
    prompt_template: str | None = None
    agent_executor: AgentExecutor | None = None
    chat_history: List[BaseMessage] = []

    async def ask(self, question: str) -> str:
        reply: str = (await self.agent_executor.ainvoke({"input": question, "chat_history": self.chat_history}))["output"]
        self.chat_history = self.chat_history + [HumanMessage(content=question), AIMessage(content=reply)]
        return reply

    @staticmethod
    def get(large_language_model: LargeLanguageModel, prompt_template: str = "", temperature: float = 0.2, loader_list: List[Loader] | None = None) -> "Agent":
        loader_list = [] if loader_list is None else loader_list
        prompt = hub.pull("langchain-ai/openai-functions-template").partial(instructions=prompt_template)

        #   TODO: This needs to be a named parameter but that doesn't work for some reason
        os.environ["OPENAI_API_KEY"] = common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY)
        llm: ChatOpenAI = ChatOpenAI(model=large_language_model.value,
                                     # openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY),
                                     temperature=temperature)

        tools: List[Tool] = [loader.get_retriever_tool() for loader in loader_list]
        openai_agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)

        agent: Agent = Agent()
        agent.agent_executor = AgentExecutor(agent=openai_agent, tools=tools, verbose=True)  # type: ignore[arg-type]
        agent.prompt_template = prompt_template
        return agent
