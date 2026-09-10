import os
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model

from icm_platform.agent.ports import ChatTurn, CodeRunner
from icm_platform.models import refusal

DEFAULT_MODEL = "openai:gpt-5.2"


@dataclass
class HarnessDeps:
    """What one run of the agent is given: its instructions, and its sandbox (if any)."""

    instructions: str
    run_code: CodeRunner | None


class PydanticAgentHarness:
    """`AgentHarnessPort` backed by a Pydantic AI `Agent`.

    The only tool registered is `run_code`, and it goes to the hosted sandbox
    seam -- so the model can never write files or execute anything on host
    infrastructure. Without a sandbox the tool refuses, leaving the model with
    text grounded in the instructions it's given.
    """

    def __init__(self, model: str | Model | None = None) -> None:
        self._agent = Agent(
            model or os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
            name="workspace_chat_agent",
            deps_type=HarnessDeps,
        )

        @self._agent.instructions
        def _load_instructions(ctx: RunContext[HarnessDeps]) -> str:
            return ctx.deps.instructions

        @self._agent.tool
        def run_code(ctx: RunContext[HarnessDeps], command: str) -> str:
            """Run a shell command in the session's sandbox and return its output."""
            if ctx.deps.run_code is None:
                return refusal(command, "this session cannot run code")
            return ctx.deps.run_code(command)

    def reply(
        self,
        instructions: str,
        history: list[ChatTurn],
        message: str,
        run_code: CodeRunner | None = None,
    ) -> str:
        result = self._agent.run_sync(
            message,
            deps=HarnessDeps(instructions=instructions, run_code=run_code),
            message_history=_to_model_messages(history),
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
