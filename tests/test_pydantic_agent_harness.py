from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from icm_platform.agent.ports import ChatTurn
from icm_platform.agent.pydantic_harness import PydanticAgentHarness


def test_sandbox_is_the_harnesss_only_tool() -> None:
    """One tool, and it runs code in the sandbox: no way to write the canonical tree."""
    model = TestModel()
    harness = PydanticAgentHarness(model=model)

    harness.reply("be helpful", [], "hello")

    params = model.last_model_request_parameters
    assert params is not None
    assert [tool.name for tool in params.function_tools] == ["run_code"]


def test_run_code_tool_calls_the_sessions_sandbox() -> None:
    model = TestModel()
    harness = PydanticAgentHarness(model=model)
    commands: list[str] = []

    def run_code(command: str) -> str:
        commands.append(command)
        return "exit code: 0"

    harness.reply("be helpful", [], "run something", run_code)

    assert len(commands) == 1


def test_run_code_refuses_when_the_session_has_no_sandbox() -> None:
    model = TestModel()
    harness = PydanticAgentHarness(model=model)

    with capture_run_messages() as messages:
        harness.reply("be helpful", [], "run something")

    returns = [
        part
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == "run_code"
    ]
    assert returns
    assert all("refused" in str(part.content) for part in returns)


def test_harness_forwards_prior_turns_as_message_history() -> None:
    model = TestModel()
    harness = PydanticAgentHarness(model=model)
    history = [ChatTurn(role="user", content="hi"), ChatTurn(role="assistant", content="hello")]

    with capture_run_messages() as messages:
        harness.reply("be helpful", history, "how are you")

    # 2 carried-over turns + 1 new request + 1 new response
    assert len(messages) == 4
