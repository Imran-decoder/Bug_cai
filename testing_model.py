import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain_community.graphs import Neo4jGraph
# from langchain_neo4j import Neo4jGraph
from langchain.tools import tool
from tools import search_tool, wiki_tool, save_tool, terminal_tool, human_assistant
from system_prompts import prompt1

load_dotenv()
uri= print(os.getenv("NEO4J_URI"))
# ---------------------------
# 1. Neo4j Connection
# ---------------------------
# Ensure NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD are in your .env
# from py2neo import Graph
# graph = Graph(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD')))
graph = Neo4jGraph(
    url="neo4j+s://d8b34f21.databases.neo4j.io:7687",
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

# Refreshes schema to ensure graph object has latest data
graph.refresh_schema()


# ---------------------------
# 2. Define Neo4j Tools
# ---------------------------

# TOOL A: Get Schema (CRITICAL: The AI needs this to know what Node Labels exist)
@tool
def get_graph_schema(ignore: str = "") -> str:
    """
    Useful for retrieving the schema of the Neo4j knowledge graph.
    Call this BEFORE writing any Cypher queries to understand the Node Labels
    and Relationships available.
    """
    return graph.schema


# TOOL B: Run Cypher (Handles both READ and WRITE)
@tool
def run_cypher_query(query: str) -> str:
    """
    Useful for running Cypher queries against the Neo4j database.
    Can be used to read data (MATCH) or write data (CREATE/MERGE).
    Always check the schema using get_graph_schema before constructing a query.
    """
    try:
        # graph.query returns a list of dictionaries
        result = graph.query(query)
        return str(result)
    except Exception as e:
        return f"Cypher Execution Error: {e}"


# ---------------------------
# 3. Memory
# ---------------------------
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# ---------------------------
# 4. LLM
# ---------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",  # Recommended for Agent logic
    temperature=0,  # Keep temp low for code generation
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# ---------------------------
# 5. Tools List
# ---------------------------
tools = [
    search_tool,
    wiki_tool,
    save_tool,
    terminal_tool,
    human_assistant,
    get_graph_schema,  # Added this
    run_cypher_query  # Replaced the separate read/write tools with this unified one
]

# ---------------------------
# 6. Agent
# ---------------------------
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt1,
    tools=tools
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True  # Helps if the LLM messes up tool formats
)

# ---------------------------
# 7. CLI Loop
# ---------------------------
print("\n🤖 Agent ready with Neo4j support!\n")
print("Tip: Ask 'What is the schema of the database?' to test the connection.\n")

while True:
    try:
        query = input(">> ")
        if query.strip().lower() in ["exit", "quit"]:
            print("Goodbye! 👋")
            break

        resp = agent_executor.invoke({"input": query})
        print("\nAI:", resp.get("output", ""))
        print("-" * 40)

    except KeyboardInterrupt:
        print("\nInterrupted.")
        break
    except Exception as e:
        print(f"Error: {e}")