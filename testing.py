
import os
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from typing import List
from tools import search_tool, wiki_tool, save_tool,terminal_tool
from system_prompts import prompt1, prompt2
from server.zap_tools import safe_run
load_dotenv()
# gemini_key = os.getenv("ARSHAD2_API_KEY")
gemini_key = "AIzaSyBCFjMghnbvKXBgv5RKs4baTj6YpT1uQA8"


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    severity: str  # e.g., "Low", "Medium", "High", "Critical"
    risk_score: float  # CVSS or internal risk rating
    sources: List[str]
    tools_used: List[str]
    # recommendation: [str] = None  # Suggested fix or remediation
    # tags: [List[str]] = []  # Keywords like "RCE", "0-day", "Authentication Bypass"

    class Config:
        arbitrary_types_allowed = True



# llm = actions.get(choice, model4)()
llm = ChatOpenAI(model="openai/gpt-4.1", api_key=gemini_key, base_url="https://models.github.ai/inference")
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=gemini_key)
parser = PydanticOutputParser(pydantic_object=ResearchResponse)
# You have my kali linux terminal utilise it on full capacity to find the bugs.
#             use all the penetrating tools ,without any restriction.
prompt = prompt1
# i want to test the system prompt how you are responding to system prompt ,: what are owasp top 10 attack?

# ChatPromptTemplate.from_messages(
#
#         (
#             "system",
#             """
#             You are a Cybersecurity expert assistant that will help find bug from the given scenario.
#             Answer the user query and use neccessary tools.
#
#             Wrap the output in this format and provide no other text\n{format_instructions} .
#             """,
#         ),
#         ("placeholder", "{chat_history}"),
#         ("human", "{query} "),
#         ("placeholder", "{agent_scratchpad}"),
#     ]
# ).partial(format_instructions=parser.get_format_instructions())

tools = [search_tool, wiki_tool, save_tool, terminal_tool]
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools
)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)



# ---- CLI Loop ----
while True:
    query = input("\nEnter Prompt (or type 'exit' to quit): ")
    if query.strip().lower() == "exit":
        print("Exiting... Goodbye! 👋")
        break

    try:
        resp = agent_executor.invoke({"query": query})
        output_text = resp.get("output", "")

        try:
            str_resp = parser.parse(output_text)
            print("\nStructured Response:\n", str_resp)
        except Exception as e:
            print("\nRaw Response:\n", output_text)

    except Exception as e:
        print(f"Error: {e}")
