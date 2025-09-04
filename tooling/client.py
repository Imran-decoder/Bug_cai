import asyncio
import sys
import os
from typing import Optional, List, Type
from contextlib import AsyncExitStack

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# LangChain Imports
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")

# --- Pydantic Models for Tool Arguments ---
class FsListArgs(BaseModel):
    """Input model for the fs_list tool."""
    path: str = Field(description="The directory path to list contents of.", default=".")
class FsReadArgs(BaseModel):
    """Input model for the fs_read tool."""
    path: str = Field(description="The complete path to the file that needs to be read.")
class FsWriteArgs(BaseModel):
    """Input model for the fs_write tool."""
    path: str = Field(description="The path to the file where content will be written.")
    content: str = Field(description="The string content to write into the file.")
class FsDeleteArgs(BaseModel):
    """Input model for the fs_delete tool."""
    path: str = Field(description="The complete path of the file to be deleted.")
class LoadDataArgs(BaseModel):
    """Input model for the dataflow_load_data tool."""
    file_path: str = Field(description="The path to the CSV file to load.")
class QueryDataArgs(BaseModel):
    """Input model for the dataflow_query_data tool."""
    sql_query: str = Field(description="The SQL query to execute on the loaded data. The table is named 'data'.")
class CreateProjectArgs(BaseModel):
    """Input model for the dataflow_create_new_project tool."""
    project_name: str = Field(description="The name for the new project directory.")
class GhCreateRepoArgs(BaseModel):
    """Input model for the gh_create_repo tool."""
    repo_name: str = Field(description="The name for the new GitHub repository.")
    token: str = Field(description="A GitHub Personal Access Token.", default=os.getenv("GITHUB_TOKEN", ""))
class GhLinkRemoteArgs(BaseModel):
    """Input model for the gh_link_remote tool."""
    project_name: str = Field(description="The local project directory name.")
    remote_url: str = Field(description="The full URL of the remote GitHub repository.")
class GhPushArgs(BaseModel):
    """Input model for the gh_push tool."""
    project_name: str = Field(description="The name of the local project directory to push.")
    commit_message: Optional[str] = Field(description="An optional commit message for the changes.", default=None)
class GhPullArgs(BaseModel):
    """Input model for the gh_pull tool."""
    project_name: str = Field(description="The name of the local project directory to pull updates for.")

# ⭐️ NEW ARGS MODEL ⭐️
class GhCloneArgs(BaseModel):
    """Input model for the gh_clone tool."""
    repo_url: str = Field(description="The full URL of the remote Git repository to clone.")
    project_name: Optional[str] = Field(description="The optional name for the new local directory. If not provided, the repository name is used.", default=None)

# --- Custom BaseTool for MCP Integration ---
class MCPTool(BaseTool):
    name: str; description: str; args_schema: Type[BaseModel]; session: ClientSession
    def _run(self, *args, **kwargs): raise NotImplementedError("Sync not supported")
    async def _arun(self, **kwargs):
        try:
            result = await self.session.call_tool(self.name, kwargs)
            return str(result.content[0].text) if result.content else "Tool executed successfully."
        except Exception as e:
            return f"An error occurred executing tool '{self.name}': {e}"

# --- Agent Manager Class ---
class AgentManager:
    def __init__(self, llm, tools: List[BaseTool]):
        self.tools = tools
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that manages a data science workflow. You have access to filesystem tools, data querying tools, and GitHub integration tools. If a git push fails because the remote has diverged, you should use the git pull tool first to merge the changes before trying to push again."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm, self.tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    async def invoke(self, query: str) -> dict:
        return await self.executor.ainvoke({"query": query})

# --- Main MCP Client Class ---
class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.agent_manager: Optional[AgentManager] = None
    
    def _create_langchain_tools_from_mcp(self) -> List[BaseTool]:
        tool_to_args_map = {
            "fs_list": FsListArgs,
            "fs_read": FsReadArgs,
            "fs_write": FsWriteArgs,
            "fs_delete": FsDeleteArgs,
            "dataflow_load_data": LoadDataArgs,
            "dataflow_query_data": QueryDataArgs,
            "dataflow_create_new_project": CreateProjectArgs,
            "gh_create_repo": GhCreateRepoArgs,
            "gh_link_remote": GhLinkRemoteArgs,
            "gh_push": GhPushArgs,
            "gh_pull": GhPullArgs,
            "gh_clone": GhCloneArgs, # ⭐️ ADD NEW TOOL TO MAP ⭐️
        }
        langchain_tools = []
        for tool_name, args_schema in tool_to_args_map.items():
            new_tool = MCPTool(
                name=tool_name, description=args_schema.__doc__ or f"Tool: {tool_name}",
                args_schema=args_schema, session=self.session
            )
            langchain_tools.append(new_tool)
        return langchain_tools
    
    async def connect_to_server(self, server_script_path: str):
        command = sys.executable
        server_params = StdioServerParameters(command=command, args=[server_script_path])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        mcp_tools = self._create_langchain_tools_from_mcp()
        print("\n✅ Connected to MCP server.")
        print("🛠️  Available Tools:", [t.name for t in mcp_tools])
        llm = ChatOpenAI(
    model="xai/grok-3",
    # model="gpt-4o-mini",
    api_key=openai_key,
    base_url="https://models.github.ai/inference",
)
        self.agent_manager = AgentManager(llm=llm, tools=mcp_tools)
    
    async def chat_loop(self):
        if not self.agent_manager:
            print("Agent not initialized.")
            return
        print("\n🤖 LLM Agent is ready. Ask me anything!")
        print("   Type 'quit' to exit.\n")
        while True:
            try:
                query = input(">> ").strip()
                if query.lower() in ("quit", "exit"): break
                if not query: continue
                response = await self.agent_manager.invoke(query)
                print(f"\n✅ Agent Response:\n{response.get('output')}\n")
            except Exception as e:
                print(f"\nAn error occurred: {e}")
    
    async def cleanup(self):
        print("\nShutting down...")
        await self.exit_stack.aclose()

# --- Script Entry Point ---
async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())