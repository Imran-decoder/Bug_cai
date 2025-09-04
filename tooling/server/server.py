from typing import Optional
import httpx
import pandas as pd
import pandasql as psql
import os
import subprocess
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("server")

load_dotenv()


class DataFlowSession:
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.working_dir = os.environ.get("MCP_FILESYSTEM_DIR", None)
        if not self.working_dir:
            raise RuntimeError("MCP_FILESYSTEM_DIR not set!")
        os.makedirs(self.working_dir, exist_ok=True)

    # ... (load_data, query_data, create_new_project, and fs methods remain the same) ...
    async def load_data(self, file_path: str) -> str:
        try:
            abs_path = os.path.join(self.working_dir, file_path)
            self.data = pd.read_csv(abs_path)
            return f"Data loaded from {abs_path}"
        except Exception as e:
            return f"Error loading data: {str(e)}"

    async def query_data(self, query: str) -> str:
        if self.data is None:
            return "No data loaded."
        try:
            result = psql.sqldf(query, {"data": self.data})
            return result.to_string()
        except Exception as e:
            return f"Error executing query: {str(e)}"

    async def create_new_project(self, project_name: str) -> str:
        try:
            project_dir = os.path.join(self.working_dir, project_name)
            if os.path.exists(project_dir):
                raise ValueError(f"Project '{project_name}' already exists.")
            os.mkdir(project_dir)
            subprocess.run(["uv", "init"], cwd=project_dir, check=True, capture_output=True)
            subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
            os.mkdir(os.path.join(project_dir, "data"))
            with open(os.path.join(project_dir, ".gitignore"), "w") as f:
                f.write(".venv/\n")
            subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True
            )
            return f"Project '{project_name}' created at {project_dir}"
        except Exception as e:
            return f"Error creating project: {str(e)}"

    async def fs_list(self, path: str = ".") -> list[str]:
        abs_path = os.path.join(self.working_dir, path)
        return os.listdir(abs_path)

    async def fs_read(self, path: str) -> str:
        abs_path = os.path.join(self.working_dir, path)
        with open(abs_path, "r") as f:
            return f.read()

    async def fs_write(self, path: str, content: str) -> str:
        abs_path = os.path.join(self.working_dir, path)
        with open(abs_path, "w") as f:
            f.write(content)
        return f"Wrote to {abs_path}"

    async def fs_delete(self, path: str) -> str:
        abs_path = os.path.join(self.working_dir, path)
        os.remove(abs_path)
        return f"Deleted {abs_path}"

    async def gh_create_repo(self, repo_name: str, token: str) -> str:
        headers = {"Authorization": f"token {token}"}
        url = "https://api.github.com/user/repos"
        payload = {"name": repo_name, "private": False}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 201:
                return f"GitHub repo '{repo_name}' created."
            return f"Error creating GitHub repo: {resp.text}"

    async def gh_link_remote(self, project_name: str, remote_url: str) -> str:
        project_dir = os.path.join(self.working_dir, project_name)
        try:
            subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=project_dir, check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=project_dir, check=True,
            )
            return f"Updated remote 'origin' to {remote_url}"
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=project_dir, check=True,
            )
            return f"Added remote 'origin' -> {remote_url}"

    # ⭐️ NEW METHOD ⭐️
    async def gh_clone(self, repo_url: str, project_name: Optional[str] = None) -> str:
        """Clones a git repository into the working directory."""
        try:
            repo_name_from_url = repo_url.split('/')[-1].replace('.git', '')
            target_dir_name = project_name or repo_name_from_url
            target_dir_path = os.path.join(self.working_dir, target_dir_name)

            if os.path.exists(target_dir_path):
                return f"Error: Directory '{target_dir_name}' already exists."

            command = ["git", "clone", repo_url]
            if project_name:
                command.append(project_name)

            result = subprocess.run(
                command, cwd=self.working_dir, check=True, capture_output=True, text=True
            )
            # stderr often contains the progress info for git clone
            return f"Successfully cloned repository into '{target_dir_name}'.\n{result.stderr}"
        except subprocess.CalledProcessError as e:
            return f"Git clone failed: {e.stderr}"
        except Exception as e:
            return f"An unexpected error occurred during clone: {str(e)}"

    async def gh_pull(self, project_name: str) -> str:
        project_dir = os.path.join(self.working_dir, project_name)
        try:
            pull_result = subprocess.run(
                ["git", "pull", "origin", "main", "--allow-unrelated-histories"],
                cwd=project_dir, check=True, capture_output=True, text=True
            )
            return f"Successfully pulled changes for '{project_name}'.\n{pull_result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Git pull failed for '{project_name}': {e.stderr}"

    async def gh_push(self, project_name: str, commit_message: Optional[str] = None) -> str:
        project_dir = os.path.join(self.working_dir, project_name)
        if commit_message is None:
            commit_message = "Automated commit of project updates"
        try:
            subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=project_dir, capture_output=True, text=True,
            )
            if commit_result.returncode == 0:
                commit_status = "Changes committed."
            elif "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                commit_status = "No new changes to commit."
            else:
                raise subprocess.CalledProcessError(
                    commit_result.returncode, cmd=commit_result.args, output=commit_result.stdout, stderr=commit_result.stderr
                )
            subprocess.run(["git", "branch", "-M", "main"], cwd=project_dir, check=True)
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=project_dir, check=True, capture_output=True, text=True,
            )
            return f"{commit_status} Successfully pushed '{project_name}' to GitHub main branch."
        except subprocess.CalledProcessError as e:
            return f"Git operation failed: {e.stderr}"

session = DataFlowSession()

# ... (all other tool definitions remain the same) ...
@mcp.tool()
async def dataflow_load_data(file_path: str) -> str: return await session.load_data(file_path)
@mcp.tool()
async def dataflow_query_data(sql_query: str) -> str: return await session.query_data(sql_query)
@mcp.tool()
async def dataflow_create_new_project(project_name: str) -> str: return await session.create_new_project(project_name)
@mcp.tool()
async def fs_list(path: str = ".") -> list[str]: return await session.fs_list(path)
@mcp.tool()
async def fs_read(path: str) -> str: return await session.fs_read(path)
@mcp.tool()
async def fs_write(path: str, content: str) -> str: return await session.fs_write(path, content)
@mcp.tool()
async def fs_delete(path: str) -> str: return await session.fs_delete(path)
@mcp.tool()
async def gh_create_repo(repo_name: str, token: str) -> str: return await session.gh_create_repo(repo_name, token)
@mcp.tool()
async def gh_link_remote(project_name: str, remote_url: str) -> str: return await session.gh_link_remote(project_name, remote_url)

# ⭐️ NEW TOOL ⭐️
@mcp.tool()
async def gh_clone(repo_url: str, project_name: Optional[str] = None) -> str:
    """Clones a remote git repository into a new local project directory."""
    return await session.gh_clone(repo_url, project_name)

@mcp.tool()
async def gh_pull(project_name: str) -> str: return await session.gh_pull(project_name)
@mcp.tool()
async def gh_push(project_name: str, commit_message: Optional[str] = None) -> str: return await session.gh_push(project_name, commit_message)

if __name__ == "__main__":
    mcp.run(transport="stdio")