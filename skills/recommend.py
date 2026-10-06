from agents import Agent
from tools import find_products, view_purchases

recommend_agent = Agent(
    name="Recommendation",
    instructions="""
    Recommend products for the user's goal.

    You decide which tools this goal needs. You can use a tool more than once.
    Read their purchase history when it could help. Search for current products before you recommend one.
    Follow their budget, category, brand, and any request for something similar.

    If their history does not include the exact product they asked for, say so.
    Then use a related purchase, such as another item in the same kind of category, and say which purchase you used.
    Only recommend products returned by the search.
    For each one, say briefly why it fits.
    """,
    tools=[view_purchases, find_products],
)
