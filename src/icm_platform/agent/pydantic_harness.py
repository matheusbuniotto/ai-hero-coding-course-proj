import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model

from icm_platform.agent.ports import ChatTurn

DEFAULT_MODEL = "openai:gpt-5.2"


class PydanticAgentHarness:
    """Read-only `AgentHarnessPort` backed by a Pydantic AI `Agent`.

    No tools are registered, so the model has no way to write files or execute
    code -- it can only produce text grounded in the instructions it's given.
    """

    def __init__(self, model: str | Model | None = None) -> None:
        self._agent = Agent(
            model or os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
            name="workspace_chat_agent",
            deps_type=str,
        )

        @self._agent.instructions
        def _load_instructions(ctx: RunContext[str]) -> str:
            return ctx.deps

    def reply(self, instructions: str, history: list[ChatTurn], message: str) -> str:
        result = self._agent.run_sync(
            message, deps=instructions, message_history=_to_model_messages(history)
        )
        return result.output


def _to_model_messages(history: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages
