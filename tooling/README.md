create .env file 

add feilds:
MCP_FILESYSTEM_DIR=
GITHUB_TOKEN=
GEMINI_API_KEY=

install uv 

add dependencies
command: uv sync

activate virutal envs

run server:
uv run server.py

run client:
uv run client.py <path_to_server_script>
