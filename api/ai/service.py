from typing import TypeVar

from openai import OpenAI
from django.conf import settings
from pydantic import BaseModel

from ai.schemas import AIQueryInput
from ai.exceptions import AIServiceError

T = TypeVar("T", bound=BaseModel)


class AIService:
    @staticmethod
    def get_client() -> OpenAI:
        return OpenAI(api_key=settings.OPENAI_API_KEY)

    @staticmethod
    def query(input: AIQueryInput) -> BaseModel:
        try:
            client = AIService.get_client()

            messages = []
            if input.system_prompt:
                messages.append({"role": "system", "content": input.system_prompt})
            messages.append({"role": "user", "content": input.prompt})

            response = client.beta.chat.completions.parse(
                model=input.model,
                messages=messages,
                temperature=input.temperature,
                response_format=input.response_format,
            )

            return response.choices[0].message.parsed

        except Exception as e:
            raise AIServiceError(str(e))
