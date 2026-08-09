from dotenv import load_dotenv
from openai import OpenAI
import json

from tools import search_tool, wiki_tool, save_tool

load_dotenv()
client = OpenAI()

TOOLS = {
    "search_tool": search_tool,
    "wiki_tool": wiki_tool,
    "save_tool": save_tool,
}

SYSTEM_PROMPT = """
You are a research assistant.

You can use tools:
- search_tool(query)
- wiki_tool(query)
- save_tool(text)

If you need a tool, call it.
Otherwise answer directly.
"""

def run_agent(question: str):
    # Step 1: Ask the model what to do
    response = client.responses.create(
        model="gpt-4.1-mini",
        tools=[
            {
                "type": "function",
                "name": "search_tool",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                },
            },
            {
                "type": "function",
                "name": "wiki_tool",
                "description": "Wikipedia lookup",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                },
            },
            {
                "type": "function",
                "name": "save_tool",
                "description": "Save notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
            },
        ],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )

    # Step 2: Check whether the model called a tool
    tool_call = None

    for output in response.output:
        if output.type == "function_call":
            tool_call = output
            break

    # No tool needed
    if tool_call is None:
        return response.output_text

    # Step 3: Run the tool ourselves
    tool_name = tool_call.name
    tool_args = json.loads(tool_call.arguments)

    tool_result = TOOLS[tool_name](**tool_args)

    # Step 4: Give the tool result back to the model
    second_response = client.responses.create(
        model="gpt-4.1-mini",
        tools=[
            {
                "type": "function",
                "name": "search_tool",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                },
            },
            {
                "type": "function",
                "name": "wiki_tool",
                "description": "Wikipedia lookup",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                },
            },
            {
                "type": "function",
                "name": "save_tool",
                "description": "Save notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
            },
        ],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": str(tool_result),
            },
        ],
    )

    return second_response.output_text
