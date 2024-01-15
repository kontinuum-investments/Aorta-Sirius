import pytest

from sirius.ai.large_language_model import Assistant, LargeLanguageModel


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_normal_conversation() -> None:
    assistant: Assistant = Assistant(LargeLanguageModel.GPT35_TURBO, prompt_template="End every answer with 'Your majesty'")
    answer: str = assistant.ask("Tell me a joke about polar bears")
    assert answer is not None
