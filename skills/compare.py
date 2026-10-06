from agents import Agent
from tools import find_products, view_purchases

compare_agent = Agent(
    name="Comparison",
    instructions="""
    Compare products and choose the best one for this user.

    You decide which tools this goal needs. You can use a tool more than once.
    Read their purchase history when it could change which option is best.
    Search when you need current prices or missing products.
    Explain the important differences, then recommend one option and say why.
    Only use products returned by the search or already named in the conversation.
    """,
    tools=[view_purchases, find_products],
)
