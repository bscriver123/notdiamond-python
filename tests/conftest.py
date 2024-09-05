"""File to define fixtures for Pytest"""

import json
import os
import random
import sys
from typing import Any, Dict, List

import pandas as pd
import pytest
import requests
from pydantic import BaseModel, Field

from notdiamond.callbacks import NDLLMBaseCallbackHandler
from notdiamond.llms.client import _NDClientTarget, _ndllm_factory
from notdiamond.llms.config import LLMConfig
from notdiamond.toolkit import CustomRouter

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))


@pytest.fixture
def prompt():
    return [
        {
            "role": "user",
            "content": "Write me a song about goldfish on the moon",
        }
    ]


@pytest.fixture
def openai_style_messages():
    """Fixture to create a Prompt Template"""
    return [
        {"role": "user", "content": "Hello, what's your name?"},
        {"role": "assistant", "content": "My name is Isaac Asimov"},
        {"role": "user", "content": "And what do you do?"},
    ]


@pytest.fixture
def llm_base_callback_handler():
    """Fixture to create a custom NDLLMBaseCallbackHandler"""

    class CustomNDLLMBaseCallbackHandler(NDLLMBaseCallbackHandler):
        def on_model_select(self, model_provider, model_name):
            self.on_model_select_called = True

        def on_latency_tracking(
            self, session_id, model_provider, tokens_per_second
        ):
            self.on_latency_tracking_called = True

        def on_api_error(self, error_message):
            self.on_api_error_called = True

        def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
        ):
            self.on_llm_start_called = True

    return CustomNDLLMBaseCallbackHandler()


@pytest.fixture
def tools_fixture():
    """Fixture that creates multiple tools"""
    from langchain_core.tools import tool

    @tool
    def add_fct(a: int, b: int) -> int:
        """Adds a and b."""
        return a + b

    return [add_fct]


@pytest.fixture
def openai_tools_fixture():
    """Fixture that creates multiple tools"""

    add_tool = {
        "name": "add_fct",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer", "description": "The first number"},
                "b": {"type": "integer", "description": "The second number"},
            },
            "required": ["a", "b"],
        },
    }

    return [add_tool]


@pytest.fixture
def response_model():
    class Joke(BaseModel):
        setup: str = Field(description="question to set up a joke")
        punchline: str = Field(description="answer to resolve the joke")

    return Joke


@pytest.fixture
def custom_router_dataset(
    url="https://github.com/google/BIG-bench/raw/main/bigbench/benchmark_tasks/implicatures/task.json",
):
    task = json.loads(requests.get(url).content)
    inputs = []
    for x in task["examples"][:15]:
        inputs.append(x["input"].strip())

    llm_configs = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku-20240307",
    ]

    dataset = {}
    for provider in llm_configs:
        data = {
            "query": inputs,
            "response": inputs,
            "score": [random.randrange(0, 10) for _ in inputs],
        }
        dataset[provider] = pd.DataFrame(data)
    return dataset, "query", "response", "score"


@pytest.fixture
def custom_router_and_model_dataset(
    url="https://github.com/google/BIG-bench/raw/main/bigbench/benchmark_tasks/implicatures/task.json",
):
    task = json.loads(requests.get(url).content)
    inputs = []
    for x in task["examples"][:15]:
        inputs.append(x["input"].strip())

    custom_model = LLMConfig(
        provider="custom",
        model="model",
        is_custom=True,
        context_length=100,
        input_price=1,
        output_price=2,
        latency=0.1,
    )

    llm_configs = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku-20240307",
        custom_model,
    ]

    dataset = {}
    for provider in llm_configs:
        data = {
            "query": inputs,
            "response": inputs,
            "score": [random.randrange(0, 10) for _ in inputs],
        }
        dataset[provider] = pd.DataFrame(data)
    return dataset, "query", "response", "score"


@pytest.fixture
def custom_router_pref_id(custom_router_dataset):
    (
        dataset,
        prompt_column,
        response_column,
        score_column,
    ) = custom_router_dataset
    custom_router = CustomRouter()

    preference_id = custom_router.fit(
        dataset=dataset,
        prompt_column=prompt_column,
        response_column=response_column,
        score_column=score_column,
    )
    assert isinstance(preference_id, str)
    return preference_id


@pytest.fixture
def nd_invoker_cls():
    return _ndllm_factory(_NDClientTarget.INVOKER)


@pytest.fixture
def nd_router_cls():
    return _ndllm_factory(_NDClientTarget.ROUTER)
