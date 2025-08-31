import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="langchain_community.utilities.duckduckgo_search")
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime
from langgraph.types import Command, interrupt
from langchain_core.tools import tool
from ddgs import DDGS
import subprocess


# from langchain.tools import Tool


@tool
def run_codeql(query: str, db_path: str = "my-database") -> str:
    """
    Runs a CodeQL query against a given database.
    Assumes CodeQL CLI is installed and database is already created.
    """
    try:
        result = subprocess.run(
            ["codeql", "query", "run", query, "--database", db_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running CodeQL: {e.stderr}"


codeql_tool = Tool(
    name="codeql_query",
    func=run_codeql,
    description=(
        "Run a CodeQL query against the codebase database. "
        "Input should be the path to a .ql query file."
    ),
)


@tool
def human_assistant(query: str) -> str:
    """Tool that asks the human a question and waits for their answer."""
    human_resp = interrupt({"query": query})

    # Safely handle dicts returned by interrupt
    if isinstance(human_resp, dict):
        # Prefer the 'data' field if present
        if "data" in human_resp:
            return str(human_resp["data"])
        else:
            return str(human_resp)  # fallback

    # Otherwise just stringify
    return str(human_resp)


def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)

    return f"Data successfully saved to {filename}"


save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured research data to a text file.",
)


def duckduckgo_search(query: str) -> str:
    with DDGS() as ddgs:
        results = [r["body"] for r in ddgs.text(query, max_results=5)]
        return "\n".join(results)


search_tool = Tool(
    name="search",
    func=duckduckgo_search,
    description="Search the web for information",
)

api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)
