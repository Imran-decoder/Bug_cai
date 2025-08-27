import os
from dotenv import load_dotenv
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor

# Tools & prompts
from tools import search_tool, wiki_tool, save_tool, human_assistant
from system_prompts import prompt1, spy, gptprompt, route_map


# ----------------- Load API Keys -----------------
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")


# ----------------- Global Routing Vars -----------------
route = ""
route_bool = False


# ----------------- State -----------------
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ----------------- Nodes -----------------
def interact_step1(state: State):
    """Multimodel agent (Gemini)."""
    last_message = state["messages"][-1]

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=gemini_key)
    tools = [search_tool, wiki_tool, save_tool, human_assistant]

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt1())
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    reply = agent_executor.invoke({"query": last_message})

    return {"messages": [{"role": "assistant",
                          "content": reply["output"]}]}


def define_path_gpt(state: State):
    """Validation + routing decision (GPT-4o)."""
    last_message = state["messages"][-1]

    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, save_tool]

    agent = create_tool_calling_agent(llm=llm,  prompt=gptprompt(), tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    reply = agent_executor.invoke({"query": last_message})

    # Route decision logic
    global route
    global route_bool
    if route_bool:
        route_message = route_map()
        route_message.append({
            "role": "user",
            "content": last_message
        })

        route = llm.invoke(route_message)   # fixed typo
    route_bool = True

    return {"messages": [{"role": "assistant", "content": reply["output"]}]}


def analyse_and_route(state: State):
    """Analysing + routing (DeepSeek)."""
    last_message = state["messages"][-1]

    llm = ChatOpenAI(
        model="deepseek/DeepSeek-V3-0324",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
        # temperature=1.0,
        # max_tokens=1000
    )
    tools = [search_tool, wiki_tool, human_assistant]

    agent = create_tool_calling_agent(llm=llm, prompt=spy(), tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    reply = agent_executor.invoke({"query": last_message})

    return {"messages": [{"role": "assistant", "content": reply["output"]}]}


def deep_research(state: State):
    """Deep research (loop node)."""
    return {"messages": [{"role": "assistant", "content": "Performed deep research"}]}


# ----------------- Build LangGraph -----------------
graph = StateGraph(State)

# Nodes
graph.add_node("multimodel_agent", interact_step1)
graph.add_node("validate_task", define_path_gpt)
graph.add_node("analyse_and_route", analyse_and_route)
graph.add_node("deep_research", deep_research)

# Edges
graph.add_edge(START, "multimodel_agent")
graph.add_edge("multimodel_agent", "validate_task")

# validate_task -> conditional routing
def validate_condition(state: State):
    global route
    if route and "security" in route.lower():
        return "true"
    return "end"

graph.add_conditional_edges(
    "validate_task",
    validate_condition,
    {
        "true": "analyse_and_route",
        "end": END
    }
)

# analyse_and_route -> conditional research
def analyse_condition(state: State):
    last = state["messages"][-1].lower()
    if "research" in last:
        return "deep"
    return "end"

graph.add_conditional_edges(
    "analyse_and_route",
    analyse_condition,
    {
        "deep": "deep_research",
        "end": END
    }
)

# loopback from deep research
graph.add_edge("deep_research", "analyse_and_route")

# ----------------- Compile -----------------
app = graph.compile()


# ----------------- Run Orchestrator -----------------
def run_orchestrator():
    state = {"messages": []}

    while True:
        user_input = input("Message: ")
        if user_input == "exit":
            print("Bye 👋")
            break

        state["messages"].append({"role": "user", "content": user_input})
        state = app.invoke(state)   # run graph

        print("Assistant:", state["messages"][-1])


if __name__ == "__main__":
    run_orchestrator()
