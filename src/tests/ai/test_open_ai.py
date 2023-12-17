from typing import Callable

import pytest

from sirius import common
from sirius.ai.large_language_model import Conversation, LargeLanguageModel
from sirius.ai.open_ai import ChatGPTFunction


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_normal_conversation() -> None:
    conversation: Conversation = Conversation.get_conversation(LargeLanguageModel.GPT35_TURBO)
    await conversation.say("You are only allowed to answer sarcastically")
    response: str = await conversation.say("What is the capital of France?")
    assert response is not None


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_picture_context() -> None:
    conversation: Conversation = Conversation.get_conversation(LargeLanguageModel.GPT4_VISION)
    response: str = await conversation.say("Describe this image",
                                           image_url="https://lh3.googleusercontent.com/c5PxSgni0rirbjsdLLlcDTZXaNEHxH7Ioitt7yfIGp5W8BtPfYPWrAT2X68MKB1Zk2VcMkPfQgdaEZnVxKUVgQc2O6s36ySsvgwz")
    assert response is not None


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_function_call() -> None:
    f: Callable = lambda: {"unique_id": common.get_unique_id()}
    chat_gpt_function: ChatGPTFunction = ChatGPTFunction(name="UNIQUE_ID", function=f, description="Generates a unique ID in the Central Finite Curve's unique ID format")
    conversation: Conversation = Conversation.get_conversation(LargeLanguageModel.GPT35_TURBO, function_list=[chat_gpt_function])
    response: str = await conversation.say("Generate a unique ID in the Central Finite Curve's unique ID format", )
    assert response is not None
