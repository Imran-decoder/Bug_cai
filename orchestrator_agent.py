import os
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI

from tools import search_tool, wiki_tool, save_tool, human_assistant
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from system_prompts import prompt1, spy, gptprompt, route_map, static_prompt


# ------------ Exterritorial work--------------
class State(TypedDict):
    messages: Annotated[list, add_messages]


# --------------------Load API keys tala chabi-------------------------
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("SHAYAN_API_KEY")
grok_key = os.getenv("ARSHAD_API_KEY")
mistral_key = None
lama_key = None
deepseek_key = None
mistral_codestral_key = None

route = ""
route_bool = False


def interact_step1(state: State):
    last_message = state["messages"][-1]
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=gemini_key)
    tools = [search_tool, wiki_tool, save_tool, human_assistant]
    prompt = prompt1()
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"query": last_message})

    return {"messages": [{"role": "You are professional Cyber assistance to guide task into success ",
                          "content": reply["output"]}]}


def define_path_gpt(state: State):
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, save_tool]
    prompt = gptprompt()
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    # agent output
    reply = agent_executor.invoke({"query": last_message})
    # route defining
    global route
    global route_bool
    if route_bool:
        route_message = route_map()
        route_message.append({
            "role": "user",
            "content": last_message.content
        })

        route = llm.inovke(route_message)

    route_bool = True

    return {"messages": [{"role": "Reconnaissance or Cybersecurity assistance", "content": reply["output"]}]}


def info_spy_step3(state: State):
    last_message = state["messages"][-1]
    llm = ChatOpenAI(
        model="deepseek/DeepSeek-V3-0324",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
    )
    tools = [search_tool, wiki_tool, human_assistant]
    prompt = spy()
    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=tools
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    reply = agent_executor.invoke({"query": last_message})

    return {"messages": [{"role": "You are expert vulnerability finder.", "content": reply["output"]}]}


#
# def static_analysis(state: State):
#     last_message = state["messages"][-1]
#     llm = ChatOpenAI(
#         model="xai/grok-3",
#         api_key=grok_key,
#         base_url="https://models.github.ai/inference",
#     )
#     tools = [search_tool, wiki_tool, human_assistant]
#     prompt = static_prompt()
#     agent = create_tool_calling_agent(
#         llm=llm,
#         prompt=prompt,
#         tools=tools
#     )
#     agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
#     reply = agent_executor.invoke({"query": last_message})
#
#     return {"messages": [{"role": "Reconnaissance or Cyber assistance", "content": reply["output"]}]}


graph = StateGraph(State)
# Nodes

graph.add_node("multimodel_agent", interact_step1)
graph.add_node("Router&analysis", define_path_gpt)
graph.add_node("Researcher", info_spy_step3)

# Edges

graph.add_edge(START,"multimodel_agent")
graph.add_edge("multimodel_agent","Router&analysis")
graph.add_conditional_edges("Router&analysis",
                            lambda state: state.get("next"),
                            {"Research": route, }
                            )
graph.add_edge("multimodel_agent",END)
graph.add_edge("Router&analysis",END)
app = graph.compile()
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


