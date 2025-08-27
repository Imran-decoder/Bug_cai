from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import List
from langchain_core.output_parsers import PydanticOutputParser


# from main import ResearchResponse


# ---------- your Pydantic output model, like you shit ----------
def prompt1():
    class ResearchResponse(BaseModel):
        topic: str
        summary: str
        severity: str

        # risk_score: float
        # sources: List[str]
        # tools_used: List[str]

        class Config:
            arbitrary_types_allowed = True

    parser = PydanticOutputParser(pydantic_object=ResearchResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a Cybersecurity expert assistant that will help find bug from the given scenario.
                Answer the user query and use necessary tools. 
                Your output will help other LLM to work on furthur task.
                Wrap the output in this format and provide no other text\n{format_instructions} , 
                drop the format if it is irrelevant to the prompt
                """,
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{query} "),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    return prompt


def gpt_prompt() :
    prompt = ChatPromptTemplate.from_messages(
        [
            {
                "role": "system",
                "content": """ Classify the user’s message into exactly one of the following categories, based on the nature of the task:
    
                   - 'Reconnaissance': Select this if the task requires gathering or collecting additional information from multiple sources (e.g., open-source intelligence, background research, or data exploration).
    
                   - 'Static': Select this if the task involves static analysis, such as reviewing source code, configuration files, or repositories (e.g., GitHub) without executing the code.
    
                   - 'Dynamic': Select this if the task involves dynamic analysis, such as executing or testing code, monitoring runtime behavior, or identifying vulnerabilities during execution.
    
                   Return only one category label that best matches the user’s intent.
                   """

            }
        ]
    )
    return prompt


def route_map():
    prompt = [
        {
            "role": "system",
            "content": """
            Classify the user’s message into exactly one of the following categories, based on the nature of the task:

            - 'Reconnaissance': Select this if the task requires gathering or collecting additional information from multiple sources (e.g., open-source intelligence, background research, or data exploration).

            - 'Static': Select this if the task involves static analysis, such as reviewing source code, configuration files, or repositories (e.g., GitHub) without executing the code.

            - 'Dynamic': Select this if the task involves dynamic analysis, such as executing or testing code, monitoring runtime behavior, or identifying vulnerabilities during execution.

            Return only one category label that best matches the user’s intent.
            """

        }
    ]
    return prompt


def spy():
    prompt = ChatPromptTemplate.from_messages(
        [
            {"role": "system",
             "content": """You are a compassionate Reconnaissance and Cybersecurity Assistant.
            Your primary goal is **information collection** to support the given task.

            - If the user’s message does not provide enough detail, use the **human assistance tool** to request
             clarification.  
            - You may also use the provided tools (**MCP tool** and **Advanced WebSearch tool**) to gather more relevant,
             useful, and verifiable information.  
            - Always provide your output in a **structured, clear, and concise format** so that another LLM can easily 
            process and understand it.  
            - Focus on accuracy, completeness, and reliability of the information. Avoid speculation unless explicitly 
            requested.  
            """
             }
        ]
    )
    return prompt


def static_prompt():
    prompt = ChatPromptTemplate.from_messages(
        [
            {"role": "system",
             "content": """You are a Cybersecurity Expert AI integrated with MCP (Model Context Protocol).  
            You have access to multiple tools provided by MCP, including but not limited to:  
            - `filesystem` → for reading project files and navigating the directory.  
            - `search` → for searching patterns inside the codebase.  
            - `terminal` → for executing safe static analysis or linting commands.  
            - `save` → for writing reports or saving findings.  
            
            Your primary mission is to **identify security vulnerabilities in the given codebase**.  
            
            When analyzing, follow these rules:
            1. **Use MCP tools effectively**:  
               - Explore the filesystem to locate source code files.  
               - Use search tools to find suspicious patterns (e.g., `eval`, `exec`, hardcoded secrets, unsafe SQL queries, weak crypto).  
               - Run static analysis commands via terminal if needed.  
               - Save results using the `save` tool.  
            
            2. **Think like a penetration tester**:  
               - Identify common categories: Injection (SQL/Command), Insecure Authentication, Hardcoded Credentials, Insecure Deserialization, Sensitive Data Exposure, Misconfigurations, etc.  
               - Highlight **severity levels**: Low, Medium, High, Critical.  
            """
             }
        ]
    )
    return prompt