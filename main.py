import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from tools import (
    search_tool, wiki_tool, save_tool,
    human_assistant, terminal_tool,
    scan_semgrep, scan_bandit, scan_pip_audit, scan_trufflehog
)
from system_prompts import prompt1,prompt2,prompt3,prompt4
from functions import extract_route

# perfrom static analysic on webapp-in-python which is present at ~/desktop/mcp

import asyncio
import threading
import concurrent.futures
from typing import Any

def run_coro_sync(coro) -> Any:
    """
    Run an async coroutine from sync code and return its result.
    - Uses asyncio.run() if possible (recommended).
    - If a running loop is present, it creates a new loop in a background thread
      and runs the coroutine there, returning the result synchronously.
    """
    try:
        # Preferred, modern API (creates and closes a fresh loop)
        return asyncio.run(coro)
    except RuntimeError:
        # There is already a running loop in this thread/process.
        # Run the coroutine in a new event loop on a background thread.
        fut = concurrent.futures.Future()

        def _thread_run():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(coro)
                fut.set_result(result)
            except Exception as e:
                fut.set_exception(e)
            finally:
                try:
                    new_loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=_thread_run, daemon=True)
        t.start()
        return fut.result()


# ------------ State type --------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    # optional routing key (set by node functions)
    next: str | None


# --------------------Load API keys -------------------------
load_dotenv()
# gemini_key = os.getenv("GEMINI_API_KEY")
gemini2_key = "AIzaSyCJWMLHBWLqzoCvP9wiltjnsMeION8TyuY"
gemini_key = os.getenv("GEMINI_API_KEY")
# openai_key = os.getenv("ARSHAD2_API_KEY")
openai_key = os.getenv("SHAYAN_API_KEY")


# -------------------- Node implementations ------------------

def define_path_gpt(state: State):
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="openai/gpt-4.1",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, save_tool, human_assistant]
    # prompt = prompt1
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt1
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"query": last_message})


    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)
    # print(reply_text)
    value = extract_route(str(reply))
    next = value
    print(next)
    # next = "Dynamic"
    print("stage 1")
    return {"messages": [{"role": "assistant", "content": reply_text}], "next": next}


def info_spy_step3(state: State):
    """
    Researcher node: runs deeper analysis / reconnaissance using DeepSeek-like model and tools.
    """
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="deepseek/DeepSeek-V3-0324",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, save_tool, terminal_tool]
    prompt = prompt2
    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=tools
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"query": last_message})

    # make sure reply is a string
    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)
    # print(reply_text)
    print("stage 3")
    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}


def static_analysis(state: State):
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="deepseek/DeepSeek-V3-0324",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    # Choose your LLM
    # llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=gemini_key)

    prompt = prompt3

    tools = [
        search_tool, save_tool,
        human_assistant, terminal_tool,
        scan_semgrep, scan_bandit, scan_pip_audit, scan_trufflehog
    ]

    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"query": last_message})

    # make sure reply is a string
    if isinstance(reply, dict):
        reply_text = reply.get("output", str(reply))
    else:
        reply_text = str(reply)
    print("stage 3")

    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}



def dynamic_analysis(state: dict):
    """LangGraph node for performing dynamic analysis using ZAP + terminal tools."""

    last_message = state["messages"][-1]# last user query

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        api_key=gemini_key
    )

    # Define system + scratchpad prompt
    prompt = prompt4

    # Create MCP client (for ZAP tools)
    client = MultiServerMCPClient(
        {
            "zap_tools": {
                "command": "python3",
                "args": ["/Users/imran/Documents/code/random/Bug_ai/server/zap_tools.py"],
                "transport": "stdio",
                "env": {
                    "ZAP_PATH": "/Applications/OWASP ZAP.app/Contents/Java/zap.sh",
                    "ZAP_HOST": "127.0.0.1",
                    "ZAP_PORT": "8080",
                    "ZAP_API_KEY": "vd9q8hbq2ra4v2o8io0ancsc28",
                },
            }
        }
    )

    # Collect tools from MCP + local
    tools = []
    try:
        tools = run_coro_sync(client.get_tools())
    except Exception as e:
        # keep a helpful log for debugging; don't silently swallow errors
        print(f"Failed to get tools from MCP client: {e}")
        tools = []

    tools.append(terminal_tool)
    tools.append(search_tool)
    tools.append(wiki_tool)

    # Create tool-calling agent
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Run agent on last message
    try:
        reply = run_coro_sync(agent_executor.ainvoke({"query": last_message}))
        if isinstance(reply, dict):
            reply_text = reply.get("output", str(reply))
        else:
            reply_text = str(reply)
    except Exception as e:
        reply_text = f"❌ Error during dynamic analysis: {e}"

    print("stage 5 (dynamic_analysis done)")
    return {"messages": [{"role": "assistant", "content": reply_text}], "next": None}

# -------------------- Build graph -------------------------
graph = StateGraph(State)

# Add nodes (name must match the string keys used in conditional edges)

graph.add_node("Router_analysis", define_path_gpt)
graph.add_node("Researcher", info_spy_step3)
graph.add_node("Static", static_analysis)
graph.add_node("Dynamic", dynamic_analysis)
# Edges: START -> Router&analysis -> conditional -> Researcher or END
graph.add_edge(START, "Router_analysis")

# conditional: the condition function reads the state's 'next' key and returns the matching mapping key
# mapping keys must be strings; map "Researcher" -> "Researcher" (node name)
graph.add_conditional_edges(
    "Router_analysis",
    lambda state: state.get("next") or END,
    {"Researcher": "Researcher", "Static": "Static", "Dynamic": "Dynamic", "END": END}
)
# graph.add_edge("Router&analysis","Researcher")
graph.add_edge("Researcher", "Router_analysis")
graph.add_edge("Static", END)
graph.add_edge("Dynamic", END)

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
        state = app.invoke(state)  # run graph

        # latest assistant message (if any)
        if state["messages"]:
            print("Assistant:", state["messages"][-1])
        else:
            print("Assistant: <no output>")


if __name__ == "__main__":
    run_orchestrator()
