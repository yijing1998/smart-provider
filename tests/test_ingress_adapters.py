"""Tests for the Smart-Provider ingress request adapter layer."""

import pytest
from pydantic import ValidationError

from src.ingress.adapters.openai import adapt
from src.ingress.models import SmartProviderCompletionRequest


class TestOpenAIAdapter:
    """Verify the OpenAI request adapter accepts standard OpenAI requests."""

    def test_basic_request_without_tools(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
        }
        req = adapt(raw)
        assert req.model == "gpt-4o"
        assert req.messages == [{"role": "user", "content": "hello"}]
        assert req.tools is None

    def test_tools_as_object_array(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "description": "Run a shell command",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                            },
                            "required": ["command"],
                        },
                    },
                }
            ],
        }
        req = adapt(raw)
        assert req.tools is not None
        assert len(req.tools) == 1
        assert req.tools[0].type == "function"
        assert req.tools[0].function.name == "bash"

    def test_tool_choice_string(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "bash", "parameters": {"type": "object"}},
                }
            ],
            "tool_choice": "auto",
        }
        req = adapt(raw)
        assert req.tool_choice == "auto"

    def test_tool_choice_object(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "bash", "parameters": {"type": "object"}},
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "bash"},
            },
        }
        req = adapt(raw)
        assert req.tool_choice == {"type": "function", "function": {"name": "bash"}}

    def test_functions_and_function_call(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "functions": [
                {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object"},
                }
            ],
            "function_call": "auto",
        }
        req = adapt(raw)
        assert req.functions is not None
        assert req.functions[0]["name"] == "get_weather"
        assert req.function_call == "auto"

    def test_extra_fields_preserved(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "chat_template_kwargs": {"foo": "bar"},
            "response_format": {"type": "json_object"},
        }
        req = adapt(raw)
        assert req.model_extra["chat_template_kwargs"] == {"foo": "bar"}
        assert req.model_extra["response_format"] == {"type": "json_object"}

    def test_invalid_tool_type_rejected(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "unsupported",
                    "function": {"name": "bash", "parameters": {"type": "object"}},
                }
            ],
        }
        with pytest.raises(ValidationError):
            adapt(raw)

    def test_missing_model_rejected(self):
        raw = {
            "messages": [{"role": "user", "content": "hello"}],
        }
        with pytest.raises(ValidationError):
            adapt(raw)

    def test_missing_messages_rejected(self):
        raw = {
            "model": "gpt-4o",
        }
        with pytest.raises(ValidationError):
            adapt(raw)


class TestSmartProviderCompletionRequestDump:
    """Verify the internal model can be dumped for upstream passthrough."""

    def test_model_dump_includes_tools_as_dicts(self):
        raw = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        }
        req = adapt(raw)
        body = req.model_dump(exclude_unset=True)
        assert body["tools"] == [
            {
                "type": "function",
                "function": {"name": "bash", "parameters": {"type": "object"}},
            }
        ]
