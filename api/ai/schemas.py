from dataclasses import dataclass
from typing import Optional, Type

from pydantic import BaseModel

from ai.constants import DEFAULT_MODEL, DEFAULT_TEMPERATURE


@dataclass
class AIQueryInput:
    prompt: str
    system_prompt: Optional[str] = None
    response_format: Optional[Type[BaseModel]] = None
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
