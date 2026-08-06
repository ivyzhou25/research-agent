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
    # step 1: ask model
    response = client.responses.create(
        model="gpt-4.1-mini",
        tools=[
            {
                "type": "function",
                "name": "search_tool",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}}
                },
            },
            {
                "type": "function",
                "name": "wiki_tool",
                "description": "Wikipedia lookup",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}}
                },
            },
            {
                "type": "function",
                "name": "save_tool",
                "description": "Save notes",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}}
                },
            },
        ],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    output = response.output[0]

    # step 2: check if tool was called
    if output.type == "function_call":
        tool_name = output.name
        tool_args = json.loads(output.arguments)

        # run the tool in Python
        tool_result = TOOLS[tool_name](**tool_args)

        # Step 3: send tool result back to model
        second_response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": str(tool_result),
                },
            ],
        )
        return second_response.output_text

    # no tool used -> direct answer
    return response.output_text