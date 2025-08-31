
import os
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from typing import List
from tools import search_tool, wiki_tool, save_tool,codeql_tool

# Load API keys
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("ARSHAD_API_KEY")


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


# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash",
#                              google_api_key=api_key,
#
#                              )
# resp = llm.invoke("Sing a ballad of LangChain")
# print(resp)
#
# llm = ChatOpenAI(model="gpt-3.5-turbo-instruct",
#                  openai_api_key="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"
#                  )

print("Choose llm and it's model:")
print("1.Openai - gpt-4o-mini")
print("2.Gemini - gemini-1.5-flash")
print("3.Gemini - gemini-2.0-flash")
print("4.Gemini - gemini-2.5-flash")
print("5.Gemini - gemini-2.5-pro")
choice = int(input("Enter the preference: \n"))


def model1():
    print("Openai 4o mini ready to rock")
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=openai_key,
        base_url="https://models.github.ai/inference"
)


def model2():
    print("Gemini 1.5 Flash ready to rock 🤧")
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_key)


def model3():
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key)


def model4():
    print("Gemini 2.5 Flash ready to rock 🤧")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_key)


def model5():
    print("Gemini 2.5 Pro ready to rock 🤧")
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=gemini_key)


actions = {
    1: model1,
    2: model2,
    3: model3,
    4: model4,
    5: model5
}
# llm = actions.get(choice, model4)()
llm = ChatOpenAI(
    model="xai/grok-3",
    # model="gpt-4o-mini",
    api_key=openai_key,
    base_url="https://models.github.ai/inference",
)
parser = PydanticOutputParser(pydantic_object=ResearchResponse)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a Cybersecurity expert assistant that will help find bug from the given scenario.
            Answer the user query and use neccessary tools. 
            Wrap the output in this format and provide no other text\n{format_instructions} , drop the format if it is irrelevant to the prompt
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query} "),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

tools = [search_tool, wiki_tool, save_tool,codeql_tool]
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
