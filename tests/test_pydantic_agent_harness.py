from pydantic_ai import capture_run_messages
from pydantic_ai.models.test import TestModel

from icm_platform.agent.ports import ChatTurn
from icm_platform.agent.pydantic_harness import PydanticAgentHarness


def test_harness_registers_no_tools() -> None:
    """No tools means the model can only reply in text: no writes, no execution."""
    model = TestModel()
    harness = PydanticAgentHarness(model=model)

    harness.reply("be helpful", [], "hello")

    params = model.last_model_request_parameters
    assert params is not None
    assert params.function_tools == []


def test_harness_forwards_prior_turns_as_message_history() -> None:
    model = TestModel()
    harness = PydanticAgentHarness(model=model)
    history = [ChatTurn(role="user", content="hi"), ChatTurn(role="assistant", content="hello")]

    with capture_run_messages() as messages:
        harness.reply("be helpful", history, "how are you")

    # 2 carried-over turns + 1 new request + 1 new response
    assert len(messages) == 4
