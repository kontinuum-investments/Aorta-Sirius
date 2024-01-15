import pytest

from sirius.ai.large_language_model_langchain import Assistant, LargeLanguageModel


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_normal_conversation() -> None:
    assistant: Assistant = Assistant.get(LargeLanguageModel.GPT4, prompt_template="Your name is Athena")
    assistant.ask("Tell me a joke about polar bears")
    answer: str = assistant.ask("Tell me a longer joke")
    assert answer is not None
