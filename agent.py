import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from tools import add_purchase, get_purchases, search_products

load_dotenv()

@function_tool
def save_purchase(product: str, price: float, store: str):
    """Save a purchase to the user's purchase history."""
    return add_purchase(product, price, store)


@function_tool
def view_purchases():
    """View the user's previous purchases."""
    return get_purchases()


@function_tool
def find_products(query: str):
    """Search for real products and prices."""
    return search_products(query)


shopping_agent = Agent(
    name="Shopping Assistant",
    instructions="""
    You are a personal shopping assistant.

    You can save purchases and view the user's purchase history.

    When the user tells you about something they purchased, save it.
    When the user asks about their purchase history, view their purchases.

    Before recommending a product, view their purchases and use that history when it is relevant.

    Be concise and helpful.
    """,
    tools=[save_purchase, view_purchases, find_products],
)


async def main():
    result = await Runner.run(
        shopping_agent,
        "Find me Nike running shoes under $100.",
    )

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())