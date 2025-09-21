import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def run_terminal_mcp():
    # Launch an MCP client over stdio
    async with stdio_client() as (read, write):
        session = ClientSession(read, write)
        await session.start()

        print("🚀 Terminal MCP Client started. Type 'exit' to quit.")

        while True:
            user_input = input(">> ")
            if user_input.strip().lower() in {"exit", "quit"}:
                break

            # Example: send user input as a request to the MCP server
            try:
                response = await session.send({"role": "user", "content": user_input})
                print("MCP Response:", response)
            except Exception as e:
                print("❌ Error:", e)

if __name__ == "__main__":
    asyncio.run(run_terminal_mcp())
