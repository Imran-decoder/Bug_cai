import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor

from tools import search_tool, wiki_tool, save_tool, human_assistant,codeql_tool
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages

from system_prompts import prompt1, spy, gpt_prompt

# ------------ State type --------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    # optional routing key (set by node functions)
    next: str | None

# --------------------Load API keys -------------------------
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("ARSHAD_API_KEY")

# -------------------- Node implementations ------------------
def interact_step1(state: State):
    """
    Multimodel agent entry node. Uses Gemini to produce a first-pass reply.
    Returns messages and does NOT set 'next' by itself.
    """
    last_message = state["messages"][-1]
    # llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=gemini_key)
    llm = ChatOpenAI(
        model="xai/grok-3",
        # model="gpt-4o-mini",
        api_key=openai_key,
        base_url="https://models.github.ai/inference",
    )
    tools = [search_tool, wiki_tool, save_tool, human_assistant]
    prompt = prompt1()
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"input": last_message})

    # make sure reply is a string
    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)

    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}


def define_path_gpt(state: State):
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        # model="gpt-3.5-turbo",
        model="xai/grok-3",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, save_tool]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an orchestrator agent. Decide the best route."),

        MessagesPlaceholder("agent_scratchpad"),  # 👈 required!
    ])
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    if hasattr(last_message, "content"):
        input_text = last_message.content
    else:
        input_text = last_message.get("content", "")

    reply = agent_executor.invoke({"input": last_message})

    # make sure reply is a string
    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)

    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}


def info_spy_step3(state: State):
    """
    Researcher node: runs deeper analysis / reconnaissance using DeepSeek-like model and tools.
    """
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="deepseek/DeepSeek-R1",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool]
    prompt = spy()
    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=tools
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"input": last_message})

    # make sure reply is a string
    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)

    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}


# -------------------- Build graph -------------------------
graph = StateGraph(State)

# Add nodes (name must match the string keys used in conditional edges)
graph.add_node("multimodel_agent", interact_step1)
graph.add_node("Router&analysis", define_path_gpt)
graph.add_node("Researcher", info_spy_step3)

# Edges: START -> multimodel_agent -> Router&analysis -> conditional -> Researcher or END
graph.add_edge(START, "multimodel_agent")
graph.add_edge("multimodel_agent", "Router&analysis")

# conditional: the condition function reads the state's 'next' key and returns the matching mapping key
# mapping keys must be strings; map "Researcher" -> "Researcher" (node name)
graph.add_conditional_edges(
    "Router&analysis",
    lambda state: state.get("next"),
    {"Researcher": "Researcher"}
)

# fallback/explicit ends
graph.add_edge("multimodel_agent", END)
graph.add_edge("Router&analysis", END)

app = graph.compile()

# -------------------- Orchestrator loop -------------------------
def run_orchestrator():
    state: State = {"messages": [], "next": None}

    while True:
        user_input = input("Message: ")
        if user_input.strip().lower() == "exit":
            print("Bye 👋")
            break

        state["messages"].append({"role": "user", "content": user_input})
        # run graph — this will execute nodes and update state
        state = app.invoke(state)   # run graph

        # latest assistant message (if any)
        if state["messages"]:
            print("Assistant:", state["messages"][-1])
        else:
            print("Assistant: <no output>")

if __name__ == "__main__":
    run_orchestrator()
