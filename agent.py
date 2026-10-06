import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner
from skills import (
    compare_products,
    discover_products,
    find_alternatives,
    recommend_products,
)
from tools import find_products, save_purchase, view_purchases

load_dotenv()

shopping_agent = Agent(
    name="Shopping Assistant",
    instructions="""
    You are a personal shopping assistant.

    You decide how to handle each request. Do not follow one fixed sequence.

    Use a tool for one concrete action.
    Use view_purchases when the user asks what they bought.
    Use save_purchase when they tell you about a new purchase.
    Use find_products for a quick product search.

    Use a skill when the goal needs judgment and may need more than one lookup.
    Use recommend_products for a recommendation, especially one based on their history.
    Use find_alternatives for something similar or cheaper.
    Use compare_products when they want options compared.
    Use discover_products to find products in a category or under a budget.

    For a follow-up about products already discussed, use the conversation.
    Call a tool or skill only when you need new information.

    Be concise and helpful.
    """,
    tools=[
        save_purchase,
        view_purchases,
        find_products,
        recommend_products,
        compare_products,
        find_alternatives,
        discover_products,
    ],
)


async def main():
    conversation = []

    print("Shopping assistant")
    print("Ask about a product, a comparison, or something based on your past purchases.")
    print("Type quit to stop.")
    print()

    while True:
        request = input("What are you looking for? ").strip()

        if request.lower() in {"quit", "exit", "q"}:
            break

        if not request:
            continue

        conversation.append({"role": "user", "content": request})

        result = await Runner.run(
            shopping_agent,
            conversation,
        )

        print(result.final_output)
        print()

        conversation = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())
