from typing import Any, Dict

import pytest

from sirius import common
from sirius.ai.large_language_model import Assistant, LargeLanguageModel
from sirius.ai.long_term_memory import LongTermMemory, LongTermMemoryDocumentType
from sirius.ai.open_ai import OpenAIGPTFunction


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_normal_conversation() -> None:
    conversation: Assistant = Assistant.get(LargeLanguageModel.GPT35_TURBO, prompt_template="You are only allowed to answer sarcastically")
    response: str = await conversation.ask("What is the capital of France?")
    assert response is not None


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_picture_context() -> None:
    conversation: Assistant = Assistant.get(LargeLanguageModel.GPT4_TURBO_VISION)
    response: str = await conversation.ask("Describe this image",
                                           image_url="https://lh3.googleusercontent.com/c5PxSgni0rirbjsdLLlcDTZXaNEHxH7Ioitt7yfIGp5W8BtPfYPWrAT2X68MKB1Zk2VcMkPfQgdaEZnVxKUVgQc2O6s36ySsvgwz")
    assert response is not None


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_function_call() -> None:
    def f(length: int | None = 16) -> Dict[str, Any]:
        """
        Args:
            length: The length of the unique ID in the Central Finite Curve's unique ID format

        Returns:
            A unique ID in the Central Finite Curve's unique ID format
        """
        return {"unique_id": common.get_unique_id(length)}

    chat_gpt_function: OpenAIGPTFunction = OpenAIGPTFunction(f)
    conversation: Assistant = Assistant.get(LargeLanguageModel.GPT35_TURBO, function_list=[chat_gpt_function])
    response: str = await conversation.ask("Generate a unique ID in the Central Finite Curve's unique ID format that has a length of 32")
    assert response is not None


# @pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_long_term_memory() -> None:
    long_term_memory: LongTermMemory = await LongTermMemory.remember_from_url("https://raw.githubusercontent.com/IbcAlpha/IBC/master/userguide.md", LongTermMemoryDocumentType.MARKDOWN, "The IBC User Guide")

    async def f(question: str) -> str:
        """
        Args:
            question: A question about IBC

        Returns:
            Information about IBC from the IBC User Guide. The results are in JSON format containing a list of information retrieved (split into chunks) along with their accuracy score (the higher the score the better the accuracy).
        """
        return await long_term_memory.recollect_for_llm(question, max_l2_distance=0.5)

    chat_gpt_function: OpenAIGPTFunction = OpenAIGPTFunction(f)
    conversation: Assistant = Assistant.get(LargeLanguageModel.GPT35_TURBO, function_list=[chat_gpt_function])
    response: str = await conversation.ask("What does the IBC use guide say about the software needed to run IBC?")
    assert response is not None
