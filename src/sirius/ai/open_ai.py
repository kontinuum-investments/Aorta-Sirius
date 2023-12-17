import base64
import datetime
import json
from typing import Dict, List, Any, Callable

from genson import SchemaBuilder
from openai import AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion

from sirius import common
from sirius.ai.large_language_model import LargeLanguageModel, Conversation, Context, Function
from sirius.constants import EnvironmentSecret
from sirius.exceptions import SDKClientException

function_calling_supported_models: List[LargeLanguageModel] = [LargeLanguageModel.GPT35_TURBO, LargeLanguageModel.GPT4]


class ChatGPTContext(Context):
    role: str
    content: str | List[Any]
    name: str | None = None

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

    @staticmethod
    def get_function_context(function_name: str, function_response_json_string: str) -> Context:
        return ChatGPTContext(role="function", content=function_response_json_string, name=function_name)


class ChatGPTFunction(Function):

    def __init__(self, name: str, function: Callable, **kwargs: Any):
        super().__init__(function=function,
                         name=name,
                         description=function.__doc__.split("Args:")[0].replace("\n", "").strip(),
                         parameters=ChatGPTFunction._get_parameters(function),
                         **kwargs)

    @staticmethod
    def _get_parameters(function: Callable) -> Dict[str, Any]:
        annotation_dict: Dict[str, Any] = function.__annotations__
        builder: SchemaBuilder = SchemaBuilder()
        builder.add_schema({"type": "object", "properties": {}})
        sample_argument_type_list: List[Any] = [1, 1.1, "a", datetime.datetime.now(), datetime.date.today()]
        optional_property_list: List[str] = []

        for argument_name, argument_type in annotation_dict.items():
            if argument_name == "return":
                continue

            if isinstance(None, argument_type):
                optional_property_list.append(argument_name)

            for sample_argument in sample_argument_type_list:
                if isinstance(sample_argument, argument_type):
                    builder.add_object({argument_name: sample_argument})

        schema: Dict[str, Any] = builder.to_schema()
        for optional_property in optional_property_list:
            schema["required"].remove(optional_property)

        # TODO: Retrieve argument description from doc string
        schema["properties"]["length"]["description"] = "The required length of the unique ID"

        return schema


class ChatGPTConversation(Conversation):
    _client: AsyncOpenAI | None = None
    completion_token_usage: int
    prompt_token_usage: int
    total_token_usage: int
    chat_completion_list: List[ChatCompletion] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(completion_token_usage=0,  # type:ignore[call-arg]
                         prompt_token_usage=0,
                         total_token_usage=0,
                         **kwargs)

        if len(self.function_list) != 0 and self.large_language_model not in function_calling_supported_models:
            raise SDKClientException(f"The chosen model ({self.large_language_model.value}) does not support function calls.\n"
                                     f"Please use any of the following models: {', '.join([model.value for model in function_calling_supported_models])}")

        self._client = AsyncOpenAI(api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY))

    async def say(self, message: str, image_url: str | None = None, image_path: str | None = None) -> str:
        self._validate(message, image_url, image_path)
        if image_url is None and image_path is None:
            self.context_list.append(ChatGPTContext.get_user_context(message))

        return await self._get_response()

    def _validate(self, message: str, image_url: str | None = None, image_path: str | None = None) -> None:
        if image_url is not None or image_path is not None:
            if self.large_language_model != LargeLanguageModel.GPT4_VISION:
                raise SDKClientException(f"Only GPT-4V model can be used to analyze images")

            elif image_url is not None and image_path is None:
                self.context_list.append(ChatGPTContext.get_image_from_url_context(message, image_url))

            elif image_url is None and image_path is not None:
                self.context_list.append(ChatGPTContext.get_image_from_path_context(message, image_path))

            else:
                raise SDKClientException("Invalid request")

    def _get_tools_list(self) -> List[Dict[str, Any]]:
        f: Callable = lambda f1: {
            "type": "function",
            "function": {
                "name": f1.name,
                "description": f1.description,
                "parameters": f1.parameters
            },
        }

        return list(map(f, self.function_list))

    async def _get_chat_completion(self) -> ChatCompletion:
        return await self._client.chat.completions.create(model=self.large_language_model.value,  # type: ignore[call-overload]
                                                          messages=[context.model_dump(exclude_none=True) for context in self.context_list],
                                                          n=1,
                                                          temperature=self.temperature,
                                                          max_tokens=self.max_tokens,
                                                          tools=self._get_tools_list(),
                                                          tool_choice="auto")

    async def _get_response(self) -> str:
        chat_completion: ChatCompletion = await self._get_chat_completion()
        self.chat_completion_list.append(chat_completion)
        self.completion_token_usage = self.completion_token_usage + chat_completion.usage.completion_tokens
        self.prompt_token_usage = self.completion_token_usage + chat_completion.usage.prompt_tokens
        self.total_token_usage = self.completion_token_usage + chat_completion.usage.total_tokens
        finish_reason: str = chat_completion.choices[0].finish_reason
        response: str = ""

        match finish_reason:
            case "stop":
                response = chat_completion.choices[0].message.content
                self.context_list.append(ChatGPTContext.get_assistant_context(response))

            case "tool_calls":
                function_name: str = chat_completion.choices[0].message.tool_calls[0].function.name
                args: Dict[str, Any] = json.loads(chat_completion.choices[0].message.tool_calls[0].function.arguments)
                function: ChatGPTFunction = next(filter(lambda f: f.name == function_name, self.function_list))  # type: ignore[assignment]
                function_response_json_string: str = json.dumps(function.function(**args))

                response = await self._get_function_response(function, function_response_json_string)

        return response

    async def _get_function_response(self, function: ChatGPTFunction, function_response_json_string: str) -> str:
        self.context_list.append(ChatGPTContext.get_function_context(function.name, function_response_json_string))
        return await self._get_response()
