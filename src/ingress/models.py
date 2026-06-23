"""OpenAI-compatible request models for Smart-Provider ingress.

These models decouple the external client protocol from litellm's internal
``CompletionRequest`` type, allowing Smart-Provider to accept standard OpenAI
request fields (such as ``tools`` as an object array) regardless of how litellm
models them internally.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class FunctionDefinition(BaseModel):
    """OpenAI function definition used inside ``tools`` and ``functions``."""

    name: str = Field(min_length=1)
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None


class CompletionTool(BaseModel):
    """OpenAI tool definition (currently only ``function`` tools)."""

    type: Literal["function"] = "function"
    function: FunctionDefinition


class SmartProviderCompletionRequest(BaseModel):
    """Internal representation of an OpenAI-compatible chat completion request.

    The model accepts all OpenAI-standard fields that Smart-Provider needs to
    understand directly, while using ``extra="allow"`` to preserve arbitrary
    additional fields (such as ``chat_template_kwargs``) for upstream passthrough.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )

    model: str = Field(min_length=1)
    messages: list[dict[str, Any]]
    stream: Optional[bool] = None

    # OpenAI-compatible function calling fields. litellm's CompletionRequest
    # models these incorrectly for direct client parsing, so we declare them
    # explicitly here.
    tools: Optional[list[CompletionTool]] = None
    tool_choice: Optional[str | dict[str, Any]] = None
    functions: Optional[list[dict[str, Any]]] = None
    function_call: Optional[str | dict[str, Any]] = None
