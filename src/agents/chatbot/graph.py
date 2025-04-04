import asyncio
import uuid
from typing import Any
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults


from src.agents.registry import State, BaseAgent
from src.agents.utils import load_chat_model
from src.agents.chatbot.configuration import ChatbotConfiguration, multiply

class ChatbotAgent(BaseAgent):
    name = "chatbot"
    description = "A chatbot that can answer questions and help with tasks."
    _graph_cache = None
    config_schema = ChatbotConfiguration.to_dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_tools(self, config_schema: RunnableConfig):
        """根据配置获取工具"""
        tools = [multiply, TavilySearchResults(max_results=10)]
        return tools

    def llm_call(self, state: State, config: RunnableConfig = None) -> dict[str, Any]:
        """调用 llm 模型"""
        config_schema = config or {}
        conf = ChatbotConfiguration.from_runnable_config(config_schema)
        model = load_chat_model(conf.model)
        model_with_tools = model.bind_tools(self._get_tools(config_schema))

        res = model_with_tools.invoke(
            [{"role": "system", "content": conf.system_prompt}, *state["messages"]]
        )
        return {"messages": [res]}

    def get_graph(self, config_schema: RunnableConfig = None):
        """构建图"""
        workflow = StateGraph(State, config_schema=ChatbotConfiguration)
        workflow.add_node("chatbot", self.llm_call)
        workflow.add_node("tools", ToolNode(tools=self._get_tools(config_schema)))
        workflow.add_edge(START, "chatbot")
        workflow.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        workflow.add_edge("tools", "chatbot")
        workflow.add_edge("chatbot", END)

        graph = workflow.compile(checkpointer=MemorySaver())
        return graph

    def stream_values(self, messages: list[str], config_schema: RunnableConfig = None):
        graph = self.get_graph(config_schema)
        for event in graph.stream({"messages": messages}, stream_mode="values", config=config_schema):
            yield event["messages"]

    def stream_messages(self, messages: list[str], config_schema: RunnableConfig = None):
        graph = self.get_graph(config_schema)
        conf = ChatbotConfiguration.from_runnable_config(config_schema)
        for msg, metadata in graph.stream({"messages": messages}, stream_mode="messages", config=config_schema):
            msg_type = msg.type

            return_keys =conf.return_keys
            if not return_keys or msg_type in return_keys:
                yield msg, metadata

def main():
    agent = ChatbotAgent(ChatbotConfiguration())

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    from src.agents.utils import agent_cli
    agent_cli(agent, config)


if __name__ == "__main__":
    main()
    # asyncio.run(main())
