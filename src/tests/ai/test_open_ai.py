import pytest

from sirius.ai.large_language_model import Conversation, LargeLanguageModel


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
