import pytest

from sirius.ai.large_language_model_langchain import LargeLanguageModel, Agent, Loader


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_normal_conversation() -> None:
    loader: Loader = Loader.get_web_loader("langsmith_search", "Search for information about LangSmith. For any questions about LangSmith, you must use this tool!", "https://docs.smith.langchain.com/overview")
    agent: Agent = Agent.get(LargeLanguageModel.GPT35_TURBO, "Your name is Athena", loader_list=[loader])

    await agent.ask("how can langsmith help with testing?")
    reply: str = await agent.ask("Summarize your last message")
    assert reply is not None
