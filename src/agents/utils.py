from src.models import select_model
from src.agents.registry import BaseAgent
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessageChunk, ToolMessage




def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    return select_model(model_name=model, model_provider=provider).chat_open_ai


def agent_cli(agent: BaseAgent, config: RunnableConfig = None):
    config = config or {}
    if "configurable" not in config:
        config["configurable"] = {}

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_flag = False
        for msg, metadata in agent.stream_messages([{"role": "user", "content": user_input}], config):
            if isinstance(msg, AIMessageChunk):
                content = msg.content or msg.tool_calls

                if not content:
                    if stream_flag == True:
                        print()
                        stream_flag = False
                    continue

                if stream_flag == False and content:
                    print(f"AI: {content}", end="", flush=True)
                    stream_flag = True
                    continue

                elif content:
                    print(f"{content}", end="", flush=True)

            if isinstance(msg, ToolMessage):
                print(f"Tool: {msg.content}")
