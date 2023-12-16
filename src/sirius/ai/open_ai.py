import base64
from typing import Dict, List, Any

from openai import AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion

from sirius import common
from sirius.ai.large_language_model import LargeLanguageModel, Conversation, Context
from sirius.constants import EnvironmentSecret
from sirius.exceptions import SDKClientException


class ChatGPTContext(Context):
    role: str
    content: str | List[Any]

    @staticmethod
    def get_system_context(message: str) -> Context:
        return ChatGPTContext(role="system", content=message)

    @staticmethod
    def get_user_context(message: str) -> Context:
        return ChatGPTContext(role="user", content=message)

    @staticmethod
    def get_image_from_url_context(message: str, image_url: str) -> Context:
        return ChatGPTContext(role="user",
                              content=[
                                  {"type": "text", "text": message},
                                  {
                                      "type": "image_url",
                                      "image_url": {
                                          "url": image_url,
                                      },
                                  },
                              ])

    @staticmethod
    def get_image_from_path_context(message: str, image_path: str) -> Context:
        with open(image_path, "rb") as image_file:
            base64_encoded_image: str = base64.b64encode(image_file.read()).decode("utf-8")

        return ChatGPTContext(role="user",
                              content=[
                                  {
                                      "type": "text",
                                      "text": message
                                  },
                                  {
                                      "type": "image_url",
                                      "image_url": {
                                          "url": f"data:image/jpeg;base64,{base64_encoded_image}"
                                      }
                                  }
                              ])

    @staticmethod
    def get_assistant_context(message: str) -> Context:
        return ChatGPTContext(role="assistant", content=message)


class ChatGPTConversation(Conversation):
    _client: AsyncOpenAI | None = None
    completion_token_usage: int
    prompt_token_usage: int
    total_token_usage: int

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(completion_token_usage=0,  # type:ignore[call-arg]
                         prompt_token_usage=0,
                         total_token_usage=0,
                         **kwargs)
        self._client = AsyncOpenAI(api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY))

    async def say(self, message: str,
                  image_url: str | None = None,
                  image_path: str | None = None,
                  options: Dict[str, Any] | None = None) -> str:

        temperature: float = 0.2 if options is None else options["temperature"]
        max_tokens: int = 1000 if options is None else options["max_tokens"]

        if image_url is None and image_path is None:
            self.context_list.append(ChatGPTContext.get_user_context(message))
        else:
            if self.large_language_model != LargeLanguageModel.GPT4_VISION:
                raise SDKClientException(f"Only GPT-4V model can be used to analyze images")

            if image_url is not None and image_path is None:
                self.context_list.append(ChatGPTContext.get_image_from_url_context(message, image_url))
            elif image_url is None and image_path is not None:
                self.context_list.append(ChatGPTContext.get_image_from_path_context(message, image_path))
            else:
                raise SDKClientException("Invalid request")

        chat_completion: ChatCompletion = await self._client.chat.completions.create(model=self.large_language_model.value if image_path is None and image_url is None else LargeLanguageModel.GPT4_VISION.value,
                                                                                     messages=[context.model_dump() for context in self.context_list],  # type:ignore[misc]
                                                                                     n=1,
                                                                                     temperature=temperature,
                                                                                     max_tokens=max_tokens)

        response: str = chat_completion.choices[0].message.content

        self.context_list.append(ChatGPTContext.get_assistant_context(response))
        self.completion_token_usage = self.completion_token_usage + chat_completion.usage.completion_tokens
        self.prompt_token_usage = self.completion_token_usage + chat_completion.usage.prompt_tokens
        self.total_token_usage = self.completion_token_usage + chat_completion.usage.total_tokens

        return response
