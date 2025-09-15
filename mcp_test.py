from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import asyncio
import os
from tools import terminal_tool
# alias zap="/Applications/ZAP.app/Contents/Java/zap.sh"

load_dotenv()
gemini_key = os.getenv("GEMINI2_API_KEY")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=gemini_key)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a Cybersecurity expert assistant that will help find bugs. "
                   "Answer the query and use necessary tools. Wrap the output in the required format."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)


# noinspection PyTypeChecker
async def main():
    # ✅ No async with here
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

    tools = await client.get_tools()
    tools.append(terminal_tool)
    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=tools
    )
    # agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    while True:
        query = str(input("\nEnter Prompt (or type 'exit' to quit): "))
        if query.strip().lower() == "exit":
            print("Exiting... Goodbye! 👋")
            break

        try:
            resp = await agent_executor.ainvoke({"input": query})
            print("\n🛡️ Result:\n", resp["output"])
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
